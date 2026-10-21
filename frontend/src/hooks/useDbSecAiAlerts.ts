import { useState, useCallback } from 'react';
import { postDbSecAiAlerts, type DbSecAiResult } from '../api/intel';

export interface DbSecAiParams {
  lookback_hours: number;
  db_name?: string;
  min_severity?: string;
}

export function useDbSecAiAlerts() {
  const [data, setData] = useState<DbSecAiResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastParams, setLastParams] = useState<DbSecAiParams>({ lookback_hours: 24 });

  const run = useCallback(async (params: DbSecAiParams) => {
    setLoading(true);
    setError(null);
    setLastParams(params);
    try {
      const result = await postDbSecAiAlerts({
        lookback_hours: params.lookback_hours,
        db_name: params.db_name || undefined,
        min_severity: params.min_severity || undefined,
        limit_events: 100,
      });
      setData(result);
    } catch (e: unknown) {
      const err = e as { response?: { status?: number }; message?: string };
      const status = err?.response?.status;
      if (status === 403) setError('Insufficient permissions for DAM AI alert analysis.');
      else if (status === 401) setError('Session expired. Please log in again.');
      else setError(err?.message || 'DAM AI analysis failed.');
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, lastParams, run };
}
