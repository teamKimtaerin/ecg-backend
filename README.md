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

## 설치 및 실행

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

🚀 PR 자동화 도구 - 팀원 설정 가이드 0. Github CLI 설치
brew install gh # macOS
winget install Github.cli # Windows

1. 최신 코드 받기
   git pull origin main
2. 설치 스크립트 실행 (한 번만)
   chmod +x install.sh
   ./install.sh
3. PATH 적용 (설치 후 한 번만)
   source ~/.zshrc # zsh 사용자 (macOS 기본)
   source ~/.bashrc # bash 사용자
4. GitHub CLI 로그인 (각자 개인 계정으로)
   gh auth login

# → GitHub.com 선택

# → HTTPS 선택

# → Y (인증)

# → Login with a web browser 선택

5. 사용 시작!

# 작업 후 변경사항 추가

git add .

# PR 생성 (자동 커밋 + 푸시 + Claude 분석 + PR)

prm "Feat: 첫 번째 테스트 PR" # ⚠️ pr이 아닌 prm 사용!\*
📝 사용 흐름
코드 작업 → 기능 구현
git add . → 변경사항 스테이징
prm "작업 내용" → 자동 커밋/푸시
Claude Code 분석
클립보드에 자동 복사된 프롬프트를 claude.ai/code에 붙여넣기
생성된 PR 내용 복사
터미널에 붙여넣기 → PR 자동 생성!
⚠️ 주의사항
명령어는 pr이 아닌 prm (PR Make)
작업은 feature 브랜치에서 (main 브랜치 X)
Claude Code 접속: https://claude.ai/code
=======
🤖 Generated with Claude Code




# 🚀 PR 자동화 도구 - 팀원 설정 가이드

-----

### 0\. Github CLI 설치

```bash
brew install gh      # macOS
winget install Github.cli  # Windows
```

-----

### 1\. 최신 코드 받기

```bash
git pull origin main
```

-----

### 2\. 설치 스크립트 실행 (한 번만)

```bash
chmod +x install.sh
./install.sh
```

-----

### 3\. PATH 적용 (설치 후 한 번만)

```bash
source ~/.zshrc  # zsh 사용자 (macOS 기본)
source ~/.bashrc # bash 사용자
```

-----

### 4\. GitHub CLI 로그인 (각자 개인 계정으로)

```bash
gh auth login
```

  * → GitHub.com 선택
  * → HTTPS 선택
  * → Y (인증)
  * → Paste an authentication token 선택

-----

### 5\. 사용 시작\!

```bash
# 작업 후 변경사항 추가
git add .
# PR 생성 (자동 커밋 + 푸시 + Claude 분석 + PR)
prm "Feat: 첫 번째 테스트 PR"  # ⚠️ pr이 아닌 prm 사용!
```

---

### 📝 사용 흐름

1.  **코드 작업** → 기능 구현
2.  **`git add .`** → 변경사항 스테이징
3.  **`prm "작업 내용"`** → 자동 커밋/푸시
4.  **Claude Code 분석**
      * 클립보드에 자동 복사된 프롬프트를 `claude.ai/code`에 붙여넣기
      * 생성된 PR 내용 복사
      * 터미널에 붙여넣기 → PR 자동 생성\!

---

### ⚠️ 주의사항

  * 명령어는 \*\*`pr`\*\*이 아닌 **`prm`** (**PR Make**)
  * 작업은 **feature 브랜치**에서 (**main** 브랜치 **X**)
  * **Claude Code 접속**: `https://claude.ai/code`

