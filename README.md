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
