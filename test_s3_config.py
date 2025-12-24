#!/usr/bin/env python3
"""
Test script to verify S3 storage configuration.

Usage:
    uv run python test_s3_config.py
"""

import sys
import asyncio
from datetime import datetime


def print_header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_success(text: str) -> None:
    print(f"  ✅ {text}")


def print_error(text: str) -> None:
    print(f"  ❌ {text}")


def print_info(text: str) -> None:
    print(f"  ℹ️  {text}")


async def test_s3_configuration() -> bool:
    """Test S3 storage configuration and basic operations."""

    print_header("Loading Configuration")

    try:
        from app.config import settings
        print_success("Configuration loaded")
        print_info(f"Storage Type: {settings.storage_type}")
        print_info(f"S3 Bucket: {settings.s3_bucket}")
        print_info(f"AWS Region: {settings.aws_region}")
        print_info(f"AWS Access Key ID: {'*' * 8}{settings.aws_access_key_id[-4:] if len(settings.aws_access_key_id) > 4 else '(not set)'}")

        if settings.storage_type != "s3":
            print_error(f"STORAGE_TYPE is '{settings.storage_type}', expected 's3'")
            print_info("Set STORAGE_TYPE=s3 in your .env file")
            return False

        if not settings.aws_access_key_id:
            print_error("AWS_ACCESS_KEY_ID is not set")
            return False

        if not settings.aws_secret_access_key:
            print_error("AWS_SECRET_ACCESS_KEY is not set")
            return False

    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        return False

    print_header("Testing boto3 Import")

    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
        print_success("boto3 imported successfully")
    except ImportError as e:
        print_error(f"Failed to import boto3: {e}")
        print_info("Run: uv pip install boto3")
        return False

    print_header("Testing S3 Connection")

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        print_success("S3 client created")
    except Exception as e:
        print_error(f"Failed to create S3 client: {e}")
        return False

    # Test bucket access
    try:
        s3_client.head_bucket(Bucket=settings.s3_bucket)
        print_success(f"Bucket '{settings.s3_bucket}' is accessible")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "404":
            print_error(f"Bucket '{settings.s3_bucket}' does not exist")
        elif error_code == "403":
            print_error(f"Access denied to bucket '{settings.s3_bucket}'")
        else:
            print_error(f"Bucket access error: {e}")
        return False
    except NoCredentialsError:
        print_error("No valid AWS credentials found")
        return False

    print_header("Testing Storage Service")

    try:
        from app.services.storage import get_storage_service
        storage = get_storage_service()
        print_success("StorageService initialized with S3 backend")
    except Exception as e:
        print_error(f"Failed to initialize StorageService: {e}")
        return False

    print_header("Testing Upload/Download/Delete Operations")

    test_content = f"S3 test file created at {datetime.now().isoformat()}".encode()
    test_filename = f"s3_config_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    # Test upload
    try:
        path = await storage.upload_bytes(test_content, test_filename, prefix="_test")
        print_success(f"Upload successful: {path}")
    except Exception as e:
        print_error(f"Upload failed: {e}")
        return False

    # Test exists
    try:
        exists = await storage.file_exists(path)
        if exists:
            print_success("File existence check: confirmed")
        else:
            print_error("File existence check: file not found after upload")
            return False
    except Exception as e:
        print_error(f"Existence check failed: {e}")
        return False

    # Test download
    try:
        downloaded = await storage.download_file(path)
        if downloaded == test_content:
            print_success("Download successful: content matches")
        else:
            print_error("Download content does not match uploaded content")
            return False
    except Exception as e:
        print_error(f"Download failed: {e}")
        return False

    # Test delete
    try:
        await storage.delete_file(path)
        exists_after_delete = await storage.file_exists(path)
        if not exists_after_delete:
            print_success("Delete successful: file removed")
        else:
            print_error("Delete failed: file still exists")
            return False
    except Exception as e:
        print_error(f"Delete failed: {e}")
        return False

    print_header("All Tests Passed!")
    print_success("Your S3 configuration is working correctly")
    print_info("You can now use S3 storage in production")

    return True


def main() -> int:
    """Main entry point."""
    print("\n" + "=" * 60)
    print("  S3 Storage Configuration Test")
    print("=" * 60)

    try:
        result = asyncio.run(test_s3_configuration())
        return 0 if result else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
