# DontDelay - AI 기반 시험 문제 생성 웹 애플리케이션 개발 계획서

## 1. 프로젝트 개요

### 1.1 목표
대학교 강의자료 PDF와 과거 시험자료를 업로드하면, 서버가 문서를 분석하고 강의 내용에 근거한 시험 대비 문제집을 자동 생성하는 웹 애플리케이션을 개발한다. 사용자는 브라우저에서 PDF를 업로드하고 문제 생성 조건을 입력하며, 생성된 문제집을 웹에서 바로 확인하고 풀 수 있다. PWA(Progressive Web App)를 적용하여 앱과 유사한 사용 경험을 제공한다.

백엔드는 Python FastAPI로 구현한다. 본 프로젝트의 핵심 로직(embedding, RAG, OCR, LLM, Knowledge Tracing)이 Python 생태계에 집중되어 있으므로, Python 단일 백엔드가 개발 속도와 AI/ML 접근성 면에서 유리하다. 모든 인프라는 Mac mini 서버에서 Docker Compose로 자체 운영하며, AWS 등 외부 클라우드 인프라를 사용하지 않는다. 파일 저장은 S3 호환 오브젝트 스토리지인 MinIO를 사용한다.

생성 결과의 정본은 구조화된 JSON이다.

- 구조화된 JSON: 문제, 정답, 해설, 출처, 개념 태그 (DB 저장, API 조회)
- 웹 렌더링: Next.js에서 JSON을 문제집 UI로 표시, 온라인 풀이 지원
- 선택적 PDF보내기 (고도화): 브라우저 인쇄(print stylesheet) 또는 HTML 기반 PDF export

### 1.2 핵심 가치

- 강의자료에 근거한 문제 생성
- 과목별·시험범위별 문제집 생성
- 교수의 과거 시험유형 또는 사용자의 요청 반영
- 객관식, 단답형, 짧은 서술형, 긴 서술형 지원
- 생성 문제의 출처 추적
- 웹에서 바로 문제 풀이 및 시간 측정
- 풀이 기록을 활용한 취약 개념 분석 및 개인화 문제 추천
- 외부 클라우드 없이 Mac mini 자체 운영

---

## 2. 서비스 범위

### 2.1 MVP 범위

1. PDF 업로드 및 MinIO 저장 (강의자료 / 족보 구분)
2. PyMuPDF 기반 텍스트 추출
3. 텍스트 추출 실패 시 OCR fallback
4. 문서 chunking 및 embedding 생성
5. PostgreSQL + pgvector 저장
6. RAG 기반 관련 chunk 검색
7. 족보(과거 시험) 업로드 및 출제 스타일 분석
8. LLM 기반 문제·정답·해설 생성 (족보 스타일 반영 토글 포함)
9. 생성 문제 JSON 저장 및 웹 렌더링 (미리보기, 온라인 풀이)
10. 웹 애플리케이션에서 업로드, 상태 확인, 문제집 생성, 브라우저 인쇄
11. 웹 기반 온라인 문제 풀이 및 시간 측정
12. PWA 적용

### 2.2 고도화 범위

#### UX 개선
1. SSE(Server-Sent Events) 기반 실시간 생성 진행 상태 스트리밍
2. 생성 문제 웹 편집 및 개별 재생성
3. PDF 목차 파싱 기반 시험 범위 시각적 선택
4. 과목별·학기별 워크스페이스 관리
5. HTML 기반 PDF export (Playwright/Chromium 또는 WeasyPrint)

#### 문제 생성 품질 고도화
5. Reranker를 활용한 검색 품질 개선
6. Bloom's Taxonomy 기반 난이도 및 인지 수준 제어
7. 오개념 기반 객관식 distractor 생성
8. 교수 출제 패턴 분석 시각화 (Bloom 수준·유형 분포 차트)

#### 학습 분석 고도화
9. 사용자 풀이 기록 저장 및 규칙 기반 취약 개념 분석
10. BKT 기반 Knowledge Tracing 적용
11. pyKT 기반 딥러닝 Knowledge Tracing 실험
12. AI 코치 및 시험기간 모드 연동

#### 비용 절감
13. 로컬 임베딩 모델 적용 (multilingual-e5-large, bge-m3 등)으로 API 비용 제거

#### 소셜 기능
14. 스터디 그룹: 자료 공유 및 통합 문제집 생성

---

## 3. 전체 아키텍처

```text
[사용자 브라우저 / PWA]
        |
        | HTTPS
        v
[Mac mini 서버 - Docker Compose]
        |
        |-- [Nginx Container]
        |     - HTTPS 종료 (Let's Encrypt)
        |     - Reverse Proxy
        |
        |-- [Next.js Frontend Container]
        |     - PDF 드래그 앤 드롭 업로드
        |     - 생성 옵션 입력 (시험 범위 시각적 선택)
        |     - SSE 기반 실시간 진행 상태 표시
        |     - 온라인 문제 풀이 및 시간 측정
        |     - 생성 문제 편집·재생성
        |     - 과목별 워크스페이스
        |     - PWA 지원
        |
        |-- [FastAPI Backend Container]
        |     - 인증 및 사용자별 데이터 격리
        |     - PDF 업로드 API
        |     - MinioStorageClient (boto3)
        |     - PyMuPDF 텍스트 추출
        |     - OcrClient
        |     - ChunkService
        |     - EmbeddingService (sentence-transformers / OpenAI)
        |     - RagService (pgvector 검색)
        |     - ExamGenerationService (LLM 호출)
        |     - ExamExportService (선택적 HTML PDF export, 고도화)
        |     - SSE 스트리밍
        |     - pyKT Knowledge Tracing (고도화)
        |
        |-- [PostgreSQL + pgvector Container]
        |     - 문서 메타데이터
        |     - chunk 본문
        |     - embedding vector
        |     - 생성 문제 JSON
        |     - Job 상태
        |     - 풀이 기록
        |     - 워크스페이스·스터디 그룹
        |
        |-- [MinIO Container]
        |     - S3 호환 오브젝트 스토리지
        |     - 원본 PDF (강의자료, 족보)
        |     - 선택적 export PDF 캐시 (고도화)
        |
        |-- [선택: OCR Worker Container]
        |     - 로컬 OCR 사용 시 Tesseract 또는 PaddleOCR 실행
        |
        +-- [외부 API]
              - OpenAI / Claude API (문제 생성 LLM)
              - OpenAI Embedding API (로컬 임베딩 전환 전까지)
              - Upstage OCR 또는 대체 OCR API
```

### 3.1 기술 스택 결정 근거

#### 백엔드: FastAPI (Python)

