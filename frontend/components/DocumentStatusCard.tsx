"use client";

import type { DocumentType, StudyDocument } from "@/lib/api";

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

export default function DocumentStatusCard({ doc }: { doc: StudyDocument }) {
  const statusStyle = STATUS_STYLES[doc.status] ?? "bg-gray-100 text-gray-600";

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-gray-900">{doc.filename}</p>
        <p className="mt-0.5 text-xs text-gray-400">
          {DOC_TYPE_LABELS[doc.document_type]}
          {doc.page_count != null && ` · ${doc.page_count}쪽`}
          {` · ${formatDate(doc.created_at)}`}
        </p>
      </div>
      <span
        className={`ml-3 shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${statusStyle}`}
      >
        {doc.status}
      </span>
    </div>
  );
}
