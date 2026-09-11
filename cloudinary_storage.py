"""Cloudinary-backed media storage for the Telegram stream bot.

The adapter intentionally keeps credentials in environment variables and returns
None on an upload failure so the bot can fall back to its Telegram stream URL.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Optional

import cloudinary
import cloudinary.utils
import cloudinary.uploader

log = logging.getLogger(__name__)


class CloudinaryStorage:
    def __init__(self) -> None:
        self.cloudinary_url = os.environ.get("CLOUDINARY_URL", "").strip()
        self.folder = os.environ.get("CLOUDINARY_FOLDER", "telegram-stream-bot").strip("/")
        self.chunk_size = max(5 * 1024 * 1024, int(os.environ.get("CLOUDINARY_CHUNK_SIZE", str(20 * 1024 * 1024))))
        self.enabled = bool(self.cloudinary_url)
        if self.enabled:
            parsed = urlparse(self.cloudinary_url)
            cloudinary.config(
                cloud_name=parsed.hostname,
                api_key=parsed.username,
                api_secret=parsed.password,
                secure=True,
            )
            log.info("Cloudinary media storage enabled (folder=%s)", self.folder)
        else:
            log.info("Cloudinary media storage disabled; Telegram streaming fallback is active")

    @staticmethod
    def _resource_type(mime_type: str, file_name: str) -> str:
        mime = (mime_type or mimetypes.guess_type(file_name)[0] or "").lower()
        return "video" if mime.startswith("video/") or mime.startswith("audio/") else "raw"

    def upload(self, local_path: str, *, public_id: str, mime_type: str = "", file_name: str = "") -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        resource_type = self._resource_type(mime_type, file_name or path.name)
        options: dict[str, Any] = {
            "resource_type": resource_type,
            "folder": self.folder,
            "public_id": public_id,
            "overwrite": True,
            "invalidate": True,
            "unique_filename": False,
            "use_filename": False,
            "context": {"source": "telegram", "original_name": file_name or path.name},
        }
        # upload_large uses the resumable/chunked endpoint and avoids loading the
        # whole file into memory, which is important on Render's small instances.
        result = cloudinary.uploader.upload_large(str(path), chunk_size=self.chunk_size, **options)
        return {
            "secure_url": result.get("secure_url") or result.get("url"),
            "public_id": result.get("public_id", ""),
            "resource_type": result.get("resource_type", resource_type),
            "bytes": int(result.get("bytes", 0) or 0),
            "format": result.get("format", ""),
        }

    def _delivery_url(self, public_id: str) -> str:
        parsed = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="raw",
            type="upload",
            secure=True,
        )
        return parsed[0]

    def restore_catalog(self, destination: str) -> bool:
        """Restore the latest catalog snapshot into the ephemeral runtime disk."""
        if not self.enabled:
            return False
        url = self._delivery_url(f"{self.folder}/catalog-db")
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            if not data or not data.startswith(b"SQLite format 3"):
                log.warning("Cloudinary catalog snapshot is missing or invalid")
                return False
            Path(destination).parent.mkdir(parents=True, exist_ok=True)
            Path(destination).write_bytes(data)
            log.info("Restored catalog snapshot from Cloudinary (%s bytes)", len(data))
            return True
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as error:
            log.info("No Cloudinary catalog snapshot available yet: %s", error)
            return False

    def sync_catalog(self, database_path: str) -> bool:
        """Upload the current SQLite catalog as one replaceable raw asset."""
        if not self.enabled:
            return False
        result = self.upload(
            database_path,
            public_id="catalog-db",
            mime_type="application/x-sqlite3",
            file_name="catalog.db",
        )
        return bool(result and result.get("secure_url"))

    async def upload_downloaded_media(
        self,
        client: Any,
        message: Any,
        *,
        chat_id: int,
        message_id: int,
        file_name: str,
        mime_type: str,
    ) -> Optional[dict[str, Any]]:
        """Download one Telegram message to a temporary path and upload it."""
        if not self.enabled:
            return None
        import asyncio
        import tempfile

        suffix = Path(file_name or "file").suffix
        tmp_path: Optional[str] = None
        try:
            tmp_path = str(Path(tempfile.gettempdir()) / f"telegram-upload-{chat_id}-{message_id}{suffix}")
            downloaded = await client.download_media(message, file_name=tmp_path)
            if not downloaded:
                raise RuntimeError("Telegram did not return a downloaded file path")
            public_id = f"chat_{chat_id}/message_{message_id}"
            return await asyncio.to_thread(
                self.upload,
                str(downloaded),
                public_id=public_id,
                mime_type=mime_type,
                file_name=file_name,
            )
        except Exception:
            log.exception("Cloudinary upload failed for Telegram message %s/%s", chat_id, message_id)
            return None
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    log.warning("Could not remove temporary upload file %s", tmp_path)
            if tmp_path and Path(tmp_path).exists():
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def storage_url(result: Optional[dict[str, Any]]) -> str:
        return str(result.get("secure_url", "")) if result else ""
