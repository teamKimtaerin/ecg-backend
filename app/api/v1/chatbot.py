from fastapi import APIRouter, HTTPException, status, Query
import time
import logging
from typing import Dict, Any, Optional, List

from app.schemas.chatbot import (
    ChatBotRequest,
    ChatBotResponse,
    ChatBotErrorResponse,
    SavedFileInfo,
)
from app.services.bedrock_service import bedrock_service
from app.services.langchain_bedrock_service import langchain_bedrock_service

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(prefix="/chatbot", tags=["ChatBot"])


def build_context_prompt(request: ChatBotRequest) -> str:
    """
    ChatBot 요청을 기반으로 컨텍스트 프롬프트 구성

    Args:
        request: ChatBot 요청 객체

    Returns:
        str: 완성된 프롬프트
    """
    system_prompt = """당신은 ECG(Easy Caption Generator) 자막 편집 도구의 AI 어시스턴트 "둘리"입니다.

주요 역할:
1. 자막 편집 관련 질문에 친절하고 정확하게 답변
2. ECG 도구의 기능 사용법 안내
3. 자막 작업 효율성 개선 팁 제공
4. 기술적 문제 해결 도움

답변 스타일:
- 친근하고 도움이 되는 톤
- 간결하면서도 충분한 정보 제공
- 단계별 설명이 필요한 경우 명확한 순서로 안내
- 한국어로 자연스럽게 대화

ECG 주요 기능:
- 자동 자막 생성 (AI 음성 인식)
- 실시간 자막 편집
- 다양한 애니메이션 효과
- 화자 분리 및 관리
- GPU 가속 렌더링
- 드래그 앤 드롭 편집"""

    # 대화 히스토리 구성
    conversation_context = ""
    if request.conversation_history and len(request.conversation_history) > 0:
        # 최근 6개 메시지만 포함 (토큰 절약)
        recent_messages = request.conversation_history[-6:]
        conversation_context = "\n\n".join(
            [
                f"{'Human' if msg.sender == 'user' else 'Assistant'}: {msg.content}"
                for msg in recent_messages
            ]
        )
        conversation_context += "\n\n"

    # 전체 프롬프트 구성
    full_prompt = f"{system_prompt}\n\n{conversation_context}Human: {request.prompt}"

    return full_prompt


