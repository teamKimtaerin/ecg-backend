import logging
from typing import Dict, Any, List, Optional

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.memory import ConversationBufferMemory
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.schemas.chatbot import ChatMessage

logger = logging.getLogger(__name__)


class LangChainBedrockService:
    """LangChain을 사용한 AWS Bedrock 서비스 클래스"""

    def __init__(self):
        """LangChain ChatBedrock 클라이언트 초기화"""
        try:
            self.llm = ChatBedrock(
                model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
                region_name=settings.aws_bedrock_region,
                credentials_profile_name=None,  # 환경변수 사용
                model_kwargs={
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
            )

            # 출력 파서 초기화
            self.output_parser = StrOutputParser()

            # 시스템 프롬프트 템플릿 정의 (MotionTextEditor 표준 적용)
            self.system_template = """당신은 MotionText v2.0 JSON을 RFC6902 JSON Patch로 수정하는 전문 편집기입니다.

<role>
사용자의 자연어 지시를 받아 MotionText v2.0 JSON을 RFC6902 JSON Patch로 수정합니다.
</role>

<rules>
- 최소 변경: 지시된 부분만 수정
- 청킹 필수: 출력이 1800토큰 초과시 여러 청크로 분할
- 순서 보장: 각 청크는 이전 청크 적용 후 적용 가능해야 함
- RFC6902 표준: 정확한 JSON Patch 형식 준수
</rules>

<schema_requirements>
- version: 2.0 유지
- timebase: unit="seconds", fps는 숫자
- time_fields: [start, end] 초 배열
- eType: "group"|"text"|"image"|"video"만 허용
- node_id: 모든 노드는 고유 id 필요
</schema_requirements>

<processing_steps>
1. 사용자 지시 파싱
2. 영향받는 JSON 경로 식별
3. JSON Patch 연산 생성
4. 1800토큰 기준으로 청킹
5. 표준 형식으로 출력
</processing_steps>

<common_patterns>
- text_change: {{"op": "replace", "path": "/cues/0/root/text", "value": "새 텍스트"}}
- time_adjustment: {{"op": "replace", "path": "/cues/0/displayTime", "value": [0, 10]}}
- plugin_add: {{"op": "add", "path": "/cues/0/root/pluginChain/-", "value": {{"pluginId": "fadein@2.0.0", "timeOffset": ["0%", "100%"], "params": {{"animationDuration": 1.0}}}}}}
- plugin_param_edit: {{"op": "replace", "path": "/cues/0/root/pluginChain/1/params/typingSpeed", "value": 0.1}}
- style_edit: {{"op": "replace", "path": "/cues/0/root/style/color", "value": "#ff0000"}}
- word_plugin_add: {{"op": "add", "path": "/cues/0/root/children/0/pluginChain/-", "value": {{"pluginId": "glow@2.0.0", "params": {{"color": "#00ffff", "intensity": 0.8}}}}}}
- angry_emotion: {{"op": "add", "path": "/cues/0/root/children/0/pluginChain/-", "value": {{"pluginId": "cwi-loud@2.0.0", "timeOffset": [0, 0], "params": {{"color": "#ff0000", "pulse": {{"scale": 2.15, "lift": 12}}, "tremble": {{"ampPx": 1.5, "freq": 12}}}}}}}}
- multi_word_animation: 여러 단어에 동일한 애니메이션 적용 시 각 단어마다 개별 patch 생성
  [
    {{"op": "add", "path": "/cues/0/root/children/0/pluginChain/-", "value": {{"pluginId": "glow@2.0.0", "params": {{"color": "#00ffff", "intensity": 0.8}}}}}},
    {{"op": "add", "path": "/cues/0/root/children/1/pluginChain/-", "value": {{"pluginId": "glow@2.0.0", "params": {{"color": "#00ffff", "intensity": 0.8}}}}}},
    {{"op": "add", "path": "/cues/0/root/children/2/pluginChain/-", "value": {{"pluginId": "glow@2.0.0", "params": {{"color": "#00ffff", "intensity": 0.8}}}}}}
  ]
- multi_word_emotion: 여러 단어에 감정 표현 적용
  [
    {{"op": "add", "path": "/cues/0/root/children/1/pluginChain/-", "value": {{"pluginId": "cwi-loud@2.0.0", "timeOffset": [0, 0], "params": {{"color": "#ff0000", "pulse": {{"scale": 2.15, "lift": 12}}, "tremble": {{"ampPx": 1.5, "freq": 12}}}}}}}},
    {{"op": "add", "path": "/cues/0/root/children/2/pluginChain/-", "value": {{"pluginId": "cwi-loud@2.0.0", "timeOffset": [0, 0], "params": {{"color": "#ff0000", "pulse": {{"scale": 2.15, "lift": 12}}, "tremble": {{"ampPx": 1.5, "freq": 12}}}}}}}}
  ]
</common_patterns>

<multi_word_handling>
여러 단어 선택 시 규칙:
1. 사용자가 "첫 번째와 세 번째 단어", "모든 단어", "단어들" 등으로 복수 단어를 언급하면 각 단어마다 개별 patch 생성
2. 동일한 애니메이션을 여러 단어에 적용할 때는 각 children[N] 인덱스별로 별도의 add 연산 수행
3. 예시: "첫 번째와 두 번째 단어에 glow 효과" → children[0]과 children[1]에 각각 glow 플러그인 추가
4. 반드시 multi_word_animation 패턴 참조하여 여러 patch 생성
</multi_word_handling>

<output_format>
<summary>선택사항: 총 N개 연산, 주요 변경사항</summary>
<json_patch_chunk index="1" total="N" ops="K">
<![CDATA[
[
  {{"op": "replace", "path": "/cues/0/root/text", "value": "새 텍스트"}}
]
]]>
</json_patch_chunk>
<apply_order>1,2,3</apply_order>
</output_format>

중요: 설명 없이 summary, json_patch_chunk, apply_order만 출력하세요."""

            # 프롬프트 템플릿 구성 (MotionTextEditor 표준)
            self.prompt_template = ChatPromptTemplate.from_messages(
                [
                    SystemMessagePromptTemplate.from_template(self.system_template),
                    HumanMessagePromptTemplate.from_template(
                        "<user_instruction>{input}</user_instruction>\n\n"
                        "<current_json>\n{scenario_data}\n</current_json>\n\n"
                        "위의 MotionText v2.0 JSON에 사용자 지시사항을 적용하여 RFC6902 JSON Patch로 출력하세요."
                    ),
                ]
            )

            # 체인 구성 (프롬프트 → LLM → 파서)
            self.chain = self.prompt_template | self.llm | self.output_parser

            logger.info(
                f"LangChain ChatBedrock initialized for region: {settings.aws_bedrock_region}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize LangChain ChatBedrock: {e}")
            raise

    def _convert_chat_history_to_messages(
        self, chat_history: List[ChatMessage]
    ) -> List:
        """ChatMessage 리스트를 LangChain 메시지로 변환"""
        messages = []

        # 최근 6개 메시지만 포함 (토큰 절약)
        recent_messages = chat_history[-6:] if len(chat_history) > 6 else chat_history

        for msg in recent_messages:
            if msg.sender == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.sender == "bot":
                messages.append(AIMessage(content=msg.content))

        return messages

    def invoke_claude_with_chain(
        self,
        prompt: str,
        conversation_history: Optional[List[ChatMessage]] = None,
        scenario_data: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        LangChain 체인을 사용하여 Claude 모델 호출

        Args:
            prompt: 사용자 입력 프롬프트
            conversation_history: 대화 히스토리
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (0.0-1.0)

        Returns:
            Dict containing completion and metadata
        """
        try:
            # 프롬프트 디버깅 로그 추가
            logger.info(f"🔍 [DEBUG] Input prompt: '{prompt}'")
            logger.info(
                f"🔍 [DEBUG] Prompt ends with '!!': {prompt.strip().endswith('!!')}"
            )
            logger.info(f"🔍 [DEBUG] Scenario data present: {scenario_data is not None}")
            if scenario_data:
                logger.info(f"🔍 [DEBUG] Scenario data type: {type(scenario_data)}")
                logger.info(
                    f"🔍 [DEBUG] Scenario data keys: {list(scenario_data.keys()) if isinstance(scenario_data, dict) else 'not dict'}"
                )

            # 데모 프롬프트 체크 ('!!'로 끝나는 경우)
            if prompt.strip().endswith("!!"):
                logger.info(
                    "🎭 DEMO PROMPT DETECTED - generating demo response with Loud animation and red gradient"
                )
                return self._generate_demo_response(scenario_data, prompt)

            # 모델 파라미터 업데이트
            self.llm.model_kwargs.update(
                {
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            )

            logger.info(
                f"Invoking Claude via LangChain: max_tokens={max_tokens}, temp={temperature}"
            )

            # 시나리오 데이터가 있으면 직접 편집 체인 사용
            if scenario_data:
                logger.info(
                    "🎯 Scenario data detected - using DIRECT SUBTITLE EDIT CHAIN"
                )
                logger.info(
                    f"📊 Scenario data size: {len(str(scenario_data))} characters"
                )
                logger.info(f"💬 User prompt: '{prompt}'")

                # MotionText v2.0 스키마 검증
                validation_result = self._validate_motion_text_schema(scenario_data)
                if not validation_result["valid"]:
                    logger.warning(
                        f"⚠️ Schema validation issues: {validation_result['errors']}"
                    )
                if validation_result["warnings"]:
                    logger.info(f"📝 Schema warnings: {validation_result['warnings']}")

                try:
                    edit_result = self.create_direct_subtitle_edit_chain(
                        user_message=prompt,
                        scenario_data=scenario_data,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )

                    logger.info("✅ Direct edit chain completed successfully")
                    logger.info(
                        f"📝 Edit result type: {edit_result.get('type', 'unknown')}"
                    )
                    logger.info(f"✨ Edit success: {edit_result.get('success', False)}")

                    # 편집 결과를 기본 응답 형식으로 변환
                    return {
                        "completion": edit_result.get("explanation", "편집이 완료되었습니다."),
                        "stop_reason": "end_turn",
                        "usage": {
                            "input_tokens": len(prompt.split()),
                            "output_tokens": len(str(edit_result).split()),
                        },
                        "model_id": self.llm.model_id,
                        "langchain_used": True,
                        "edit_result": edit_result,  # 실제 편집 결과 포함
                        "json_patches": edit_result.get("patches", []),  # JSON patch 정보
                        "request_params": {
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                            "prompt_length": len(prompt),
                            "has_scenario_data": True,
                        },
                    }
                except Exception as e:
                    logger.error(
                        f"❌ Direct edit chain failed, falling back to standard chain: {e}"
                    )
                    logger.warning(
                        "🔄 Switching to standard chain processing with scenario context"
                    )
                    # 편집 체인 실패시 기본 체인으로 fallback

            # 기본 체인 사용 (시나리오 데이터 없거나 편집 체인 실패시)
            logger.info("🔧 Using STANDARD CHAIN processing")

            scenario_json = ""
            if scenario_data:
                try:
                    import json

                    scenario_json = json.dumps(
                        scenario_data, indent=2, ensure_ascii=False
                    )
                    logger.info(
                        f"Scenario data included: {len(scenario_json)} characters"
                    )
                except Exception as e:
                    logger.warning(f"Failed to serialize scenario data: {e}")
                    scenario_json = "시나리오 데이터 처리 중 오류 발생"
            else:
                scenario_json = "시나리오 데이터 없음"

            # 대화 히스토리가 있는 경우 메모리 사용
            if conversation_history and len(conversation_history) > 0:
                # 메모리 초기화
                memory = ConversationBufferMemory(
                    memory_key="chat_history", return_messages=True
                )

                # 대화 히스토리를 메모리에 추가
                messages = self._convert_chat_history_to_messages(conversation_history)
                for message in messages:
                    if isinstance(message, HumanMessage):
                        memory.chat_memory.add_user_message(message.content)
                    elif isinstance(message, AIMessage):
                        memory.chat_memory.add_ai_message(message.content)

                # 대화 히스토리를 포함한 프롬프트 템플릿 (시나리오 데이터 포함)
                history_prompt = ChatPromptTemplate.from_messages(
                    [
                        SystemMessagePromptTemplate.from_template(self.system_template),
                        *messages,
                        HumanMessagePromptTemplate.from_template(
                            "사용자 요청: {input}\n\n"
                            "현재 시나리오 파일 (자막 및 스타일링 데이터):\n"
                            "```json\n{scenario_data}\n```\n\n"
                            "위 시나리오 파일을 참고하여 사용자의 요청을 처리해주세요."
                        ),
                    ]
                )

                # 히스토리 포함 체인
                history_chain = history_prompt | self.llm | self.output_parser
                completion = history_chain.invoke(
                    {"input": prompt, "scenario_data": scenario_json}
                )
            else:
                # 시나리오 데이터와 함께 단순 체인 사용
                completion = self.chain.invoke(
                    {"input": prompt, "scenario_data": scenario_json}
                )

            logger.info("LangChain Claude invocation successful")
            logger.debug(f"Response preview: {completion[:200]}...")

            # 응답 결과 구성
            result = {
                "completion": completion,
                "stop_reason": "end_turn",  # LangChain에서는 직접 제공하지 않으므로 기본값
                "usage": {
                    "input_tokens": len(prompt.split()),  # 근사치
                    "output_tokens": len(completion.split()),  # 근사치
                },
                "model_id": self.llm.model_id,
                "langchain_used": True,
                "request_params": {
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "prompt_length": len(prompt),
                    "history_length": len(conversation_history)
                    if conversation_history
                    else 0,
                },
            }

            return result

        except Exception as e:
            logger.error(f"LangChain Claude invocation failed: {e}")

            # 에러 타입별 처리
            if "credentials" in str(e).lower() or "access" in str(e).lower():
                raise Exception("AWS 자격증명이 유효하지 않습니다. 설정을 확인해주세요.")
            elif "throttling" in str(e).lower() or "rate" in str(e).lower():
                raise Exception("API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")
            elif "validation" in str(e).lower():
                raise Exception("요청 형식이 올바르지 않습니다.")
            else:
                raise Exception(f"LangChain을 통한 Claude 호출 실패: {str(e)}")

    def test_connection(self) -> bool:
        """
        LangChain을 통한 Bedrock 연결 테스트

        Returns:
            bool: 연결 성공 여부
        """
        try:
            test_result = self.invoke_claude_with_chain(
                prompt="안녕하세요",
                max_tokens=50,
                temperature=0.1,
            )
            return "completion" in test_result and len(test_result["completion"]) > 0
        except Exception as e:
            logger.error(f"LangChain connection test failed: {e}")
            return False

    def create_multi_step_chain(
        self,
        steps: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        여러 단계로 구성된 체인 실행

        Args:
            steps: 단계별 프롬프트 리스트 [{"step": "1", "prompt": "..."}, ...]
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절

        Returns:
            Dict: 각 단계별 결과와 최종 결과
        """
        try:
            results = {}
            accumulated_context = ""

            logger.info(f"Starting multi-step chain with {len(steps)} steps")

            for i, step_info in enumerate(steps, 1):
                step_name = step_info.get("step", f"step_{i}")
                step_prompt = step_info.get("prompt", "")

                # 이전 단계 결과를 컨텍스트로 포함
                if accumulated_context:
                    full_prompt = (
                        f"이전 단계 결과:\n{accumulated_context}\n\n현재 단계: {step_prompt}"
                    )
                else:
                    full_prompt = step_prompt

                logger.info(f"Executing step {i}/{len(steps)}: {step_name}")

                # 각 단계별 체인 실행
                step_result = self.invoke_claude_with_chain(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                results[step_name] = {
                    "prompt": step_prompt,
                    "response": step_result["completion"],
                    "step_number": i,
                    "usage": step_result.get("usage", {}),
                }

                # 다음 단계를 위해 결과 누적
                accumulated_context += f"\n[{step_name}] {step_result['completion']}"

            # 최종 결과 구성
            final_result = {
                "multi_step_results": results,
                "final_context": accumulated_context,
                "total_steps": len(steps),
                "langchain_used": True,
                "chain_type": "multi_step",
            }

            logger.info(
                f"Multi-step chain completed successfully with {len(steps)} steps"
            )
            return final_result

        except Exception as e:
            logger.error(f"Multi-step chain failed: {e}")
            raise Exception(f"다단계 체인 실행 실패: {str(e)}")

    def create_parallel_chain(
        self,
        parallel_prompts: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        여러 프롬프트를 병렬로 실행하는 체인

        Args:
            parallel_prompts: 병렬 실행할 프롬프트들 [{"name": "task1", "prompt": "..."}, ...]
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절

        Returns:
            Dict: 각 병렬 작업별 결과
        """
        try:
            results = {}

            logger.info(f"Starting parallel chain with {len(parallel_prompts)} tasks")

            for task_info in parallel_prompts:
                task_name = task_info.get("name", f"task_{len(results) + 1}")
                task_prompt = task_info.get("prompt", "")

                logger.info(f"Executing parallel task: {task_name}")

                # 각 작업별 독립적인 체인 실행
                task_result = self.invoke_claude_with_chain(
                    prompt=task_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                results[task_name] = {
                    "prompt": task_prompt,
                    "response": task_result["completion"],
                    "usage": task_result.get("usage", {}),
                    "model_id": task_result.get("model_id"),
                }

            # 최종 결과 구성
            final_result = {
                "parallel_results": results,
                "total_tasks": len(parallel_prompts),
                "langchain_used": True,
                "chain_type": "parallel",
            }

            logger.info(
                f"Parallel chain completed successfully with {len(parallel_prompts)} tasks"
            )
            return final_result

        except Exception as e:
            logger.error(f"Parallel chain failed: {e}")
            raise Exception(f"병렬 체인 실행 실패: {str(e)}")

    def create_conditional_chain(
        self,
        initial_prompt: str,
        conditions: List[Dict[str, Any]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        조건부 체인 실행 (첫 번째 응답에 따라 다음 단계 결정)

        Args:
            initial_prompt: 초기 프롬프트
            conditions: 조건별 다음 단계들 [{"condition_keyword": "키워드", "next_prompt": "..."}, ...]
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절

        Returns:
            Dict: 조건부 실행 결과
        """
        try:
            logger.info("Starting conditional chain")

            # 1단계: 초기 프롬프트 실행
            initial_result = self.invoke_claude_with_chain(
                prompt=initial_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            initial_response = initial_result["completion"].lower()

            # 2단계: 조건 확인 및 다음 단계 결정
            matched_condition = None
            for condition in conditions:
                condition_keyword = condition.get("condition_keyword", "").lower()
                if condition_keyword and condition_keyword in initial_response:
                    matched_condition = condition
                    break

            if matched_condition:
                logger.info(
                    f"Condition matched: {matched_condition.get('condition_keyword')}"
                )

                # 조건에 맞는 다음 단계 실행
                next_prompt = matched_condition.get("next_prompt", "")
                context_prompt = (
                    f"이전 응답: {initial_result['completion']}\n\n{next_prompt}"
                )

                next_result = self.invoke_claude_with_chain(
                    prompt=context_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                final_result = {
                    "initial_step": {
                        "prompt": initial_prompt,
                        "response": initial_result["completion"],
                        "usage": initial_result.get("usage", {}),
                    },
                    "conditional_step": {
                        "matched_condition": matched_condition.get("condition_keyword"),
                        "prompt": next_prompt,
                        "response": next_result["completion"],
                        "usage": next_result.get("usage", {}),
                    },
                    "final_response": next_result["completion"],
                    "langchain_used": True,
                    "chain_type": "conditional",
                }
            else:
                logger.info("No condition matched, using initial response")
                final_result = {
                    "initial_step": {
                        "prompt": initial_prompt,
                        "response": initial_result["completion"],
                        "usage": initial_result.get("usage", {}),
                    },
                    "conditional_step": None,
                    "final_response": initial_result["completion"],
                    "langchain_used": True,
                    "chain_type": "conditional",
                }

            logger.info("Conditional chain completed successfully")
            return final_result

        except Exception as e:
            logger.error(f"Conditional chain failed: {e}")
            raise Exception(f"조건부 체인 실행 실패: {str(e)}")

    def invoke_claude_with_xml_request(
        self,
        xml_request: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        통합된 XML 구조를 사용하여 Claude를 호출하고 응답을 파싱합니다.

        Args:
            xml_request: XML 형식의 요청 (<user_instruction> + <current_json>)
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절

        Returns:
            Dict: 파싱된 응답 (completion, json_patches, has_scenario_edits 등)
        """
        try:
            logger.info("🚀 Processing unified XML request")

            # Claude 호출
            result = self.invoke_claude_with_chain(
                prompt=xml_request,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # XML 응답 파싱
            motion_result = self._parse_motion_text_editor_response(
                result["completion"]
            )

            if motion_result["success"] and "patches" in motion_result:
                # plugin 형식 변환 적용
                transformed_patches = self._transform_json_patches(
                    motion_result["patches"]
                )

                # 성공적으로 파싱된 경우
                return {
                    "completion": result["completion"],
                    "stop_reason": result["stop_reason"],
                    "usage": result.get("usage"),
                    "model_id": result.get("model_id"),
                    "langchain_used": True,
                    "json_patches": transformed_patches,
                    "has_scenario_edits": bool(transformed_patches),
                }
            else:
                # 파싱 실패 또는 일반 대화인 경우
                return {
                    "completion": result["completion"],
                    "stop_reason": result["stop_reason"],
                    "usage": result.get("usage"),
                    "model_id": result.get("model_id"),
                    "langchain_used": True,
                    "json_patches": [],
                    "has_scenario_edits": False,
                }

        except Exception as e:
            logger.error(f"XML request processing failed: {e}")
            raise Exception(f"XML 요청 처리 실패: {str(e)}")

    def create_subtitle_animation_chain(
        self,
        user_message: str,
        subtitle_json: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1500,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        HOIT 자막 애니메이션 처리를 위한 특화된 순차 체인
        Prompt.md의 워크플로우를 따름

        Args:
            user_message: 사용자 메시지
            subtitle_json: 기존 자막 JSON 데이터 (선택사항)
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (낮은 값으로 정확성 우선)

        Returns:
            Dict: 단계별 처리 결과와 최종 JSON patch
        """
        try:
            logger.info("Starting HOIT subtitle animation chain")

            # 단계 1: 메시지 유형 분류
            classification_prompt = f"""다음 사용자 메시지를 분석하여 유형을 분류해주세요:

사용자 메시지: "{user_message}"

분류 기준:
1. "simple_info" - 단순한 정보 요청
2. "simple_edit" - 간단한 자막 수정 (오탈자, 단어 변경 등)
3. "animation_request" - 자막 애니메이션 수정/추가 요청

응답 형식:
{{
    "classification": "분류결과",
    "confidence": 0.95,
    "reasoning": "분류 근거"
}}"""

            step1_result = self.invoke_claude_with_chain(
                prompt=classification_prompt,
                max_tokens=200,
                temperature=0.1,
            )

            logger.info("Step 1 completed: Message classification")

            # 분류 결과 파싱 시도
            logger.info(
                f"🔍 Raw AI classification response: {step1_result['completion']}"
            )

            try:
                import json

                classification_data = json.loads(step1_result["completion"])
                classification = classification_data.get(
                    "classification", "animation_request"
                )
                confidence = classification_data.get("confidence", "unknown")
                reasoning = classification_data.get(
                    "reasoning", "No reasoning provided"
                )

                logger.info(
                    f"✅ JSON parsing successful - Classification: {classification}, Confidence: {confidence}"
                )
                logger.info(f"📝 AI reasoning: {reasoning}")

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(
                    f"❌ JSON parsing failed ({type(e).__name__}: {e}), falling back to keyword-based classification"
                )

                # JSON 파싱 실패시 키워드 기반 분류
                response_lower = step1_result["completion"].lower()
                logger.info(
                    f"🔤 Analyzing keywords in lowercase response: '{response_lower[:200]}...'"
                )

                if "simple_info" in response_lower or "정보" in response_lower:
                    classification = "simple_info"
                    logger.info("🎯 Keyword match: 'simple_info' or '정보' found")
                elif "simple_edit" in response_lower or "간단" in response_lower:
                    classification = "simple_edit"
                    logger.info("🎯 Keyword match: 'simple_edit' or '간단' found")
                else:
                    classification = "animation_request"
                    logger.info("🎯 Default fallback: classified as 'animation_request'")

            logger.info(
                f"🏷️  FINAL CLASSIFICATION: '{classification}' for user message: '{user_message}')"
            )

            # 단계 2: 분류에 따른 처리
            logger.info(f"🔄 Processing classification: {classification}")

            if classification == "simple_info":
                logger.info(
                    "📚 Processing as SIMPLE_INFO request - providing general information"
                )
                # 단순 정보 요청 - 바로 응답
                info_prompt = f"""HOIT 자막 편집 도구에 대한 질문에 답변해주세요:

질문: {user_message}

HOIT 주요 기능:
- 자동 자막 생성
- 실시간 자막 편집
- 다양한 애니메이션 효과
- 화자 분리 및 관리
- GPU 가속 렌더링
- 드래그 앤 드롭 편집

친근하고 도움이 되는 톤으로 답변해주세요."""

                final_result = self.invoke_claude_with_chain(
                    prompt=info_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                return {
                    "chain_type": "subtitle_animation",
                    "classification": "simple_info",
                    "steps": {
                        "classification": step1_result,
                        "final_response": final_result,
                    },
                    "final_response": final_result["completion"],
                    "json_patch": None,
                    "langchain_used": True,
                }

            elif classification == "simple_edit":
                logger.info(
                    "✏️  Processing as SIMPLE_EDIT request - modifying subtitle text/style"
                )
                # 간단한 자막 수정
                if not subtitle_json:
                    return {
                        "chain_type": "subtitle_animation",
                        "classification": "simple_edit",
                        "error": "자막 JSON 데이터가 필요합니다.",
                        "langchain_used": True,
                    }

                edit_prompt = f"""기존 자막 JSON을 바탕으로 사용자 요청사항을 JSON patch 형태로 수정해주세요:

사용자 요청: {user_message}
기존 자막 JSON: {json.dumps(subtitle_json, ensure_ascii=False, indent=2)}

JSON patch 형태로 수정사항을 제공해주세요. 기존 구조를 유지하면서 필요한 부분만 수정하세요.

응답 형식:
{{
    "patches": [
        {{"op": "replace", "path": "/clips/0/text", "value": "수정된 텍스트"}},
        {{"op": "add", "path": "/clips/1/style/color", "value": "#FF0000"}}
    ],
    "summary": "수정 내용 요약"
}}"""

                edit_result = self.invoke_claude_with_chain(
                    prompt=edit_prompt,
                    max_tokens=max_tokens,
                    temperature=0.1,
                )

                return {
                    "chain_type": "subtitle_animation",
                    "classification": "simple_edit",
                    "steps": {
                        "classification": step1_result,
                        "edit_result": edit_result,
                    },
                    "final_response": edit_result["completion"],
                    "json_patch": edit_result["completion"],
                    "langchain_used": True,
                }

            else:  # animation_request
                logger.info(
                    "🎬 Processing as ANIMATION_REQUEST - extracting animation category and generating effects"
                )
                # 단계 3: 애니메이션 카테고리 추출 (실제 manifest 기반)
                category_prompt = f"""사용자가 원하는 애니메이션 효과의 카테고리를 추출해주세요:

사용자 메시지: "{user_message}"

사용 가능한 애니메이션 카테고리 (실제 manifest 기반):

1. **rotation@2.0.0** - 3D 회전 효과
   - 파라미터: rotationDegrees(90-720°), animationDuration(0.5-3s), axisX/Y/Z(boolean), perspective(200-1500px), staggerDelay(0-0.3s)

2. **fadein@2.0.0** - 페이드 인 효과
   - 파라미터: staggerDelay(0.02-0.5s), animationDuration(0.2-2s), startOpacity(0-0.5), scaleStart(0.5-1), ease(power1-3.out/back.out/elastic.out)

3. **typewriter@2.0.0** - 타이핑 효과
   - 파라미터: typingSpeed(0.02-0.2s), cursorBlink(boolean), cursorChar(string), showCursor(boolean), soundEffect(boolean)

4. **glow@2.0.0** - 글로우 효과
   - 파라미터: color(#hex), intensity(0-1), pulse(boolean), cycles(1-120)

5. **scalepop@2.0.0** - 스케일 팝 효과
   - 파라미터: popScale(1.1-3), animationDuration(0.5-2.5s), staggerDelay(0-0.3s), bounceStrength(0.1-2), colorPop(boolean)

6. **slideup@2.0.0** - 슬라이드 업 효과
   - 파라미터: slideDistance(10-100px), animationDuration(0.3-2s), staggerDelay(0-0.5s), easeType(power2.out/back.out/elastic.out/bounce.out), blurEffect(boolean)

7. **elastic@2.0.0** - 탄성 효과
   - 파라미터: bounceStrength(0.1-2), animationDuration(0.5-4s), staggerDelay(0-0.5s), startScale(0-1), overshoot(1-2)

8. **glitch@2.0.0** - 글리치 효과
   - 파라미터: glitchIntensity(1-20px), animationDuration(0.5-5s), glitchFrequency(0.1-1s), colorSeparation(boolean), noiseEffect(boolean)

9. **flames@2.0.0** - 불꽃 효과 (GIF 기반)
   - 파라미터: baseOpacity(0-1), flicker(0-1), cycles(1-120)

10. **pulse@2.0.0** - 펄스 효과
    - 파라미터: maxScale(1-2.5), cycles(0-10)

만약 카테고리가 명확하지 않다면 사용자에게 구체적인 예시를 제공하세요.

응답 형식:
{{
    "category": "추출된 카테고리명",
    "confidence": 0.85,
    "suggested_parameters": {{
        "animationDuration": 1.5,
        "staggerDelay": 0.1
    }},
    "clarification_needed": false,
    "user_intent": "사용자 의도 분석"
}}"""

                step3_result = self.invoke_claude_with_chain(
                    prompt=category_prompt,
                    max_tokens=300,
                    temperature=0.2,
                )

                # 단계 4: 애니메이션 JSON 생성 (manifest 스키마 기반)
                animation_prompt = f"""추출된 카테고리를 바탕으로 실제 manifest 스키마에 맞는 애니메이션 JSON을 생성해주세요:

카테고리 분석 결과: {step3_result["completion"]}
사용자 원본 요청: {user_message}

실제 manifest 스키마에 따라 JSON patch를 생성하세요:

예시 구조:
- **rotation@2.0.0**: {{"rotationDegrees": 360, "animationDuration": 1.5, "axisY": true, "perspective": 800, "staggerDelay": 0.1}}
- **fadein@2.0.0**: {{"staggerDelay": 0.1, "animationDuration": 0.8, "startOpacity": 0, "scaleStart": 0.9, "ease": "power2.out"}}
- **typewriter@2.0.0**: {{"typingSpeed": 0.05, "cursorBlink": true, "cursorChar": "|", "showCursor": true}}
- **glow@2.0.0**: {{"color": "#00ffff", "intensity": 0.4, "pulse": true, "cycles": 8}}
- **scalepop@2.0.0**: {{"popScale": 1.5, "animationDuration": 1.2, "staggerDelay": 0.08, "bounceStrength": 0.6, "colorPop": true}}
- **slideup@2.0.0**: {{"slideDistance": 30, "animationDuration": 1, "staggerDelay": 0.12, "easeType": "power2.out", "blurEffect": true}}
- **elastic@2.0.0**: {{"bounceStrength": 0.7, "animationDuration": 1.5, "staggerDelay": 0.1, "startScale": 0, "overshoot": 1.3}}
- **glitch@2.0.0**: {{"glitchIntensity": 5, "animationDuration": 2, "glitchFrequency": 0.3, "colorSeparation": true, "noiseEffect": true}}
- **flames@2.0.0**: {{"baseOpacity": 0.8, "flicker": 0.3, "cycles": 12}}
- **pulse@2.0.0**: {{"maxScale": 1.2, "cycles": 1}}

응답 형식 (JSON patch):
{{
    "patches": [
        {{
            "op": "add",
            "path": "/clips/0/animation",
            "value": {{
                "plugin": "카테고리명@2.0.0",
                "manifest": {{
                    "name": "카테고리명",
                    "version": "2.0.0"
                }},
                "parameters": {{
                    "실제스키마파라미터들": "적절한값"
                }}
            }}
        }}
    ],
    "animation_summary": "적용된 애니메이션의 상세 설명",
    "manifest_used": {{
        "plugin": "카테고리명@2.0.0",
        "parameters_count": 5,
        "schema_validated": true
    }}
}}"""

                final_result = self.invoke_claude_with_chain(
                    prompt=animation_prompt,
                    max_tokens=max_tokens,
                    temperature=0.3,
                )

                return {
                    "chain_type": "subtitle_animation",
                    "classification": "animation_request",
                    "steps": {
                        "classification": step1_result,
                        "category_extraction": step3_result,
                        "animation_generation": final_result,
                    },
                    "final_response": final_result["completion"],
                    "json_patch": final_result["completion"],
                    "langchain_used": True,
                }

        except Exception as e:
            logger.error(f"Subtitle animation chain failed: {e}")
            raise Exception(f"자막 애니메이션 체인 실행 실패: {str(e)}")

    def create_direct_subtitle_edit_chain(
        self,
        user_message: str,
        scenario_data: Dict[str, Any],
        max_tokens: int = 1500,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        사용자 요청에 따라 시나리오 데이터를 직접 수정하는 체인

        Args:
            user_message: 사용자 편집 요청
            scenario_data: 현재 시나리오 JSON 데이터
            max_tokens: 최대 토큰 수
            temperature: 창의성 조절 (정확성을 위해 낮게 설정)

        Returns:
            Dict: JSON patch와 편집 결과
        """
        try:
            logger.info("Starting direct subtitle edit chain")

            # 1단계: 요청 유형 분류
            classification_prompt = f"""사용자의 자막 편집 요청을 분석해주세요:

사용자 요청: "{user_message}"

분류 기준:
- "text_edit": 자막 텍스트 수정 (오탈자, 단어 변경)
- "style_edit": 자막 스타일 수정 (색상, 크기, 위치)
- "animation_request": 애니메이션 효과 추가/수정
- "info_request": 단순 정보 질문

JSON 형태로 응답:
{{"classification": "분류결과", "confidence": 0.95}}"""

            classification_result = self.invoke_claude_with_chain(
                prompt=classification_prompt,
                max_tokens=200,
                temperature=0.1,
            )

            logger.info(
                f"🔍 [DIRECT EDIT] Raw AI classification response: {classification_result['completion']}"
            )

            # 분류 결과 파싱
            try:
                import json

                classification_data = json.loads(classification_result["completion"])
                classification = classification_data.get("classification", "text_edit")
                confidence = classification_data.get("confidence", "unknown")

                logger.info(
                    f"✅ [DIRECT EDIT] JSON parsing successful - Classification: {classification}, Confidence: {confidence}"
                )

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(
                    f"❌ [DIRECT EDIT] JSON parsing failed ({type(e).__name__}: {e}), using fallback classification"
                )
                classification = "text_edit"  # 기본값

            logger.info(
                f"🏷️ [DIRECT EDIT] FINAL CLASSIFICATION: '{classification}' for user message: '{user_message}'"
            )

            # 2단계: 분류에 따른 편집 실행
            logger.info(f"🔄 [DIRECT EDIT] Dispatching to handler for: {classification}")

            if classification == "text_edit":
                logger.info("📝 [DIRECT EDIT] Calling text edit handler")
                return self._handle_text_edit(
                    user_message, scenario_data, max_tokens, temperature
                )
            elif classification == "style_edit":
                logger.info("🎨 [DIRECT EDIT] Calling style edit handler")
                return self._handle_style_edit(
                    user_message, scenario_data, max_tokens, temperature
                )
            elif classification == "animation_request":
                logger.info("🎬 [DIRECT EDIT] Calling animation request handler")
                return self._handle_animation_request(
                    user_message, scenario_data, max_tokens, temperature
                )
            else:
                logger.info("📚 [DIRECT EDIT] Calling info request handler")
                return self._handle_info_request(user_message, max_tokens, temperature)

        except Exception as e:
            logger.error(f"Direct subtitle edit chain failed: {e}")
            return {
                "type": "error",
                "error": f"편집 처리 중 오류가 발생했습니다: {str(e)}",
                "success": False,
                "langchain_used": True,
            }

    def _handle_text_edit(
        self,
        user_message: str,
        scenario_data: Dict[str, Any],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """텍스트 수정 처리"""
        try:
            import json

            scenario_json = json.dumps(scenario_data, indent=2, ensure_ascii=False)

            edit_prompt = f"""<user_instruction>{user_message}</user_instruction>

<current_json>
{scenario_json}
</current_json>

위의 MotionText v2.0 JSON에서 텍스트를 수정하세요. RFC6902 JSON Patch 표준을 준수하여 출력하세요."""

            result = self.invoke_claude_with_chain(
                prompt=edit_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # MotionTextEditor 응답 파싱 시도
            motion_result = self._parse_motion_text_editor_response(
                result["completion"]
            )
            if motion_result["success"]:
                return motion_result

            # 파싱 실패시 기존 JSON 형식으로 fallback
            try:
                import json

                edit_result = json.loads(result["completion"])
                edit_result["langchain_used"] = True
                return edit_result
            except json.JSONDecodeError:
                return {
                    "type": "text_edit",
                    "success": False,
                    "error": "JSON 파싱 실패",
                    "langchain_used": True,
                }

        except Exception as e:
            logger.error(f"Text edit handling failed: {e}")
            return {
                "type": "text_edit",
                "error": f"텍스트 수정 실패: {str(e)}",
                "success": False,
                "langchain_used": True,
            }

    def _handle_style_edit(
        self,
        user_message: str,
        scenario_data: Dict[str, Any],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """스타일 수정 처리"""
        try:
            import json

            scenario_json = json.dumps(scenario_data, indent=2, ensure_ascii=False)

            style_prompt = f"""<user_instruction>{user_message}</user_instruction>

<current_json>
{scenario_json}
</current_json>

위의 MotionText v2.0 JSON에서 스타일을 수정하세요. RFC6902 JSON Patch 표준을 준수하여 출력하세요."""

            result = self.invoke_claude_with_chain(
                prompt=style_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # MotionTextEditor 응답 파싱 시도
            motion_result = self._parse_motion_text_editor_response(
                result["completion"]
            )
            if motion_result["success"]:
                return motion_result

            # 파싱 실패시 기존 JSON 형식으로 fallback
            try:
                import json

                edit_result = json.loads(result["completion"])
                edit_result["langchain_used"] = True
                return edit_result
            except json.JSONDecodeError:
                return {
                    "type": "style_edit",
                    "success": False,
                    "error": "JSON 파싱 실패",
                    "langchain_used": True,
                }

        except Exception as e:
            logger.error(f"Style edit handling failed: {e}")
            return {
                "type": "style_edit",
                "error": f"스타일 수정 실패: {str(e)}",
                "success": False,
                "langchain_used": True,
            }

    def _handle_animation_request(
        self,
        user_message: str,
        scenario_data: Dict[str, Any],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        """애니메이션 요청 처리"""
        try:
            import json

            scenario_json = json.dumps(scenario_data, indent=2, ensure_ascii=False)

            animation_prompt = f"""<user_instruction>{user_message}</user_instruction>

<current_json>
{scenario_json}
</current_json>

위의 MotionText v2.0 JSON에 애니메이션 효과를 추가하세요. RFC6902 JSON Patch 표준을 준수하여 출력하세요.

사용 가능한 애니메이션:
- **bobY@2.0.0**: 수직 바운싱 움직임 (amplitudePx, cycles)
- **cwi-bouncing@2.0.0**: 바운싱 웨이브 (speaker, palette, color, waveHeight)
- **cwi-color@2.0.0**: 색상 전환 효과 (speaker, palette, color, bulk)
- **cwi-loud@2.0.0**: 화난 느낌/큰 소리 애니메이션 - 강렬한 감정 표현에 최적 (speaker, palette, color, pulse.scale, pulse.lift, tremble.ampPx, tremble.freq, timeOffset: [0,0])
- **cwi-whisper@2.0.0**: 속삭임 애니메이션 (speaker, palette, color, shrink.scale, shrink.drop, flutter.amp, flutter.freq)
- **elastic@2.0.0**: 탄성 바운스 효과 (bounceStrength, animationDuration, staggerDelay, startScale, overshoot)
- **fadein@2.0.0**: 페이드인 애니메이션 (staggerDelay, animationDuration, startOpacity, scaleStart, ease)
- **flames@2.0.0**: 불꽃 효과 (baseOpacity, flicker, cycles)
- **fliptype@2.0.0**: 플립 타이핑 애니메이션 (typingSpeed, flipDuration, flipAngle, flipDirection, typingDelay)
- **glitch@2.0.0**: 글리치 효과 (glitchIntensity, animationDuration, glitchFrequency, colorSeparation, noiseEffect)
- **glow@2.0.0**: 글로우 효과 (color, intensity, pulse, cycles)
- **magnetic@2.0.0**: 자기 끌림 효과 (magnetStrength, animationDuration, attractionDelay, elasticity)
- **pulse@2.0.0**: 펄스 애니메이션 (maxScale, cycles)
- **rotation@2.0.0**: 3D 회전 효과 (rotationDegrees, animationDuration, staggerDelay, perspective, axisX, axisY, axisZ)
- **scalepop@2.0.0**: 스케일 팝 효과 (popScale, animationDuration, staggerDelay, bounceStrength, colorPop)
- **slideup@2.0.0**: 슬라이드업 애니메이션 (slideDistance, animationDuration, staggerDelay, easeType, blurEffect)
- **spin@2.0.0**: 스핀 애니메이션 (fullTurns)
- **typewriter@2.0.0**: 타이프라이터 효과 (typingSpeed, cursorBlink, cursorChar, showCursor, soundEffect)"""

            result = self.invoke_claude_with_chain(
                prompt=animation_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # MotionTextEditor 응답 파싱 시도
            motion_result = self._parse_motion_text_editor_response(
                result["completion"]
            )
            if motion_result["success"]:
                return motion_result

            # 파싱 실패시 기존 JSON 형식으로 fallback
            try:
                import json

                edit_result = json.loads(result["completion"])
                edit_result["langchain_used"] = True
                return edit_result
            except json.JSONDecodeError:
                return {
                    "type": "animation_request",
                    "success": False,
                    "error": "JSON 파싱 실패",
                    "langchain_used": True,
                }

        except Exception as e:
            logger.error(f"Animation request handling failed: {e}")
            return {
                "type": "animation_request",
                "error": f"애니메이션 처리 실패: {str(e)}",
                "success": False,
                "langchain_used": True,
            }

    def _handle_info_request(
        self, user_message: str, max_tokens: int, temperature: float
    ) -> Dict[str, Any]:
        """정보 요청 처리"""
        try:
            info_prompt = f"""ECG 자막 편집 도구에 대한 질문에 답변해주세요.

질문: "{user_message}"

ECG 주요 기능:
- 자동 자막 생성 및 편집
- 다양한 애니메이션 효과
- 실시간 미리보기
- GPU 가속 렌더링

친근하고 도움이 되는 톤으로 답변해주세요."""

            result = self.invoke_claude_with_chain(
                prompt=info_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return {
                "type": "info_request",
                "success": True,
                "response": result["completion"],
                "langchain_used": True,
            }

        except Exception as e:
            logger.error(f"Info request handling failed: {e}")
            return {
                "type": "info_request",
                "error": f"정보 요청 처리 실패: {str(e)}",
                "success": False,
                "langchain_used": True,
            }

    def _generate_demo_response(
        self, scenario_data: Optional[Dict[str, Any]], prompt: str
    ) -> Dict[str, Any]:
        """데모 프롬프트('!!'로 끝나는 경우) 처리 - 기존 plugin chain을 비우고 Claude가 채우도록 함"""
        try:
            logger.info(
                "🎭 Demo mode: Clearing existing plugin chains and letting Claude fill them"
            )

            if not scenario_data or "cues" not in scenario_data:
                logger.warning("⚠️  No scenario data available for demo")
                # MotionTextEditor 표준 형식으로 에러 응답
                error_response = """<summary>데모 모드 실행 실패, 시나리오 데이터 없음</summary>
<json_patch_chunk index="1" total="1" ops="0">
<![CDATA[
[]
]]>
</json_patch_chunk>
<apply_order>1</apply_order>"""
                return {
                    "completion": error_response,
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": len(prompt.split()), "output_tokens": 20},
                    "model_id": self.llm.model_id,
                    "langchain_used": True,
                    "edit_result": {
                        "type": "motion_text_edit",
                        "success": False,
                        "error": "No scenario data",
                    },
                    "json_patches": [],
                    "has_scenario_edits": False,
                }

            # Step 1: 기존 plugin chain 제거를 위한 patches 생성
            import json
            import copy

            cleaned_scenario = copy.deepcopy(scenario_data)
            clear_patches = []

            logger.info("🧹 Clearing existing plugin chains from scenario data")

            # 모든 cue와 children에서 pluginChain 제거
            for cue_index, cue in enumerate(cleaned_scenario.get("cues", [])):
                if "root" in cue:
                    root = cue["root"]

                    # root의 pluginChain 제거
                    if "pluginChain" in root:
                        clear_patches.append(
                            {
                                "op": "remove",
                                "path": f"/cues/{cue_index}/root/pluginChain",
                            }
                        )
                        del root["pluginChain"]

                    # children의 pluginChain 제거
                    if "children" in root and isinstance(root["children"], list):
                        for child_index, child in enumerate(root["children"]):
                            if isinstance(child, dict) and "pluginChain" in child:
                                clear_patches.append(
                                    {
                                        "op": "remove",
                                        "path": f"/cues/{cue_index}/root/children/{child_index}/pluginChain",
                                    }
                                )
                                del child["pluginChain"]

            logger.info(
                f"🧹 Generated {len(clear_patches)} clear patches for existing plugin chains"
            )

            # Step 2: Claude에게 plugin 추가 요청
            cleaned_scenario_json = json.dumps(
                cleaned_scenario, indent=2, ensure_ascii=False
            )

            demo_prompt = f"""<user_instruction>데모 모드: 모든 단어와 텍스트에 화난 감정을 표현하는 강렬한 애니메이션 효과를 추가해주세요. cwi-loud@2.0.0 애니메이션과 붉은 색상 계열의 glow 효과를 적용하여 역동적이고 눈에 띄는 효과를 만들어주세요.</user_instruction>

<current_json>
{cleaned_scenario_json}
</current_json>

위의 MotionText v2.0 JSON에 강렬한 애니메이션 효과를 추가하세요. RFC6902 JSON Patch 표준을 준수하여 출력하세요."""

            logger.info("🤖 Requesting Claude to add plugin chains for demo mode")

            result = self.invoke_claude_with_chain(
                prompt=demo_prompt,
                max_tokens=2000,
                temperature=0.3,
            )

            # Claude 응답 파싱
            motion_result = self._parse_motion_text_editor_response(
                result["completion"]
            )

            if motion_result["success"] and "patches" in motion_result:
                # plugin 형식 변환 적용
                transformed_claude_patches = self._transform_json_patches(
                    motion_result["patches"]
                )

                # 기존 clear_patches와 변환된 Claude patches 합치기
                all_patches = clear_patches + transformed_claude_patches

                logger.info(
                    f"✅ Demo completed: {len(clear_patches)} clear + {len(transformed_claude_patches)} Claude patches (transformed)"
                )

                return {
                    "completion": result["completion"],
                    "stop_reason": result["stop_reason"],
                    "usage": result.get(
                        "usage",
                        {
                            "input_tokens": len(demo_prompt.split()),
                            "output_tokens": 100,
                        },
                    ),
                    "model_id": result.get("model_id", self.llm.model_id),
                    "langchain_used": True,
                    "json_patches": all_patches,
                    "has_scenario_edits": True,
                    "demo_mode": True,
                }
            else:
                logger.warning("⚠️ Claude failed to generate demo patches")
                return {
                    "completion": "데모 모드 실행 중 오류가 발생했습니다.",
                    "stop_reason": "end_turn",
                    "usage": {
                        "input_tokens": len(demo_prompt.split()),
                        "output_tokens": 20,
                    },
                    "model_id": self.llm.model_id,
                    "langchain_used": True,
                    "json_patches": clear_patches,  # 최소한 기존 것은 제거
                    "has_scenario_edits": True,
                    "demo_mode": True,
                }

        except Exception as e:
            logger.error(f"❌ Demo response generation failed: {e}")
            import traceback

            logger.error(f"❌ Full traceback: {traceback.format_exc()}")

            # MotionTextEditor 표준 형식으로 에러 응답
            error_response = """<summary>데모 모드 실행 중 오류 발생</summary>
<json_patch_chunk index="1" total="1" ops="0">
<![CDATA[
[]
]]>
</json_patch_chunk>
<apply_order>1</apply_order>"""

            return {
                "completion": error_response,
                "stop_reason": "end_turn",
                "usage": {"input_tokens": len(prompt.split()), "output_tokens": 20},
                "model_id": self.llm.model_id,
                "langchain_used": True,
                "edit_result": {
                    "type": "motion_text_edit",
                    "success": False,
                    "error": str(e),
                },
                "json_patches": [],
                "has_scenario_edits": False,
                "demo_mode": True,
            }

    def _parse_motion_text_editor_response(self, response_text: str) -> Dict[str, Any]:
        """MotionTextEditor 표준 응답 파싱 (CDATA 형식 또는 일반 텍스트 지원)"""
        try:
            import re
            import json

            logger.info("🔍 Parsing MotionTextEditor response format")

            # summary 추출
            summary_match = re.search(
                r"<summary>(.*?)</summary>", response_text, re.DOTALL
            )
            summary = summary_match.group(1).strip() if summary_match else ""

            # json_patch_chunk 추출
            chunk_pattern = r"<json_patch_chunk[^>]*>(.*?)</json_patch_chunk>"
            chunks = re.findall(chunk_pattern, response_text, re.DOTALL)

            # apply_order 추출
            order_match = re.search(
                r"<apply_order>(.*?)</apply_order>", response_text, re.DOTALL
            )
            apply_order = order_match.group(1).strip() if order_match else "1"

            all_patches = []

            for chunk_content in chunks:
                patch_json = ""

                # 1. CDATA 형식 시도
                cdata_match = re.search(
                    r"<!\[CDATA\[(.*?)\]\]>", chunk_content, re.DOTALL
                )
                if cdata_match:
                    patch_json = cdata_match.group(1).strip()
                    logger.debug("Found CDATA format JSON patch")
                else:
                    # 2. 일반 텍스트 형식 시도
                    patch_json = chunk_content.strip()
                    logger.debug("Using plain text format JSON patch")

                if patch_json:
                    try:
                        patches = json.loads(patch_json)
                        if isinstance(patches, list):
                            all_patches.extend(patches)
                        else:
                            all_patches.append(patches)
                        logger.debug(
                            f"Successfully parsed {len(patches) if isinstance(patches, list) else 1} patch(es)"
                        )
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON parsing failed for chunk: {e}")
                        logger.debug(f"Failed JSON content: {patch_json[:200]}...")

            logger.info(
                f"✅ Parsed {len(all_patches)} patches from MotionTextEditor response"
            )

            # plugin 형식 변환 적용
            transformed_patches = self._transform_json_patches(all_patches)

            return {
                "type": "motion_text_edit",
                "summary": summary or "MotionTextEditor 표준 응답 처리 완료",
                "apply_order": apply_order,
                "success": len(transformed_patches) > 0,
                "langchain_used": True,
                "patches": transformed_patches,  # 변환된 형식으로 전달
            }

        except Exception as e:
            logger.error(f"MotionTextEditor response parsing failed: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")

            # 파싱 실패시 기존 JSON 형식으로 fallback 시도
            try:
                legacy_result = json.loads(response_text)
                if isinstance(legacy_result, dict) and "patches" in legacy_result:
                    return {
                        **legacy_result,
                        "langchain_used": True,
                        "fallback_parsing": True,
                    }
            except Exception as fallback_error:
                logger.debug(f"Legacy JSON parsing also failed: {fallback_error}")

            return {
                "type": "motion_text_edit",
                "summary": "",
                "success": False,
                "error": f"응답 파싱 실패: {str(e)}",
                "langchain_used": True,
            }

    def _transform_plugin_format(self, plugin_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Claude가 생성한 plugin 정보를 프론트엔드 형식으로 변환

        From: {"pluginId": "cwi-loud@2.0.0", "timeOffset": [0, 0], "params": {...}}
        To: {"name": "cwi-loud", "params": {...}, "timeOffset": [...]}
        """
        try:
            # pluginId에서 name 추출 (버전 제거)
            plugin_id = plugin_data.get("pluginId", "")
            name = plugin_id.split("@")[0] if "@" in plugin_id else plugin_id

            # 새로운 형식으로 변환
            transformed = {
                "name": name,
                "params": plugin_data.get("params", {}),
                "timeOffset": plugin_data.get("timeOffset", [0, 0]),
            }

            logger.debug(f"🔄 Transformed plugin: {plugin_id} -> {name}")
            return transformed

        except Exception as e:
            logger.warning(f"⚠️ Plugin transformation failed: {e}")
            # fallback: 원본 데이터 반환
            return plugin_data

    def _transform_json_patches(
        self, patches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        JSON patches에서 plugin 관련 데이터를 새로운 형식으로 변환
        """
        try:
            transformed_patches = []

            for patch in patches:
                transformed_patch = patch.copy()

                # pluginChain 관련 patch인지 확인
                if (
                    patch.get("op") == "add"
                    and "pluginChain" in patch.get("path", "")
                    and "value" in patch
                ):
                    value = patch["value"]

                    # 단일 plugin 객체인 경우
                    if isinstance(value, dict) and "pluginId" in value:
                        transformed_patch["value"] = self._transform_plugin_format(
                            value
                        )

                    # plugin 배열인 경우
                    elif isinstance(value, list):
                        transformed_value = []
                        for item in value:
                            if isinstance(item, dict) and "pluginId" in item:
                                transformed_value.append(
                                    self._transform_plugin_format(item)
                                )
                            else:
                                transformed_value.append(item)
                        transformed_patch["value"] = transformed_value

                transformed_patches.append(transformed_patch)

            logger.info(
                f"🔄 Transformed {len(patches)} patches with plugin format conversion"
            )
            return transformed_patches

        except Exception as e:
            logger.error(f"❌ JSON patch transformation failed: {e}")
            return patches  # fallback: 원본 반환

    def _estimate_token_count(self, text: str) -> int:
        """토큰 수 추정 (대략적 계산)"""
        # 간단한 토큰 수 추정: 단어 수 * 1.3 (한국어/영어 혼재 고려)
        return int(len(text.split()) * 1.3)

    def _should_chunk_response(self, response_text: str) -> bool:
        """응답이 청킹이 필요한지 확인 (1800토큰 기준)"""
        estimated_tokens = self._estimate_token_count(response_text)
        return estimated_tokens > 1800

    def _validate_motion_text_schema(
        self, scenario_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """MotionText v2.0 스키마 요구사항 검증"""
        validation_result = {"valid": True, "errors": [], "warnings": []}

        try:
            # 1. version 확인
            if not scenario_data.get("version"):
                validation_result["errors"].append("Missing version field")
            elif scenario_data.get("version") != "2.0":
                validation_result["warnings"].append(
                    f"Version {scenario_data.get('version')} != 2.0"
                )

            # 2. timebase 확인
            timebase = scenario_data.get("timebase")
            if not timebase:
                validation_result["errors"].append("Missing timebase field")
            else:
                if not timebase.get("unit") == "seconds":
                    validation_result["errors"].append(
                        "timebase.unit must be 'seconds'"
                    )
                if not isinstance(timebase.get("fps"), (int, float)):
                    validation_result["errors"].append("timebase.fps must be a number")

            # 3. cues 구조 확인
            cues = scenario_data.get("cues", [])
            if not isinstance(cues, list):
                validation_result["errors"].append("cues must be an array")
            else:
                for i, cue in enumerate(cues):
                    # displayTime 확인
                    display_time = cue.get("displayTime")
                    if not isinstance(display_time, list) or len(display_time) != 2:
                        validation_result["errors"].append(
                            f"cues[{i}].displayTime must be [start, end] array"
                        )

                    # eType 확인 (root 노드)
                    root = cue.get("root", {})
                    if root.get("eType") not in ["group", "text", "image", "video"]:
                        validation_result["errors"].append(
                            f"cues[{i}].root.eType must be one of: group, text, image, video"
                        )

                    # node_id 확인
                    if not root.get("id"):
                        validation_result["warnings"].append(
                            f"cues[{i}].root missing id field"
                        )

            validation_result["valid"] = len(validation_result["errors"]) == 0

            if validation_result["valid"]:
                logger.info("✅ MotionText v2.0 schema validation passed")
            else:
                logger.warning(
                    f"⚠️ Schema validation failed: {validation_result['errors']}"
                )

        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Schema validation error: {str(e)}")
            logger.error(f"Schema validation exception: {e}")

        return validation_result


# 전역 인스턴스 (싱글톤 패턴)
langchain_bedrock_service = LangChainBedrockService()