| 기준 | Spring Boot (Java) | FastAPI (Python) |
|---|---|---|
| AI/ML 생태계 접근성 | OpenAI API 호출만 가능, ML 라이브러리 부족 | LangChain, LlamaIndex, sentence-transformers, pyKT 직접 사용 |
| 임베딩 처리 | 외부 API 호출 필수 | 로컬 모델 직접 로드 가능 (sentence-transformers) |
| Knowledge Tracing | 별도 Python 서비스 필요 (이중 구조) | 같은 프로세스에서 pyKT 직접 호출 |
| PDF 텍스트 추출 | PDFBox (Java) | PyMuPDF (더 빠르고 정확) |
| 개발 속도 | 보일러플레이트가 많음 | 코드량이 적고 프로토타이핑이 빠름 |
| 비동기 처리 | Spring WebFlux 또는 @Async | async/await 네이티브 지원 |
| SSE 스트리밍 | SseEmitter (제한적) | StreamingResponse (자연스러움) |

본 프로젝트의 핵심 로직(embedding, RAG, OCR, LLM, KT)이 모두 Python 생태계에 있으므로, Spring Boot에서 Python ML 서비스를 호출하는 이중 구조 대신 FastAPI 단일 백엔드로 통일한다.

#### 프론트엔드: Next.js

- App Router 기반 페이지 라우팅
- SSE 클라이언트 연동이 용이
- PWA 설정이 간단 (next-pwa)
- Tailwind CSS를 활용한 빠른 UI 개발

### 3.2 역할 분리

| 구성 요소 | 역할 |
|---|---|
| Next.js Frontend | PDF 업로드, 시험 범위 선택, 생성 옵션 입력, JSON 문제집 렌더링, 실시간 상태 조회, 온라인 풀이·타이머, 문제 편집, 브라우저 인쇄, PWA |
| Nginx Container | HTTPS, reverse proxy, 외부 요청 진입점 |
| FastAPI Backend Container | 전체 비즈니스 로직, embedding, RAG, LLM 호출, SSE 스트리밍, 보안, Job 관리 |
| PostgreSQL + pgvector Container | 일반 데이터, RAG용 vector, 풀이 기록, 워크스페이스 저장 |
| MinIO Container | S3 호환 오브젝트 스토리지, 업로드 PDF 저장 (export PDF는 고도화 시 선택) |
| Mac mini 서버 | Docker Compose 기반 전체 서비스 운영 (Apple Silicon) |
| Upstage OCR 또는 대체 OCR API | 이미지 기반 PDF의 텍스트 추출 |
| OpenAI / Claude API | 문제·정답·해설 생성 |
| pgvector | RAG용 vector 검색 |

### 3.3 배포 원칙

- 외부에 공개하는 포트는 기본적으로 `80`, `443`만 사용한다.
- PostgreSQL 포트 `5432`와 MinIO 포트 `9000`은 외부에 공개하지 않고 Docker 내부 네트워크에서만 접근한다.
- MinIO 웹 콘솔 `9001`은 관리 목적으로만 내부에서 접근한다.
- FastAPI 포트도 Nginx를 통해서만 접근하도록 구성한다.
- DB 데이터와 MinIO 데이터는 Docker volume에 저장하고 정기적으로 백업한다.
- API 키는 `.env` 또는 서버 환경변수로 관리하며 Git에 올리지 않는다.
- 원본 PDF는 MinIO에 저장하고 Docker volume 단위로 백업한다. 생성 문제집의 정본은 PostgreSQL JSON이다.

## 4. 문제 생성 파이프라인

### 4.1 문서 업로드 및 인덱싱

```text
PDF 업로드 (드래그 앤 드롭)
→ FastAPI 수신
→ MinIO 원본 저장
→ PyMuPDF 텍스트 추출
→ 텍스트가 부족하면 OCR fallback
→ 페이지·문단 기준 chunking
→ embedding 생성 (sentence-transformers 또는 OpenAI)
→ PostgreSQL + pgvector 저장
→ SSE로 진행 상태 스트리밍
→ 문서 상태 READY
```

### 4.2 족보(과거 시험) 업로드 및 출제 스타일 분석

```text
족보 PDF 또는 텍스트 업로드
→ document_type = "past_exam" 으로 구분
→ PyMuPDF / OCR로 텍스트 추출
→ LLM으로 기존 문제를 구조화 분석:
   - 문제 유형 (객관식, 단답형, 서술형 등)
   - 난이도 추정
   - Bloom 수준 분류
   - 출제 개념 추출
   - 문제 형식 패턴 (지문 길이, 보기 수, 배점 구조 등)
→ 분석 결과를 exam_style_profile 테이블에 저장
→ 해당 과목/교수의 출제 스타일 프로필 생성
```

분석 결과 JSON 예시:

```json
{
  "profileId": "style-uuid-1",
  "professorName": "김교수",
  "subject": "운영체제",
  "analyzedExamCount": 3,
  "typeDistribution": {
    "multiple_choice": 30,
    "short_answer": 20,
    "essay_short": 30,
    "essay_long": 20
  },
  "bloomDistribution": {
    "remember": 10,
    "understand": 20,
    "apply": 40,
    "analyze": 30
  },
  "avgQuestionsPerExam": 25,
  "commonConcepts": ["프로세스", "스레드", "동기화", "데드락", "페이징"],
  "styleNotes": "서술형에서 두 개념을 비교하는 문제를 자주 출제, 코드 분석 문제 포함"
}
```

### 4.3 시험 문제 생성

```text
사용자 요청 입력
예: 운영체제 Chapter 3~5 선택, 서술형 10문제, 난이도 중

[족보 스타일 반영 옵션]
☑ 김교수 출제 스타일 반영 (토글 ON/OFF)
  → ON: exam_style_profile을 LLM 프롬프트에 포함
  → 유형 비율, 난이도 분포, 문제 형식을 족보 패턴에 맞춤
  → OFF: 사용자가 직접 지정한 옵션만 사용

→ 요청 embedding 생성
→ pgvector 유사도 검색
→ 관련 chunk 수집
→ 필요 시 reranker로 재정렬
→ LLM 문제 생성 (OpenAI / Claude)
   - 족보 스타일 ON 시: 프롬프트에 스타일 프로필 + 예시 문제 형식 포함
→ 구조화 JSON 검증
→ generated_question / generated_exam DB 저장
→ SSE로 "문제 3/10 생성 중..." 스트리밍
→ 웹에서 문제집 미리보기·온라인 풀이 제공
→ (선택) 브라우저 인쇄 또는 HTML 기반 PDF export
```

### 4.4 생성 문제 JSON 예시

```json
{
  "number": 1,
  "type": "short_answer",
  "difficulty": "medium",
  "bloomLevel": "understand",
  "stem": "세션 기반 인증에서 세션 ID 탈취가 위험한 이유를 설명하시오.",
  "answer": "서버는 세션 ID를 기준으로 사용자를 식별하므로, 공격자가 탈취한 세션 ID를 사용해 정상 사용자처럼 요청할 수 있다.",
  "explanation": "세션 ID는 인증 상태를 식별하는 핵심 값이므로 노출 방지가 중요하다.",
  "concepts": ["session", "session_hijacking", "authentication"],
  "sourceChunkIds": ["chunk-uuid-1"]
}
```

