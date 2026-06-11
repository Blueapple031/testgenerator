"use client";

import { useState } from "react";

import ExamStyleToggle from "@/components/ExamStyleToggle";
import type {
  Difficulty,
  ExamGenerationRequest,
  ExamStyleProfile,
  GenerationMode,
  QuestionType,
  StudyDocument,
} from "@/lib/api";

const QUESTION_TYPE_OPTIONS: { value: QuestionType; label: string }[] = [
  { value: "multiple_choice", label: "객관식" },
  { value: "short_answer", label: "단답형" },
  { value: "essay_short", label: "짧은 서술형" },
  { value: "essay_long", label: "긴 서술형" },
];

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string }[] = [
  { value: "easy", label: "쉬움" },
  { value: "medium", label: "보통" },
  { value: "hard", label: "어려움" },
];

const MAX_QUESTIONS = 30;

interface ExamGenerationFormProps {
  documents: StudyDocument[];
  styleProfiles: ExamStyleProfile[];
  onSubmit: (request: ExamGenerationRequest) => Promise<void>;
  disabled?: boolean;
}

export default function ExamGenerationForm({
  documents,
  styleProfiles,
  onSubmit,
  disabled,
}: ExamGenerationFormProps) {
  const readyLectures = documents.filter(
    (d) =>
      d.document_type === "lecture" &&
      (d.status === "READY" || d.status === "UPLOADED" || d.status === "INDEXING" || d.status === "EXTRACTING")
  );
  const ragReadyLectures = documents.filter(
    (d) => d.document_type === "lecture" && d.status === "READY"
  );

  const [generationMode, setGenerationMode] = useState<"rag" | "full_context">("rag");

  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [questionCount, setQuestionCount] = useState(5);
  const [questionTypes, setQuestionTypes] = useState<QuestionType[]>([
    "short_answer",
    "essay_short",
  ]);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [pageStart, setPageStart] = useState("");
  const [pageEnd, setPageEnd] = useState("");
  const [styleEnabled, setStyleEnabled] = useState(false);
  const [styleProfileId, setStyleProfileId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleDocument = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const toggleQuestionType = (type: QuestionType) => {
    setQuestionTypes((prev) => {
      if (prev.includes(type)) {
        const next = prev.filter((t) => t !== type);
        return next.length > 0 ? next : prev;
      }
      return [...prev, type];
    });
  };

  const selectableLectures = generationMode === "rag" ? ragReadyLectures : readyLectures;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (selectedDocIds.length === 0) {
      setError("강의자료를 하나 이상 선택하세요.");
      return;
    }
    if (generationMode === "rag" && selectedDocIds.some((id) => !ragReadyLectures.find((d) => d.id === id))) {
      setError("RAG 모드는 인덱싱 완료(READY) 문서만 사용할 수 있습니다.");
      return;
    }
    if (styleEnabled && !styleProfileId) {
      setError("족보 스타일 반영을 켠 경우 프로필을 선택하세요.");
      return;
    }

    const request: ExamGenerationRequest = {
      document_ids: selectedDocIds,
      question_count: questionCount,
      question_types: questionTypes,
      difficulty,
      generation_mode: generationMode,
    };

    if (title.trim()) request.title = title.trim();
    if (styleEnabled && styleProfileId) request.exam_style_profile_id = styleProfileId;

    const start = parseInt(pageStart, 10);
    const end = parseInt(pageEnd, 10);
    if (pageStart.trim()) request.page_range_start = start;
    if (pageEnd.trim()) request.page_range_end = end;
    if (
      (pageStart.trim() && Number.isNaN(start)) ||
      (pageEnd.trim() && Number.isNaN(end)) ||
      (request.page_range_start && request.page_range_end &&
        request.page_range_start > request.page_range_end)
    ) {
      setError("페이지 범위가 올바르지 않습니다.");
      return;
    }

    setSubmitting(true);
    try {
      await onSubmit(request);
    } catch (err) {
      setError(err instanceof Error ? err.message : "생성 요청에 실패했습니다.");
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">강의자료 선택</h2>
        <p className="mt-1 text-xs text-gray-500">
          {generationMode === "rag"
            ? "인덱싱이 완료(READY)된 강의자료만 선택할 수 있습니다."
            : "업로드된 PDF면 인덱싱 없이도 사용 가능합니다 (PyMuPDF→텍스트→LLM)."}
        </p>

        {(generationMode === "rag" ? ragReadyLectures : readyLectures).length === 0 ? (
          <p className="mt-4 text-sm text-amber-700">
            사용 가능한 강의자료가 없습니다.{" "}
            <a href="/documents" className="font-medium underline">
              문서 관리
            </a>
            에서 PDF를 업로드하고 인덱싱을 완료하세요.
          </p>
        ) : (
          <ul className="mt-4 space-y-2">
            {(generationMode === "rag" ? ragReadyLectures : readyLectures).map((doc) => (
              <li key={doc.id}>
                <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-gray-100 px-3 py-2 hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedDocIds.includes(doc.id)}
                    onChange={() => toggleDocument(doc.id)}
                    className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-gray-900">{doc.filename}</span>
                    <span className="text-xs text-gray-400">
                      {doc.page_count != null && `${doc.page_count}쪽 · `}
                      {doc.status}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">생성 파이프라인</h2>
        <p className="mt-1 text-xs text-gray-500">
          벤치마크 비교용. FULL_CONTEXT는 PDF에서 추출한 전체 텍스트를 LLM 1회 호출로
          문제 생성합니다 (OpenAI에 PDF 원본 바이트를 보내지 않음).
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {(
            [
              { value: "rag" as GenerationMode, label: "RAG (기본)" },
              { value: "full_context" as GenerationMode, label: "FULL_CONTEXT (벤치마크)" },
            ] as const
          ).map((opt) => (
            <label
              key={opt.value}
              className={`cursor-pointer rounded-lg border px-3 py-2 text-sm ${
                generationMode === opt.value
                  ? "border-primary-500 bg-primary-50 text-primary-700"
                  : "border-gray-200 text-gray-600 hover:bg-gray-50"
              }`}
            >
              <input
                type="radio"
                name="generation_mode"
                value={opt.value}
                checked={generationMode === opt.value}
                onChange={() => setGenerationMode(opt.value)}
                className="sr-only"
              />
              {opt.label}
            </label>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-900">생성 옵션</h2>

        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600">문제집 제목 (선택)</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="예: 중간고사 대비 — 3~5장"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600">
              문항 수 (1~{MAX_QUESTIONS})
            </label>
            <input
              type="number"
              min={1}
              max={MAX_QUESTIONS}
              value={questionCount}
              onChange={(e) => setQuestionCount(Number(e.target.value))}
              className="mt-1 w-32 rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
          </div>

          <div>
            <span className="block text-xs font-medium text-gray-600">문제 유형</span>
            <div className="mt-2 flex flex-wrap gap-2">
              {QUESTION_TYPE_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className={`cursor-pointer rounded-lg border px-3 py-1.5 text-sm ${
                    questionTypes.includes(opt.value)
                      ? "border-primary-500 bg-primary-50 text-primary-700"
                      : "border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={questionTypes.includes(opt.value)}
                    onChange={() => toggleQuestionType(opt.value)}
                    className="sr-only"
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          <div>
            <span className="block text-xs font-medium text-gray-600">난이도</span>
            <div className="mt-2 flex gap-2">
              {DIFFICULTY_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className={`cursor-pointer rounded-lg border px-3 py-1.5 text-sm ${
                    difficulty === opt.value
                      ? "border-primary-500 bg-primary-50 text-primary-700"
                      : "border-gray-200 text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <input
                    type="radio"
                    name="difficulty"
                    value={opt.value}
                    checked={difficulty === opt.value}
                    onChange={() => setDifficulty(opt.value)}
                    className="sr-only"
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600">시작 페이지 (선택)</label>
              <input
                type="number"
                min={1}
                value={pageStart}
                onChange={(e) => setPageStart(e.target.value)}
                placeholder="1"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">끝 페이지 (선택)</label>
              <input
                type="number"
                min={1}
                value={pageEnd}
                onChange={(e) => setPageEnd(e.target.value)}
                placeholder="50"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          </div>
        </div>
      </section>

      <ExamStyleToggle
        profiles={styleProfiles}
        enabled={styleEnabled}
        selectedProfileId={styleProfileId}
        onEnabledChange={setStyleEnabled}
        onProfileChange={setStyleProfileId}
      />

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={disabled || submitting || selectableLectures.length === 0}
        className="w-full rounded-lg bg-primary-600 py-3 text-sm font-semibold text-white hover:bg-primary-700 disabled:opacity-50"
      >
        {submitting ? "요청 중..." : "문제집 생성 시작"}
      </button>
    </form>
  );
}
