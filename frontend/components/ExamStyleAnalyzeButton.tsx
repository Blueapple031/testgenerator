"use client";

import { useState } from "react";

import ExamStyleSummary from "@/components/ExamStyleSummary";
import { api, type ExamStyleProfile, type StudyDocument } from "@/lib/api";

interface ExamStyleAnalyzeButtonProps {
  doc: StudyDocument;
  onAnalyzed?: () => void;
}

export default function ExamStyleAnalyzeButton({
  doc,
  onAnalyzed,
}: ExamStyleAnalyzeButtonProps) {
  const [open, setOpen] = useState(false);
  const [professorName, setProfessorName] = useState("");
  const [subject, setSubject] = useState("");
  const [rawText, setRawText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExamStyleProfile | null>(null);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      const body: Record<string, string> = { document_id: doc.id };
      if (professorName.trim()) body.professor_name = professorName.trim();
      if (subject.trim()) body.subject = subject.trim();
      if (rawText.trim()) body.raw_text = rawText.trim();

      const profile = await api.post<ExamStyleProfile>("/exam-styles/analyze", body);
      setResult(profile);
      onAnalyzed?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "분석에 실패했습니다.");
    } finally {
      setAnalyzing(false);
    }
  };

  if (doc.document_type !== "past_exam") return null;

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
          setError(null);
          setResult(null);
        }}
        className="rounded-lg px-2.5 py-1 text-xs font-medium text-primary-600 transition-colors hover:bg-primary-50"
      >
        스타일 분석
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900">족보 출제 스타일 분석</h3>
            <p className="mt-1 truncate text-sm text-gray-500">{doc.filename}</p>

            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600">교수명 (선택)</label>
                <input
                  type="text"
                  value={professorName}
                  onChange={(e) => setProfessorName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="예: 김교수"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600">과목 (선택)</label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="예: 운영체제"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600">
                  족보 텍스트 직접 입력 (선택, PDF 추출 실패 시)
                </label>
                <textarea
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  rows={4}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="족보 내용을 붙여넣으면 PDF 추출 대신 사용합니다."
                />
              </div>
            </div>

            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

            {result && (
              <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4">
                <p className="mb-2 text-sm font-medium text-green-800">분석 완료</p>
                <ExamStyleSummary profile={result} compact />
              </div>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
              >
                닫기
              </button>
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={analyzing}
                className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {analyzing ? "분석 중..." : "분석 시작"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
