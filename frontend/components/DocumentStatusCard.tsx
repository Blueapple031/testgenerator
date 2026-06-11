"use client";

import { useState } from "react";

import { api, type DocumentType, type StudyDocument } from "@/lib/api";

const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  lecture: "강의자료",
  past_exam: "족보",
};

const STATUS_STYLES: Record<string, string> = {
  UPLOADED: "bg-gray-100 text-gray-600",
  EXTRACTING: "bg-amber-100 text-amber-700",
  INDEXING: "bg-blue-100 text-blue-700",
  READY: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("ko-KR");
  } catch {
    return iso;
  }
}

interface DocumentStatusCardProps {
  doc: StudyDocument;
  onDeleted?: () => void;
}

export default function DocumentStatusCard({ doc, onDeleted }: DocumentStatusCardProps) {
  const [deleting, setDeleting] = useState(false);
  const statusStyle = STATUS_STYLES[doc.status] ?? "bg-gray-100 text-gray-600";

  const handleDelete = async () => {
    const confirmed = window.confirm(
      `"${doc.filename}" 문서를 삭제할까요?\n연관된 청크·임베딩 데이터도 함께 삭제됩니다.`
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await api.delete(`/documents/${doc.id}`);
      onDeleted?.();
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "문서 삭제에 실패했습니다.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-gray-900">{doc.filename}</p>
        <p className="mt-0.5 text-xs text-gray-400">
          {DOC_TYPE_LABELS[doc.document_type]}
          {doc.page_count != null && ` · ${doc.page_count}쪽`}
          {` · ${formatDate(doc.created_at)}`}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusStyle}`}>
          {doc.status}
        </span>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="rounded-lg px-2.5 py-1 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
        >
          {deleting ? "삭제 중..." : "삭제"}
        </button>
      </div>
    </div>
  );
}
