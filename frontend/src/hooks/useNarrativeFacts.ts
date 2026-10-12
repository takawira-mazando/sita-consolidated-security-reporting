import { useApi } from './useApi';
import { fetchNarrativeFacts } from '../api/meta';
import type { NarrativeFacts } from '../types';

/**
 * Platform model constants (risk weights, band thresholds, estate counts,
 * framework applicability) used by the dashboard narrative.
 *
 * These are deliberately fetched from the API rather than imported: the values
 * live in `risk_engine`, `compliance`, `frameworks` and `tenant` on the server,
 * and a literal copy in the frontend is exactly what drifted out of date
 * before. The narrative degrades to plain wording when this fails to load.
 */
export function useNarrativeFacts() {
  const model = useApi(() => fetchNarrativeFacts());

  return {
    loading: model.loading,
    error: model.error,
    facts: (model.data || {}) as NarrativeFacts,
  };
}