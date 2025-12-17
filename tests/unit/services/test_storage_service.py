"""Unit tests for Storage Service.

Tests path generation, local storage, S3 storage, and sync/async operations.
"""

import pytest
import tempfile
import os
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from uuid import uuid4, UUID

from app.services.storage import (
    StorageService,
    LocalStorageBackend,
    S3StorageBackend,
    StorageBackend,
)


# ============================================================================
# Test Path Generation
# ============================================================================


class TestPathGeneration:
    """Tests for path generation in StorageService."""

    @pytest.fixture
    def storage_service(self, tmp_path):
        """Create a StorageService with local backend for path generation tests."""
        backend = LocalStorageBackend(base_path=str(tmp_path))
        return StorageService(backend=backend)

    def test_uuid_uniqueness(self, storage_service):
        """Test that generated paths are unique due to UUID usage."""
        filename = "test_document.pdf"

        # Generate multiple paths
        paths = set()
        for _ in range(100):
            path = storage_service._generate_path(filename)
            paths.add(path)

        # All paths should be unique
        assert len(paths) == 100, "Generated paths should be unique"

    def test_extension_preservation(self, storage_service):
        """Test that file extensions are preserved in generated paths."""
        test_cases = [
            ("document.pdf", ".pdf"),
            ("image.PNG", ".PNG"),
            ("file.tar.gz", ".gz"),  # Only last extension
            ("noextension", ""),
            ("file.with.multiple.dots.txt", ".txt"),
        ]

        for filename, expected_ext in test_cases:
            path = storage_service._generate_path(filename)
            assert path.endswith(expected_ext), f"Path for {filename} should end with {expected_ext}"

    def test_tenant_path_isolation(self, storage_service):
        """Test that paths include prefix for tenant isolation."""
        filename = "document.pdf"

        # Test with default prefix
        default_path = storage_service._generate_path(filename)
        assert default_path.startswith("documents/"), "Default prefix should be 'documents'"

        # Test with custom prefix (tenant-specific)
        tenant_prefix = "tenant_123/documents"
        tenant_path = storage_service._generate_path(filename, prefix=tenant_prefix)
        assert tenant_path.startswith(f"{tenant_prefix}/"), f"Path should start with {tenant_prefix}"

        # Test with pages prefix
        pages_path = storage_service._generate_path(filename, prefix="pages")
        assert pages_path.startswith("pages/"), "Pages prefix should work"

    def test_safe_filename_generation(self, storage_service):
        """Test that generated filenames are sanitized and safe."""
        # Potentially dangerous filenames
        dangerous_filenames = [
            "../../../etc/passwd",
            "..\\..\\system.ini",
            "/absolute/path/file.txt",
            "file with spaces.pdf",
            "file\x00null.pdf",  # Null byte
        ]

        for filename in dangerous_filenames:
            path = storage_service._generate_path(filename)

            # Path should not contain traversal sequences
            assert ".." not in path, f"Path should not contain '..' for {filename}"
            assert not path.startswith("/"), f"Path should not start with '/' for {filename}"

            # Path should be a valid relative path
            assert "/" in path, "Path should contain directory separator"

            # UUID portion should be valid
            parts = path.split("/")
            assert len(parts) == 2, "Path should have format 'prefix/uuid.ext'"


# ============================================================================
# Test Local Backend
# ============================================================================


