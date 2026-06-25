"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api";

/** Async state container shared by the data hooks. */
export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/**
 * Run a typed fetcher on mount and expose `{ data, loading, error }`.
 *
 * The fetcher must be a stable reference (wrap in `useCallback` at the call
 * site if it closes over props) or passed via the `deps` array.
 */
export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: ReadonlyArray<unknown> = []
): AsyncState<T> & { refetch: () => void } {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  const run = useCallback(() => {
    let active = true;
    setState((s) => ({ ...s, loading: true, error: null }));

    fetcher()
      .then((data) => {
        if (active) setState({ data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!active) return;
        const message =
          err instanceof ApiError
            ? `${err.status}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Unknown error";
        setState({ data: null, loading: false, error: message });
      });

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => run(), [run]);

  return { ...state, refetch: run };
}

/**
 * Imperative async action with `{ run, data, loading, error }` — for
 * form submissions and on-demand calls (e.g. asking the AI assistant).
 */
export function useAction<TArgs extends unknown[], TResult>(
  action: (...args: TArgs) => Promise<TResult>
): AsyncState<TResult> & { run: (...args: TArgs) => Promise<TResult | null> } {
  const [state, setState] = useState<AsyncState<TResult>>({
    data: null,
    loading: false,
    error: null,
  });

  const run = useCallback(
    async (...args: TArgs): Promise<TResult | null> => {
      setState({ data: null, loading: true, error: null });
      try {
        const data = await action(...args);
        setState({ data, loading: false, error: null });
        return data;
      } catch (err: unknown) {
        const message =
          err instanceof ApiError
            ? `${err.status}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Unknown error";
        setState({ data: null, loading: false, error: message });
        return null;
      }
    },
    [action]
  );

  return { ...state, run };
}
