import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ResponseFileManager:
    """응답 파일 관리 클래스"""

    def __init__(self, base_dir: str = "output"):
        """
        ResponseFileManager 초기화

        Args:
            base_dir: 출력 파일을 저장할 기본 디렉토리
        """
        self.base_dir = Path(base_dir)
        self.ensure_output_directory()

    def ensure_output_directory(self) -> None:
        """출력 디렉토리가 존재하는지 확인하고 없으면 생성"""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory ensured: {self.base_dir}")
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
            raise

    def generate_filename(
        self, prefix: str = "response", extension: str = "json"
    ) -> str:
        """
        날짜와 시간을 기반으로 파일명 생성

        Args:
            prefix: 파일명 접두사
            extension: 파일 확장자 (기본값: json)

        Returns:
            str: 생성된 파일명 (예: response_20241201_143022.json)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"

    def save_response(
        self,
        data: Dict[str, Any],
        filename: Optional[str] = None,
        prefix: str = "bedrock_response",
    ) -> str:
        """
        응답 데이터를 JSON 파일로 저장

        Args:
            data: 저장할 데이터 (딕셔너리)
            filename: 사용할 파일명 (None이면 자동 생성)
            prefix: 파일명 접두사

        Returns:
            str: 저장된 파일의 전체 경로

        Raises:
            Exception: 파일 저장 실패 시
        """
        try:
            if filename is None:
                filename = self.generate_filename(prefix=prefix)

            file_path = self.base_dir / filename

            # 메타데이터 추가
            save_data = {
                "timestamp": datetime.now().isoformat(),
                "filename": filename,
                "data": data,
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Response saved successfully: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save response to {filename}: {e}")
            raise

    def save_text_response(
        self,
        text: str,
        filename: Optional[str] = None,
        prefix: str = "bedrock_text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        텍스트 응답을 파일로 저장

        Args:
            text: 저장할 텍스트
            filename: 사용할 파일명 (None이면 자동 생성)
            prefix: 파일명 접두사
            metadata: 추가 메타데이터

        Returns:
            str: 저장된 파일의 전체 경로
        """
        try:
            if filename is None:
                filename = self.generate_filename(prefix=prefix, extension="txt")

            file_path = self.base_dir / filename

            # 메타데이터가 있으면 파일 상단에 추가
            content = ""
            if metadata:
                content += f"# Metadata\n"
                content += f"# Generated: {datetime.now().isoformat()}\n"
                for key, value in metadata.items():
                    content += f"# {key}: {value}\n"
                content += f"\n# Content\n\n"

            content += text

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Text response saved successfully: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save text response to {filename}: {e}")
            raise

    def list_saved_files(self, pattern: str = "*") -> list:
        """
        저장된 파일 목록 조회

        Args:
            pattern: 파일 패턴 (기본값: 모든 파일)

        Returns:
            list: 파일 경로 목록
        """
        try:
            files = list(self.base_dir.glob(pattern))
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # 최신순 정렬
            return [str(f) for f in files]
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def get_file_info(self, filename: str) -> Dict[str, Any]:
        """
        파일 정보 조회

        Args:
            filename: 파일명

        Returns:
            Dict: 파일 정보 (크기, 생성일시 등)
        """
        try:
            file_path = self.base_dir / filename
            if not file_path.exists():
                return {"error": "File not found"}

            stat = file_path.stat()
            return {
                "filename": filename,
                "path": str(file_path),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get file info for {filename}: {e}")
            return {"error": str(e)}


# 전역 인스턴스
response_file_manager = ResponseFileManager()