class TestLocalBackend:
    """Tests for LocalStorageBackend."""

    @pytest.fixture
    def local_backend(self, tmp_path):
        """Create LocalStorageBackend with temp directory."""
        return LocalStorageBackend(base_path=str(tmp_path))

    @pytest.fixture
    def sample_content(self):
        """Sample file content for testing."""
        return b"This is test content for storage testing."

    @pytest.mark.asyncio
    async def test_upload_file_success(self, local_backend, sample_content, tmp_path):
        """Test that file uploads successfully to local storage."""
        file_obj = BytesIO(sample_content)
        path = "documents/test-file.txt"

        result = await local_backend.upload(file_obj, path)

        # Check return value
        assert result == path, "Upload should return the path"

        # Verify file was written
        full_path = tmp_path / path
        assert full_path.exists(), "File should exist on disk"
        assert full_path.read_bytes() == sample_content, "Content should match"

    @pytest.mark.asyncio
    async def test_download_file_success(self, local_backend, sample_content, tmp_path):
        """Test that file downloads successfully from local storage."""
        # Setup: write file directly
        path = "documents/download-test.txt"
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(sample_content)

        # Test download
        result = await local_backend.download(path)

        assert result == sample_content, "Downloaded content should match original"

    @pytest.mark.asyncio
    async def test_delete_file_success(self, local_backend, sample_content, tmp_path):
        """Test that file deletes successfully from local storage."""
        # Setup: write file directly
        path = "documents/delete-test.txt"
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(sample_content)
        assert full_path.exists(), "File should exist before delete"

        # Test delete
        await local_backend.delete(path)

        assert not full_path.exists(), "File should not exist after delete"

    @pytest.mark.asyncio
    async def test_file_exists_true(self, local_backend, sample_content, tmp_path):
        """Test that exists returns True for existing file."""
        # Setup: write file
        path = "documents/exists-test.txt"
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(sample_content)

        # Test exists
        result = await local_backend.exists(path)

        assert result is True, "exists() should return True for existing file"

    @pytest.mark.asyncio
    async def test_file_exists_false(self, local_backend):
        """Test that exists returns False for missing file."""
        path = "documents/nonexistent-file.txt"

        result = await local_backend.exists(path)

        assert result is False, "exists() should return False for missing file"

    @pytest.mark.asyncio
    async def test_upload_creates_directories(self, local_backend, sample_content, tmp_path):
        """Test that upload creates parent directories if they don't exist."""
        file_obj = BytesIO(sample_content)
        # Deeply nested path
        path = "tenant/123/documents/2024/01/file.txt"

        result = await local_backend.upload(file_obj, path)

        # Check directories were created
        full_path = tmp_path / path
        assert full_path.exists(), "File should exist"
        assert full_path.parent.is_dir(), "Parent directories should be created"
        assert result == path

    def test_get_url_returns_file_uri(self, local_backend, tmp_path):
        """Test that get_url returns a file:// URI."""
        path = "documents/url-test.txt"

        url = local_backend.get_url(path)

        expected_path = tmp_path / path
        assert url == f"file://{expected_path}", "URL should be file:// URI"

    def test_init_creates_base_directory(self, tmp_path):
        """Test that initialization creates base directory if it doesn't exist."""
        new_base = tmp_path / "new_storage_dir"
        assert not new_base.exists()

        backend = LocalStorageBackend(base_path=str(new_base))

        assert new_base.exists(), "Base directory should be created on init"
        assert new_base.is_dir(), "Should be a directory"


# ============================================================================
# Test S3 Backend
# ============================================================================


