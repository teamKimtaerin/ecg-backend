from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    # App Settings
    app_name: str = Field(default="ECG Backend", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(..., description="Application secret key")
    mode: str = Field(default="dev", description="Application mode")
    backend_port: int = Field(default=8000, description="Backend port")

    # CORS Settings
    cors_origins: Union[List[str], str] = Field(
        default="http://localhost:3000", description="CORS allowed origins"
    )

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # AWS Settings
    aws_access_key_id: str = Field(..., description="AWS Access Key ID")
    aws_secret_access_key: str = Field(..., description="AWS Secret Access Key")
    aws_region: str = Field(default="ap-northeast-2", description="AWS Region")

    # S3 Settings
    s3_bucket_name: str = Field(..., description="S3 bucket name for video storage")
    s3_presigned_url_expire: int = Field(
        default=3600, description="Presigned URL expiration time in seconds"
    )

    # ML Server Settings
    MODEL_SERVER_URL: str = Field(
        ..., description="ML server URL", alias="MODEL_SERVER_URL"
    )
    ML_API_TIMEOUT: int = Field(
        default=300, description="ML API timeout in seconds (default: 5 minutes)"
    )
    FASTAPI_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="Backend server URL for ML callbacks",
    )

    # Database Settings
    database_url: str = Field(
        default="postgresql://ecg_user:ecg_password@localhost:5432/ecg_db",
        description="Database URL",
    )
    db_user: str = Field(default="ecg_user", description="Database username")
    db_password: str = Field(default="ecg_password", description="Database password")
    db_name: str = Field(default="ecg_db", description="Database name")
    db_port: int = Field(default=5432, description="Database port")

    # API Settings
    api_prefix: str = Field(default="/api/v1", description="API path prefix")

    # JWT Settings
    jwt_secret_key: str = Field(..., description="JWT secret key")
    jwt_access_token_expire_minutes: int = Field(
        default=1440, description="JWT token expiration time in minutes"
    )

    # Google OAuth Settings
    google_client_id: str = Field(..., description="Google OAuth client ID")
    google_client_secret: str = Field(..., description="Google OAuth client secret")
    google_redirect_uri: str = Field(..., description="Google OAuth redirect URI")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
