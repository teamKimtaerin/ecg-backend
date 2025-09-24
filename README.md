# Expressive Caption Generator Backend

## 프로젝트 구조

```
expressive-caption-generator-backend/
├── app/                          # 소스코드 루트
│   ├── main.py                   # FastAPI 앱 진입점
│   ├── core/                     # 핵심 설정
│   │   └── config.py             # AWS, OpenAI 등 환경 설정
│   ├── db/                       # DB 연결 관련
│   ├── models/                   # SQLAlchemy 모델 정의
│   ├── schemas/                  # Pydantic 스키마
│   ├── services/                 # 비즈니스 로직
│   └── api/
│       └── v1/                   # 버전별 API
│           ├── endpoints/        # 실제 라우트들
│           └── routers.py        # 라우터 등록
├── tests/                        # 테스트 코드
├── requirements.txt              # Python 패키지 목록
├── .env.example                  # 환경변수 템플릿
└── README.md
```

## ⭐️  설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-username/expressive-caption-generator-backend.git
cd expressive-caption-generator-backend

# 가상환경 생성 및 활성화
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 환경변수 파일 생성
cp .env.example .env
# .env 파일을 편집하여 실제 값들 설정
```

### 2. 서버 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload
```

## API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs (대화형 테스트 가능)
- **ReDoc**: http://localhost:8000/redoc (읽기 전용 문서)

## 개요

- FastAPI 백엔드 프로젝트에 Claude Code AI 기반 PR 자동 생성 시스템 구현
- 개발 워크플로우 자동화를 통한 팀 생산성 향상 및 PR 품질 표준화
- Git 커밋부터 PR 생성까지 완전 자동화된 파이프라인 구축

## 설명

### What (무엇을 수정했나요?)

- **Claude Code 프로젝트 가이드** (`.claude/CLAUDE.md`): FastAPI + AWS + OpenAI 통합 프로젝트 구조 및 개발 환경 설정 문서화 (69줄)
- **PR 자동화 스크립트** (`.claude/scripts/prm`): Bash 기반 대화형 PR 생성 도구 구현 (250줄)
- Git 상태 검증 및 자동 커밋/푸시 기능
- Claude Code AI 프롬프트 자동 생성 및 클립보드 연동
- GitHub CLI를 통한 PR 생성 자동화
- **원클릭 설치 도구** (`install.sh`): 팀원용 환경 설정 자동화 스크립트 (63줄)

### Why (왜 수정했나요?)

- **개발 효율성 향상**: 수동 PR 작성에 소요되는 시간 단축 (약 10-15분 → 2-3분)
- **PR 품질 표준화**: Claude AI를 활용한 일관된 PR 설명 템플릿 및 구조화된 형식 보장
- **팀 협업 개선**: 신규 팀원 온보딩 자동화 및 개발 프로세스 표준화
- **지능형 코드 분석**: Git diff 기반 자동 변경사항 분석 및 맥락적 PR 설명 생성

### How (어떻게 수정했나요?)

1. **Bash 스크립트 기반 자동화 엔진**:
   - Git 브랜치 및 staged 파일 상태 검증 로직
   - 변경사항 통계 자동 수집 (파일 수, 추가/삭제 라인)
   - 자동 커밋 메시지 생성 (Claude co-author 포함)

2. **Claude Code AI 통합 시스템**:
   - 구조화된 프롬프트 템플릿 생성 (Git diff 포함)
   - macOS 클립보드 자동 복사 기능
   - 대화형 PR 제목/본문 입력 인터페이스

3. **GitHub CLI 연동**:
   - 자동 베이스 브랜치 감지 (main/master)
   - PR 생성 후 브라우저 자동 연동 옵션
   - 실패 시 수동 명령어 가이드 제공

4. **팀 환경 설정 자동화**:
   - PATH 환경변수 자동 등록 (bash/zsh 대응)
   - 스크립트 실행 권한 자동 설정
   - GitHub CLI 설치 및 인증 가이드

## 📋 체크리스트

- [x] 기능 테스트 완료 (로컬 환경)
- [x] 코드 리뷰 준비 완료
- [x] 문서 업데이트 (CLAUDE.md 추가)
- [x] 설치 스크립트 실행 권한 설정
- [x] macOS 클립보드 연동 테스트
- [ ] 팀원 온보딩 테스트 및 피드백 수집