class TestS3Backend:
    """Tests for S3StorageBackend with mocked boto3."""

    @pytest.fixture
    def mock_s3_client(self):
        """Create a mock S3 client."""
        mock_client = MagicMock()
        return mock_client

    @pytest.fixture
    def mock_client_error(self):
        """Create a mock ClientError class for S3 error testing."""

        class MockClientError(Exception):
            """Mock boto3 ClientError."""

            def __init__(self, message="S3 Error"):
                super().__init__(message)

        return MockClientError

    @pytest.fixture
    def s3_backend(self, mock_s3_client, mock_client_error):
        """Create S3StorageBackend with mocked boto3."""
        with patch("boto3.client", return_value=mock_s3_client):
            # Need to also patch the ClientError import
            with patch.dict(
                "sys.modules",
                {
                    "boto3": MagicMock(),
                    "botocore": MagicMock(),
                    "botocore.exceptions": MagicMock(ClientError=mock_client_error),
                },
            ):
                # Import after patching
                import boto3

                boto3.client = MagicMock(return_value=mock_s3_client)

                backend = S3StorageBackend(
                    bucket="test-bucket",
                    access_key_id="test-access-key",
                    secret_access_key="test-secret-key",
                    region="us-east-1",
                )
                backend.s3_client = mock_s3_client
                backend.ClientError = mock_client_error
                return backend

    @pytest.mark.asyncio
    async def test_upload_to_s3_success(self, s3_backend, mock_s3_client):
        """Test that file uploads to S3 successfully."""
        content = b"S3 test content"
        file_obj = BytesIO(content)
        path = "documents/s3-test.txt"

        result = await s3_backend.upload(file_obj, path)

        assert result == path, "Upload should return the path"
        mock_s3_client.upload_fileobj.assert_called_once_with(
            file_obj, "test-bucket", path
        )

    @pytest.mark.asyncio
    async def test_download_from_s3_success(self, s3_backend, mock_s3_client):
        """Test that file downloads from S3 successfully."""
        expected_content = b"Downloaded S3 content"
        mock_body = MagicMock()
        mock_body.read.return_value = expected_content
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        path = "documents/s3-download.txt"
        result = await s3_backend.download(path)

        assert result == expected_content, "Download should return file content"
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key=path
        )

    @pytest.mark.asyncio
    async def test_delete_from_s3_success(self, s3_backend, mock_s3_client):
        """Test that file deletes from S3 successfully."""
        path = "documents/s3-delete.txt"

        await s3_backend.delete(path)

        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key=path
        )

    @pytest.mark.asyncio
    async def test_s3_exists_check(self, s3_backend, mock_s3_client):
        """Test that exists check works with S3."""
        path = "documents/s3-exists.txt"

        # Test when file exists
        mock_s3_client.head_object.return_value = {"ContentLength": 100}
        result = await s3_backend.exists(path)
        assert result is True, "exists() should return True when head_object succeeds"

        # Test when file doesn't exist
        mock_s3_client.head_object.side_effect = s3_backend.ClientError(
            "File not found"
        )
        result = await s3_backend.exists(path)
        assert result is False, "exists() should return False when head_object fails"

    def test_s3_get_url(self, s3_backend):
        """Test that get_url returns correct S3 URI."""
        path = "documents/s3-url-test.txt"

        url = s3_backend.get_url(path)

        assert url == "s3://test-bucket/documents/s3-url-test.txt"

    @pytest.mark.asyncio
    async def test_upload_s3_error_handling(self, s3_backend, mock_s3_client):
        """Test that S3 upload errors are properly handled."""
        mock_s3_client.upload_fileobj.side_effect = s3_backend.ClientError(
            "Upload failed"
        )

        file_obj = BytesIO(b"test content")
        path = "documents/error-test.txt"

        with pytest.raises(Exception, match="Failed to upload to S3"):
            await s3_backend.upload(file_obj, path)

    @pytest.mark.asyncio
    async def test_download_s3_error_handling(self, s3_backend, mock_s3_client):
        """Test that S3 download errors are properly handled."""
        mock_s3_client.get_object.side_effect = s3_backend.ClientError(
            "Download failed"
        )

        path = "documents/error-download.txt"

        with pytest.raises(Exception, match="Failed to download from S3"):
            await s3_backend.download(path)

    @pytest.mark.asyncio
    async def test_delete_s3_error_handling(self, s3_backend, mock_s3_client):
        """Test that S3 delete errors are properly handled."""
        mock_s3_client.delete_object.side_effect = s3_backend.ClientError(
            "Delete failed"
        )

        path = "documents/error-delete.txt"

        with pytest.raises(Exception, match="Failed to delete from S3"):
            await s3_backend.delete(path)


# ============================================================================
# Test Sync/Async Fallback
# ============================================================================


