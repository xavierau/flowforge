"""Storage service for handling file uploads and downloads."""

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, TYPE_CHECKING

from fastapi import UploadFile

from app.config import settings

if TYPE_CHECKING:
    import boto3
    from botocore.exceptions import ClientError


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def upload(self, file: BinaryIO, path: str) -> str:
        """Upload a file and return its path."""
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download a file and return its contents."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete a file."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if a file exists."""
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        """Get the URL for a file."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str):
        """Initialize local storage with base path."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, path: str) -> Path:
        """Get full filesystem path."""
        return self.base_path / path

    def upload_sync(self, file: BinaryIO, path: str) -> str:
        """Upload file to local filesystem (synchronous)."""
        full_path = self._get_full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            content = file.read()
            f.write(content)

        return path

    async def upload(self, file: BinaryIO, path: str) -> str:
        """Upload file to local filesystem."""
        return self.upload_sync(file, path)

    def download_sync(self, path: str) -> bytes:
        """Download file from local filesystem (synchronous)."""
        full_path = self._get_full_path(path)
        with open(full_path, "rb") as f:
            return f.read()

    async def download(self, path: str) -> bytes:
        """Download file from local filesystem."""
        return self.download_sync(path)

    def delete_sync(self, path: str) -> None:
        """Delete file from local filesystem (synchronous)."""
        full_path = self._get_full_path(path)
        if full_path.exists():
            full_path.unlink()

    async def delete(self, path: str) -> None:
        """Delete file from local filesystem."""
        self.delete_sync(path)

    def exists_sync(self, path: str) -> bool:
        """Check if file exists (synchronous)."""
        return self._get_full_path(path).exists()

    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        return self.exists_sync(path)

    def get_url(self, path: str) -> str:
        """Get file URL (file:// for local)."""
        return f"file://{self._get_full_path(path)}"


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend."""

    def __init__(
        self,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str,
    ):
        """Initialize S3 storage."""
        import boto3  # Import only when S3 is used
        from botocore.exceptions import ClientError as CE

        self.ClientError = CE  # Store for use in methods
        self.bucket = bucket
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
        )

    async def upload(self, file: BinaryIO, path: str) -> str:
        """Upload file to S3."""
        try:
            self.s3_client.upload_fileobj(file, self.bucket, path)
            return path
        except self.ClientError as e:
            raise Exception(f"Failed to upload to S3: {e}")

    async def download(self, path: str) -> bytes:
        """Download file from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=path)
            return response["Body"].read()
        except self.ClientError as e:
            raise Exception(f"Failed to download from S3: {e}")

    async def delete(self, path: str) -> None:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=path)
        except self.ClientError as e:
            raise Exception(f"Failed to delete from S3: {e}")

    async def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=path)
            return True
        except self.ClientError:
            return False

    def get_url(self, path: str) -> str:
        """Get S3 URL."""
        return f"s3://{self.bucket}/{path}"


class StorageService:
    """High-level storage service."""

    def __init__(self, backend: StorageBackend):
        """Initialize with a storage backend."""
        self.backend = backend

    def _generate_path(self, filename: str, prefix: str = "documents") -> str:
        """
        Generate a unique storage path for a file.

        Args:
            filename: Original filename
            prefix: Path prefix (e.g., 'documents', 'pages')

        Returns:
            Unique file path
        """
        file_id = str(uuid.uuid4())
        extension = Path(filename).suffix
        return f"{prefix}/{file_id}{extension}"

    async def upload_file(
        self, file: UploadFile, prefix: str = "documents"
    ) -> tuple[str, int]:
        """
        Upload a file.

        Args:
            file: FastAPI UploadFile
            prefix: Storage path prefix

        Returns:
            Tuple of (file_path, file_size)
        """
        # Generate unique path
        path = self._generate_path(file.filename or "file", prefix)

        # Get file size
        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)

        # Upload
        await self.backend.upload(file.file, path)

        return path, size

    async def upload_bytes(
        self, content: bytes, filename: str, prefix: str = "documents"
    ) -> str:
        """
        Upload bytes content.

        Args:
            content: File content as bytes
            filename: Filename (for extension)
            prefix: Storage path prefix

        Returns:
            File path
        """
        from io import BytesIO

        path = self._generate_path(filename, prefix)
        file_obj = BytesIO(content)
        await self.backend.upload(file_obj, path)
        return path

    def download_file_sync(self, path: str) -> bytes:
        """
        Download a file (synchronous - for Celery tasks).

        Args:
            path: File path

        Returns:
            File contents as bytes
        """
        if hasattr(self.backend, "download_sync"):
            return self.backend.download_sync(path)
        # Fallback for backends without sync methods (like S3)
        import asyncio
        return asyncio.run(self.backend.download(path))

    async def download_file(self, path: str) -> bytes:
        """
        Download a file.

        Args:
            path: File path

        Returns:
            File contents as bytes
        """
        return await self.backend.download(path)

    def upload_bytes_sync(self, content: bytes, filename: str, prefix: str = "documents") -> str:
        """
        Upload bytes content (synchronous - for Celery tasks).

        Args:
            content: File content as bytes
            filename: Filename (for extension)
            prefix: Storage path prefix

        Returns:
            File path
        """
        from io import BytesIO

        path = self._generate_path(filename, prefix)
        file_obj = BytesIO(content)

        if hasattr(self.backend, "upload_sync"):
            return self.backend.upload_sync(file_obj, path)
        # Fallback for backends without sync methods (like S3)
        import asyncio
        return asyncio.run(self.backend.upload(file_obj, path))

    async def delete_file(self, path: str) -> None:
        """
        Delete a file.

        Args:
            path: File path
        """
        await self.backend.delete(path)

    async def file_exists(self, path: str) -> bool:
        """
        Check if file exists.

        Args:
            path: File path

        Returns:
            True if file exists
        """
        return await self.backend.exists(path)

    def get_file_url(self, path: str) -> str:
        """
        Get file URL.

        Args:
            path: File path

        Returns:
            File URL
        """
        return self.backend.get_url(path)


def get_storage_service() -> StorageService:
    """
    Get storage service instance based on configuration.

    Returns:
        StorageService instance
    """
    if settings.storage_type == "s3":
        backend = S3StorageBackend(
            bucket=settings.s3_bucket,
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
            region=settings.aws_region,
        )
    else:
        backend = LocalStorageBackend(base_path=settings.local_storage_path)

    return StorageService(backend=backend)
