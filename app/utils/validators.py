"""
렌더링 API 입력 검증 유틸리티
"""

import json
import re
from typing import Dict, Any
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def validate_video_url(url: str) -> Dict[str, Any]:
    """
    비디오 URL 유효성 검사

    Args:
        url: 검증할 비디오 URL

    Returns:
        dict: {"valid": bool, "reason": str}
    """
    try:
        # 기본 URL 형식 검증
        parsed = urlparse(url)

        # 호스트명 필수
        if not parsed.netloc:
            return {"valid": False, "reason": "Invalid URL format"}

        # 로컬호스트인지 확인
        is_localhost = parsed.netloc.startswith(
            "localhost"
        ) or parsed.netloc.startswith("127.0.0.1")

        # 프로토콜 검증 (로컬호스트는 HTTP 허용, 그 외는 HTTPS 필수)
        if not is_localhost and parsed.scheme != "https":
            return {
                "valid": False,
                "reason": "Only HTTPS URLs are allowed (except for localhost)",
            }

        # 허용된 도메인 체크 (화이트리스트)
        allowed_domains = [
            "s3.amazonaws.com",
            "s3.ap-northeast-2.amazonaws.com",
            "s3.us-east-1.amazonaws.com",
            "storage.googleapis.com",
            "storage.cloud.google.com",
            "d1234567890.cloudfront.net",  # CloudFront 패턴 예시
            "localhost",  # 로컬 테스트용
            "127.0.0.1",  # 로컬 테스트용
        ]

        # 도메인 매칭 (서브도메인 포함)
        domain_allowed = False

        # 로컬호스트인 경우 포트 번호 무시하고 검증
        if is_localhost:
            domain_allowed = True
        else:
            for allowed_domain in allowed_domains:
                if parsed.netloc.endswith(allowed_domain):
                    domain_allowed = True
                    break

        if not domain_allowed:
            return {
                "valid": False,
                "reason": f"Domain '{parsed.netloc}' is not allowed. Allowed domains: {', '.join(allowed_domains)}",
            }

        # 파일 확장자 체크
        path = parsed.path.lower()
        allowed_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm"]

        if not any(path.endswith(ext) for ext in allowed_extensions):
            return {
                "valid": False,
                "reason": f"File extension not allowed. Allowed extensions: {', '.join(allowed_extensions)}",
            }

        return {"valid": True, "reason": "Valid video URL"}

    except Exception as e:
        logger.error(f"URL 검증 중 오류: {str(e)}")
        return {"valid": False, "reason": f"URL validation error: {str(e)}"}


