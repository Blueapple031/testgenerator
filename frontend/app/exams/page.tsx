"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { api, type ExamListItem } from "@/lib/api";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ko-KR");
  } catch {
    return iso;
  }
}

export default function ExamsPage() {
  const [exams, setExams] = useState<ExamListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const loadExams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ExamListItem[]>("/exams");
      setExams(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "시험 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadExams();
  }, [loadExams]);

  const handleCreateDemo = async () => {
    setCreating(true);
    try {
      const exam = await api.post<{ id: string }>("/exams/demo");
      await loadExams();
      window.location.href = `/exams/${exam.id}`;
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "데모 시험 생성에 실패했습니다.");
      setCreating(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">문제집</h1>
          <p className="mt-1 text-sm text-gray-500">
            AI로 생성한 시험을 미리보고 인쇄할 수 있습니다.
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2 sm:flex-row sm:items-center">
          <Link
            href="/exams/generate"
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-semibold text-white hover:bg-primary-700"
          >
            문제집 생성
          </Link>
          <button
            type="button"
            onClick={handleCreateDemo}
            disabled={creating}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {creating ? "생성 중..." : "데모"}
          </button>
        </div>
      </header>

      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">불러오는 중...</p>
      ) : error ? (
        <p className="py-8 text-center text-sm text-red-600">{error}</p>
      ) : exams.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white py-12 text-center">
          <p className="text-sm text-gray-500">생성된 문제집이 없습니다.</p>
          <Link
            href="/exams/generate"
            className="mt-4 inline-block text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            AI로 문제집 생성하기 →
          </Link>
        </div>
      ) : (
        <ul className="space-y-2">
          {exams.map((exam) => (
            <li key={exam.id}>
              <Link
                href={`/exams/${exam.id}`}
                className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm transition-colors hover:border-primary-300"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {exam.title}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    {exam.question_count}문항 · {formatDate(exam.created_at)}
                  </p>
                </div>
                <span className="ml-3 shrink-0 text-xs text-primary-600">보기 →</span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <p className="no-print mt-8 text-center text-xs text-gray-400">
        <Link href="/documents" className="hover:text-gray-600">
          ← 문서 관리로 돌아가기
        </Link>
      </p>
    </main>
  );
}
