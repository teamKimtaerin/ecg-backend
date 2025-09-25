from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """채팅 메시지 스키마"""

    id: str = Field(..., description="메시지 고유 ID")
    content: str = Field(..., description="메시지 내용")
    sender: str = Field(..., description="발신자 (user 또는 bot)")
    timestamp: datetime = Field(..., description="메시지 생성 시간")


class SavedFiles(BaseModel):
    """저장된 파일 정보 스키마"""

    json_file: Optional[str] = Field(default=None, description="JSON 형태로 저장된 파일 경로")
    text_file: Optional[str] = Field(default=None, description="텍스트 형태로 저장된 파일 경로")


class ChatBotRequest(BaseModel):
    """ChatBot API 요청 스키마"""

    prompt: str = Field(..., description="사용자 입력 프롬프트", min_length=1, max_length=5000)
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=[], description="대화 히스토리 (최근 6개 메시지)"
    )
    scenario_data: Optional[Dict[str, Any]] = Field(
        default=None, description="현재 시나리오 파일 (자막 및 스타일링 데이터)"
    )
    max_tokens: Optional[int] = Field(
        default=1000, description="최대 토큰 수", ge=1, le=4000
    )
    temperature: Optional[float] = Field(
        default=0.7, description="온도 (창의성 조절)", ge=0.0, le=1.0
    )
    save_response: Optional[bool] = Field(default=True, description="응답을 파일로 저장할지 여부")
    use_langchain: Optional[bool] = Field(default=False, description="LangChain 사용 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "첫 번째 자막의 색상을 빨간색으로 변경해주세요",
                "conversation_history": [
                    {
                        "id": "1",
                        "content": "안녕하세요",
                        "sender": "user",
                        "timestamp": "2024-01-01T00:00:00Z",
                    },
                    {
                        "id": "2",
                        "content": "안녕하세요! ECG 자막 편집 도구에 대해 도움을 드릴 수 있습니다.",
                        "sender": "bot",
                        "timestamp": "2024-01-01T00:00:01Z",
                    },
                ],
                "scenario_data": {
                    "cues": [
                        {
                            "root": {
                                "id": "clip-clip-1",
                                "children": [
                                    {
                                        "id": "word-1",
                                        "text": "안녕하세요",
                                        "baseTime": [0.0, 1.5],
                                        "style": {"color": "#ffffff"},
                                    }
                                ],
                            }
                        }
                    ]
                },
                "max_tokens": 1000,
                "temperature": 0.7,
                "save_response": True,
                "use_langchain": True,
            }
        }


class ChatBotResponse(BaseModel):
    """ChatBot API 응답 스키마"""

    completion: str = Field(..., description="AI 응답 텍스트")
    stop_reason: str = Field(..., description="응답 종료 이유")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="토큰 사용량 정보")
    processing_time_ms: Optional[int] = Field(default=None, description="처리 시간 (밀리초)")
    saved_files: Optional[SavedFiles] = Field(default=None, description="저장된 파일 정보")
    save_error: Optional[str] = Field(default=None, description="파일 저장 중 발생한 오류")

    # 시나리오 편집 관련 필드
    edit_result: Optional[Dict[str, Any]] = Field(default=None, description="편집 결과 정보")
    json_patches: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="JSON patch 배열"
    )
    has_scenario_edits: Optional[bool] = Field(default=False, description="시나리오 편집 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "completion": "ECG에서 자막 색상을 변경하는 방법은 다음과 같습니다:\\n\\n1. 자막을 선택합니다\\n2. 우측 패널에서 색상 옵션을 찾습니다\\n3. 원하는 색상을 선택하세요",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 50, "output_tokens": 150},
                "processing_time_ms": 1500,
                "saved_files": {
                    "json_file": "output/bedrock_response_20241201_143022.json",
                    "text_file": "output/bedrock_completion_20241201_143022.txt",
                },
            }
        }


class SavedFileInfo(BaseModel):
    """저장된 파일 정보 스키마"""

    filename: str = Field(..., description="파일명")
    path: str = Field(..., description="파일 경로")
    size: int = Field(..., description="파일 크기 (바이트)")
    created: str = Field(..., description="파일 생성 시간 (ISO 형식)")
    modified: str = Field(..., description="파일 수정 시간 (ISO 형식)")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "bedrock_response_20241201_143022.json",
                "path": "output/bedrock_response_20241201_143022.json",
                "size": 1024,
                "created": "2024-12-01T14:30:22.123456",
                "modified": "2024-12-01T14:30:22.123456",
            }
        }


class ChatBotErrorResponse(BaseModel):
    """ChatBot API 에러 응답 스키마"""

    error: str = Field(..., description="에러 메시지")
    error_code: Optional[str] = Field(default=None, description="에러 코드")
    details: Optional[str] = Field(default=None, description="상세 에러 정보")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "AWS Bedrock API 호출에 실패했습니다",
                "error_code": "BEDROCK_API_ERROR",
                "details": "UnrecognizedClientException: The security token included in the request is invalid",
            }
        }
