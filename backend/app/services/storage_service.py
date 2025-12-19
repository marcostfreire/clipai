"""Storage service - handles file storage with Cloudflare R2."""

import os
import logging
from typing import Optional
import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)


class StorageService:
    """Storage service supporting local and Cloudflare R2 storage."""

    def __init__(
        self,
        r2_account_id: Optional[str] = None,
        r2_access_key_id: Optional[str] = None,
        r2_secret_access_key: Optional[str] = None,
        r2_bucket_name: Optional[str] = None,
        r2_public_url: Optional[str] = None,
        local_path: str = "./storage/videos",
    ):
        """
        Initialize storage service.

        Args:
            r2_account_id: Cloudflare account ID
            r2_access_key_id: R2 access key ID
            r2_secret_access_key: R2 secret access key
            r2_bucket_name: R2 bucket name
            r2_public_url: Public URL for R2 bucket (optional, for public access)
            local_path: Local storage path for temporary files
        """
        self.local_path = local_path
        self.r2_bucket_name = r2_bucket_name
        self.r2_public_url = r2_public_url
        self.use_r2 = all([r2_account_id, r2_access_key_id, r2_secret_access_key, r2_bucket_name])

        if self.use_r2:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=f"https://{r2_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=r2_access_key_id,
                aws_secret_access_key=r2_secret_access_key,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "adaptive"},
                ),
                region_name="auto",
            )
            logger.info(f"Storage initialized with Cloudflare R2 bucket: {r2_bucket_name}")
        else:
            self.s3_client = None
            logger.info(f"Storage initialized with local path: {local_path}")

        # Ensure local path exists for temp files
        os.makedirs(local_path, exist_ok=True)

    def get_local_path(self, video_id: str, filename: str = "") -> str:
        """Get local path for a video file (for temp processing)."""
        video_dir = os.path.join(self.local_path, video_id)
        os.makedirs(video_dir, exist_ok=True)
        if filename:
            return os.path.join(video_dir, filename)
        return video_dir

    def upload_file(self, local_path: str, video_id: str, filename: str) -> str:
        """
        Upload a file to storage.

        Args:
            local_path: Local file path
            video_id: Video ID
            filename: Filename to use in storage

        Returns:
            Storage path/URL
        """
        key = f"{video_id}/{filename}"

        if self.use_r2:
            try:
                # Determine content type
                content_type = self._get_content_type(filename)

                self.s3_client.upload_file(
                    local_path,
                    self.r2_bucket_name,
                    key,
                    ExtraArgs={"ContentType": content_type},
                )
                logger.info(f"Uploaded {filename} to R2: {key}")

                # Return public URL if available, otherwise return key
                if self.r2_public_url:
                    return f"{self.r2_public_url}/{key}"
                return f"r2://{self.r2_bucket_name}/{key}"

            except Exception as e:
                logger.error(f"Error uploading to R2: {e}")
                raise
        else:
            # Local storage - file is already in place
            return local_path

    def download_file(self, storage_path: str, local_path: str) -> str:
        """
        Download a file from storage to local path.

        Args:
            storage_path: Storage path/URL or R2 key
            local_path: Local destination path

        Returns:
            Local file path
        """
        if self.use_r2 and (storage_path.startswith("r2://") or storage_path.startswith(self.r2_public_url or "https://")):
            try:
                # Extract key from path
                if storage_path.startswith("r2://"):
                    key = storage_path.replace(f"r2://{self.r2_bucket_name}/", "")
                elif self.r2_public_url and storage_path.startswith(self.r2_public_url):
                    key = storage_path.replace(f"{self.r2_public_url}/", "")
                else:
                    key = storage_path

                # Ensure local directory exists
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                self.s3_client.download_file(self.r2_bucket_name, key, local_path)
                logger.info(f"Downloaded {key} from R2 to {local_path}")
                return local_path

            except Exception as e:
                logger.error(f"Error downloading from R2: {e}")
                raise
        else:
            # Local storage - file already exists
            return storage_path

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            storage_path: Storage path/URL

        Returns:
            True if deleted successfully
        """
        if self.use_r2 and (storage_path.startswith("r2://") or (self.r2_public_url and storage_path.startswith(self.r2_public_url))):
            try:
                if storage_path.startswith("r2://"):
                    key = storage_path.replace(f"r2://{self.r2_bucket_name}/", "")
                else:
                    key = storage_path.replace(f"{self.r2_public_url}/", "")

                self.s3_client.delete_object(Bucket=self.r2_bucket_name, Key=key)
                logger.info(f"Deleted {key} from R2")
                return True

            except Exception as e:
                logger.error(f"Error deleting from R2: {e}")
                return False
        else:
            # Local storage
            if os.path.exists(storage_path):
                os.remove(storage_path)
                logger.info(f"Deleted local file: {storage_path}")
                return True
            return False

    def delete_video_folder(self, video_id: str) -> bool:
        """
        Delete all files for a video.

        Args:
            video_id: Video ID

        Returns:
            True if deleted successfully
        """
        if self.use_r2:
            try:
                # List all objects with video_id prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=self.r2_bucket_name,
                    Prefix=f"{video_id}/",
                )

                if "Contents" in response:
                    objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
                    if objects:
                        self.s3_client.delete_objects(
                            Bucket=self.r2_bucket_name,
                            Delete={"Objects": objects},
                        )
                        logger.info(f"Deleted {len(objects)} files for video {video_id} from R2")

                return True

            except Exception as e:
                logger.error(f"Error deleting video folder from R2: {e}")
                return False

        # Also clean up local temp files
        local_dir = os.path.join(self.local_path, video_id)
        if os.path.exists(local_dir):
            import shutil
            shutil.rmtree(local_dir)
            logger.info(f"Deleted local folder: {local_dir}")

        return True

    def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists in storage."""
        if self.use_r2 and (storage_path.startswith("r2://") or (self.r2_public_url and storage_path.startswith(self.r2_public_url))):
            try:
                if storage_path.startswith("r2://"):
                    key = storage_path.replace(f"r2://{self.r2_bucket_name}/", "")
                else:
                    key = storage_path.replace(f"{self.r2_public_url}/", "")

                self.s3_client.head_object(Bucket=self.r2_bucket_name, Key=key)
                return True
            except:
                return False
        else:
            return os.path.exists(storage_path)

    def get_presigned_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """
        Get a presigned URL for a file (for secure access).

        Args:
            storage_path: Storage path
            expires_in: URL expiration in seconds

        Returns:
            Presigned URL or original path
        """
        if self.use_r2:
            try:
                if storage_path.startswith("r2://"):
                    key = storage_path.replace(f"r2://{self.r2_bucket_name}/", "")
                elif self.r2_public_url and storage_path.startswith(self.r2_public_url):
                    # Already a public URL
                    return storage_path
                else:
                    key = storage_path

                url = self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.r2_bucket_name, "Key": key},
                    ExpiresIn=expires_in,
                )
                return url

            except Exception as e:
                logger.error(f"Error generating presigned URL: {e}")
                return storage_path

        return storage_path

    def get_public_url(self, video_id: str, filename: str) -> str:
        """Get the public URL for a file."""
        if self.use_r2 and self.r2_public_url:
            return f"{self.r2_public_url}/{video_id}/{filename}"
        return os.path.join(self.local_path, video_id, filename)

    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        content_types = {
            "mp4": "video/mp4",
            "webm": "video/webm",
            "mov": "video/quicktime",
            "avi": "video/x-msvideo",
            "mkv": "video/x-matroska",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "ass": "text/x-ass",
            "srt": "text/srt",
        }
        return content_types.get(ext, "application/octet-stream")


# Global instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        from ..config import settings
        _storage_service = StorageService(
            r2_account_id=getattr(settings, "r2_account_id", None),
            r2_access_key_id=getattr(settings, "r2_access_key_id", None),
            r2_secret_access_key=getattr(settings, "r2_secret_access_key", None),
            r2_bucket_name=getattr(settings, "r2_bucket_name", None),
            r2_public_url=getattr(settings, "r2_public_url", None),
            local_path=settings.storage_path,
        )
    return _storage_service
