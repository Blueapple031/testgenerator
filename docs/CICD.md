# DontDelay CI/CD 가이드

## 전체 흐름

```
노트북(개발)                  GitHub                        Mac mini(운영)
    │                           │                               │
    ├── git push ──────────────>│                               │
    │                           ├── CI 자동 실행                │
    │                           │   ├── Backend Lint (ruff)     │
    │                           │   ├── Backend Test (pytest)   │
    │                           │   ├── Frontend Lint & Build   │
    │                           │   └── Docker Compose 검증     │
    │                           │                               │
    │                           ├── main 브랜치 push 시 ───────>│
    │                           │   CD 자동 배포                │
    │                           │   ├── git pull                │
    │                           │   ├── docker compose build    │
    │                           │   ├── docker compose up -d    │
    │                           │   └── alembic upgrade head    │
    │                           │                               │
```

---

## 1. CI (Continuous Integration)

**파일**: `.github/workflows/ci.yml`
**트리거**: `main` 브랜치 push 또는 PR

4개 Job이 **병렬**로 실행됩니다.

### 1-1. Backend Lint

| 항목 | 내용 |
|---|---|
| 도구 | ruff |
| 검사 | 코드 스타일 (`ruff check`) + 포맷 (`ruff format --check`) |
| 설정 | `backend/pyproject.toml`의 `[tool.ruff]` 섹션 |

로컬에서 미리 확인하려면:

```bash
cd backend
ruff check .
ruff format .
```

### 1-2. Backend Test

| 항목 | 내용 |
|---|---|
| 도구 | pytest |
| 테스트 위치 | `backend/tests/` |
| 설정 | `backend/pyproject.toml`의 `[tool.pytest.ini_options]` 섹션 |

로컬에서 실행:

```bash
cd backend
pytest -v
```

### 1-3. Frontend Lint & Build

| 단계 | 명령어 |
|---|---|
| 의존성 설치 | `npm ci` |
| ESLint | `npm run lint` |
| 타입 체크 | `npx tsc --noEmit` |
| 빌드 | `npm run build` |

로컬에서 실행:

```bash
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

### 1-4. Docker Compose Validate

`docker-compose.yml` 문법 오류를 검사합니다.

---

## 2. CD (Continuous Deployment)

**파일**: `.github/workflows/deploy.yml`
**트리거**: `main` 브랜치 push (PR merge 포함)

### 배포 과정

```
1. GitHub Actions에서 Mac mini로 SSH 접속
2. git pull origin main
3. docker compose build --parallel
4. docker compose up -d
5. docker image prune -f        ← 오래된 이미지 정리
6. alembic upgrade head          ← DB 마이그레이션
```

### 필수: GitHub Secrets 등록

Repository > Settings > Secrets and variables > Actions 에서 추가:

| Secret | 설명 | 예시 |
|---|---|---|
| `DEPLOY_HOST` | Mac mini 외부 IP 또는 도메인 | `myserver.duckdns.org` |
| `DEPLOY_USER` | SSH 접속 사용자 | `deploy` |
| `DEPLOY_SSH_KEY` | SSH private key (전체 내용) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEPLOY_PORT` | SSH 포트 (기본 22) | `22` |
| `DEPLOY_PATH` | Mac mini 내 프로젝트 경로 | `/Users/deploy/testgenerator` |

### Mac mini 사전 준비

```bash
# 1. 배포 전용 사용자 생성 (선택)
sudo dscl . -create /Users/deploy

# 2. SSH key 등록
mkdir -p ~/.ssh
echo "여기에 public key 붙여넣기" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 3. 프로젝트 clone
cd ~
git clone https://github.com/your-username/testgenerator.git

# 4. .env 파일 생성
cd testgenerator
cp .env.example .env
# .env에 실제 값 채우기

# 5. 첫 실행
docker compose up -d
```

### 동시 배포 방지

`deploy.yml`에 `concurrency` 설정이 있어서 배포가 진행 중일 때 새 push가 오면 이전 배포를 취소하고 최신 것만 실행합니다.

---

## 3. 로컬 개발 환경 (노트북)

**파일**: `docker-compose.dev.yml`

프로덕션(`docker-compose.yml`)과 다른 점:

| | 프로덕션 | 로컬 개발 |
|---|---|---|
| nginx | 있음 | **없음** |
| frontend | Docker 내부 빌드 | **npm run dev** (Docker 밖) |
| backend | 고정 실행 | **hot reload** (코드 수정 즉시 반영) |
| postgres | 내부 포트만 | **5432 열림** (DB 도구 접속 가능) |
| minio | 내부 포트만 | **9000, 9001 열림** |

### 사용법

```bash
# 터미널 1: DB + MinIO + Backend
docker compose -f docker-compose.dev.yml up

# 터미널 2: Frontend (HMR 빠름)
cd frontend
npm install
npm run dev
```

접속:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/health
- MinIO 콘솔: http://localhost:9001 (minioadmin / minioadmin)

---

## 4. 권장 개발 워크플로우

```
1. feature 브랜치 생성
   git checkout -b feature/pdf-upload

2. 노트북에서 개발 + 로컬 테스트
   docker compose -f docker-compose.dev.yml up

3. push → PR 생성
   git push -u origin feature/pdf-upload
   → CI 자동 실행 (lint, test, build)

4. CI 통과 확인 후 main에 merge
   → CD 자동 실행 (Mac mini 배포)
```

---

## 5. 파일 구조

```
.github/
└── workflows/
    ├── ci.yml              ← PR/push 시 lint, test, build
    └── deploy.yml          ← main push 시 Mac mini 배포

docker-compose.yml          ← 프로덕션 (Mac mini)
docker-compose.dev.yml      ← 로컬 개발 (노트북)

backend/
├── pyproject.toml          ← ruff, pytest 설정
└── tests/
    └── test_health.py      ← 기본 테스트

nginx/
└── nginx.conf              ← 프로덕션 리버스 프록시
```

---

## 6. 트러블슈팅

### CI가 실패할 때

- **Backend Lint 실패**: `cd backend && ruff check . && ruff format .` 로 자동 수정
- **Backend Test 실패**: `cd backend && pytest -v` 로 로컬에서 재현
- **Frontend Build 실패**: `cd frontend && npx tsc --noEmit` 으로 타입 에러 확인

### 배포가 실패할 때

- GitHub Actions 로그 확인: Repository > Actions 탭
- Mac mini SSH 직접 접속해서 `docker compose logs` 확인
- `.env` 파일이 Mac mini에 있는지 확인
- Docker 디스크 공간: `docker system df`

### 배포 롤백

```bash
# Mac mini에서
cd ~/testgenerator
git log --oneline -5          # 이전 커밋 확인
git checkout <이전커밋해시>
docker compose build --parallel
docker compose up -d
```
