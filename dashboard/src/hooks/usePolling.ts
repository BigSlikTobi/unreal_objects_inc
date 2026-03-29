import { useCallback, useEffect, useRef, useState } from 'react';

export interface PollingResult<T> {
  data: T | null;
  error: string | null;
  isLoading: boolean;
  refresh: () => void;
}

export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number): PollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const inFlight = useRef(false);

  const doFetch = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const result = await fetcher();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed');
    } finally {
      inFlight.current = false;
      setIsLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    doFetch();
    const id = setInterval(doFetch, intervalMs);
    return () => clearInterval(id);
  }, [doFetch, intervalMs]);

  return { data, error, isLoading, refresh: doFetch };
}
