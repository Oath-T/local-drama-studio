import logging
import mimetypes
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.character import CharacterErrorCode
from app.domain.media_asset import (
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_IMAGE_MIME_TYPES,
    ALLOWED_VIDEO_EXTENSIONS,
    ALLOWED_VIDEO_MIME_TYPES,
)

CHARACTER_ERROR_MESSAGES = {
    CharacterErrorCode.IMAGE_EXTENSION_NOT_ALLOWED: "仅支持 JPG、PNG 和 WEBP 图片。",
    CharacterErrorCode.IMAGE_TOO_LARGE: "图片文件不能超过 15 MB。",
    CharacterErrorCode.IMAGE_INVALID: "图片文件已损坏或无法识别。",
    CharacterErrorCode.IMAGE_UPLOAD_FAILED: "图片上传失败，请重试。",
    CharacterErrorCode.FILE_NOT_FOUND: "媒体文件不存在或已被删除。",
}

HTTP_422 = 422
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredImage:
    original_filename: str
    stored_filename: str
    relative_path: str
    thumbnail_relative_path: str
    mime_type: str
    extension: str
    size_bytes: int
    width: int
    height: int
    sha256: str


@dataclass(frozen=True)
class StoredVideo:
    original_filename: str
    stored_filename: str
    relative_path: str
    mime_type: str
    extension: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ImageFileMetadata:
    mime_type: str
    extension: str
    size_bytes: int
    width: int
    height: int
    sha256: str


class MediaStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def store_reference_image(
        self,
        project_id: str,
        character_id: str,
        look_id: str,
        upload: UploadFile,
    ) -> StoredImage:
        relative_dir = Path("projects") / project_id / "media" / "references"
        return await self._store_image(upload, relative_dir)

    async def store_scene_reference_image(
        self,
        project_id: str,
        scene_id: str,
        state_id: str,
        upload: UploadFile,
    ) -> StoredImage:
        relative_dir = Path("projects") / project_id / "media" / "scene-references"
        return await self._store_image(upload, relative_dir)

    async def store_project_input_image(
        self,
        project_id: str,
        upload: UploadFile,
    ) -> StoredImage:
        relative_dir = Path("projects") / project_id / "media" / "video-inputs"
        return await self._store_image(upload, relative_dir)

    def store_generated_keyframe_image(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        mime_type_hint: str | None,
    ) -> StoredImage:
        relative_dir = Path("projects") / project_id / "media" / "generated-keyframes"
        return self._store_image_bytes(filename, content, mime_type_hint, relative_dir)

    def store_generated_video(
        self,
        project_id: str,
        filename: str,
        content: bytes,
        mime_type_hint: str | None,
    ) -> StoredVideo:
        relative_dir = Path("projects") / project_id / "media" / "generated-videos"
        return self._store_video_bytes(filename, content, mime_type_hint, relative_dir)

    def project_export_path(self, project_id: str, export_id: str, filename: str) -> Path:
        relative_path = Path("projects") / project_id / "exports" / export_id / filename
        return self.resolve_relative_path(relative_path.as_posix(), must_exist=False)

    def project_export_segments_dir(self, project_id: str, export_id: str) -> Path:
        relative_path = Path("projects") / project_id / "exports" / export_id / "segments"
        return self.resolve_relative_path(relative_path.as_posix(), must_exist=False)

    def generated_video_poster_relative_path(self, project_id: str, video_output_id: str) -> str:
        return (
            Path("projects")
            / project_id
            / "media"
            / "generated-video-posters"
            / f"{video_output_id}.png"
        ).as_posix()

    def generated_video_poster_path(self, project_id: str, video_output_id: str) -> Path:
        return self.resolve_relative_path(
            self.generated_video_poster_relative_path(project_id, video_output_id),
            must_exist=False,
        )

    def register_project_export_video(
        self,
        project_id: str,
        export_id: str,
        path: Path,
    ) -> StoredVideo:
        expected_prefix = (Path("projects") / project_id / "exports" / export_id).as_posix()
        relative_path = self._relative_to_storage(path).as_posix()
        if not relative_path.startswith(f"{expected_prefix}/"):
            raise_media_error(CharacterErrorCode.FILE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        safe_path = self.resolve_relative_path(
            relative_path,
            must_exist=True,
        )
        original_filename = "final.mp4"
        detected_mime_type = mimetypes.guess_type(original_filename)[0] or "video/mp4"
        if detected_mime_type not in ALLOWED_VIDEO_MIME_TYPES:
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)
        content = safe_path.read_bytes()
        max_bytes = self.settings.generated_video_max_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise_media_error(
                CharacterErrorCode.IMAGE_TOO_LARGE,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        return StoredVideo(
            original_filename=f"project-export-{export_id}.mp4",
            stored_filename=safe_path.name,
            relative_path=relative_path,
            mime_type=detected_mime_type,
            extension="mp4",
            size_bytes=len(content),
            sha256=sha256(content).hexdigest(),
        )

    async def _store_image(self, upload: UploadFile, relative_dir: Path) -> StoredImage:
        original_filename = Path(upload.filename or "image").name
        extension = self._get_extension(original_filename)
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise_media_error(
                CharacterErrorCode.IMAGE_EXTENSION_NOT_ALLOWED,
                HTTP_422,
            )

        content = await upload.read()
        max_bytes = self.settings.max_image_upload_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise_media_error(
                CharacterErrorCode.IMAGE_TOO_LARGE,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        digest = sha256(content).hexdigest()
        try:
            image = Image.open(BytesIO(content))
            image.verify()
            image = Image.open(BytesIO(content))
            image_format = image.format
            image = ImageOps.exif_transpose(image)
        except (UnidentifiedImageError, OSError):
            raise_media_error(
                CharacterErrorCode.IMAGE_INVALID,
                HTTP_422,
            )

        mime_type = Image.MIME.get(image_format or "")
        if (
            mime_type not in ALLOWED_IMAGE_MIME_TYPES
            or upload.content_type not in ALLOWED_IMAGE_MIME_TYPES
        ):
            raise_media_error(
                CharacterErrorCode.IMAGE_INVALID,
                HTTP_422,
            )

        width, height = image.size
        asset_id = str(uuid4())
        normalized_extension = "jpg" if extension == "jpeg" else extension
        stored_filename = f"{asset_id}.{normalized_extension}"
        thumbnail_filename = f"{asset_id}_thumb.webp"
        original_relative_path = relative_dir / stored_filename
        thumbnail_relative_path = relative_dir / thumbnail_filename
        original_path = self.resolve_relative_path(
            original_relative_path.as_posix(),
            must_exist=False,
        )
        thumbnail_path = self.resolve_relative_path(
            thumbnail_relative_path.as_posix(),
            must_exist=False,
        )
        original_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            image.save(original_path)
            thumbnail = image.copy()
            thumbnail.thumbnail(
                (self.settings.thumbnail_max_size, self.settings.thumbnail_max_size)
            )
            thumbnail.save(thumbnail_path, format="WEBP", quality=82)
        except OSError:
            self.delete_relative_file(original_relative_path.as_posix())
            self.delete_relative_file(thumbnail_relative_path.as_posix())
            raise_media_error(
                CharacterErrorCode.IMAGE_UPLOAD_FAILED,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return StoredImage(
            original_filename=original_filename,
            stored_filename=stored_filename,
            relative_path=original_relative_path.as_posix(),
            thumbnail_relative_path=thumbnail_relative_path.as_posix(),
            mime_type=mime_type,
            extension=normalized_extension,
            size_bytes=len(content),
            width=width,
            height=height,
            sha256=digest,
        )

    def _store_image_bytes(
        self,
        filename: str,
        content: bytes,
        mime_type_hint: str | None,
        relative_dir: Path,
    ) -> StoredImage:
        original_filename = Path(filename or "generated-keyframe.png").name
        extension = self._get_extension(original_filename) or "png"
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise_media_error(CharacterErrorCode.IMAGE_EXTENSION_NOT_ALLOWED, HTTP_422)

        max_bytes = self.settings.generated_output_max_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise_media_error(
                CharacterErrorCode.IMAGE_TOO_LARGE,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        digest = sha256(content).hexdigest()
        try:
            image = Image.open(BytesIO(content))
            image.verify()
            image = Image.open(BytesIO(content))
            image_format = image.format
            image = ImageOps.exif_transpose(image)
        except (UnidentifiedImageError, OSError):
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)

        detected_mime_type = Image.MIME.get(image_format or "")
        if detected_mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)
        if mime_type_hint and mime_type_hint not in ALLOWED_IMAGE_MIME_TYPES:
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)

        width, height = image.size
        asset_id = str(uuid4())
        normalized_extension = "jpg" if extension == "jpeg" else extension
        stored_filename = f"{asset_id}.{normalized_extension}"
        thumbnail_filename = f"{asset_id}_thumb.webp"
        original_relative_path = relative_dir / stored_filename
        thumbnail_relative_path = relative_dir / thumbnail_filename
        original_path = self.resolve_relative_path(
            original_relative_path.as_posix(),
            must_exist=False,
        )
        thumbnail_path = self.resolve_relative_path(
            thumbnail_relative_path.as_posix(),
            must_exist=False,
        )
        original_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            image.save(original_path)
            thumbnail = image.copy()
            thumbnail.thumbnail(
                (self.settings.thumbnail_max_size, self.settings.thumbnail_max_size)
            )
            thumbnail.save(thumbnail_path, format="WEBP", quality=82)
        except OSError:
            self.delete_relative_file(original_relative_path.as_posix())
            self.delete_relative_file(thumbnail_relative_path.as_posix())
            raise_media_error(
                CharacterErrorCode.IMAGE_UPLOAD_FAILED,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return StoredImage(
            original_filename=original_filename,
            stored_filename=stored_filename,
            relative_path=original_relative_path.as_posix(),
            thumbnail_relative_path=thumbnail_relative_path.as_posix(),
            mime_type=detected_mime_type,
            extension=normalized_extension,
            size_bytes=len(content),
            width=width,
            height=height,
            sha256=digest,
        )

    def _store_video_bytes(
        self,
        filename: str,
        content: bytes,
        mime_type_hint: str | None,
        relative_dir: Path,
    ) -> StoredVideo:
        original_filename = Path(filename or "generated-video.mp4").name
        extension = self._get_extension(original_filename)
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise_media_error(CharacterErrorCode.IMAGE_EXTENSION_NOT_ALLOWED, HTTP_422)

        max_bytes = self.settings.generated_video_max_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise_media_error(
                CharacterErrorCode.IMAGE_TOO_LARGE,
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        detected_mime_type = mimetypes.guess_type(original_filename)[0]
        if detected_mime_type not in ALLOWED_VIDEO_MIME_TYPES:
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)
        if mime_type_hint and mime_type_hint not in ALLOWED_VIDEO_MIME_TYPES:
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)

        digest = sha256(content).hexdigest()
        asset_id = str(uuid4())
        stored_filename = f"{asset_id}.{extension}"
        original_relative_path = relative_dir / stored_filename
        original_path = self.resolve_relative_path(
            original_relative_path.as_posix(),
            must_exist=False,
        )
        original_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            original_path.write_bytes(content)
        except OSError:
            self.delete_relative_file(original_relative_path.as_posix())
            raise_media_error(
                CharacterErrorCode.IMAGE_UPLOAD_FAILED,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return StoredVideo(
            original_filename=original_filename,
            stored_filename=stored_filename,
            relative_path=original_relative_path.as_posix(),
            mime_type=detected_mime_type,
            extension=extension,
            size_bytes=len(content),
            sha256=digest,
        )

    def resolve_relative_path(self, relative_path: str, must_exist: bool = True) -> Path:
        root = self.settings.resolved_storage_dir.resolve()
        target = (root / relative_path).resolve()
        if root not in target.parents and target != root:
            raise_media_error(CharacterErrorCode.FILE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        if must_exist and not target.exists():
            raise_media_error(CharacterErrorCode.FILE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return target

    def inspect_image_file(self, relative_path: str) -> ImageFileMetadata:
        path = self.resolve_relative_path(relative_path, must_exist=True)
        try:
            content = path.read_bytes()
            image = Image.open(BytesIO(content))
            image.verify()
            image = Image.open(BytesIO(content))
            image_format = image.format
            image = ImageOps.exif_transpose(image)
        except (OSError, UnidentifiedImageError):
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)
        mime_type = Image.MIME.get(image_format or "")
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)
        extension = (image_format or "").lower()
        if extension == "jpeg":
            extension = "jpg"
        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise_media_error(CharacterErrorCode.IMAGE_INVALID, HTTP_422)
        width, height = image.size
        return ImageFileMetadata(
            mime_type=mime_type,
            extension=extension,
            size_bytes=len(content),
            width=width,
            height=height,
            sha256=sha256(content).hexdigest(),
        )

    def _relative_to_storage(self, path: Path) -> Path:
        root = self.settings.resolved_storage_dir.resolve()
        target = path.resolve()
        if root not in target.parents and target != root:
            raise_media_error(CharacterErrorCode.FILE_NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return target.relative_to(root)

    def delete_relative_file(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        try:
            path = self.resolve_relative_path(relative_path, must_exist=False)
            if path.exists():
                path.unlink()
        except OSError:
            raise_media_error(
                CharacterErrorCode.IMAGE_UPLOAD_FAILED,
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete_relative_file_safely(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        try:
            self.delete_relative_file(relative_path)
        except AppError:
            logger.warning("Failed to clean stored media file after database delete.")

    @staticmethod
    def _get_extension(filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")
        return suffix


def raise_media_error(code: CharacterErrorCode, http_status: int) -> None:
    raise AppError(
        code=code.value,
        message=CHARACTER_ERROR_MESSAGES[code],
        status_code=http_status,
    )