---

## 5. RAG 사용 이유

짧은 PDF 한두 개는 OCR 텍스트 전체를 LLM에 넣어 문제를 생성할 수 있다. 그러나 본 프로젝트는 여러 강의자료 PDF와 반복 생성 요청을 처리하므로 RAG 구조를 기본으로 사용한다.

| 전체 텍스트 직접 입력 | RAG 기반 입력 |
|---|---|
| 구현이 단순함 | 초기 구현이 조금 더 복잡함 |
| PDF가 길어질수록 비용 증가 | 관련 chunk만 전달하므로 비용 절감 |
| 특정 범위 제어가 어려움 | 주차·개념·페이지별 검색 가능 |
| 출처 추적이 어려움 | chunk ID와 페이지 정보 연결 가능 |
| AI 코치에 재사용하기 어려움 | 요약, 복습 추천, 약점 문제 생성에 재사용 가능 |

### 5.1 생성 모드 권장안

```text
FULL_CONTEXT 모드
- 짧은 문서 또는 빠른 MVP 데모
- OCR 텍스트 전체를 LLM에 전달

RAG 모드
- 여러 PDF 또는 긴 강의자료
- 관련 chunk만 검색하여 LLM에 전달
```

---

## 6. RAG 검색 품질 고도화

### 6.1 1차 검색

```text
사용자 요청 embedding
→ pgvector cosine similarity 검색
→ topK chunk 반환
```

### 6.2 2차 검색: Reranker

초기에는 pgvector 검색만 사용한다. 검색 품질이 부족한 경우 reranker를 추가한다.

후보:

| 후보 | 특징 | 적용 시점 |
|---|---|---|
| BGE reranker | 오픈소스, 자체 운영 가능 | 비용 절감이 중요할 때 |
| Jina reranker | API 또는 모델 기반 선택 가능 | 빠른 고도화가 필요할 때 |
| Cohere Rerank API | 구현이 간단함 | 외부 API 비용을 허용할 때 |

권장 흐름:

```text
pgvector top 30
→ reranker 재정렬
→ 상위 8~15개 chunk만 LLM에 전달
```

### 6.3 로컬 임베딩 모델을 통한 비용 절감

Mac mini(Apple Silicon)에서 로컬 임베딩 모델을 실행하면 OpenAI embedding API 비용을 완전히 제거할 수 있다.

| 모델 | 특징 | 차원 | 적합성 |
|---|---|---|---|
| intfloat/multilingual-e5-large | 다국어 성능 우수, 한국어 지원 | 1024 | 권장 |
| BAAI/bge-m3 | 다국어, 경량, 빠른 추론 | 1024 | 리소스 절약 시 |
| OpenAI text-embedding-3-small | API 기반, 별도 GPU 불필요 | 1536 | 초기 MVP |

적용 전략:

```text
MVP 초기: OpenAI embedding API 사용 (빠른 구현)
고도화: sentence-transformers로 로컬 모델 전환
        → EMBEDDING_PROVIDER 환경 변수로 전환
        → embedding_client.py에서 provider별 분기
```

로컬 모델 사용 시 sentence-transformers로 모델을 로드하고, FastAPI 시작 시 한 번만 로딩하여 요청마다 재사용한다. Apple Silicon의 MPS 가속을 활용할 수 있다.

LLM 호출(문제 생성)은 품질상 OpenAI/Claude를 유지하되, 임베딩과 reranking은 로컬로 처리하면 API 비용의 상당 부분을 절약할 수 있다.

---

## 7. 문제 생성 품질 고도화

### 7.1 핵심 개념 기반 생성

단순히 "문제 10개 생성"을 요청하지 않고 다음 순서로 생성한다.

```text
검색된 chunk
→ 핵심 개념 추출
→ 정답 후보(answer phrase) 추출
→ 문제 유형과 난이도 지정
→ 문제 생성
→ 문제-정답 정합성 검증
```

### 7.2 Bloom's Taxonomy 반영

| 수준 | 생성 예시 |
|---|---|
| Remember | 용어 정의, 기본 개념 확인 |
| Understand | 개념 의미 설명 |
| Apply | 사례에 개념 적용 |
| Analyze | 두 개념 비교, 원인 분석 |
| Evaluate | 방식의 장단점 판단 |
| Create | 설계형 서술 문제 |

사용자는 문제집 생성 시 원하는 비율을 선택할 수 있다.

```json
{
  "remember": 20,
  "understand": 30,
  "apply": 30,
  "analyze": 20
}
```

### 7.3 객관식 distractor 생성

객관식 오답은 단순한 헛소리가 아니라 학습자가 자주 혼동하는 오개념을 반영하도록 한다.

```json
{
  "label": "B",
  "text": "세션 정보는 항상 클라이언트에 저장된다.",
  "isAnswer": false,
  "misconception": "쿠키와 세션 저장 위치를 혼동함"
}
```

---

## 8. 풀이 이력 기반 취약 개념 분석 및 KT 확장

### 8.1 목적

MVP에서는 Knowledge Tracing이라는 이름을 전면에 내세우기보다, 풀이 이력 기반 취약 개념 분석을 구현한다. 사용자가 생성된 문제를 풀면 정오답, 풀이 시간, 시도 횟수, 힌트 사용 여부를 저장하고, 규칙 기반으로 개념별 숙련도를 계산하여 다음 문제 생성과 AI 코치 추천에 반영한다.

이후 데이터가 쌓이면 BKT(Bayesian Knowledge Tracing)를 적용하고, 장기 고도화 단계에서 pyKT 기반 딥러닝 KT 모델을 실험한다.

```text
문제 풀이
→ 문항별 상호작용 기록 저장
→ 문제에 연결된 concepts 조회
→ 개념별 숙련도 업데이트
→ 취약 개념 및 과잉 반복 개념 추출
→ 관련 chunk RAG 검색
→ 취약 개념 중심 문제 재생성
→ AI 코치가 복습 순서와 학습 전략 추천
```

### 8.2 필요한 데이터

| 필드 | 설명 |
|---|---|
| user_id | 사용자 ID |
| exam_id | 사용자가 푼 시험 ID |
| question_id | 문제 ID |
| concept_ids | 문제에 연결된 개념 ID 목록 |
| is_correct | 정답 여부 |
| selected_answer | 사용자가 선택하거나 입력한 답 |
| score | 부분 점수 또는 채점 점수 |
| timestamp | 풀이 시각 |
| response_time_ms | 응답 시간 |
| attempt_count | 재시도 횟수 |
| hint_used | 힌트 사용 여부 |
| confidence | 사용자가 표시한 자신감 (선택) |
| difficulty | 문제 난이도 |
| bloom_level | Bloom 수준 |

### 8.3 단계별 적용

#### 1차: 규칙 기반 분석

MVP에서는 복잡한 딥러닝 모델보다 해석 가능한 규칙 기반 숙련도 계산을 먼저 적용한다.

