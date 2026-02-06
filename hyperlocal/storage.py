from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import boto3


@dataclass
class StorageConfig:
    enabled: bool = os.getenv("HYPERLOCAL_STORAGE_ENABLED", "0") == "1"
    endpoint_url: str | None = os.getenv("S3_ENDPOINT_URL")
    access_key: str | None = os.getenv("S3_ACCESS_KEY")
    secret_key: str | None = os.getenv("S3_SECRET_KEY")
    bucket: str | None = os.getenv("S3_BUCKET")
    region: str | None = os.getenv("S3_REGION")
    public_base_url: str | None = os.getenv("S3_PUBLIC_BASE_URL")


class StorageClient:
    def __init__(self, config: StorageConfig) -> None:
        if not config.bucket:
            raise RuntimeError("S3_BUCKET is not set")
        self.config = config
        self.client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.secret_key,
            region_name=config.region,
        )

    def upload_file(self, path: str, key: str, content_type: str = "image/png") -> str:
        self.client.upload_file(
            path,
            self.config.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        if self.config.public_base_url:
            return f"{self.config.public_base_url.rstrip('/')}/{key}"
        return f"s3://{self.config.bucket}/{key}"


def build_storage() -> StorageClient | None:
    config = StorageConfig()
    if not config.enabled:
        return None
    return StorageClient(config)


def key_for_image(run_id: int, variant_index: int, suffix: str = "png") -> str:
    return f"creative_runs/{run_id}/variant_{variant_index:02d}.{suffix}"
