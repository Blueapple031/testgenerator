"use client";

import { useEffect, useRef } from "react";

import { useJobStream } from "@/hooks/useSSE";
import type { JobStreamEvent } from "@/lib/api";
import { formatTokenUsageDetail } from "@/lib/tokenUsage";

const STAGE_LABELS: Record<string, string> = {
  PENDING: "대기 중",
  GENERATING: "생성 중",
  FINALIZING: "저장 중",
  COMPLETED: "완료",
  FAILED: "실패",
};

interface ProgressStreamProps {
  jobId: string;
  onComplete: (examId: string) => void;
  onFailed: (message: string | null) => void;
}

export default function ProgressStream({ jobId, onComplete, onFailed }: ProgressStreamProps) {
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleComplete = (examId: string, event: JobStreamEvent) => {
    if (redirectTimerRef.current) return;
    redirectTimerRef.current = setTimeout(() => onComplete(examId), 3500);
  };

  const { event, connected, error } = useJobStream(jobId, {
    onComplete: handleComplete,
    onFailed,
  });

  useEffect(() => {
    return () => {
      if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
    };
  }, []);

  const progress = event?.progress ?? 0;
  const stage = event?.stage ?? "PENDING";
  const message = event?.message ?? "준비 중...";
  const tokenUsage = event?.token_usage;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">문제집 생성 진행</h3>
        <span className="text-xs text-gray-400">
          {connected ? "실시간 연결됨" : "연결 중..."}
        </span>
      </div>

      <div className="mb-2 flex justify-between text-xs text-gray-600">
        <span>{STAGE_LABELS[stage] ?? stage}</span>
        <span>{progress}%</span>
      </div>

      <div className="h-3 overflow-hidden rounded-full bg-gray-100">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            stage === "FAILED" ? "bg-red-500" : "bg-primary-600"
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <p className="mt-3 text-sm text-gray-600">{message}</p>

      {stage === "COMPLETED" && tokenUsage && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
          <p className="text-xs font-semibold text-emerald-800">토큰 사용량</p>
          <p className="mt-1 text-sm text-emerald-900">{formatTokenUsageDetail(tokenUsage)}</p>
          <p className="mt-2 text-xs text-emerald-700">잠시 후 결과 페이지로 이동합니다...</p>
        </div>
      )}

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      {stage === "FAILED" && (
        <p className="mt-2 text-sm text-red-600">{message || "생성에 실패했습니다."}</p>
      )}
    </div>
  );
}