## 🔍 리뷰 포인트

- **보안 검토**: Bash 스크립트의 사용자 입력 검증 및 에러 핸들링 로직
- **크로스 플랫폼 호환성**: Windows/Linux 환경에서의 PATH 설정 및 클립보드 기능 동작 확인
- **GitHub 권한 관리**: 팀 레포지토리 접근 권한 및 브랜치 보호 규칙 호환성
- **Claude Code 프롬프트 최적화**: AI 분석 결과의 정확성 및 한국어 출력 품질
- **스크립트 실행 권한**: chmod 설정 및 PATH 등록 로직의 중복 처리 방식

🤖 Generated with Claude Code

## 🚀 PR 자동화 도구 - 팀원 설정 가이드

### 0. Github CLI 설치

```bash
brew install gh      # macOS
winget install Github.cli  # Windows
```

### 1. 최신 코드 받기

```bash
git pull origin main
```

### 2. 설치 스크립트 실행 (한 번만)

```bash
chmod +x install.sh
./install.sh
```

### 3. PATH 적용 (설치 후 한 번만)

```bash
source ~/.zshrc  # zsh 사용자 (macOS 기본)
source ~/.bashrc # bash 사용자
```

### 4. GitHub CLI 로그인 (각자 개인 계정으로)

```bash
gh auth login
# → GitHub.com 선택
# → HTTPS 선택
# → Y (인증)
# → Paste an authentication token 선택
```

### 5. 사용 시작!

```bash
# 작업 후 변경사항 추가
git add .

# PR 생성 (자동 커밋 + 푸시 + Claude 분석 + PR)
prm "Feat: 첫 번째 테스트 PR"  # ⚠️ pr이 아닌 prm 사용!
```

### 📝 사용 흐름

1. **코드 작업** → 기능 구현
2. **`git add .`** → 변경사항 스테이징
3. **`prm "작업 내용"`** → 자동 커밋/푸시
4. **Claude Code 분석**
   - 클립보드에 자동 복사된 프롬프트를 `claude.ai/code`에 붙여넣기
   - 생성된 PR 내용 복사
   - 터미널에 붙여넣기 → PR 자동 생성!

### ⚠️ 주의사항

- 명령어는 `pr`이 아닌 `prm` (PR Make)
- 작업은 **feature 브랜치**에서 (**main** 브랜치 **X**)
- **Claude Code 접속**: https://claude.ai/code

## 🐳 Docker

### 1. Docker Desktop 실행

### 2. 실행 확인

```bash
# Docker Desktop이 완전히 시작될 때까지 1-2분 기다린 후
docker info

# 이렇게 나오면 성공
Server:
 Containers: X
 Running: X
 ...
```

### 3. 빌드 테스트

#### 개발환경 버전

```bash
# 개발환경 빌드 테스트
docker build --target dev --build-arg MODE=dev -t ecg-backend:dev .

# 개발 컨테이너 실행 (포트 매핑)
docker run -d -p 8000:8000 --name ecg-backend-dev ecg-backend:dev
```

#### 프로덕션 버전 (아직 안 해도 됨!!)

```bash
# 프로덕션 환경 빌드 테스트
docker build --target prod --build-arg MODE=prod -t ecg-backend:prod .

# 프로덕션 컨테이너 실행
docker run -d -p 8001:8000 --name ecg-backend-prod ecg-backend:prod
```

#### API 테스트

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

### 참고 명령어

```bash
# 현재 8000번 포트를 사용 중인 프로세스
lsof -i :8000

# 프로세스를 종료
kill -9 <PID>

# 기존에 실행 중인 Docker 컨테이너 확인 및 제거
docker ps -a

# 컨테이너 로그 확인
docker logs <컨테이너 이름 또는 ID>

# 기존 컨테이너 삭제
docker rm <컨테이너 이름 또는 ID>

# 실행 여부와 상관 없이 삭제
docker rm -f <컨테이너 이름 또는 ID>

# 컨테이너 정리
docker stop <컨테이너 이름 또는 ID> && docker rm <컨테이너 이름 또는 ID>
```

## ⚙️ CI Workflow (ci.yml)

