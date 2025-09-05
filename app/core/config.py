import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App Settings
    app_name: str = Field(default="ECG Backend", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")

    # CORS Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], description="CORS allowed origins"
    )

    # AWS Settings
    aws_access_key_id: str = Field(..., description="AWS Access Key ID")
    aws_secret_access_key: str = Field(..., description="AWS Secret Access Key")
    aws_region: str = Field(default="ap-northeast-2", description="AWS Region")

    # S3 Settings
    s3_bucket_name: str = Field(..., description="S3 bucket name for video storage")
    s3_presigned_url_expire: int = Field(
        default=3600, description="Presigned URL expiration time in seconds"
    )

    # Model Server Settings
    model_server_url: str = Field(..., description="Model server URL")

    # Database Settings
    database_url: str = Field(
        default="postgresql://ecg_user:ecg_password@localhost:5432/ecg_db",
        description="Database URL"
    )
    db_user: str = Field(default="ecg_user", description="Database username")
    db_password: str = Field(default="ecg_password", description="Database password")
    db_name: str = Field(default="ecg_db", description="Database name")
    db_port: int = Field(default=5432, description="Database port")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
