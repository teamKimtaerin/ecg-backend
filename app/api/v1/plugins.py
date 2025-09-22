from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import RedirectResponse
from urllib.parse import unquote
from botocore.exceptions import ClientError
from app.services.s3_service import s3_service

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("/{plugin_key:path}/manifest.json")
async def get_plugin_manifest(
    plugin_key: str = Path(..., description="Plugin key with version")
):
    """Get plugin manifest.json via S3 presigned URL redirect."""
    try:
        # URL 디코딩: fliptype%402.0.0 → fliptype@2.0.0
        plugin_key = unquote(plugin_key)

        # TODO: 플러그인 권한 체크 (isPro 등)
        # 현재는 모든 사용자에게 허용

        presigned_url = s3_service.generate_plugin_presigned_url(
            plugin_key, "manifest.json"
        )

        return RedirectResponse(url=presigned_url, status_code=302)

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{plugin_key:path}/index.mjs")
async def get_plugin_entry(
    plugin_key: str = Path(..., description="Plugin key with version")
):
    """Get plugin index.mjs via S3 presigned URL redirect."""
    try:
        # URL 디코딩: fliptype%402.0.0 → fliptype@2.0.0
        plugin_key = unquote(plugin_key)

        # TODO: 플러그인 권한 체크 (isPro 등)
        # 현재는 모든 사용자에게 허용

        presigned_url = s3_service.generate_plugin_presigned_url(
            plugin_key, "index.mjs"
        )

        return RedirectResponse(url=presigned_url, status_code=302)

    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{plugin_key:path}/assets/{asset_path:path}")
async def get_plugin_asset(
    plugin_key: str = Path(..., description="Plugin key with version"),
    asset_path: str = Path(..., description="Asset path relative to plugin"),
):
    """Redirect plugin asset files (e.g., thumbnails, fonts) via S3 presigned URL."""
    try:
        plugin_key = unquote(plugin_key)
        asset_path = unquote(asset_path)

        file_key = f"plugins/{plugin_key}/assets/{asset_path}"

        s3_service.logger.info(
            "Generating plugin asset presigned URL",
            extra={
                "plugin_bucket": s3_service.plugin_bucket_name,
                "plugin_key": plugin_key,
                "asset_path": asset_path,
                "file_key": file_key,
            },
        )

        # Ensure asset exists
        try:
            s3_service.s3_client.head_object(
                Bucket=s3_service.plugin_bucket_name, Key=file_key
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise HTTPException(status_code=404, detail="Asset not found")
            raise HTTPException(status_code=500, detail=str(e))

        presigned_url = s3_service.s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": s3_service.plugin_bucket_name,
                "Key": file_key,
            },
            ExpiresIn=s3_service.presigned_expire,
        )

        return RedirectResponse(url=presigned_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
