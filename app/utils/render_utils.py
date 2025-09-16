"""
GPU 렌더링 관련 유틸리티 함수들
"""

import re
from urllib.parse import urlparse


def extract_video_name(video_url: str) -> str:
    """비디오 URL에서 파일명 추출"""
    try:
        parsed_url = urlparse(video_url)
        filename = parsed_url.path.split("/")[-1]

        # 확장자 제거
        if "." in filename:
            name = filename.rsplit(".", 1)[0]
        else:
            name = filename

        # URL 디코딩 및 특수문자 정리
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"\s+", " ", name).strip()

        return name if name else "Untitled"
    except Exception:
        return "Untitled"


def calculate_estimated_time(scenario: dict) -> int:
    """시나리오 기반 예상 처리 시간 계산 (초 단위)"""
    try:
        base_time = 30  # 기본 30초

        if "cues" not in scenario:
            return base_time

        cues = scenario["cues"]
        if not isinstance(cues, list):
            return base_time

        # Cue 개수에 따른 추가 시간 (cue당 5초 추가)
        additional_time = len(cues) * 5

        # 복잡한 이펙트가 있는지 확인
        complexity_multiplier = 1.0
        for cue in cues:
            if isinstance(cue, dict):
                # 텍스트 길이에 따른 복잡도
                if "text" in cue and len(str(cue["text"])) > 50:
                    complexity_multiplier += 0.2

                # 특수 이펙트 확인
                if "effects" in cue or "animations" in cue:
                    complexity_multiplier += 0.3

        total_time = int((base_time + additional_time) * complexity_multiplier)

        # 최소 20초, 최대 300초 (5분)
        return max(20, min(300, total_time))

    except Exception:
        return 30  # 계산 실패시 기본값 반환
