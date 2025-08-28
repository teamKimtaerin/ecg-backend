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
# → Login with a web browser 선택
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
   - 클립보드에 자동 복사된 프롬프트를 claude.ai/code에 붙여넣기
   - 생성된 PR 내용 복사
5. **터미널에 붙여넣기** → PR 자동 생성!

### ⚠️ 주의사항
- 명령어는 `pr`이 아닌 `prm` (PR Make)
- 작업은 feature 브랜치에서 (main 브랜치 X)
- Claude Code 접속: https://claude.ai/code