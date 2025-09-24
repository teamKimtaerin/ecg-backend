#!/usr/bin/env python3
"""
S3에 플러그인 파일들을 업로드하는 스크립트
motiontext-renderer의 demo/plugin-server/plugins/* → S3 plugins/
"""

import os
import boto3
from pathlib import Path
from botocore.exceptions import ClientError


def setup_s3_client():
    """S3 클라이언트 설정"""
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    if not all([aws_access_key_id, aws_secret_access_key]):
        raise Exception("AWS credentials not found in environment variables")

    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )


def create_bucket_if_not_exists(s3_client, bucket_name, region):
    """S3 버킷이 없으면 생성"""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ 버킷 '{bucket_name}'이 이미 존재합니다.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "404":
            try:
                if region == "us-east-1":
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": region},
                    )
                print(f"✅ 버킷 '{bucket_name}'을 생성했습니다.")
            except ClientError as create_error:
                print(f"❌ 버킷 생성 실패: {create_error}")
                raise
        else:
            print(f"❌ 버킷 확인 실패: {e}")
            raise


def setup_cors_policy(s3_client, bucket_name):
    """S3 버킷에 CORS 정책 설정"""
    cors_configuration = {
        "CORSRules": [
            {
                "AllowedOrigins": [
                    "http://localhost:3000",
                    "https://ho-it.site",
                    "https://*.ho-it.site",
                ],
                "AllowedMethods": ["GET", "HEAD"],
                "AllowedHeaders": ["*"],
                "MaxAgeSeconds": 3600,
            }
        ]
    }

    try:
        s3_client.put_bucket_cors(
            Bucket=bucket_name, CORSConfiguration=cors_configuration
        )
        print("✅ CORS 정책을 설정했습니다.")
    except ClientError as e:
        print(f"❌ CORS 설정 실패: {e}")


def upload_plugin_files(s3_client, bucket_name, source_path):
    """플러그인 파일들을 S3에 업로드"""
    source_dir = Path(source_path)

    if not source_dir.exists():
        print(f"❌ 소스 디렉토리를 찾을 수 없습니다: {source_path}")
        return

    uploaded_count = 0

    # plugins 디렉토리 하위의 모든 플러그인 폴더 순회
    for plugin_dir in source_dir.iterdir():
        if plugin_dir.is_dir():
            plugin_name = plugin_dir.name  # e.g., "rotation@2.0.0"

            # manifest.json 업로드
            manifest_file = plugin_dir / "manifest.json"
            if manifest_file.exists():
                s3_key = f"plugins/{plugin_name}/manifest.json"
                try:
                    s3_client.upload_file(
                        str(manifest_file),
                        bucket_name,
                        s3_key,
                        ExtraArgs={"ContentType": "application/json"},
                    )
                    print(f"✅ 업로드됨: {s3_key}")
                    uploaded_count += 1
                except ClientError as e:
                    print(f"❌ {s3_key} 업로드 실패: {e}")

            # index.mjs 업로드
            entry_file = plugin_dir / "index.mjs"
            if entry_file.exists():
                s3_key = f"plugins/{plugin_name}/index.mjs"
                try:
                    s3_client.upload_file(
                        str(entry_file),
                        bucket_name,
                        s3_key,
                        ExtraArgs={"ContentType": "text/javascript"},
                    )
                    print(f"✅ 업로드됨: {s3_key}")
                    uploaded_count += 1
                except ClientError as e:
                    print(f"❌ {s3_key} 업로드 실패: {e}")

    print(f"\n📊 총 {uploaded_count}개 파일이 업로드되었습니다.")


def main():
    """메인 함수"""
    # 환경변수에서 설정 읽기
    bucket_name = os.getenv("S3_BUCKET_NAME")
    aws_region = os.getenv("AWS_REGION", "us-east-1")

    if not bucket_name:
        print("❌ S3_BUCKET_NAME 환경변수가 설정되지 않았습니다.")
        return

    # motiontext-renderer 플러그인 소스 경로
    source_path = "/Users/yerin/Desktop/motiontext-renderer/demo/plugin-server/plugins"

    try:
        print("🚀 S3 플러그인 업로드를 시작합니다...")
        print(f"📁 소스 경로: {source_path}")
        print(f"🪣 대상 버킷: {bucket_name}")
        print(f"🌍 리전: {aws_region}")
        print()

        # S3 클라이언트 설정
        s3_client = setup_s3_client()

        # 버킷 생성 (필요시)
        create_bucket_if_not_exists(s3_client, bucket_name, aws_region)

        # CORS 정책 설정
        setup_cors_policy(s3_client, bucket_name)

        # 플러그인 파일 업로드
        upload_plugin_files(s3_client, bucket_name, source_path)

        print("\n🎉 모든 작업이 완료되었습니다!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