```text
개념별 정답률 = 해당 개념 정답 수 / 해당 개념 풀이 수
시간 보정 = 평균 풀이 시간보다 오래 걸린 정답은 낮은 가중치
최근성 보정 = 최근 풀이 기록에 더 높은 가중치

숙련도 예시:
mastery = 0.6 * 정답률 + 0.2 * 시간 점수 + 0.2 * 최근성 점수
```

개념별 상태는 다음처럼 분류한다.

| 상태 | 조건 예시 | 활용 |
|---|---|---|
| weak | 숙련도 < 0.45 또는 최근 3문제 중 2문제 이상 오답 | 취약 개념 문제 재생성 |
| learning | 0.45 <= 숙련도 < 0.75 | 유사 난이도 반복 |
| strong | 숙련도 >= 0.75 | 더 높은 Bloom 수준 문제 추천 |
| stale | 과거에는 strong이었지만 오래 풀지 않음 | 짧은 복습 문제 추천 |

#### 2차: BKT 기반 Knowledge Tracing

풀이 데이터가 어느 정도 쌓이면 BKT를 적용한다. BKT는 데이터가 적은 초기 단계에서도 해석 가능성이 높고, 개념별 숙련도를 확률로 표현하기 좋다.

```text
P(L0): 초기 숙련 확률
P(T): 학습 전이 확률
P(G): 찍어서 맞힐 확률
P(S): 알고도 틀릴 확률

문제 풀이 결과 입력
→ 개념별 P(learned | history) 업데이트
→ 다음 문제 정답 확률 예측
```

적용 예:

```text
동기화 개념 mastery = 0.38
데드락 개념 mastery = 0.71
스레드 개념 mastery = 0.82

추천:
- 동기화: 기본 개념 확인 문제 3개
- 데드락: 적용 문제 2개
- 스레드: Analyze 수준 비교 문제 1개
```

#### 3차: pyKT 기반 딥러닝 KT 실험

```text
사용자 풀이 sequence
→ FastAPI 내부 KT 모듈
→ pyKT 모델 추론
→ 다음 문제 정답 확률 및 취약 개념 반환
```

FastAPI(Python) 단일 백엔드이므로 별도 ML 서비스 없이 같은 프로세스에서 pyKT/PyTorch를 직접 호출한다. 모델 로딩은 앱 시작 시 수행하고, 추론은 비동기로 처리한다.

pyKT 후보 모델:

| 모델 | 특징 | 적용 시점 |
|---|---|---|
| DKT | LSTM 기반 기본 KT 모델 | 풀이 sequence가 충분히 쌓인 뒤 |
| DKVMN | 메모리 네트워크 기반, 개념 상태 추적에 유리 | 개념 수가 많아질 때 |
| AKT | Attention 기반, 장기 의존성 반영 | 데이터가 충분히 많을 때 |
| SAKT | Self-Attention 기반, 구현과 추론이 비교적 단순 | pyKT 실험용 |

초기에는 규칙 기반 → BKT → pyKT 순서로 확장한다. pyKT는 MVP의 필수 기능이 아니라, 사용자 풀이 데이터가 충분히 누적되고 문제-concept 태깅 품질이 안정된 이후 연구·고도화 모듈로 둔다.

### 8.4 개인화 문제 생성 방식

Knowledge Tracing 결과는 문제 생성 옵션에 직접 반영한다.

```text
사용자 숙련도 조회
→ weak concepts 추출
→ weak concept와 연결된 document_chunk 검색
→ 사용자 현재 수준에 맞는 Bloom 비율 결정
→ LLM 문제 생성 프롬프트에 개인화 조건 추가
```

예시:

```json
{
  "targetUserId": "user-uuid",
  "weakConcepts": ["deadlock", "mutex", "critical_section"],
  "mastery": {
    "deadlock": 0.32,
    "mutex": 0.41,
    "critical_section": 0.47
  },
  "recommendedBloomMix": {
    "remember": 30,
    "understand": 40,
    "apply": 30
  },
  "generationInstruction": "취약 개념 위주로 기본 개념 확인과 적용 문제를 섞어서 생성한다."
}
```

### 8.5 AI 코치 연동

AI 코치는 KT 결과를 설명 가능한 문장으로 바꿔 사용자에게 제공한다.

```text
오늘의 추천:
1. 임계 구역 개념을 먼저 복습하세요. 최근 4문제 중 3문제를 틀렸고 풀이 시간이 평균보다 길었습니다.
2. 데드락은 정답률은 높지만 Apply 문제에서 약합니다. 사례 적용 문제를 2개 더 풀어보세요.
3. 스레드는 숙련도가 높으므로 긴 서술형 비교 문제로 넘어가도 됩니다.
```

AI 코치가 사용하는 입력:

- 개념별 숙련도
- 최근 오답 개념
- 풀이 시간 변화
- 문제 난이도별 정답률
- Bloom 수준별 정답률
- 시험일까지 남은 기간 (시험기간 모드)

---

## 9. 고도화 기능 상세

### 9.1 SSE 기반 실시간 진행 상태

문제 생성이 수 분 걸릴 수 있으므로 실시간 진행률 표시가 중요하다. FastAPI의 `StreamingResponse`를 활용한다.

```text
클라이언트 → GET /api/jobs/{jobId}/stream
서버 → SSE 스트림:
  data: {"stage": "EXTRACTING", "progress": 30, "message": "텍스트 추출 중..."}
  data: {"stage": "GENERATING", "progress": 50, "message": "문제 3/10 생성 중..."}
  data: {"stage": "FINALIZING", "progress": 90, "message": "문제집 저장 중..."}
  data: {"stage": "COMPLETED", "progress": 100, "message": "완료"}
```

프론트엔드는 `useSSE` 커스텀 훅으로 연결을 관리하고, 연결 끊김 시 자동 재연결한다.

### 9.2 시험 범위 시각적 선택

PDF 업로드 시 PyMuPDF로 목차(Table of Contents)를 파싱하여 DB에 저장한다. 사용자는 텍스트 입력 대신 체크박스로 범위를 선택한다.

```text
PDF 업로드
→ PyMuPDF toc 추출: doc.get_toc()
→ document_toc 테이블 저장: [level, title, page_number]
→ 프론트엔드 체크박스 트리 렌더링

예시:
☑ Chapter 3: 프로세스 관리 (p.45~62)
☑ Chapter 4: 스레드 (p.63~80)
☐ Chapter 5: CPU 스케줄링 (p.81~100)
☑ Chapter 6: 동기화 (p.101~120)

→ 선택된 범위의 page 번호로 chunk 필터링
→ 필터링된 chunk에 대해서만 RAG 검색
```

목차가 없는 PDF는 페이지 번호 범위 입력으로 fallback한다.

### 9.3 생성 문제 편집 및 재생성

LLM이 생성한 문제를 사용자가 확인하고 커스터마이징할 수 있다.

