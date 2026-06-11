export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900">
          DontDelay
        </h1>
        <p className="mt-4 text-lg text-gray-600">
          AI 기반 시험 문제 생성 서비스
        </p>
        <div className="mt-8 flex flex-wrap gap-4 justify-center">
          <a
            href="/documents"
            className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
          >
            문서 관리
          </a>
          <a
            href="/exams/generate"
            className="rounded-lg bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-primary-700 transition-colors"
          >
            문제집 생성
          </a>
          <a
            href="/exams"
            className="rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
          >
            문제집 보기
          </a>
        </div>
      </div>
    </main>
  );
}
