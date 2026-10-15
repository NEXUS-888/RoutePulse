import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { MOCK_EVAL_RESULTS } from '../fixtures/richData';
import type { EvalHeadline } from '../types';

// The bundled fixture is a copy of results/results.json's headline, so offline and live agree.
const FALLBACK = MOCK_EVAL_RESULTS.headline as EvalHeadline;

let cached: EvalHeadline | null = null;
let inflight: Promise<void> | null = null;

/**
 * Headline evaluation numbers (wait / left-behind / missed-connection reductions, ETA error, violations).
 * Starts from the bundled measured fixture and upgrades to the live API value when available.
 */
export function useEvalHeadline(): EvalHeadline {
  const [headline, setHeadline] = useState<EvalHeadline>(cached ?? FALLBACK);

  useEffect(() => {
    if (cached) return;
    inflight ??= api
      .getEvalResults()
      .then(res => {
        if (res.data.headline) cached = res.data.headline;
      })
      .catch(() => undefined);
    inflight.then(() => {
      if (cached) setHeadline(cached);
    });
  }, []);

  return headline;
}

/** "29.6%" style helper */
export const pct = (n: number): string => `${n.toFixed(1)}%`;
