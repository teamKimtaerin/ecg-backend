import json
import boto3
from typing import Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class BedrockService:
    """AWS Bedrock 서비스 클래스 - Claude 모델과 통신 및 응답 저장"""

    def __init__(self):
        """Bedrock 클라이언트 초기화"""
        try:
            self.client = boto3.client(
                "bedrock-runtime",
                region_name=settings.aws_bedrock_region,
                aws_access_key_id=settings.aws_bedrock_access_key_id,
                aws_secret_access_key=settings.aws_bedrock_secret_access_key,
            )
            logger.info(
                f"Bedrock client initialized for region: {settings.aws_bedrock_region}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise

    def invoke_claude(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        model_id: str = "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    ) -> Dict[str, Any]:
        """
        Claude 모델을 호출하여 응답 생성 및 저장

        Args:
            prompt: 입력 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 온도 (창의성 조절)
            model_id: 사용할 Claude 모델 ID

        Returns:
            Dict containing completion, stop_reason, and file_path (if saved)

        Raises:
            Exception: Bedrock API 호출 실패 시
        """
        try:
            # Claude 3.5 요청 포맷
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }

            logger.info(f"Invoking Claude model: {model_id}")
            logger.debug(
                f"Request body: {json.dumps(request_body, ensure_ascii=False)[:200]}..."
            )

            # Bedrock API 호출
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

            # 응답 파싱
            response_body = json.loads(response["body"].read())

            logger.info("Claude model invocation successful")
            logger.debug(
                f"Response: {json.dumps(response_body, ensure_ascii=False)[:200]}..."
            )

            # Claude 3.5 응답 포맷에서 텍스트 추출
            if "content" in response_body and len(response_body["content"]) > 0:
                completion = response_body["content"][0]["text"]
                stop_reason = response_body.get("stop_reason", "end_turn")
                usage = response_body.get("usage", {})

                result = {
                    "completion": completion,
                    "stop_reason": stop_reason,
                    "usage": usage,
                    "model_id": model_id,
                    "request_params": {
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "prompt_length": len(prompt),
                    },
                }

                return result
            else:
                raise Exception("Invalid response format from Claude model")

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(f"AWS Bedrock ClientError: {error_code} - {error_message}")

            # 사용자 친화적 에러 메시지 제공
            if error_code == "UnrecognizedClientException":
                raise Exception("AWS 자격증명이 유효하지 않습니다. 설정을 확인해주세요.")
            elif error_code == "AccessDeniedException":
                raise Exception("AWS Bedrock 액세스 권한이 없습니다. IAM 권한을 확인해주세요.")
            elif error_code == "ThrottlingException":
                raise Exception("API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            elif error_code == "ValidationException":
                raise Exception("요청 형식이 올바르지 않습니다.")
            else:
                raise Exception(f"AWS Bedrock API 오류: {error_message}")

        except BotoCoreError as e:
            logger.error(f"AWS BotoCoreError: {e}")
            raise Exception("AWS 연결에 문제가 발생했습니다. 네트워크를 확인해주세요.")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise Exception("응답 파싱 중 오류가 발생했습니다.")

        except Exception as e:
            logger.error(f"Unexpected error in invoke_claude: {e}")
            raise Exception(f"예상치 못한 오류가 발생했습니다: {str(e)}")

    def test_connection(self) -> bool:
        """
        Bedrock 연결 테스트

        Returns:
            bool: 연결 성공 여부
        """
        try:
            # 간단한 테스트 프롬프트로 연결 확인
            self.invoke_claude(
                prompt="안녕하세요",
                max_tokens=50,
                temperature=0.1,
                # 테스트용
            )
            return True
        except Exception as e:
            logger.error(f"Bedrock connection test failed: {e}")
            return False


# 전역 인스턴스 (싱글톤 패턴)
bedrock_service = BedrockService()