class TestSyncAsyncFallback:
    """Tests for sync/async method availability and fallback behavior."""

    @pytest.fixture
    def local_backend(self, tmp_path):
        """Create LocalStorageBackend for sync/async tests."""
        return LocalStorageBackend(base_path=str(tmp_path))

    @pytest.fixture
    def storage_service(self, local_backend):
        """Create StorageService with local backend."""
        return StorageService(backend=local_backend)

    def test_sync_method_available(self, local_backend, tmp_path):
        """Test that sync methods work on LocalStorageBackend."""
        content = b"Sync test content"
        file_obj = BytesIO(content)
        path = "documents/sync-test.txt"

        # Test upload_sync
        result = local_backend.upload_sync(file_obj, path)
        assert result == path

        # Verify file was written
        full_path = tmp_path / path
        assert full_path.exists()

        # Test download_sync
        downloaded = local_backend.download_sync(path)
        assert downloaded == content

        # Test exists_sync
        exists = local_backend.exists_sync(path)
        assert exists is True

        # Test delete_sync
        local_backend.delete_sync(path)
        assert not full_path.exists()

    @pytest.mark.asyncio
    async def test_async_method_available(self, local_backend, tmp_path):
        """Test that async methods work on LocalStorageBackend."""
        content = b"Async test content"
        file_obj = BytesIO(content)
        path = "documents/async-test.txt"

        # Test async upload
        result = await local_backend.upload(file_obj, path)
        assert result == path

        # Verify file was written
        full_path = tmp_path / path
        assert full_path.exists()

        # Test async download
        downloaded = await local_backend.download(path)
        assert downloaded == content

        # Test async exists
        exists = await local_backend.exists(path)
        assert exists is True

        # Test async delete
        await local_backend.delete(path)
        assert not full_path.exists()

    def test_fallback_to_sync_for_download(self, storage_service, tmp_path):
        """Test that download_file_sync falls back correctly when backend has sync method."""
        content = b"Fallback test content"

        # First upload a file
        path = "documents/fallback-test.txt"
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        # Test download_file_sync (should use sync method when available)
        result = storage_service.download_file_sync(path)

        assert result == content, "download_file_sync should return correct content"

    def test_fallback_to_sync_for_upload(self, storage_service, tmp_path):
        """Test that upload_bytes_sync falls back correctly."""
        content = b"Upload sync test content"
        filename = "sync-upload.txt"

        # Test upload_bytes_sync
        path = storage_service.upload_bytes_sync(content, filename, prefix="documents")

        # Verify path format
        assert path.startswith("documents/")
        assert path.endswith(".txt")

        # Verify file was written
        full_path = tmp_path / path
        assert full_path.exists()
        assert full_path.read_bytes() == content


# ============================================================================
# Test StorageService High-Level Methods
# ============================================================================


class TestStorageServiceMethods:
    """Tests for high-level StorageService methods."""

    @pytest.fixture
    def local_backend(self, tmp_path):
        """Create LocalStorageBackend."""
        return LocalStorageBackend(base_path=str(tmp_path))

    @pytest.fixture
    def storage_service(self, local_backend):
        """Create StorageService."""
        return StorageService(backend=local_backend)

    @pytest.fixture
    def mock_upload_file(self):
        """Create a mock FastAPI UploadFile."""
        content = b"Mock upload file content"
        mock_file = MagicMock()
        mock_file.filename = "test-upload.pdf"
        mock_file.file = BytesIO(content)
        return mock_file, content

    @pytest.mark.asyncio
    async def test_upload_file_returns_path_and_size(
        self, storage_service, mock_upload_file, tmp_path
    ):
        """Test that upload_file returns correct path and size."""
        mock_file, content = mock_upload_file

        path, size = await storage_service.upload_file(mock_file)

        # Check path format
        assert path.startswith("documents/")
        assert path.endswith(".pdf")

        # Check size
        assert size == len(content)

        # Verify file exists
        full_path = tmp_path / path
        assert full_path.exists()

    @pytest.mark.asyncio
    async def test_upload_bytes_returns_path(self, storage_service, tmp_path):
        """Test that upload_bytes returns correct path."""
        content = b"Bytes content to upload"
        filename = "bytes-test.json"

        path = await storage_service.upload_bytes(content, filename, prefix="data")

        # Check path format
        assert path.startswith("data/")
        assert path.endswith(".json")

        # Verify file exists and has correct content
        full_path = tmp_path / path
        assert full_path.exists()
        assert full_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_download_file_returns_content(self, storage_service, tmp_path):
        """Test that download_file returns file content."""
        content = b"Content to download"
        path = "documents/download-test.txt"

        # Create file directly
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        result = await storage_service.download_file(path)

        assert result == content

    @pytest.mark.asyncio
    async def test_delete_file_removes_file(self, storage_service, tmp_path):
        """Test that delete_file removes the file."""
        content = b"Content to delete"
        path = "documents/delete-test.txt"

        # Create file
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        assert full_path.exists()

        await storage_service.delete_file(path)

        assert not full_path.exists()

    @pytest.mark.asyncio
    async def test_file_exists_check(self, storage_service, tmp_path):
        """Test that file_exists correctly reports file existence."""
        content = b"Test content"
        path = "documents/exists-check.txt"

        # Initially should not exist
        assert await storage_service.file_exists(path) is False

        # Create file
        full_path = tmp_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        # Now should exist
        assert await storage_service.file_exists(path) is True

    def test_get_file_url(self, storage_service, tmp_path):
        """Test that get_file_url returns correct URL."""
        path = "documents/url-test.txt"

        url = storage_service.get_file_url(path)

        expected_path = tmp_path / path
        assert url == f"file://{expected_path}"


