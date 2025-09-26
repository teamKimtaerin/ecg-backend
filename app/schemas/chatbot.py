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
    scenario_data: Optional[Dict[str, Any]] = Field(
        default=None, description="현재 시나리오 파일 (자막 및 스타일링 데이터)"
    )
    max_tokens: Optional[int] = Field(
        default=2000, description="최대 토큰 수 (백엔드에서 2000으로 고정 설정됨)", ge=1, le=4000
    )
    temperature: Optional[float] = Field(
        default=0.7, description="온도 (백엔드에서 0.7로 고정 설정됨)", ge=0.0, le=1.0
    )
    use_langchain: Optional[bool] = Field(
        default=True, description="LangChain 사용 여부 (항상 True로 처리됨)"
    )

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
                        "content": "안녕하세요! HOIT 자막 편집 도구에 대해 도움을 드릴 수 있습니다.",
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
                "max_tokens": 2000,
                "temperature": 0.7,
                "use_langchain": True,
            }
        }


class ChatBotResponse(BaseModel):
    """ChatBot API 응답 스키마"""

    completion: str = Field(
        ...,
        description="사용자에게 표시할 메시지 (XML 응답의 <summary> 태그 내용 추출)",
    )
    stop_reason: str = Field(..., description="응답 종료 이유")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="토큰 사용량 정보")
    processing_time_ms: Optional[int] = Field(default=None, description="처리 시간 (밀리초)")

    # 시나리오 편집 관련 필드
    json_patches: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="파싱된 RFC6902 JSON Patch 배열 (시나리오 편집용)"
    )
    has_scenario_edits: Optional[bool] = Field(default=False, description="시나리오 편집 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "completion": "총 1개 연산, 자막 색상을 빨간색으로 변경",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 120, "output_tokens": 280},
                "processing_time_ms": 2100,
                "json_patches": [
                    {
                        "op": "replace",
                        "path": "/cues/0/root/children/0/style/color",
                        "value": "#ff0000",
                    }
                ],
                "has_scenario_edits": True,
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