```text
문제집 생성 완료
→ 미리보기 화면에서 전체 문제 목록 표시
→ 개별 문제에 대해:
   - 직접 수정 (문제, 정답, 해설 텍스트 편집)
   - 삭제 (불필요한 문제 제거)
   - 재생성 ("이 문제를 더 어렵게" 등 조건 지정 후 해당 문제만 재생성)
→ 최종 확인 후 웹에서 바로 사용 (선택적으로 export API로 PDF 생성)
```

### 9.4 과목별·학기별 워크스페이스

여러 과목을 관리하는 학생을 위해 자료와 문제집을 과목 단위로 묶어 관리한다.

```text
워크스페이스 예시:
├── 2024-2학기 운영체제
│   ├── 강의자료: OS_ch01.pdf, OS_ch02.pdf, ...
│   ├── 과거시험: midterm_2023.pdf
│   └── 문제집: 중간고사 대비 #1, #2
├── 2024-2학기 데이터베이스
│   ├── 강의자료: DB_week01.pdf, ...
│   └── 문제집: 기말고사 대비 #1
```

### 9.5 스터디 그룹 (고도화)

같은 수업을 듣는 학생들이 자료를 공유하고, 각자 생성한 문제를 모아 통합 문제집을 만든다.

```text
그룹 생성 → 초대 링크 공유 → 멤버 참여
→ 멤버별 생성 문제집 공유
→ 통합 문제집 생성 (중복 제거, 난이도 균형 조정)
→ 그룹원 모두 다운로드 가능
```

### 9.6 교수 출제 패턴 분석 시각화 (고도화)

MVP에서 저장된 `exam_style_profile` 데이터를 차트로 시각화하여 더 직관적인 인사이트를 제공한다.

```text
exam_style_profile 데이터 기반 시각화:
  - Bloom 수준 분포 도넛 차트
  - 문제 유형 분포 막대 차트
  - 주요 출제 개념 TOP 10 워드 클라우드
  - 시험별 난이도 추이 (족보가 여러 개일 때)
  - "이 교수는 Apply 수준 40%, 서술형 비교 문제를 선호합니다" 요약 텍스트

여러 족보 비교:
  - 중간고사 vs 기말고사 출제 패턴 비교
  - 연도별 출제 트렌드 변화
```

---

## 10. DB 설계

### 10.1 주요 테이블

| 테이블 | 역할 |
|---|---|
| users | 사용자 정보 |
| workspace | 과목별·학기별 워크스페이스 |
| study_document | 업로드 문서 메타데이터 (type: lecture / past_exam) |
| document_toc | PDF 목차 정보 (시험 범위 선택용) |
| exam_style_profile | 족보 분석 결과: 유형·난이도·Bloom 분포, 출제 패턴 |
| document_chunk | chunk 본문, 페이지 번호, embedding |
| exam_generation_job | 비동기 시험 생성 Job |
| generated_exam | 생성 시험 메타데이터 (선택적 export PDF 캐시 키) |
| generated_question | 문제, 답안, 해설, 출처 (수정 이력 포함) |
| question_concept | 문제와 개념 연결 |
| user_answer | 사용자 풀이 기록 (풀이 시간 포함) |
| question_interaction | 풀이 이벤트 로그: 시도, 힌트, 정답 변경, 체류 시간 |
| user_concept_mastery | 개념별 숙련도 (규칙 기반/BKT 결과) |
| kt_model_snapshot | pyKT/BKT 모델 버전 및 파라미터 스냅샷 |
| kt_prediction | 문항·개념별 다음 정답 확률 예측 결과 |
| study_group | 스터디 그룹 (고도화) |
| group_member | 그룹 멤버 (고도화) |

### 10.2 Job 상태

#### 문서 처리 상태

```text
UPLOADED → EXTRACTING → INDEXING → READY
                         ↘ FAILED
```

#### 시험 생성 상태

```text
PENDING → GENERATING → FINALIZING → COMPLETED
                         ↘ FAILED
```

---

## 11. FastAPI 백엔드 프로젝트 구조

```text
backend/
├── app/
│   ├── main.py                    # FastAPI 앱 생성, 라우터 등록
│   ├── config.py                  # 환경 변수 로딩 (Pydantic Settings)
│   ├── database.py                # SQLAlchemy + asyncpg 세션
│   │
│   ├── routers/
│   │   ├── documents.py           # PDF 업로드, 문서 목록·상태 조회
│   │   ├── jobs.py                # 문제집 생성 Job 등록·상태 조회·SSE 스트리밍
│   │   ├── exams.py               # 시험 JSON 조회, 선택적 PDF export, 문제 편집·재생성
│   │   ├── solve.py               # 풀이 결과 제출
│   │   ├── learning.py            # 취약 개념 조회
│   │   ├── workspaces.py          # 과목별 워크스페이스 관리
│   │   └── auth.py                # 인증·세션 관리
│   │
│   ├── models/
│   │   ├── user.py                # User
│   │   ├── document.py            # StudyDocument, DocumentChunk
│   │   ├── exam_style.py          # ExamStyleProfile (족보 분석 결과)
│   │   ├── exam.py                # ExamGenerationJob, GeneratedExam, GeneratedQuestion
│   │   ├── concept.py             # QuestionConcept
│   │   ├── answer.py              # UserAnswer, UserConceptMastery
│   │   └── workspace.py           # Workspace, StudyGroup
│   │
│   ├── schemas/                   # Pydantic 요청·응답 스키마
│   │
│   ├── services/
│   │   ├── document_service.py    # 업로드, 목차 파싱
│   │   ├── extraction_service.py  # PyMuPDF 텍스트 추출
│   │   ├── chunk_service.py       # chunking
│   │   ├── embedding_service.py   # sentence-transformers 또는 OpenAI
│   │   ├── rag_service.py         # pgvector 검색 + reranker
│   │   ├── exam_style_service.py  # 족보 분석 → 출제 스타일 프로필 생성
│   │   ├── exam_generation_service.py  # LLM 문제 생성 (스타일 프로필 반영)
│   │   ├── exam_export_service.py # 선택적 HTML → PDF export (고도화)
│   │   ├── learning_service.py    # 규칙 기반 취약 개념 분석
│   │   └── kt_service.py          # pyKT Knowledge Tracing (고도화)
│   │
│   ├── workers/
│   │   ├── document_indexing.py   # 비동기 문서 인덱싱 태스크
│   │   └── exam_generation.py     # 비동기 시험 생성 태스크
│   │
│   └── infra/
│       ├── minio_client.py        # MinIO (boto3)
│       ├── ocr_client.py          # Upstage OCR 또는 대체 OCR
│       ├── llm_client.py          # OpenAI / Claude API 호출
│       └── embedding_client.py    # 로컬 모델 또는 OpenAI embedding
│
├── requirements.txt
├── Dockerfile
└── alembic/                       # DB 마이그레이션
    └── versions/
```

### 11.1 주요 의존성

