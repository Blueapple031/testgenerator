"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import ExamGenerationForm from "@/components/ExamGenerationForm";
import ProgressStream from "@/components/ProgressStream";
import {
  api,
  type ExamGenerationRequest,
  type ExamStyleProfile,
  type JobCreateResponse,
  type StudyDocument,
} from "@/lib/api";

type Phase = "form" | "generating" | "failed";

export default function ExamGeneratePage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("form");
  const [jobId, setJobId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<StudyDocument[]>([]);
  const [styleProfiles, setStyleProfiles] = useState<ExamStyleProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [failMessage, setFailMessage] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [docs, profiles] = await Promise.all([
        api.get<StudyDocument[]>("/documents?document_type=lecture"),
        api.get<ExamStyleProfile[]>("/exam-styles"),
      ]);
      setDocuments(docs);
      setStyleProfiles(profiles);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "데이터를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSubmit = async (request: ExamGenerationRequest) => {
    const res = await api.post<JobCreateResponse>("/jobs", request);
    setJobId(res.job_id);
    setPhase("generating");
    setFailMessage(null);
  };

  const handleComplete = (examId: string) => {
    router.push(`/exams/${examId}`);
  };

  const handleFailed = (message: string | null) => {
    setPhase("failed");
    setFailMessage(message);
  };

  const handleRetry = () => {
    setPhase("form");
    setJobId(null);
    setFailMessage(null);
  };

  return (
    <main className="mx-auto max-w-2xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">문제집 생성</h1>
        <p className="mt-1 text-sm text-gray-500">
          강의자료 범위와 옵션을 선택하면 AI가 RAG 기반으로 문제를 생성합니다.
        </p>
      </header>

      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">불러오는 중...</p>
      ) : loadError ? (
        <p className="py-8 text-center text-sm text-red-600">{loadError}</p>
      ) : phase === "generating" && jobId ? (
        <div className="space-y-6">
          <ProgressStream
            jobId={jobId}
            onComplete={handleComplete}
            onFailed={handleFailed}
          />
          <p className="text-center text-xs text-gray-400">
            생성에는 문항 수에 따라 수 분이 걸릴 수 있습니다.
          </p>
        </div>
      ) : (
        <>
          {phase === "failed" && (
            <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {failMessage || "문제집 생성에 실패했습니다."}
              <button
                type="button"
                onClick={handleRetry}
                className="ml-2 font-medium underline"
              >
                다시 시도
              </button>
            </div>
          )}
          <ExamGenerationForm
            documents={documents}
            styleProfiles={styleProfiles}
            onSubmit={handleSubmit}
            disabled={phase === "generating"}
          />
        </>
      )}

      <p className="no-print mt-8 text-center text-xs text-gray-400">
        <Link href="/exams" className="hover:text-gray-600">
          ← 문제집 목록
        </Link>
      </p>
    </main>
  );
}
