"use client";

import { useCallback, useEffect, useState } from "react";

import DocumentStatusCard from "@/components/DocumentStatusCard";
import PdfUploadForm from "@/components/PdfUploadForm";
import { api, type DocumentType, type StudyDocument } from "@/lib/api";

const FILTERS: { value: DocumentType | "all"; label: string }[] = [
  { value: "all", label: "전체" },
  { value: "lecture", label: "강의자료" },
  { value: "past_exam", label: "족보" },
];

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<StudyDocument[]>([]);
  const [filter, setFilter] = useState<DocumentType | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = filter === "all" ? "" : `?document_type=${filter}`;
      const data = await api.get<StudyDocument[]>(`/documents${query}`);
      setDocuments(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "문서 목록을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">문서 관리</h1>
        <p className="mt-1 text-sm text-gray-500">
          강의자료와 족보 PDF를 업로드하고 처리 상태를 확인하세요.
        </p>
      </header>

      <PdfUploadForm onUploaded={loadDocuments} />

      <section className="mt-10">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => setFilter(f.value)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  filter === f.value
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={loadDocuments}
            className="text-sm font-medium text-primary-600 hover:text-primary-700"
          >
            새로고침
          </button>
        </div>

        {loading ? (
          <p className="py-8 text-center text-sm text-gray-400">불러오는 중...</p>
        ) : error ? (
          <p className="py-8 text-center text-sm text-red-600">{error}</p>
        ) : documents.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-400">
            업로드된 문서가 없습니다.
          </p>
        ) : (
          <div className="space-y-2">
            {documents.map((doc) => (
              <DocumentStatusCard key={doc.id} doc={doc} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