```text
fastapi, uvicorn          # 웹 프레임워크
sqlalchemy, asyncpg        # 비동기 ORM + PostgreSQL
alembic                    # DB 마이그레이션
boto3                      # MinIO (S3 호환) 클라이언트
pymupdf (fitz)             # PDF 텍스트 추출
sentence-transformers      # 로컬 임베딩 모델
pgvector                   # SQLAlchemy pgvector 지원
openai                     # OpenAI / Claude API
httpx                      # 비동기 HTTP 클라이언트 (OCR API 등)
pydantic-settings          # 환경 변수 관리
celery / arq               # 비동기 Job 큐 (선택)
```

---

## 12. 웹 프론트엔드 기능 구조

웹 프론트엔드는 `Next.js` 기반으로 구현한다. 페이지 라우팅, API 연동, 로그인 상태 관리, 파일 업로드 UI를 구성하기 쉽기 때문이다. PWA를 적용하여 홈 화면 추가 시 앱과 유사한 경험을 제공한다.

```text
frontend/
├── app/
│   ├── login/
│   │   └── page.tsx
│   ├── workspaces/
│   │   ├── page.tsx                    # 과목별 워크스페이스 목록
│   │   └── [workspaceId]/
│   │       ├── page.tsx                # 워크스페이스 대시보드
│   │       └── documents/
│   │           └── page.tsx
│   ├── documents/
│   │   └── page.tsx
│   ├── exams/
│   │   ├── generate/
│   │   │   └── page.tsx
│   │   └── [examId]/
│   │       ├── page.tsx                # 문제 미리보기·편집
│   │       └── edit/
│   │           └── page.tsx            # 개별 문제 수정·재생성
│   ├── solve/
│   │   └── [examId]/
│   │       └── page.tsx
│   ├── results/
│   │   └── [examId]/
│   │       └── page.tsx
│   └── groups/
│       └── [groupId]/
│           └── page.tsx                # 스터디 그룹 (고도화)
├── components/
│   ├── PdfUploadForm.tsx               # 드래그 앤 드롭 PDF 업로드 (강의자료/족보 구분)
│   ├── PastExamUploadForm.tsx          # 족보 전용 업로드 (PDF 또는 텍스트 입력)
│   ├── ExamStyleToggle.tsx             # 족보 스타일 반영 ON/OFF 토글 + 프로필 선택
│   ├── ExamStyleSummary.tsx            # 족보 분석 결과 요약 표시
│   ├── DocumentStatusCard.tsx
│   ├── ChapterRangeSelector.tsx        # 목차 기반 시험 범위 선택
│   ├── ExamGenerationForm.tsx
│   ├── ExamPreview.tsx
│   ├── ExamPrintView.tsx               # print stylesheet 기반 브라우저 인쇄/저장
│   ├── QuestionEditor.tsx              # 문제 편집·재생성
│   ├── QuestionSolver.tsx              # 온라인 풀이
│   ├── TimerDisplay.tsx                # 풀이 시간 측정
│   ├── ProgressStream.tsx              # SSE 진행 상태
│   ├── WeakConceptChart.tsx
│   ├── ProfessorPatternChart.tsx       # 교수 출제 패턴 시각화 (고도화)
│   └── WorkspaceCard.tsx
├── hooks/
│   ├── useTimer.ts                     # Web Worker 기반 정확한 타이머
│   ├── useSSE.ts                       # SSE 연결 관리
│   └── usePageVisibility.ts            # 탭 이탈 감지
├── lib/
│   ├── api.ts
│   └── auth.ts
├── public/
│   └── manifest.json
└── package.json
```

### 12.1 주요 화면

| 화면 | 기능 |
|---|---|
| 로그인 | 세션 로그인 |
| 워크스페이스 | 과목별·학기별 자료와 문제집 통합 관리 |
| 문서 목록 | 과목별 PDF 조회 (강의자료·족보 구분), 처리 상태 확인 |
| 강의자료 업로드 | PDF 드래그 앤 드롭 업로드, 과목명 입력 |
| 족보 업로드 | 과거 시험 PDF 또는 텍스트 직접 입력, 교수명·시험 유형(중간/기말) 입력 |
| 족보 분석 결과 | 출제 스타일 프로필 요약 (유형 비율, Bloom 분포, 주요 개념, 문제 형식 특징) |
| 시험 범위 선택 | PDF 목차 파싱 결과를 체크박스로 시각적 선택 |
| 생성 옵션 | 문제 수, 유형, 난이도, Bloom 수준 선택 + **족보 스타일 반영 토글** |
| 생성 진행 | SSE 기반 실시간 진행 상태 표시 ("문제 3/10 생성 중...") |
| 미리보기·편집 | 생성 문제 확인, 개별 문제 수정·삭제·재생성 |
| 인쇄/저장 | 브라우저 인쇄(print stylesheet)로 오프라인 학습용 PDF 저장 |
| 온라인 풀이 | Web Worker 기반 문제별 타이머, 풀이 시간 측정, 자동 채점, 즉각 피드백 |
| 결과 분석 | 점수, 오답, 풀이 시간, 취약 개념 확인 |
| 교수 패턴 차트 | 족보 분석 기반 Bloom 수준·유형 분포 시각화 (고도화) |
| 스터디 그룹 | 자료 공유, 통합 문제집 생성 (고도화) |

## 13. API 개요

### 13.1 문서 관리

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/documents` | PDF 업로드 (type: lecture / past_exam) |
| GET | `/api/documents` | 문서 목록 (강의자료·족보 필터) |
| GET | `/api/documents/{documentId}` | 문서 처리 상태 |
| GET | `/api/documents/{documentId}/toc` | PDF 목차 조회 (시험 범위 선택용) |
| POST | `/api/documents/{documentId}/search` | RAG 검색 테스트 |

### 13.2 족보 분석 및 출제 스타일

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/exam-styles/analyze` | 족보 업로드 후 출제 스타일 분석 요청 |
| GET | `/api/exam-styles` | 내 출제 스타일 프로필 목록 |
| GET | `/api/exam-styles/{profileId}` | 스타일 프로필 상세 조회 |
| DELETE | `/api/exam-styles/{profileId}` | 스타일 프로필 삭제 |

### 13.3 문제집 생성

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/jobs` | 문제집 생성 Job 등록 |
| GET | `/api/jobs/{jobId}` | 생성 상태 조회 |
| GET | `/api/jobs/{jobId}/stream` | SSE 기반 생성 진행 상태 스트리밍 |

### 13.4 시험 및 문제 관리

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/exams/{examId}` | 전체 시험 JSON 조회 (웹 렌더링용) |
| GET | `/api/exams/{examId}/export` | 선택적 PDF export (고도화) |
| PATCH | `/api/exams/{examId}/questions/{questionId}` | 개별 문제 수정 |
| POST | `/api/exams/{examId}/questions/{questionId}/regenerate` | 개별 문제 재생성 |
| DELETE | `/api/exams/{examId}/questions/{questionId}` | 문제 삭제 |
| POST | `/api/exams/{examId}/export` | 편집 후 PDF export 재생성 (고도화) |

