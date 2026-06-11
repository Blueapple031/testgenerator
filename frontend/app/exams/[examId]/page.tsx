"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import ExamPrintView from "@/components/ExamPrintView";
import { api, type GeneratedExam } from "@/lib/api";

export default function ExamDetailPage() {
  const params = useParams();
  const examId = params.examId as string;

  const [exam, setExam] = useState<GeneratedExam | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAnswers, setShowAnswers] = useState(false);
  const [printWithAnswers, setPrintWithAnswers] = useState(false);

  const loadExam = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<GeneratedExam>(`/exams/${examId}`);
      setExam(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "시험을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [examId]);

  useEffect(() => {
    loadExam();
  }, [loadExam]);

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-10 text-center text-sm text-gray-400">
        불러오는 중...
      </main>
    );
  }

  if (error || !exam) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-10 text-center">
        <p className="text-sm text-red-600">{error ?? "시험을 찾을 수 없습니다."}</p>
        <Link href="/exams" className="mt-4 inline-block text-sm text-primary-600">
          ← 문제집 목록
        </Link>
      </main>
    );
  }

  return (
    <>
      <div className="no-print sticky top-0 z-10 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link href="/exams" className="text-sm text-gray-500 hover:text-gray-700">
            ← 문제집 목록
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={showAnswers}
                onChange={(e) => setShowAnswers(e.target.checked)}
                className="rounded border-gray-300"
              />
              정답·해설 보기
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={printWithAnswers}
                onChange={(e) => setPrintWithAnswers(e.target.checked)}
                className="rounded border-gray-300"
              />
              인쇄 시 정답 포함
            </label>
            <button
              type="button"
              onClick={handlePrint}
              className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
            >
              인쇄 / PDF 저장
            </button>
          </div>
        </div>
      </div>

      <main>
        <ExamPrintView
          exam={exam}
          showAnswers={showAnswers}
          printAnswersOnly={printWithAnswers && !showAnswers}
        />
      </main>
    </>
  );
}
