from functools import lru_cache
from hashlib import sha256
from io import BytesIO

from minio import Minio
from minio.sse import SseS3

from app.core.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    client = get_minio_client()
    bucket = get_settings().minio_bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_file(key: str, data: bytes, mime: str) -> str:
    client = get_minio_client()
    bucket = get_settings().minio_bucket
    client.put_object(bucket, key, BytesIO(data), len(data), content_type=mime, sse=SseS3())
    return key


def get_presigned_url(key: str, expires: int = 300) -> str:
    from datetime import timedelta

    return get_minio_client().presigned_get_object(
        get_settings().minio_bucket, key, expires=timedelta(seconds=expires)
    )


def delete_file(key: str) -> None:
    get_minio_client().remove_object(get_settings().minio_bucket, key)


def get_file_hash(key: str) -> str:
    response = get_minio_client().get_object(get_settings().minio_bucket, key)
    try:
        digest = sha256()
        for chunk in response.stream(1024 * 1024):
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        response.close()
        response.release_conn()