### 13.5 풀이 및 학습 분석

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/exams/{examId}/answers` | 풀이 결과 제출 (풀이 시간 포함) |
| POST | `/api/exams/{examId}/interactions` | 풀이 이벤트 로그 저장 (시작, 제출, 힌트, 답 변경, 이탈) |
| GET | `/api/learning/weak-concepts` | 취약 개념 조회 |
| GET | `/api/learning/mastery` | 사용자 개념별 숙련도 조회 |
| GET | `/api/learning/recommendations` | KT 기반 개인화 복습·문제 추천 |
| POST | `/api/learning/kt/predict` | BKT/pyKT 기반 다음 문제 정답 확률 예측 |
| POST | `/api/learning/kt/recompute` | 사용자 풀이 기록 기반 숙련도 재계산 |

### 13.6 워크스페이스 및 소셜

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/workspaces` | 워크스페이스 생성 |
| GET | `/api/workspaces` | 워크스페이스 목록 |
| GET | `/api/workspaces/{workspaceId}` | 워크스페이스 상세 (문서·시험 포함) |
| POST | `/api/groups` | 스터디 그룹 생성 (고도화) |
| POST | `/api/groups/{groupId}/merge-exams` | 통합 문제집 생성 (고도화) |

---

## 14. 개발 일정

| Phase | 기간 | 목표 |
|---|---:|---|
| Phase 0 | 1일 | Mac mini Docker 환경, MinIO, FastAPI 프로젝트 초기화, API 명세 확정 |
| Phase 1 | 3~4일 | FastAPI + MinIO 업로드 + 웹 드래그 앤 드롭 업로드 UI (강의자료/족보 구분) |
| Phase 2A | 2~3일 | PyMuPDF 텍스트 추출 + chunk 저장 |
| Phase 2B | 2~3일 | embedding (OpenAI 또는 로컬) + pgvector 저장 |
| Phase 2C | 2~3일 | OCR fallback 적용 |
| Phase 3 | 2~3일 | RAG 검색 API + 검색 품질 확인 |
| Phase 3.5 | 3~4일 | 족보 업로드 + LLM 출제 스타일 분석 + 스타일 프로필 저장 |
| Phase 4 | 4~6일 | LLM 문제 생성 (족보 스타일 반영 토글 포함) + JSON 검증 + SSE 스트리밍 |
| Phase 5 | 2~3일 | 문제집 웹 렌더링 + 브라우저 인쇄(print stylesheet) |
| Phase 6 | 3~4일 | 웹 프론트엔드 E2E 연결 + 문제 편집·재생성 |
| Phase 6.5 | 1~2일 | Mac mini Docker Compose 배포 + Nginx HTTPS |
| Phase 7 | 3~5일 | 온라인 문제 풀이 (Web Worker 타이머, 자동 채점) + 풀이 이벤트 로그 |
| Phase 7.2 | 2~3일 | 규칙 기반 개념 숙련도 계산 + 취약 개념 추천 |
| Phase 7.3 | 2~4일 | BKT 기반 Knowledge Tracing 도입 (데이터 누적 이후) |
| Phase 7.5 | 1~2일 | PWA 적용 + 과목별 워크스페이스 |
| Phase 8 | 선택 | 로컬 임베딩, reranker, 목차 파싱 시험 범위 선택, 교수 패턴 차트 시각화 |
| Phase 9 | 선택 | pyKT 모델 실험(장기 고도화), AI 코치, 스터디 그룹, 통합 문제집 |

권장 구현 순서:

```text
MinIO 업로드 (강의자료 + 족보)
→ PyMuPDF 추출
→ chunk 저장
→ embedding (OpenAI → 이후 로컬 전환)
→ pgvector 검색
→ 족보 출제 스타일 분석 + 프로필 저장
→ LLM 문제 생성 (족보 스타일 토글) + SSE 스트리밍
→ 웹 문제집 렌더링 + 브라우저 인쇄
→ 웹 프론트엔드 E2E + 문제 편집·재생성
→ 온라인 문제 풀이 + 타이머 + 자동 채점
→ OCR fallback
→ PWA 적용 + 워크스페이스
→ 풀이 이벤트 로그 저장
→ 규칙 기반 숙련도 계산
→ BKT 기반 Knowledge Tracing
→ KT 기반 개인화 문제 추천
→ 로컬 임베딩 모델 전환
→ 목차 파싱 + 시험 범위 시각적 선택
→ 교수 출제 패턴 차트 시각화
→ reranker
→ pyKT 모델 실험
→ 스터디 그룹 + 통합 문제집
→ AI 코치
```

---

## 15. Mac mini Docker 배포 계획

### 15.1 Docker Compose 구성

```text
Mac mini
├── nginx
├── frontend (Next.js + PWA)
├── backend (FastAPI + uvicorn)
├── postgres-pgvector
├── minio
└── optional-ocr-worker
```

예상 `docker-compose.yml` 구성:

```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - frontend
      - backend

  frontend:
    build: ./frontend
    expose:
      - "3000"

  backend:
    build: ./backend
    expose:
      - "8000"
    env_file:
      - .env
    depends_on:
      - postgres
      - minio
    volumes:
      - embedding_cache:/app/models

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: dontdelay
      POSTGRES_USER: dontdelay
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    expose:
      - "9000"
    ports:
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
  embedding_cache:
```

### 15.2 운영 체크리스트

- 공유기에서 Mac mini 내부 IP를 DHCP 고정 할당한다.
- 외부 접속이 필요하면 공유기 포트포워딩은 `80`, `443`만 설정한다.
- DuckDNS 또는 별도 도메인을 Nginx에 연결한다.
- Let's Encrypt 인증서로 HTTPS를 적용한다.
- PostgreSQL과 MinIO는 외부에서 직접 접근할 수 없도록 한다.
- MinIO 웹 콘솔(`9001`)은 관리 목적으로만 내부에서 접근한다.
- Docker volume(postgres_data, minio_data)을 정기 백업한다.
- MinIO 버킷은 private으로 유지하고 presigned URL 또는 FastAPI proxy download를 사용한다.

---

## 16. 평가 및 벤치마킹 계획

### 16.1 비용 평가

| 지표 | 설명 |
|---|---|
| 입력 토큰 수 | 생성 1회당 LLM 입력량 |
| 출력 토큰 수 | 문제·정답·해설 생성량 |
| embedding 비용 | 문서 업로드 1회당 비용 |
| OCR 비용 | 스캔 PDF 처리 비용 |
| 전체 생성 비용 | 문제집 1개당 총 비용 |

비교 대상:

```text
FULL_CONTEXT 방식
vs
RAG 방식
vs
RAG + reranker 방식
```

### 16.2 문제 품질 평가

