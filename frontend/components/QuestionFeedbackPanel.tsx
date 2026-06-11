"use client";

import { useCallback, useState } from "react";

import { api, type FeedbackRating, type QuestionFeedback, type FeedbackReasonTag } from "@/lib/api";

export const FEEDBACK_REASON_OPTIONS: { tag: FeedbackReasonTag; label: string }[] = [
  { tag: "answer_explanation_error", label: "정답·해설 오류" },
  { tag: "unclear_stem", label: "문제가 애매함" },
  { tag: "off_topic", label: "강의와 무관함" },
  { tag: "wrong_difficulty", label: "난이도 안 맞음" },
  { tag: "poor_choices", label: "보기 이상함" },
];

interface QuestionFeedbackPanelProps {
  examId: string;
  questionId: string;
  initialFeedback?: QuestionFeedback;
  onFeedbackChange?: (feedback: QuestionFeedback) => void;
}

export default function QuestionFeedbackPanel({
  examId,
  questionId,
  initialFeedback,
  onFeedbackChange,
}: QuestionFeedbackPanelProps) {
  const [feedback, setFeedback] = useState<QuestionFeedback | undefined>(initialFeedback);
  const [showDownForm, setShowDownForm] = useState(false);
  const [selectedTags, setSelectedTags] = useState<FeedbackReasonTag[]>(
    initialFeedback?.reason_tags ?? [],
  );
  const [comment, setComment] = useState(initialFeedback?.comment ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const saveFeedback = useCallback(
    async (payload: { rating: FeedbackRating; reason_tags?: FeedbackReasonTag[]; comment?: string | null }) => {
      setSaving(true);
      setError(null);
      try {
        const saved = await api.put<QuestionFeedback>(
          `/exams/${examId}/questions/${questionId}/feedback`,
          payload,
        );
        setFeedback(saved);
        onFeedbackChange?.(saved);
        return saved;
      } catch (e) {
        setError(e instanceof Error ? e.message : "평가 저장에 실패했습니다.");
        return null;
      } finally {
        setSaving(false);
      }
    },
    [examId, questionId, onFeedbackChange],
  );

  const handleUp = async () => {
    setShowDownForm(false);
    setSelectedTags([]);
    setComment("");
    await saveFeedback({ rating: "up" });
  };

  const handleDownClick = () => {
    if (feedback?.rating === "down") {
      setSelectedTags(feedback.reason_tags ?? []);
      setComment(feedback.comment ?? "");
    } else {
      setSelectedTags([]);
      setComment("");
    }
    setShowDownForm(true);
  };

  const toggleTag = (tag: FeedbackReasonTag) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const handleDownSubmit = async () => {
    if (selectedTags.length === 0 && !comment.trim()) {
      setError("사유를 하나 이상 선택하거나 코멘트를 입력해 주세요.");
      return;
    }
    await saveFeedback({
      rating: "down",
      reason_tags: selectedTags,
      comment: comment.trim() || null,
    });
  };

  const isUp = feedback?.rating === "up";
  const isDown = feedback?.rating === "down";

  return (
    <div className="no-print mt-4 rounded-md border border-gray-200 bg-gray-50 px-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-gray-600">이 문제 어땠나요?</span>
        <button
          type="button"
          onClick={handleUp}
          disabled={saving}
          aria-pressed={isUp}
          className={`rounded-full px-3 py-1 text-sm transition ${
            isUp
              ? "bg-green-100 font-semibold text-green-800 ring-1 ring-green-300"
              : "bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-green-50"
          }`}
        >
          👍 좋아요
        </button>
        <button
          type="button"
          onClick={handleDownClick}
          disabled={saving}
          aria-pressed={isDown}
          className={`rounded-full px-3 py-1 text-sm transition ${
            isDown
              ? "bg-red-100 font-semibold text-red-800 ring-1 ring-red-300"
              : "bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-red-50"
          }`}
        >
          👎 별로예요
        </button>
        {isUp && (
          <span className="text-xs text-green-700">피드백 감사합니다!</span>
        )}
        {isDown && !showDownForm && (
          <span className="text-xs text-gray-500">피드백이 저장되었습니다.</span>
        )}
      </div>

      {showDownForm && (
        <div className="mt-3 space-y-3 border-t border-gray-200 pt-3">
          <div className="flex flex-wrap gap-2">
            {FEEDBACK_REASON_OPTIONS.map(({ tag, label }) => {
              const selected = selectedTags.includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleTag(tag)}
                  disabled={saving}
                  className={`rounded-full px-2.5 py-1 text-xs transition ${
                    selected
                      ? "bg-red-100 font-medium text-red-800 ring-1 ring-red-300"
                      : "bg-white text-gray-600 ring-1 ring-gray-200 hover:bg-red-50"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="예: 3번 보기가 정답 같아요"
            rows={2}
            maxLength={1000}
            disabled={saving}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-800 placeholder:text-gray-400 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDownSubmit}
              disabled={saving}
              className="rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-50"
            >
              {saving ? "저장 중..." : "보내기"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowDownForm(false);
                setError(null);
                if (!isDown) {
                  setSelectedTags([]);
                  setComment("");
                }
              }}
              disabled={saving}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              닫기
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}
