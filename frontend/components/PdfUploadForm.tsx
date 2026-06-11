"use client";

import { useRef, useState } from "react";

import { api, type DocumentType, type StudyDocument } from "@/lib/api";

const MAX_BYTES = 50 * 1024 * 1024;

const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  lecture: "강의자료",
  past_exam: "족보 (과거 시험)",
};

interface PdfUploadFormProps {
  onUploaded?: (doc: StudyDocument) => void;
}

export default function PdfUploadForm({ onUploaded }: PdfUploadFormProps) {
  const [documentType, setDocumentType] = useState<DocumentType>("lecture");
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function validate(file: File): string | null {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return "PDF 파일만 업로드할 수 있습니다.";
    }
    if (file.size > MAX_BYTES) {
      return "파일 크기는 최대 50MB까지 허용됩니다.";
    }
    if (file.size === 0) {
      return "빈 파일은 업로드할 수 없습니다.";
    }
    return null;
  }

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError(null);

    for (const file of Array.from(files)) {
      const validationError = validate(file);
      if (validationError) {
        setError(validationError);
        continue;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("document_type", documentType);

      setUploading(true);
      try {
        const doc = await api.upload<StudyDocument>("/documents", formData);
        onUploaded?.(doc);
      } catch (e) {
        setError(e instanceof Error ? e.message : "업로드에 실패했습니다.");
      } finally {
        setUploading(false);
      }
    }

    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex gap-2">
        {(Object.keys(DOC_TYPE_LABELS) as DocumentType[]).map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setDocumentType(type)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              documentType === type
                ? "bg-primary-600 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {DOC_TYPE_LABELS[type]}
          </button>
        ))}
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-12 text-center transition-colors ${
          dragOver
            ? "border-primary-500 bg-primary-50"
            : "border-gray-300 hover:border-primary-400 hover:bg-gray-50"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {uploading ? (
          <p className="text-sm font-medium text-primary-600">업로드 중...</p>
        ) : (
          <>
            <p className="text-sm font-medium text-gray-700">
              PDF를 여기로 드래그하거나 클릭하여 선택하세요
            </p>
            <p className="mt-1 text-xs text-gray-400">
              {DOC_TYPE_LABELS[documentType]} · 최대 50MB
            </p>
          </>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
