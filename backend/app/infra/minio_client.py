"""MinIO (S3 호환) 파일 업로드·다운로드 클라이언트.

boto3는 동기 라이브러리이므로 비동기 핸들러에서는 `run_in_executor`로 감싸 호출한다.
"""

import asyncio
import functools
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from app.config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


def _ensure_bucket_sync(bucket: str) -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def _upload_sync(bucket: str, key: str, data: bytes, content_type: str) -> None:
    client = get_s3_client()
    client.upload_fileobj(
        BytesIO(data),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )


def _download_sync(bucket: str, key: str) -> bytes:
    client = get_s3_client()
    buffer = BytesIO()
    client.download_fileobj(bucket, key, buffer)
    return buffer.getvalue()


def _delete_sync(bucket: str, key: str) -> None:
    client = get_s3_client()
    client.delete_object(Bucket=bucket, Key=key)


def _presigned_url_sync(bucket: str, key: str, expires_in: int) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


async def _run(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args))


async def ensure_bucket() -> None:
    """버킷이 없으면 생성한다. 앱 시작 시 1회 호출."""
    await _run(_ensure_bucket_sync, settings.MINIO_BUCKET)


async def upload_file(key: str, data: bytes, content_type: str = "application/pdf") -> None:
    await _run(_upload_sync, settings.MINIO_BUCKET, key, data, content_type)


async def download_file(key: str) -> bytes:
    return await _run(_download_sync, settings.MINIO_BUCKET, key)


async def delete_file(key: str) -> None:
    await _run(_delete_sync, settings.MINIO_BUCKET, key)


async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    return await _run(_presigned_url_sync, settings.MINIO_BUCKET, key, expires_in)
