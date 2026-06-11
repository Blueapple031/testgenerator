"use client";

import type { GeneratedExam, GeneratedQuestion, QuestionType } from "@/lib/api";

const TYPE_LABELS: Record<QuestionType, string> = {
  multiple_choice: "객관식",
  short_answer: "단답형",
  essay_short: "짧은 서술형",
  essay_long: "긴 서술형",
};

const DIFFICULTY_LABELS: Record<string, string> = {
  easy: "쉬움",
  medium: "중",
  hard: "어려움",
};

function QuestionBlock({
  question,
  showAnswers,
  printAnswersOnly,
}: {
  question: GeneratedQuestion;
  showAnswers: boolean;
  printAnswersOnly: boolean;
}) {
  const showAnswerBlock = showAnswers || printAnswersOnly;
  const answerClass = printAnswersOnly && !showAnswers
    ? "exam-answer exam-answer-print-only"
    : "exam-answer";
  return (
    <article className="exam-question break-inside-avoid">
      <header className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-base font-bold text-gray-900">
          {question.number}.
        </span>
        <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
          {TYPE_LABELS[question.question_type]}
        </span>
        <span className="text-xs text-gray-400">
          {DIFFICULTY_LABELS[question.difficulty] ?? question.difficulty}
          {question.bloom_level && ` · ${question.bloom_level}`}
        </span>
      </header>

      <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-900">
        {question.stem}
      </p>

      {question.choices && question.choices.length > 0 && (
        <ol className="mt-3 list-none space-y-1.5 pl-0">
          {question.choices.map((choice) => (
            <li
              key={choice.label}
              className={`text-sm ${
                showAnswers && choice.isAnswer
                  ? "font-semibold text-green-800"
                  : "text-gray-800"
              }`}
            >
              <span className="mr-2 font-medium">{choice.label}.</span>
              {choice.text}
            </li>
          ))}
        </ol>
      )}

      {showAnswerBlock && (
        <div className={`${answerClass} mt-4 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm`}>
          <p>
            <span className="font-semibold text-green-900">정답: </span>
            <span className="text-green-900">{question.answer}</span>
          </p>
          {question.explanation && (
            <p className="mt-1 text-green-800">
              <span className="font-semibold">해설: </span>
              {question.explanation}
            </p>
          )}
        </div>
      )}
    </article>
  );
}

interface ExamPreviewProps {
  exam: GeneratedExam;
  showAnswers?: boolean;
  printAnswersOnly?: boolean;
}

export default function ExamPreview({
  exam,
  showAnswers = false,
  printAnswersOnly = false,
}: ExamPreviewProps) {
  return (
    <div className="exam-preview space-y-8">
      <header className="exam-header border-b border-gray-200 pb-4 text-center">
        <h1 className="text-xl font-bold text-gray-900">{exam.title}</h1>
        <p className="mt-1 text-sm text-gray-500">
          총 {exam.question_count}문항
        </p>
      </header>

      <div className="space-y-8">
        {exam.questions.map((q) => (
          <QuestionBlock
            key={q.id}
            question={q}
            showAnswers={showAnswers}
            printAnswersOnly={printAnswersOnly}
          />
        ))}
      </div>
    </div>
  );
}
