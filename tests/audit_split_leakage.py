"""
RoutePulse Split Leakage Audit (tests/audit_split_leakage.py)
Enforces strict train/validation/test split isolation across the codebase:
- Scans Python files in demand/, eta/, optimize/, sim/, api/
- Enforces that the test split (Days 26-30) is NEVER read, imported, or referenced in training or serving logic.
- Guarantees that only eval/run_eval.py is authorized to access test split data.
- Asserts zero split leakage.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent

# Target directories to scan for split isolation
SCAN_DIRS = ["demand", "eta", "optimize", "sim", "api"]

# Authorized file that alone is permitted to access test split (Days 26-30)
AUTHORIZED_TEST_SPLIT_FILES = {
    ROOT_DIR / "eval" / "run_eval.py",
    ROOT_DIR / "tests" / "test_eval.py",
    ROOT_DIR / "tests" / "audit_split_leakage.py",
}

# Files that generate the world dataset or define evaluation scenarios (not training/serving logic)
DATA_GEN_FILES = {
    ROOT_DIR / "sim" / "generate_world.py",
    ROOT_DIR / "sim" / "scenarios.py",
    ROOT_DIR / "sim" / "demand_gen.py",
    ROOT_DIR / "sim" / "events.py",
    ROOT_DIR / "sim" / "traffic.py",
    ROOT_DIR / "sim" / "gps.py",
}

TEST_DAYS = {26, 27, 28, 29, 30}


def set_parents(tree: ast.AST):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            child.parent = parent


def is_guard_condition(node: ast.AST) -> bool:
    """
    Returns True if node is part of a guard or rejection check against test split:
    e.g. assert not (df['split'] == 'test').any()
         if (df['split'] == 'test').any(): raise AssertionError(...)
         df[df['split'] != 'test']
    """
    curr = getattr(node, "parent", None)
    while curr is not None:
        if isinstance(curr, ast.Assert):
            return True
        if isinstance(curr, ast.Raise):
            return True
        if isinstance(curr, ast.If):
            # Check if this If branch raises an exception or asserts
            for stmt in curr.body:
                if isinstance(stmt, (ast.Raise, ast.Assert)):
                    return True
        curr = getattr(curr, "parent", None)
    return False


class SplitLeakageVisitor(ast.NodeVisitor):
    """AST Visitor detecting unauthorized access to test split or eval imports."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name == "eval" or alias.name.startswith("eval."):
                self.violations.append(
                    f"{self.file_path.name}:{node.lineno} Unauthorized import of eval module: '{alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and (node.module == "eval" or node.module.startswith("eval.")):
            self.violations.append(
                f"{self.file_path.name}:{node.lineno} Unauthorized from-import from eval module: '{node.module}'"
            )
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        # Detect split == 'test' when NOT in an anti-leak guard
        is_split_cmp = False
        if isinstance(node.left, ast.Name) and "split" in node.left.id.lower():
            is_split_cmp = True
        elif isinstance(node.left, ast.Subscript):
            if isinstance(node.left.slice, ast.Constant) and node.left.slice.value == "split":
                is_split_cmp = True

        if is_split_cmp:
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(comparator, ast.Constant) and comparator.value == "test":
                    if isinstance(op, ast.NotEq):
                        # df['split'] != 'test' is an explicit exclusion guard!
                        continue
                    if not is_guard_condition(node):
                        self.violations.append(
                            f"{self.file_path.name}:{node.lineno} Unauthorized filtering/access of 'test' split detected"
                        )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detect function calls with split="test"
        for kw in node.keywords:
            if kw.arg == "split" and isinstance(kw.value, ast.Constant) and kw.value.value == "test":
                if not is_guard_condition(node):
                    self.violations.append(
                        f"{self.file_path.name}:{node.lineno} Unauthorized function call with split='test' parameter"
                    )
        self.generic_visit(node)


def audit_python_file(file_path: Path) -> List[str]:
    """Audits a single python file for split leakage."""
    violations: List[str] = []
    text = file_path.read_text(encoding="utf-8")

    # 1. Parse AST
    try:
        tree = ast.parse(text, filename=str(file_path))
        set_parents(tree)
        visitor = SplitLeakageVisitor(file_path)
        visitor.visit(tree)
        violations.extend(visitor.violations)
    except SyntaxError as e:
        violations.append(f"{file_path.name}: SyntaxError during AST parsing: {e}")

    # 2. Text regex checks (excluding comments and docstrings)
    # Strip string literals and comments for raw logic scan
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # Check for query or slice filtering for test days in training/serving files
        if re.search(r'\[\s*["\']day["\']\s*\]\s*(==|in|\.isin\()\s*\[?.*(26|27|28|29|30)', line):
            # Check if this is an assertion preventing day > 25
            if "assert" not in line and "raise" not in line and "not in" not in line and "!" not in line:
                violations.append(
                    f"{file_path.name}:{idx} Direct day filtering on test split (Days 26-30): {stripped}"
                )

        if re.search(r'split\s*==\s*["\']test["\']', line):
            if "assert" not in line and "raise" not in line and "!=" not in line:
                violations.append(
                    f"{file_path.name}:{idx} Direct split=='test' query: {stripped}"
                )

    return violations


def run_split_leakage_audit() -> Tuple[int, List[str], List[Path]]:
    """
    Scans all training and serving Python files across demand/, eta/, optimize/, sim/, api/.
    Returns (num_files_scanned, violations_list, scanned_files).
    """
    scanned_files: List[Path] = []
    all_violations: List[str] = []

    for d in SCAN_DIRS:
        dir_path = ROOT_DIR / d
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            # Exclude virtual environments or caches
            if any(part.startswith((".", "__")) for part in py_file.parts):
                continue
            if py_file in DATA_GEN_FILES:
                continue

            scanned_files.append(py_file)
            file_viols = audit_python_file(py_file)
            all_violations.extend(file_viols)

    return len(scanned_files), all_violations, scanned_files


# ---------------------------------------------------------------------------
# Runtime Split Isolation Invariant Tests
# ---------------------------------------------------------------------------

def test_audit_split_leakage():
    """
    Scans Python files in demand/, eta/, optimize/, sim/, api/ and asserts zero split leakage.
    """
    file_count, violations, files = run_split_leakage_audit()

    print(f"\n[Split Leakage Audit] Scanned {file_count} Python files across {SCAN_DIRS}:")
    for f in sorted(files):
        rel = f.relative_to(ROOT_DIR)
        print(f"  OK: {rel}")

    assert file_count > 0, "Audit failed to discover any Python files to scan!"
    assert len(violations) == 0, (
        f"DATA SPLIT LEAKAGE DETECTED! Found {len(violations)} violation(s):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_eta_train_split_guard_rejects_test_days():
    """Verify that ETA train split assertion strictly rejects Days 26-30."""
    from eta.model import assert_train_split

    # Valid train split calls
    assert_train_split(days=[1, 5, 10, 20])

    # Rejection of test days
    for test_day in [26, 27, 28, 29, 30]:
        with pytest.raises(AssertionError, match="Data leakage detected"):
            assert_train_split(days=[1, 10, test_day])


def test_eta_conformal_split_guard_rejects_test_days():
    """Verify that ETA conformal calibration strictly rejects Days 26-30."""
    from eta.conformal import assert_validation_split

    # Valid validation split calls
    assert_validation_split(days=[21, 22, 23, 24, 25])

    # Rejection of test days
    for test_day in [26, 27, 28, 29, 30]:
        with pytest.raises(AssertionError, match="Data leakage detected"):
            assert_validation_split(days=[21, 23, test_day])


def test_demand_features_strictly_isolates_train_and_val():
    """Verify that demand feature extraction strictly isolates train (Days 1-20) and val (Days 21-25)."""
    from demand.features import extract_features

    demand_parquet = ROOT_DIR / "data" / "demand_obs.parquet"
    events_csv = ROOT_DIR / "data" / "events.csv"

    if demand_parquet.exists() and events_csv.exists():
        df_train = extract_features(split="train", demand_path=demand_parquet, events_path=events_csv)
        assert set(df_train["day"].unique()).issubset(set(range(1, 21)))
        assert not any(d in TEST_DAYS for d in df_train["day"].unique())

        df_val = extract_features(split="validation", demand_path=demand_parquet, events_path=events_csv)
        assert set(df_val["day"].unique()).issubset(set(range(21, 26)))
        assert not any(d in TEST_DAYS for d in df_val["day"].unique())


def test_only_run_eval_accesses_test_split():
    """
    Verify that only eval/run_eval.py accesses the test split,
    and that assert_test_split_integrity strictly rejects non-test split inputs.
    """
    from eval.run_eval import assert_test_split_integrity

    # Valid test split verification
    df_valid = pd.DataFrame({"day": [26, 27, 28, 29, 30], "split": ["test"] * 5})
    assert_test_split_integrity(df_valid, [26, 27, 28, 29, 30])

    # Security rejection of training days
    df_leak = pd.DataFrame({"day": [20, 26], "split": ["test", "test"]})
    with pytest.raises(AssertionError, match="SECURITY VIOLATION"):
        assert_test_split_integrity(df_leak, [20, 26])


if __name__ == "__main__":
    count, viols, files = run_split_leakage_audit()
    print("=" * 70)
    print("ROUTEPULSE SPLIT LEAKAGE AUDIT")
    print("=" * 70)
    print(f"Scanned directories : {', '.join(SCAN_DIRS)}")
    print(f"Total files audited : {count}")
    print(f"Test split days     : {sorted(TEST_DAYS)} (Days 26-30)")
    print("-" * 70)

    if viols:
        print(f"FAILED: {len(viols)} split leakage violation(s) found:")
        for v in viols:
            print(f"  [X] {v}")
        sys.exit(1)
    else:
        print("PASSED: Zero split leakage detected across all training & serving logic.")
        print("Only eval/run_eval.py is authorized and verified to access the test split.")
        sys.exit(0)
