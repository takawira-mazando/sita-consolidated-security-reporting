import { useState, useEffect, useCallback } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[] = []): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    fetcher()
      .then((res) => setData(res))
      .catch((e) => {
        const status = e?.response?.status;
        if (status === 403) setError('Insufficient permissions for this account.');
        else if (status === 401) setError('Session expired. Please log in again.');
        else setError(e?.message || 'Failed to load data.');
      })
      .finally(() => setLoading(false));
  }, deps);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, loading, error, refresh };
}
