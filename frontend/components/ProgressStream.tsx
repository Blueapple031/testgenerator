"use client";

import { useJobStream } from "@/hooks/useSSE";

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
  const { event, connected, error } = useJobStream(jobId, { onComplete, onFailed });

  const progress = event?.progress ?? 0;
  const stage = event?.stage ?? "PENDING";
  const message = event?.message ?? "준비 중...";

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

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

      {stage === "FAILED" && (
        <p className="mt-2 text-sm text-red-600">{message || "생성에 실패했습니다."}</p>
      )}
    </div>
  );
}