@router.post(
    "/",
    response_model=ChatBotResponse,
    responses={
        400: {"model": ChatBotErrorResponse, "description": "잘못된 요청"},
        500: {"model": ChatBotErrorResponse, "description": "서버 내부 오류"},
        503: {"model": ChatBotErrorResponse, "description": "외부 서비스 이용 불가"},
    },
    summary="ChatBot 메시지 전송",
    description="ECG ChatBot과 대화를 나누는 API 엔드포인트입니다. 자막 편집 관련 질문에 답변하고 응답을 파일로 저장합니다.",
)
async def send_chatbot_message(request: ChatBotRequest) -> ChatBotResponse:
    """
    ChatBot에게 메시지를 전송하고 응답을 받습니다. 응답은 자동으로 output 폴더에 저장됩니다.

    - **prompt**: 사용자 입력 메시지 (필수)
    - **conversation_history**: 이전 대화 내역 (선택사항)
    - **scenario_data**: 시나리오 데이터 (선택사항)
    - **save_response**: 응답을 파일로 저장할지 여부 (기본값: True)
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
        
        # 시나리오 데이터가 있거나 LangChain이 요청된 경우 LangChain 사용
        if request.use_langchain or request.scenario_data is not None:
            # LangChain을 통한 호출 (시나리오 데이터 포함)
            logger.info(f"Using LangChain service with backend-set values: max_tokens={max_tokens}, temperature={temperature}")
            result = langchain_bedrock_service.invoke_claude_with_chain(
                prompt=request.prompt,
                conversation_history=request.conversation_history,
                scenario_data=request.scenario_data,
                max_tokens=max_tokens,
                temperature=temperature,
                save_response=request.save_response,
            )
        else:
            # 기존 직접 API 호출 방식 (시나리오 데이터 없는 경우만)
            logger.info(f"Using basic Bedrock service with backend-set values: max_tokens={max_tokens}, temperature={temperature}")
            # 프롬프트 구성
            full_prompt = build_context_prompt(request)
            logger.debug(f"Full prompt preview: {full_prompt[:200]}...")

            # Bedrock 서비스 호출 (파일 저장 포함)
            result = bedrock_service.invoke_claude(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                save_response=request.save_response,
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

        # 파일 저장 정보 추가
        if "saved_files" in result:
            response_data["saved_files"] = result["saved_files"]

        if "save_error" in result:
            response_data["save_error"] = result["save_error"]

        # 시나리오 편집 정보 추가
        if "edit_result" in result:
            response_data["edit_result"] = result["edit_result"]

        if "json_patches" in result:
            response_data["json_patches"] = result["json_patches"]
            response_data["has_scenario_edits"] = bool(result["json_patches"])

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
            "service": "ECG ChatBot API",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "bedrock_connection": False,
            "langchain_connection": False,
            "error": str(e),
            "timestamp": time.time(),
            "service": "ECG ChatBot API",
        }


@router.get(
    "/saved-responses",
    response_model=List[str],
    summary="저장된 응답 파일 목록 조회",
    description="저장된 ChatBot 응답 파일들의 목록을 조회합니다.",
)
async def get_saved_responses(
    pattern: Optional[str] = Query(default="bedrock_*", description="파일 패턴 필터")
) -> List[str]:
    """
    저장된 응답 파일 목록을 조회합니다.

    - **pattern**: 파일 패턴 (예: "bedrock_*", "*.json")
    """
    try:
        files = bedrock_service.get_saved_responses(pattern)
        logger.info(f"Found {len(files)} saved response files")
        return files
    except Exception as e:
        logger.error(f"Failed to get saved responses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "저장된 파일 목록을 가져오는데 실패했습니다",
                "error_code": "FILE_LIST_ERROR",
                "details": str(e),
            },
        )


@router.get(
    "/file-info/{filename}",
    response_model=SavedFileInfo,
    summary="파일 정보 조회",
    description="특정 응답 파일의 상세 정보를 조회합니다.",
)
async def get_file_info(filename: str) -> SavedFileInfo:
    """
    특정 파일의 정보를 조회합니다.

    - **filename**: 조회할 파일명
    """
    try:
        file_info = bedrock_service.get_response_file_info(filename)

        if "error" in file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "파일을 찾을 수 없습니다",
                    "error_code": "FILE_NOT_FOUND",
                    "details": file_info["error"],
                },
            )

        return SavedFileInfo(**file_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get file info for {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "파일 정보를 가져오는데 실패했습니다",
                "error_code": "FILE_INFO_ERROR",
                "details": str(e),
            },
        )


@router.post(
    "/langchain",
    response_model=ChatBotResponse,
    responses={
        400: {"model": ChatBotErrorResponse, "description": "잘못된 요청"},
        500: {"model": ChatBotErrorResponse, "description": "서버 내부 오류"},
        503: {"model": ChatBotErrorResponse, "description": "외부 서비스 이용 불가"},
    },
    summary="LangChain ChatBot 메시지 전송",
    description="LangChain을 사용하여 ECG ChatBot과 대화하는 전용 엔드포인트입니다. 고급 기능(메모리, 체인)을 제공합니다.",
)
async def send_langchain_chatbot_message(request: ChatBotRequest) -> ChatBotResponse:
    """
    LangChain을 사용하여 ChatBot에게 메시지를 전송합니다.

    이 엔드포인트는 항상 LangChain을 사용하며 다음 고급 기능을 제공합니다:
    - 대화 메모리 관리
    - 프롬프트 템플릿
    - 체인 기반 처리
    - MotionTextEditor 표준 준수
    
    참고: max_tokens(2000)와 temperature(0.7)는 백엔드에서 고정값으로 설정됩니다.
    """
    start_time = time.time()

    try:
        logger.info(
            f"LangChain ChatBot request received: prompt length={len(request.prompt)}"
        )
        
        # 백엔드에서 토큰 수와 온도 설정
        max_tokens = 2000  # 프론트엔드 값 무시하고 고정값 사용
        temperature = 0.7  # 프론트엔드 값 무시하고 고정값 사용

        # LangChain을 통한 호출 (강제, 시나리오 데이터 포함)
        logger.info(f"LangChain endpoint with backend-set values: max_tokens={max_tokens}, temperature={temperature}")
        result = langchain_bedrock_service.invoke_claude_with_chain(
            prompt=request.prompt,
            conversation_history=request.conversation_history,
            scenario_data=request.scenario_data,
            max_tokens=max_tokens,
            temperature=temperature,
            save_response=request.save_response,
        )

        # 처리 시간 계산
        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"LangChain ChatBot response generated successfully in {processing_time_ms}ms"
        )

        # 응답 구성
        response_data = {
            "completion": result["completion"],
            "stop_reason": result["stop_reason"],
            "usage": result.get("usage"),
            "processing_time_ms": processing_time_ms,
        }

        # 파일 저장 정보 추가
        if "saved_files" in result:
            response_data["saved_files"] = result["saved_files"]

        if "save_error" in result:
            response_data["save_error"] = result["save_error"]

        # 시나리오 편집 정보 추가
        if "edit_result" in result:
            response_data["edit_result"] = result["edit_result"]

        if "json_patches" in result:
            response_data["json_patches"] = result["json_patches"]
            response_data["has_scenario_edits"] = bool(result["json_patches"])

        return ChatBotResponse(**response_data)

    except ValueError as e:
        logger.error(f"LangChain validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "요청 형식이 올바르지 않습니다",
                "error_code": "VALIDATION_ERROR",
                "details": str(e),
            },
        )

    except Exception as e:
        logger.error(f"LangChain ChatBot API error: {e}")

        # LangChain 관련 에러인지 확인
        error_message = str(e)
        if "langchain" in error_message.lower() or "bedrock" in error_message.lower():
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            error_code = "LANGCHAIN_API_ERROR"
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
