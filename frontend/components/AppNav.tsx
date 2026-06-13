"use client";

import { formatQuota, useAuth } from "@/contexts/AuthContext";

export function AppNav() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <nav className="no-print border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 text-sm">
        <a href="/" className="font-semibold text-gray-900">
          DontDelay
        </a>
        <a href="/documents" className="text-gray-600 hover:text-gray-900">
          문서
        </a>
        <a href="/exam-styles" className="text-gray-600 hover:text-gray-900">
          출제 스타일
        </a>
        <a href="/exams" className="text-gray-600 hover:text-gray-900">
          문제집
        </a>
        <a href="/exams/generate" className="text-gray-600 hover:text-gray-900">
          생성
        </a>
        <div className="ml-auto flex items-center gap-3 text-xs text-gray-500">
          <span className="hidden sm:inline">
            {user.display_name} · 토큰 {formatQuota(user)}
          </span>
          <button
            type="button"
            onClick={() => logout()}
            className="rounded-md border border-gray-200 px-2 py-1 text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          >
            로그아웃
          </button>
        </div>
      </div>
    </nav>
  );
}