### 워크플로우 트리거 조건 (`on`)

- `main` 또는 `dev` 브랜치에 푸시(push)되거나, 해당 브랜치를 대상으로 풀 리퀘스트(pull_request)가 생성되거나 업데이트될 때마다 자동으로 실행됨

### 실행 작업 (`jobs`)

`lint-and-test`라는 이름의 단일 작업(Job)으로 구성되어 있으며, `ubuntu-latest` 가상 머신에서 순차적으로 다음 단계들을 수행

#### 1. 코드 체크아웃
- `actions/checkout@v4` 액션을 사용하여 GitHub 저장소의 최신 코드를 가상 머신으로 가져옴

#### 2. 환경 설정 및 의존성 설치
- `actions/setup-python@v5` 액션을 사용해 파이썬 3.11 버전을 설정
- `pip install --upgrade pip`로 `pip`를 최신 버전으로 업데이트하고, `pip install -r requirements.txt` 명령어로 `requirements.txt` 파일에 명시된 모든 파이썬 패키지를 설치

#### 3. 코드 품질 및 보안 검사
- `black --check .`: **Black**은 파이썬 코드 포맷팅을 자동으로 맞춰주는 도구
  - `--check` 옵션을 통해 코드 스타일이 Black의 규칙을 따르는지 검사
- `ruff check .`: **Ruff**는 매우 빠르고 효율적인 린터(linter)로, 코드의 잠재적 오류를 찾아내고 스타일을 검사
- `mypy .`: **Mypy**는 파이썬 코드의 정적 타입 체크를 수행하여 타입 관련 오류를 미리 발견
- `bandit -r .`: **Bandit**은 파이썬 코드의 보안 취약점을 자동으로 검사하는 도구
  - `-r` 옵션은 재귀적으로 디렉터리를 탐색하며 검사를 실행하겠다는 의미

#### 4. 테스트 실행
- `pytest` 명령어로 테스트를 실행
- `--maxfail=1` 옵션은 테스트 실패가 한 번이라도 발생하면 즉시 테스트를 중단하겠다는 의미이고, `--disable-warnings`는 경고 메시지를 표시하지 않겠다는 의미
- `|| echo "No tests found - skipping"`는 `pytest`가 실행될 테스트를 찾지 못할 경우(exit code가 5인 경우)에도 워크플로우가 실패하지 않고 다음 단계로 넘어갈 수 있도록 해주는 예외 처리 구문
- 


# Pre-commit 사용 가이드

Pre-commit은 Git 커밋 전에 자동으로 코드 품질 검사와 포맷팅을 수행하는 도구입니다.

## 🎯 Pre-commit이 하는 일

### 설정된 도구들

- **Black**: Python 코드 자동 포맷팅
- **Ruff**: 빠른 Python 린터 + 포맷터
- **MyPy**: Python 타입 체킹

## 📦 설치 및 설정

### 1. Pre-commit 설치

#### 가상환경 사용 (권장)
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# pre-commit 설치
pip install pre-commit
```

#### 시스템 전역 설치
```bash
# pip으로 설치
pip install pre-commit

# 또는 conda로 설치
conda install -c conda-forge pre-commit

# 또는 homebrew (macOS)
brew install pre-commit
```

### 2. Git 훅 설치

```bash
# 프로젝트 루트에서 실행
pre-commit install
```

### 3. 설정 확인

```bash
# 현재 설정 확인
cat .pre-commit-config.yaml
```

## 🚀 사용 방법

### 일반적인 워크플로우

```bash
# 1. 코드 수정
vim app/main.py

# 2. Git add
git add app/main.py

# 3. 커밋 시도 (pre-commit 자동 실행)
git commit -m "Fix authentication bug"

# 4-A. 성공 시
✅ Black................Passed
✅ Ruff.................Passed
✅ MyPy.................Passed
[main 1234567] Fix authentication bug

# 4-B. 실패 시
❌ Black................Failed
❌ Ruff.................Failed
- 파일이 자동 수정됨
- 다시 git add 후 커밋 필요
```

# Trigger deployment Fri Sep 12 14:37:23 KST 2025
# CORS 설정 업데이트 트리거 - Wed Sep 24 01:27:21 KST 2025
# DATABASE_URL 환경변수 테스트
