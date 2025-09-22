from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """채팅 메시지 스키마"""

    id: str = Field(..., description="메시지 고유 ID")
    content: str = Field(..., description="메시지 내용")
    sender: str = Field(..., description="발신자 (user 또는 bot)")
    timestamp: datetime = Field(..., description="메시지 생성 시간")


class ChatBotRequest(BaseModel):
    """ChatBot API 요청 스키마"""

    prompt: str = Field(..., description="사용자 입력 프롬프트", min_length=1, max_length=5000)
    conversation_history: Optional[List[ChatMessage]] = Field(
        default=[], description="대화 히스토리 (최근 6개 메시지)"
    )
    max_tokens: Optional[int] = Field(
        default=1000, description="최대 토큰 수", ge=1, le=4000
    )
    temperature: Optional[float] = Field(
        default=0.7, description="온도 (창의성 조절)", ge=0.0, le=1.0
    )

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "ECG에서 자막 색상을 변경하는 방법을 알려주세요",
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
                "max_tokens": 1000,
                "temperature": 0.7,
            }
        }


class ChatBotResponse(BaseModel):
    """ChatBot API 응답 스키마"""

    completion: str = Field(..., description="AI 응답 텍스트")
    stop_reason: str = Field(..., description="응답 종료 이유")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="토큰 사용량 정보")
    processing_time_ms: Optional[int] = Field(default=None, description="처리 시간 (밀리초)")

    class Config:
        json_schema_extra = {
            "example": {
                "completion": "ECG에서 자막 색상을 변경하는 방법은 다음과 같습니다:\\n\\n1. 자막을 선택합니다\\n2. 우측 패널에서 색상 옵션을 찾습니다\\n3. 원하는 색상을 선택하세요",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 50, "output_tokens": 150},
                "processing_time_ms": 1500,
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
