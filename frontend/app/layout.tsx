import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DontDelay",
  description: "AI 기반 시험 문제 생성 서비스",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#2563eb",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gray-50 antialiased">
        <nav className="no-print border-b border-gray-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3 text-sm">
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
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
