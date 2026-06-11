const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

async function upload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  if (!res.ok) {
    let detail = `${res.status}: ${res.statusText}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload,
};

export type DocumentType = "lecture" | "past_exam";

export interface StudyDocument {
  id: string;
  filename: string;
  document_type: DocumentType;
  status: string;
  page_count: number | null;
  created_at: string;
}

export type QuestionType =
  | "multiple_choice"
  | "short_answer"
  | "essay_short"
  | "essay_long";

export interface QuestionChoice {
  label: string;
  text: string;
  isAnswer: boolean;
}

export interface GeneratedQuestion {
  id: string;
  number: number;
  question_type: QuestionType;
  difficulty: string;
  bloom_level: string | null;
  stem: string;
  choices: QuestionChoice[] | null;
  answer: string;
  explanation: string | null;
  concepts: string[];
}

export interface GeneratedExam {
  id: string;
  title: string;
  question_count: number;
  questions: GeneratedQuestion[];
  created_at: string;
}

export interface ExamListItem {
  id: string;
  title: string;
  question_count: number;
  created_at: string;
}

export interface ExamStyleProfile {
  id: string;
  document_id: string;
  document_filename: string | null;
  professor_name: string | null;
  subject: string | null;
  analyzed_exam_count: number;
  type_distribution: Record<string, number> | null;
  bloom_distribution: Record<string, number> | null;
  avg_questions_per_exam: number | null;
  common_concepts: string[] | null;
  style_notes: string | null;
  created_at: string;
}

export interface ExamStyleAnalyzeRequest {
  document_id: string;
  professor_name?: string;
  subject?: string;
  raw_text?: string;
}
