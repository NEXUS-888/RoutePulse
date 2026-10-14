"""
RoutePulse Independent Hard-Constraint Validator
Pure functional validator ensuring plan feasibility under real-world constraints.
Does NOT import any optimizer code.
Section 8.6 implementation of constraints H1..H12 and soft checks A1, A4, A6.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from core.schemas import (
    Plan,
    Vehicle,
    ServiceRules,
    Violation,
    PlanValidationResponse,
)
from validate.constraints import (
    normalize_plan,
    normalize_fleet,
    normalize_rules,
    check_h1,
    check_h2,
    check_h3,
    check_h4,
    check_h5,
    check_h6,
    check_h7,
    check_h8,
    check_h9,
    check_h10,
    check_h11,
    check_h12,
    check_a1,
    check_a4,
    check_a6,
)


def validate(
    plan: Union[Plan, Dict[str, Any]],
    fleet: Optional[Union[Sequence[Union[Vehicle, Dict[str, Any]]], Dict[str, Union[Vehicle, Dict[str, Any]]]]] = None,
    rules: Optional[Union[ServiceRules, Dict[str, Any]]] = None,
    travel_time_model: Any = None,
    **kwargs: Any,
) -> List[Violation]:
    """
    Validate a transport plan against all published hard constraints (H1..H12)
    and evaluate soft service violations (A1, A4, A6).

    Pure function: does not modify inputs and does not depend on optimizer code.

    Parameters
    ----------
    plan : Plan or dict
        Operating plan with trips and vehicle blocks.
    fleet : list/dict of Vehicle, optional
        Available vehicle fleet. If None, default network fleet is loaded.
    rules : ServiceRules or dict, optional
        Service constraints and thresholds. Defaults to ServiceRules().
    travel_time_model : Any, optional
        Travel time or deadhead prediction model / callable.
    **kwargs : Any
        Additional context such as baseline_plan, p80_loads, or transfers.

    Returns
    -------
    list[Violation]
        All detected violations with code, severity ('hard' or 'soft'), entity, time, and detail.
    """
    p = normalize_plan(plan)
    fl = normalize_fleet(fleet)
    r = normalize_rules(rules)
    context = dict(kwargs)

    violations: List[Violation] = []

    # Hard Constraints H1..H12
    violations.extend(check_h1(p, fl, r, context))
    violations.extend(check_h2(p, fl, r, context))
    violations.extend(check_h3(p, fl, r, context))
    violations.extend(check_h4(p, fl, r, context, travel_time_model=travel_time_model))
    violations.extend(check_h5(p, fl, r, context))
    violations.extend(check_h6(p, fl, r, context))
    violations.extend(check_h7(p, fl, r, context))
    violations.extend(check_h8(p, fl, r, context, baseline_plan=kwargs.get("baseline_plan")))
    violations.extend(check_h9(p, fl, r, context))
    violations.extend(check_h10(p, fl, r, context))
    violations.extend(check_h11(p, fl, r, context, travel_time_model=travel_time_model))
    violations.extend(check_h12(p, fl, r, context))

    # Soft Alerts / Checks (severity='soft')
    violations.extend(check_a1(p, fl, r, context))
    violations.extend(check_a4(p, fl, r, context))
    violations.extend(check_a6(p, fl, r, context))

    return violations


def validate_plan_response(
    plan: Union[Plan, Dict[str, Any]],
    fleet: Optional[Union[Sequence[Union[Vehicle, Dict[str, Any]]], Dict[str, Union[Vehicle, Dict[str, Any]]]]] = None,
    rules: Optional[Union[ServiceRules, Dict[str, Any]]] = None,
    travel_time_model: Any = None,
    **kwargs: Any,
) -> PlanValidationResponse:
    """
    Validate plan and format as standard PlanValidationResponse.
    """
    violations = validate(plan, fleet, rules, travel_time_model, **kwargs)
    hard_count = sum(1 for v in violations if v.severity == "hard")
    soft_count = sum(1 for v in violations if v.severity == "soft")
    return PlanValidationResponse(
        is_valid=(hard_count == 0),
        hard_violations_count=hard_count,
        soft_violations_count=soft_count,
        violations=violations,
    )


def is_valid_plan(
    plan: Union[Plan, Dict[str, Any]],
    fleet: Optional[Union[Sequence[Union[Vehicle, Dict[str, Any]]], Dict[str, Union[Vehicle, Dict[str, Any]]]]] = None,
    rules: Optional[Union[ServiceRules, Dict[str, Any]]] = None,
    travel_time_model: Any = None,
    **kwargs: Any,
) -> bool:
    """Return True if plan has zero hard violations."""
    violations = validate(plan, fleet, rules, travel_time_model, **kwargs)
    return not any(v.severity == "hard" for v in violations)


def get_hard_violations(
    plan: Union[Plan, Dict[str, Any]],
    fleet: Optional[Union[Sequence[Union[Vehicle, Dict[str, Any]]], Dict[str, Union[Vehicle, Dict[str, Any]]]]] = None,
    rules: Optional[Union[ServiceRules, Dict[str, Any]]] = None,
    travel_time_model: Any = None,
    **kwargs: Any,
) -> List[Violation]:
    """Filter and return only hard violations (H1..H12)."""
    return [v for v in validate(plan, fleet, rules, travel_time_model, **kwargs) if v.severity == "hard"]


def get_soft_violations(
    plan: Union[Plan, Dict[str, Any]],
    fleet: Optional[Union[Sequence[Union[Vehicle, Dict[str, Any]]], Dict[str, Union[Vehicle, Dict[str, Any]]]]] = None,
    rules: Optional[Union[ServiceRules, Dict[str, Any]]] = None,
    travel_time_model: Any = None,
    **kwargs: Any,
) -> List[Violation]:
    """Filter and return only soft violations (A1, A4, A6)."""
    return [v for v in validate(plan, fleet, rules, travel_time_model, **kwargs) if v.severity == "soft"]
