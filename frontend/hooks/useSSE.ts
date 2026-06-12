"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE, type JobStreamEvent } from "@/lib/api";

const TERMINAL_STAGES = new Set(["COMPLETED", "FAILED"]);
const MAX_RECONNECT = 5;

interface UseJobStreamOptions {
  enabled?: boolean;
  onComplete?: (examId: string, event: JobStreamEvent) => void;
  onFailed?: (message: string | null) => void;
}

export function useJobStream(jobId: string | null, options: UseJobStreamOptions = {}) {
  const { enabled = true, onComplete, onFailed } = options;
  const [event, setEvent] = useState<JobStreamEvent | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventRef = useRef<JobStreamEvent | null>(null);
  const callbacksRef = useRef({ onComplete, onFailed });
  callbacksRef.current = { onComplete, onFailed };

  useEffect(() => {
    if (!jobId || !enabled) return;

    let closed = false;
    let reconnectAttempt = 0;
    let es: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (closed) return;

      es = new EventSource(`${API_BASE}/jobs/${jobId}/stream`, {
        withCredentials: true,
      });

      es.onopen = () => {
        setConnected(true);
        setError(null);
        reconnectAttempt = 0;
      };

      es.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data) as JobStreamEvent;
          eventRef.current = data;
          setEvent(data);

          if (data.stage === "COMPLETED" && data.exam_id) {
            es?.close();
            setConnected(false);
            callbacksRef.current.onComplete?.(data.exam_id, data);
          } else if (data.stage === "FAILED") {
            es?.close();
            setConnected(false);
            callbacksRef.current.onFailed?.(data.message);
          }
        } catch {
          setError("진행 상태를 해석하지 못했습니다.");
        }
      };

      es.onerror = () => {
        es?.close();
        setConnected(false);

        const last = eventRef.current;
        if (last && TERMINAL_STAGES.has(last.stage)) return;

        if (reconnectAttempt < MAX_RECONNECT) {
          reconnectAttempt += 1;
          reconnectTimer = setTimeout(connect, 1000 * reconnectAttempt);
        } else {
          setError("실시간 연결이 끊어졌습니다. 잠시 후 다시 시도해 주세요.");
        }
      };
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      es?.close();
    };
  }, [jobId, enabled]);

  return { event, connected, error };
}
