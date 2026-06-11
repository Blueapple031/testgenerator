"use client";

import ExamPreview from "@/components/ExamPreview";
import type { GeneratedExam } from "@/lib/api";

interface ExamPrintViewProps {
  exam: GeneratedExam;
  showAnswers: boolean;
  printAnswersOnly: boolean;
}

/** 브라우저 인쇄(print stylesheet)용 래퍼. 화면·인쇄 레이아웃을 함께 제공한다. */
export default function ExamPrintView({
  exam,
  showAnswers,
  printAnswersOnly,
}: ExamPrintViewProps) {
  return (
    <div className="exam-print-root mx-auto max-w-3xl bg-white px-6 py-8 print:max-w-none print:px-0 print:py-0">
      <ExamPreview
        exam={exam}
        showAnswers={showAnswers}
        printAnswersOnly={printAnswersOnly}
      />
    </div>
  );
}
