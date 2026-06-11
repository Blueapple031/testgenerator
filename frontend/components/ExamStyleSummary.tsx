"use client";

import type { ExamStyleProfile } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  multiple_choice: "객관식",
  short_answer: "단답형",
  essay_short: "짧은 서술형",
  essay_long: "긴 서술형",
};

const BLOOM_LABELS: Record<string, string> = {
  remember: "기억",
  understand: "이해",
  apply: "적용",
  analyze: "분석",
  evaluate: "평가",
  create: "창출",
};

function DistributionBar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-primary-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

interface ExamStyleSummaryProps {
  profile: ExamStyleProfile;
  compact?: boolean;
}

export default function ExamStyleSummary({ profile, compact }: ExamStyleSummaryProps) {
  const typeEntries = Object.entries(profile.type_distribution ?? {}).filter(
    ([, v]) => v > 0
  );
  const bloomEntries = Object.entries(profile.bloom_distribution ?? {}).filter(
    ([, v]) => v > 0
  );
  const typeMax = typeEntries.reduce((sum, [, v]) => sum + v, 0) || 100;
  const bloomMax = bloomEntries.reduce((sum, [, v]) => sum + v, 0) || 100;

  return (
    <div className={compact ? "space-y-3" : "space-y-5"}>
      <div className="flex flex-wrap gap-2 text-sm text-gray-600">
        {profile.professor_name && (
          <span className="rounded-full bg-gray-100 px-2.5 py-0.5">
            {profile.professor_name}
          </span>
        )}
        {profile.subject && (
          <span className="rounded-full bg-gray-100 px-2.5 py-0.5">{profile.subject}</span>
        )}
        {profile.avg_questions_per_exam != null && (
          <span className="rounded-full bg-gray-100 px-2.5 py-0.5">
            평균 {profile.avg_questions_per_exam}문항
          </span>
        )}
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5">
          분석 {profile.analyzed_exam_count}회
        </span>
      </div>

      {profile.style_notes && (
        <p className="text-sm leading-relaxed text-gray-700">{profile.style_notes}</p>
      )}

      {!compact && typeEntries.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            문제 유형 분포
          </h4>
          <div className="space-y-2">
            {typeEntries.map(([key, value]) => (
              <DistributionBar
                key={key}
                label={TYPE_LABELS[key] ?? key}
                value={value}
                max={typeMax}
              />
            ))}
          </div>
        </div>
      )}

      {!compact && bloomEntries.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
            Bloom 분포
          </h4>
          <div className="space-y-2">
            {bloomEntries.map(([key, value]) => (
              <DistributionBar
                key={key}
                label={BLOOM_LABELS[key] ?? key}
                value={value}
                max={bloomMax}
              />
            ))}
          </div>
        </div>
      )}

      {profile.common_concepts && profile.common_concepts.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {profile.common_concepts.map((concept) => (
            <span
              key={concept}
              className="rounded-md bg-primary-50 px-2 py-0.5 text-xs text-primary-700"
            >
              {concept}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