| 평가 항목 | 설명 |
|---|---|
| 명확성 | 문제 문장이 모호하지 않은가 |
| 강의자료 관련성 | 업로드한 자료의 내용을 반영하는가 |
| 난이도 적절성 | 요청한 난이도와 일치하는가 |
| 문제-답안 정합성 | 정답과 해설이 문제에 적합한가 |
| 출처 정확성 | 연결된 chunk가 문제 근거로 적절한가 |
| 오답 품질 | 객관식 distractor가 그럴듯한가 |
| 개념 커버리지 | 중요한 강의 개념을 고르게 다루는가 |

### 16.3 학습 효과 평가

| 평가 항목 | 설명 |
|---|---|
| 사전·사후 점수 변화 | 문제집 사용 전후 점수 비교 |
| 취약 개념 개선율 | 낮은 숙련도 개념의 정답률 변화 |
| 반복 학습 효과 | 취약 개념 중심 재생성 후 성능 변화 |
| 학습 시간 | 동일 성취도 도달에 필요한 시간 변화 |
| 사용자 만족도 | 문제 품질과 학습 도움 정도 설문 |

---

## 17. 보안 및 운영 정책

| 항목 | 정책 |
|---|---|
| 인증 | FastAPI 세션 또는 JWT 기반 인증 |
| API 키 | 서버 환경변수로만 관리, `.env`는 Git에 올리지 않음 |
| MinIO | private bucket, presigned URL 또는 FastAPI proxy download |
| 파일 제한 | PDF만 허용, 최대 50MB |
| 사용자 격리 | 모든 조회·삭제를 user_id 기준으로 제한 |
| 워크스페이스 격리 | 워크스페이스 소유자와 스터디 그룹 멤버만 접근 가능 |
| 로그 | PDF 원문과 chunk 전문은 운영 로그에 기록하지 않음 |
| HTTPS | Nginx reverse proxy + Let's Encrypt 적용 |

---

## 18. 환경 변수 예시

```env
# OpenAI / Claude (문제 생성 LLM)
OPENAI_API_KEY=...
LLM_MODEL=gpt-4o
# ANTHROPIC_API_KEY=...
# LLM_MODEL=claude-sonnet-4-20250514

# Embedding
EMBEDDING_PROVIDER=local
# local: sentence-transformers 로컬 모델 (API 비용 없음)
# openai: OpenAI text-embedding-3-small
EMBEDDING_MODEL=intfloat/multilingual-e5-large
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# MinIO (S3 호환)
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=...
MINIO_SECRET_KEY=...
MINIO_BUCKET=dontdelay-exam

# PostgreSQL + pgvector
DATABASE_URL=postgresql+asyncpg://dontdelay:${POSTGRES_PASSWORD}@postgres:5432/dontdelay
POSTGRES_PASSWORD=...

# OCR
OCR_ENABLED=true
UPSTAGE_API_KEY=...

# Exam Generator
EXAM_MAX_UPLOAD_BYTES=52428800
EXAM_CHUNK_SIZE=800
EXAM_CHUNK_OVERLAP=120
EXAM_RATE_LIMIT_UPLOAD_PER_HOUR=10
EXAM_RATE_LIMIT_GENERATE_PER_DAY=20

# App
SECRET_KEY=...
CORS_ORIGINS=https://yourdomain.com
```

---

## 19. 연구 및 발표 포인트

본 프로젝트는 단순한 PDF 요약 또는 문제 생성 서비스가 아니라 다음 요소를 결합한 학습 지원 시스템을 목표로 한다.

1. FastAPI + Python 단일 백엔드로 AI/ML 파이프라인 통합
2. 강의자료 기반 RAG를 통한 출처 추적 가능한 문제 생성
3. Bloom's Taxonomy 기반 인지 수준별 문제 제어
4. 오개념 기반 distractor 생성
5. FULL_CONTEXT, RAG, RAG + reranker 방식 비교
6. 로컬 임베딩 모델 vs OpenAI embedding 비용·품질 비교
7. 문제집 생성 비용과 품질 벤치마킹
8. SSE 기반 실시간 생성 진행 상태 스트리밍
9. 웹 기반 온라인 풀이 및 시간 측정 (Web Worker 타이머)
10. 사용자 풀이 기록 기반 취약 개념 분석
11. BKT 기반 Knowledge Tracing 확장
12. pyKT 기반 딥러닝 Knowledge Tracing 실험
13. 교수 출제 패턴 분석 및 시각화
14. 스터디 그룹 협업 기반 통합 문제집 생성
15. Mac mini 자체 호스팅 (외부 클라우드 없는 셀프 인프라)

---

## 20. 참고 연구 방향

### 문제·답안 적절성 평가

- **Comparison of Large Language Models for Generating Contextually Relevant Questions**
  - 대학 슬라이드 기반 질문 생성
  - 명확성, 관련성, 난이도, 슬라이드 관련성, question-answer alignment 평가

- **Automated Educational Question Generation at Different Bloom's Skill Levels using Large Language Models: Strategies and Evaluation**
  - Bloom's Taxonomy 기반 인지 수준별 문제 생성
  - 자동 평가와 인간 평가의 차이 분석

### 향후 추가 조사

- distractor generation survey 및 오개념 기반 객관식 생성
- KT4EQG 계열 개인화 문제 생성
- TutorLLM 계열 Knowledge Tracing + RAG 기반 학습 추천

---

## 21. 최종 MVP 완료 기준

```text
1. 사용자가 웹 브라우저에서 강의자료 PDF를 드래그 앤 드롭으로 업로드할 수 있다.
2. 사용자가 족보(과거 시험) PDF 또는 텍스트를 업로드할 수 있다.
3. 원본 PDF가 MinIO에 저장된다.
4. PyMuPDF 또는 OCR로 텍스트가 추출된다.
5. chunk와 embedding이 PostgreSQL + pgvector에 저장된다.
6. 족보가 업로드되면 LLM이 출제 스타일을 분석하고 프로필을 생성한다.
7. 사용자가 문제 유형, 난이도, 족보 스타일 반영 여부를 선택할 수 있다.
8. RAG 검색 결과를 근거로 LLM이 문제, 답안, 해설을 JSON으로 생성한다.
9. 족보 스타일 반영 토글이 ON이면 해당 교수의 출제 패턴에 맞춰 문제가 생성된다.
10. 생성된 문제집이 JSON으로 DB에 저장되고 웹에서 렌더링된다.
11. 사용자가 브라우저 인쇄로 문제집을 저장할 수 있다.
12. 생성 문제에 sourceChunkIds와 concepts가 포함된다.
13. 사용자가 웹에서 문제를 풀고 풀이 시간이 측정된다.
14. 풀이 이벤트 로그(정오답, 풀이 시간, 시도 횟수, 힌트 사용 여부)가 저장된다.
15. 규칙 기반으로 개념별 숙련도와 취약 개념을 계산할 수 있다.
16. 토큰 사용량과 문제 품질을 기록하여 벤치마킹할 수 있다.
17. 모든 서비스가 Mac mini Docker Compose 환경에서 외부 클라우드 없이 운영된다.
```
