import { useCallback, useEffect, useRef, useState } from "react";
import { askQuestion } from "../api.js";

/**
 * Owns one question/answer round trip: the request, the result, and a live
 * elapsed-time counter that ticks while the request is in flight (the backend
 * reports its own authoritative `time_seconds` once the answer lands).
 */
export function useAsk() {
  const [status, setStatus] = useState("idle"); // idle | loading | success | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [asked, setAsked] = useState(null); // { question, mode } as sent
  const [elapsed, setElapsed] = useState(0);

  const timerRef = useRef(null);
  const abortRef = useRef(null);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopTimer();
      abortRef.current?.abort();
    };
  }, [stopTimer]);

  const ask = useCallback(
    async (question, mode) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setStatus("loading");
      setResult(null);
      setError(null);
      setAsked({ question, mode });
      setElapsed(0);

      const start = performance.now();
      stopTimer();
      timerRef.current = setInterval(() => {
        setElapsed((performance.now() - start) / 1000);
      }, 100);

      try {
        const data = await askQuestion({ question, mode, signal: controller.signal });
        setResult(data);
        setStatus("success");
      } catch (err) {
        if (err?.name === "AbortError") return;
        setError(err);
        setStatus("error");
      } finally {
        if (abortRef.current === controller) {
          stopTimer();
          abortRef.current = null;
        }
      }
    },
    [stopTimer]
  );

  return { status, result, error, asked, elapsed, ask };
}
