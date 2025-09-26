from fastapi import APIRouter, HTTPException, status
import time
import logging
from typing import Dict, Any

from app.schemas.chatbot import (
    ChatBotRequest,
    ChatBotResponse,
    ChatBotErrorResponse,
)
from app.services.bedrock_service import bedrock_service
from app.services.langchain_bedrock_service import langchain_bedrock_service

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/chatbot", tags=["ChatBot"])


def build_xml_request(request: ChatBotRequest) -> str:
    """
    ChatBot 요청을 통일된 XML 구조로 변환

    Args:
        request: ChatBot 요청 객체

    Returns:
        str: XML 구조의 Claude 요청
    """
    import json

    # 사용자 지시사항 구성
    user_instruction = request.prompt

    # 대화 히스토리가 있는 경우 컨텍스트 추가
    if request.conversation_history and len(request.conversation_history) > 0:
        recent_messages = request.conversation_history[-6:]
        conversation_context = "\n".join(
            [
                f"{'Human' if msg.sender == 'user' else 'Assistant'}: {msg.content}"
                for msg in recent_messages
            ]
        )
        user_instruction = (
            f"대화 히스토리:\n{conversation_context}\n\n현재 요청: {request.prompt}"
        )

    # 현재 JSON 데이터 (시나리오가 있는 경우)
    current_json = ""
    if request.scenario_data:
        current_json = json.dumps(request.scenario_data, indent=2, ensure_ascii=False)
    else:
        current_json = "{}"

    # XML 구조로 변환
    xml_request = f"""<user_instruction>{user_instruction}</user_instruction>

<current_json>
{current_json}
</current_json>"""

    return xml_request


@router.post(
    "/",
    response_model=ChatBotResponse,
    responses={
        400: {"model": ChatBotErrorResponse, "description": "잘못된 요청"},
        500: {"model": ChatBotErrorResponse, "description": "서버 내부 오류"},
        503: {"model": ChatBotErrorResponse, "description": "외부 서비스 이용 불가"},
    },
    summary="ChatBot 메시지 전송",
    description="HOIT ChatBot과 대화를 나누는 API 엔드포인트입니다. 자막 편집 관련 질문에 답변합니다.",
)
async def send_chatbot_message(request: ChatBotRequest) -> ChatBotResponse:
    """
    ChatBot에게 메시지를 전송하고 응답을 받습니다.

    - **prompt**: 사용자 입력 메시지 (필수)
    - **conversation_history**: 이전 대화 내역 (선택사항)
    - **scenario_data**: 시나리오 데이터 (선택사항)
    - **use_langchain**: LangChain 사용 여부 (기본값: True)

    참고: max_tokens(2000)와 temperature(0.7)는 백엔드에서 고정값으로 설정됩니다.
    """
    start_time = time.time()

    try:
        logger.info(
            f"ChatBot request received: prompt length={len(request.prompt)}, use_langchain={request.use_langchain}, has_scenario={request.scenario_data is not None}"
        )

        # 백엔드에서 토큰 수와 온도 설정
        max_tokens = 2000  # 프론트엔드 값 무시하고 고정값 사용
        temperature = 0.7  # 프론트엔드 값 무시하고 고정값 사용

        # XML 구조로 변환된 요청 생성
        xml_request = build_xml_request(request)

        logger.info(
            f"Using LangChain service with XML request structure: max_tokens={max_tokens}, temperature={temperature}"
        )
        result = langchain_bedrock_service.invoke_claude_with_xml_request(
            xml_request=xml_request,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # 처리 시간 계산
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"ChatBot response generated successfully in {processing_time_ms}ms"
        )

        # 응답 구성
        response_data = {
            "completion": result["completion"],
            "stop_reason": result["stop_reason"],
            "usage": result.get("usage"),
            "processing_time_ms": processing_time_ms,
        }

        # 시나리오 편집 정보 추가
        if "json_patches" in result:
            response_data["json_patches"] = result["json_patches"]
            response_data["has_scenario_edits"] = bool(result["json_patches"])
        else:
            response_data["has_scenario_edits"] = False

        return ChatBotResponse(**response_data)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "요청 형식이 올바르지 않습니다",
                "error_code": "VALIDATION_ERROR",
                "details": str(e),
            },
        )

    except Exception as e:
        logger.error(f"ChatBot API error: {e}")

        # AWS 관련 에러인지 확인
        error_message = str(e)
        if "AWS" in error_message or "Bedrock" in error_message:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_code = "BEDROCK_API_ERROR"
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_code = "INTERNAL_SERVER_ERROR"

        raise HTTPException(
            status_code=status_code,
            detail={
                "error": error_message,
                "error_code": error_code,
                "details": f"처리 시간: {int((time.time() - start_time) * 1000)}ms",
            },
        )


@router.get(
    "/health",
    summary="ChatBot 서비스 상태 확인",
    description="ChatBot 서비스와 AWS Bedrock 연결 상태를 확인합니다.",
)
async def chatbot_health_check() -> Dict[str, Any]:
    """
    ChatBot 서비스 상태를 확인합니다.
    """
    try:
        # 기존 Bedrock 연결 테스트
        is_bedrock_healthy = bedrock_service.test_connection()

        # LangChain Bedrock 연결 테스트
        is_langchain_healthy = langchain_bedrock_service.test_connection()

        return {
            "status": "healthy"
            if (is_bedrock_healthy and is_langchain_healthy)
            else "unhealthy",
            "bedrock_connection": is_bedrock_healthy,
            "langchain_connection": is_langchain_healthy,
            "timestamp": time.time(),
            "service": "HOIT ChatBot API",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "bedrock_connection": False,
            "langchain_connection": False,
            "error": str(e),
            "timestamp": time.time(),
            "service": "HOIT ChatBot API",
        }
