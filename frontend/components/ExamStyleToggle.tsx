"use client";

import ExamStyleSummary from "@/components/ExamStyleSummary";
import type { ExamStyleProfile } from "@/lib/api";

interface ExamStyleToggleProps {
  profiles: ExamStyleProfile[];
  enabled: boolean;
  selectedProfileId: string | null;
  onEnabledChange: (enabled: boolean) => void;
  onProfileChange: (profileId: string | null) => void;
}

export default function ExamStyleToggle({
  profiles,
  enabled,
  selectedProfileId,
  onEnabledChange,
  onProfileChange,
}: ExamStyleToggleProps) {
  const selected = profiles.find((p) => p.id === selectedProfileId) ?? null;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <label className="flex cursor-pointer items-center gap-3">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
        />
        <span className="text-sm font-medium text-gray-900">족보 출제 스타일 반영</span>
      </label>
      <p className="mt-1 pl-7 text-xs text-gray-500">
        분석된 족보 프로필의 유형·Bloom 비율을 문제 생성에 반영합니다.
      </p>

      {enabled && (
        <div className="mt-4 space-y-3 pl-7">
          {profiles.length === 0 ? (
            <p className="text-sm text-amber-700">
              등록된 출제 스타일 프로필이 없습니다.{" "}
              <a href="/exam-styles" className="font-medium underline">
                족보 분석
              </a>
              후 사용할 수 있습니다.
            </p>
          ) : (
            <>
              <select
                value={selectedProfileId ?? ""}
                onChange={(e) => onProfileChange(e.target.value || null)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="">프로필 선택...</option>
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {[profile.subject, profile.professor_name, profile.document_filename]
                      .filter(Boolean)
                      .join(" · ") || profile.id}
                  </option>
                ))}
              </select>
              {selected && (
                <div className="rounded-lg border border-gray-200 bg-white p-3">
                  <ExamStyleSummary profile={selected} compact />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
