"use client";

import { useCallback, useEffect, useState } from "react";

import ExamStyleSummary from "@/components/ExamStyleSummary";
import { api, type ExamStyleProfile } from "@/lib/api";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ko-KR");
  } catch {
    return iso;
  }
}

export default function ExamStylesPage() {
  const [profiles, setProfiles] = useState<ExamStyleProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ExamStyleProfile[]>("/exam-styles");
      setProfiles(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "프로필 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  const selected = profiles.find((p) => p.id === selectedId) ?? null;

  const handleDelete = async (profileId: string) => {
    const confirmed = window.confirm("이 출제 스타일 프로필을 삭제할까요?");
    if (!confirmed) return;

    setDeleting(true);
    try {
      await api.delete(`/exam-styles/${profileId}`);
      setProfiles((prev) => prev.filter((p) => p.id !== profileId));
      if (selectedId === profileId) {
        setSelectedId(null);
      }
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">출제 스타일 프로필</h1>
        <p className="mt-1 text-sm text-gray-500">
          족보 분석 결과를 확인하고, 문제 생성 시 스타일 반영에 사용할 수 있습니다.
        </p>
      </header>

      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">불러오는 중...</p>
      ) : error ? (
        <p className="py-8 text-center text-sm text-red-600">{error}</p>
      ) : profiles.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white px-6 py-12 text-center">
          <p className="text-sm text-gray-500">아직 분석된 족보 프로필이 없습니다.</p>
          <a
            href="/documents"
            className="mt-3 inline-block text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            문서 관리에서 족보 업로드 후 분석하기 →
          </a>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-5">
          <aside className="space-y-2 lg:col-span-2">
            {profiles.map((profile) => (
              <button
                key={profile.id}
                type="button"
                onClick={() => setSelectedId(profile.id)}
                className={`w-full rounded-lg border px-4 py-3 text-left transition-colors ${
                  selectedId === profile.id
                    ? "border-primary-500 bg-primary-50"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <p className="truncate text-sm font-medium text-gray-900">
                  {profile.subject ?? profile.document_filename ?? "족보 프로필"}
                </p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {profile.professor_name ?? "교수명 미입력"} · {formatDate(profile.created_at)}
                </p>
              </button>
            ))}
          </aside>

          {selected && (
            <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm lg:col-span-3">
              <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {selected.subject ?? "과목 미지정"}
                  </h2>
                  <p className="mt-0.5 text-sm text-gray-500">
                    {selected.document_filename}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(selected.id)}
                  disabled={deleting}
                  className="shrink-0 text-sm text-red-600 hover:text-red-700 disabled:opacity-50"
                >
                  삭제
                </button>
              </div>
              <ExamStyleSummary profile={selected} />
              <p className="mt-6 text-xs text-gray-400">
                프로필 ID: {selected.id} — 문제 생성 시{" "}
                <code className="rounded bg-gray-100 px-1">exam_style_profile_id</code>로
                전달합니다.
              </p>
            </section>
          )}
        </div>
      )}
    </main>
  );
}