# ============================================================================
# Test Edge Cases and Error Handling
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def local_backend(self, tmp_path):
        """Create LocalStorageBackend."""
        return LocalStorageBackend(base_path=str(tmp_path))

    @pytest.fixture
    def storage_service(self, local_backend):
        """Create StorageService."""
        return StorageService(backend=local_backend)

    @pytest.mark.asyncio
    async def test_download_nonexistent_file_raises(self, local_backend):
        """Test that downloading a nonexistent file raises FileNotFoundError."""
        path = "documents/nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            await local_backend.download(path)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file_succeeds(self, local_backend, tmp_path):
        """Test that deleting a nonexistent file does not raise error."""
        path = "documents/nonexistent-delete.txt"

        # Should not raise
        await local_backend.delete(path)

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, local_backend, tmp_path):
        """Test uploading an empty file."""
        file_obj = BytesIO(b"")
        path = "documents/empty-file.txt"

        result = await local_backend.upload(file_obj, path)

        assert result == path
        full_path = tmp_path / path
        assert full_path.exists()
        assert full_path.read_bytes() == b""

    @pytest.mark.asyncio
    async def test_upload_large_file(self, local_backend, tmp_path):
        """Test uploading a large file (1MB)."""
        large_content = b"X" * (1024 * 1024)  # 1MB
        file_obj = BytesIO(large_content)
        path = "documents/large-file.bin"

        result = await local_backend.upload(file_obj, path)

        assert result == path
        full_path = tmp_path / path
        assert full_path.exists()
        assert full_path.read_bytes() == large_content

    def test_generate_path_with_no_filename(self, storage_service):
        """Test path generation with fallback filename."""
        # When no filename is provided, upload_file uses "file" as default
        path = storage_service._generate_path("file")

        # Should still generate valid path
        assert path.startswith("documents/")
        # No extension since filename has no extension
        parts = path.split("/")
        assert len(parts) == 2

    @pytest.mark.asyncio
    async def test_binary_file_content_preserved(self, local_backend, tmp_path):
        """Test that binary file content is preserved exactly."""
        # Create content with all possible byte values
        binary_content = bytes(range(256))
        file_obj = BytesIO(binary_content)
        path = "documents/binary-test.bin"

        await local_backend.upload(file_obj, path)
        downloaded = await local_backend.download(path)

        assert downloaded == binary_content, "Binary content should be preserved exactly"


# ============================================================================
# Test Factory Function
# ============================================================================


class TestGetStorageService:
    """Tests for the get_storage_service factory function."""

    def test_factory_returns_local_backend_by_default(self):
        """Test that factory creates local backend when storage_type is local."""
        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.storage_type = "local"
            mock_settings.local_storage_path = "/tmp/test_storage"

            from app.services.storage import get_storage_service

            service = get_storage_service()

            assert isinstance(service, StorageService)
            assert isinstance(service.backend, LocalStorageBackend)

    def test_factory_returns_s3_backend_when_configured(self):
        """Test that factory creates S3 backend when storage_type is s3."""
        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.storage_type = "s3"
            mock_settings.s3_bucket = "test-bucket"
            mock_settings.aws_access_key_id = "test-key"
            mock_settings.aws_secret_access_key = "test-secret"
            mock_settings.aws_region = "us-east-1"

            with patch("boto3.client") as mock_boto3:
                mock_boto3.return_value = MagicMock()

                from app.services.storage import get_storage_service

                service = get_storage_service()

                assert isinstance(service, StorageService)
                assert isinstance(service.backend, S3StorageBackend)