def validate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    MotionText 시나리오 유효성 검사

    Args:
        scenario: MotionText 시나리오 객체

    Returns:
        dict: {"valid": bool, "reason": str}
    """
    try:
        # 필수 필드 체크
        required_fields = ["version", "cues"]
        for field in required_fields:
            if field not in scenario:
                return {"valid": False, "reason": f"Missing required field: {field}"}

        # 버전 체크
        version = scenario.get("version")
        if not isinstance(version, str) or not re.match(r"^\d+\.\d+$", version):
            return {"valid": False, "reason": "Invalid version format. Expected: 'X.Y'"}

        # Cues 체크
        cues = scenario.get("cues", [])
        if not isinstance(cues, list):
            return {"valid": False, "reason": "cues must be an array"}

        # Cue 개수 제한
        max_cues = 1000
        if len(cues) > max_cues:
            return {
                "valid": False,
                "reason": f"Too many cues. Maximum allowed: {max_cues}, provided: {len(cues)}",
            }

        # 각 Cue 검증
        for i, cue in enumerate(cues):
            if not isinstance(cue, dict):
                return {"valid": False, "reason": f"Cue {i} must be an object"}

            # 필수 필드
            if "id" not in cue:
                return {"valid": False, "reason": f"Cue {i} missing required field: id"}

            # hintTime 검증
            if "hintTime" in cue:
                hint_time = cue["hintTime"]
                if not isinstance(hint_time, dict):
                    return {
                        "valid": False,
                        "reason": f"Cue {i} hintTime must be an object",
                    }

                if "start" in hint_time and "end" in hint_time:
                    start = hint_time["start"]
                    end = hint_time["end"]

                    if not isinstance(start, (int, float)) or not isinstance(
                        end, (int, float)
                    ):
                        return {
                            "valid": False,
                            "reason": f"Cue {i} hintTime start/end must be numbers",
                        }

                    if start < 0 or end < 0:
                        return {
                            "valid": False,
                            "reason": f"Cue {i} hintTime cannot be negative",
                        }

                    if start >= end:
                        return {
                            "valid": False,
                            "reason": f"Cue {i} hintTime start must be less than end",
                        }

        # JSON 직렬화 크기 체크
        try:
            scenario_json = json.dumps(scenario)
            max_size = 5 * 1024 * 1024  # 5MB

            if len(scenario_json.encode("utf-8")) > max_size:
                return {
                    "valid": False,
                    "reason": f"Scenario too large. Maximum size: {max_size // (1024*1024)}MB",
                }
        except Exception:
            return {"valid": False, "reason": "Scenario cannot be serialized to JSON"}

        return {"valid": True, "reason": "Valid scenario"}

    except Exception as e:
        logger.error(f"시나리오 검증 중 오류: {str(e)}")
        return {"valid": False, "reason": f"Scenario validation error: {str(e)}"}


def validate_render_options(options: Dict[str, Any]) -> Dict[str, Any]:
    """
    렌더링 옵션 유효성 검사

    Args:
        options: 렌더링 옵션 객체

    Returns:
        dict: {"valid": bool, "reason": str}
    """
    try:
        # 해상도 제한
        width = options.get("width", 1920)
        height = options.get("height", 1080)

        # 최대 해상도 제한 (4K)
        max_width = 3840
        max_height = 2160

        if width > max_width or height > max_height:
            return {
                "valid": False,
                "reason": f"Resolution too high. Maximum: {max_width}x{max_height}, provided: {width}x{height}",
            }

        # 최소 해상도
        min_width = 480
        min_height = 360

        if width < min_width or height < min_height:
            return {
                "valid": False,
                "reason": f"Resolution too low. Minimum: {min_width}x{min_height}, provided: {width}x{height}",
            }

        # FPS 제한
        fps = options.get("fps", 30)
        if not isinstance(fps, int) or fps < 1 or fps > 60:
            return {"valid": False, "reason": "FPS must be between 1 and 60"}

        # 품질 제한
        quality = options.get("quality", 90)
        if not isinstance(quality, int) or quality < 10 or quality > 100:
            return {"valid": False, "reason": "Quality must be between 10 and 100"}

        # 포맷 체크
        format_type = options.get("format", "mp4")
        allowed_formats = ["mp4", "mov", "webm"]

        if format_type not in allowed_formats:
            return {
                "valid": False,
                "reason": f"Format '{format_type}' not allowed. Allowed formats: {', '.join(allowed_formats)}",
            }

        return {"valid": True, "reason": "Valid render options"}

    except Exception as e:
        logger.error(f"렌더링 옵션 검증 중 오류: {str(e)}")
        return {"valid": False, "reason": f"Options validation error: {str(e)}"}


def validate_render_request(
    video_url: str, scenario: Dict[str, Any], options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    전체 렌더링 요청 검증

    Args:
        video_url: 비디오 URL
        scenario: MotionText 시나리오
        options: 렌더링 옵션

    Returns:
        dict: {"valid": bool, "reason": str, "details": List[str]}
    """
    errors = []

    # 비디오 URL 검증
    url_result = validate_video_url(video_url)
    if not url_result["valid"]:
        errors.append(f"Video URL: {url_result['reason']}")

    # 시나리오 검증
    scenario_result = validate_scenario(scenario)
    if not scenario_result["valid"]:
        errors.append(f"Scenario: {scenario_result['reason']}")

    # 옵션 검증 (옵션이 있는 경우)
    if options:
        options_result = validate_render_options(options)
        if not options_result["valid"]:
            errors.append(f"Options: {options_result['reason']}")

    if errors:
        return {"valid": False, "reason": "Validation failed", "details": errors}

    return {"valid": True, "reason": "All validations passed", "details": []}
