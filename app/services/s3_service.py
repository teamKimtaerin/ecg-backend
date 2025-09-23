import boto3
import uuid
import logging
from datetime import datetime
from botocore.exceptions import ClientError
import os
from typing import Tuple


class S3Service:
    def __init__(self):
        # 환경변수에서 AWS 설정 읽기
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("S3_BUCKET_NAME")
        self.plugin_bucket_name = os.getenv("S3_PLUGIN_BUCKET_NAME", self.bucket_name)
        self.presigned_expire = int(os.getenv("S3_PRESIGNED_URL_EXPIRE", "3600"))

        if not all(
            [self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]
        ):
            raise Exception(
                "Missing AWS credentials or bucket name in environment variables"
            )

        self.logger = logging.getLogger(__name__)

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
        )

    def generate_file_key(self, filename: str, user_id: str) -> str:
        """Generate unique file key for S3 storage."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        # Create file key: videos/user_id/timestamp_uniqueid_filename.ext
        file_key = f"videos/{user_id}/{timestamp}_{unique_id}_{filename}"

        return file_key

    def generate_presigned_url(
        self, filename: str, filetype: str, user_id: str
    ) -> Tuple[str, str]:
        """Generate presigned URL for S3 upload."""
        try:
            file_key = self.generate_file_key(filename, user_id)

            presigned_url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": file_key,
                    "ContentType": filetype,
                },
                ExpiresIn=self.presigned_expire,
            )

            return presigned_url, file_key

        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def generate_download_url(self, file_key: str) -> str:
        """Generate presigned URL for S3 download."""
        try:
            # 파일 존재 확인
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)

            # 다운로드용 presigned URL 생성
            download_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": file_key},
                ExpiresIn=self.presigned_expire,
            )

            return download_url

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise Exception("File not found")
            raise Exception(f"Failed to generate download URL: {str(e)}")

    def check_file_exists(self, file_key: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise Exception(f"Failed to check file existence: {str(e)}")

    def generate_plugin_presigned_url(self, plugin_key: str, file_type: str) -> str:
        """Generate presigned URL for plugin files (manifest.json or index.mjs)."""
        try:
            # 플러그인 파일 경로: plugins/rotation@2.0.0/manifest.json
            file_key = f"plugins/{plugin_key}/{file_type}"

            self.logger.info(
                "Generating plugin presigned URL",
                extra={
                    "plugin_bucket": self.plugin_bucket_name,
                    "plugin_key": plugin_key,
                    "file_key": file_key,
                    "file_type": file_type,
                },
            )

            # 파일 존재 확인
            self.s3_client.head_object(Bucket=self.plugin_bucket_name, Key=file_key)

            # 다운로드용 presigned URL 생성
            presigned_url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.plugin_bucket_name, "Key": file_key},
                ExpiresIn=self.presigned_expire,
            )

            return presigned_url

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise Exception(f"Plugin file not found: {plugin_key}/{file_type}")
            raise Exception(f"Failed to generate plugin presigned URL: {str(e)}")


# Create singleton instance
s3_service = S3Service()
