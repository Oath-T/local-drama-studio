from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.video_generation import VideoGenerationErrorCode
from app.infrastructure.generation.base import (
    GenerationProviderHealth,
    GenerationProviderRuntimeError,
    ProviderJobStatus,
    ProviderOutputFile,
    ProviderSubmission,
    ProviderUploadedImage,
    VideoProviderRequest,
)


class ComfyUIVideoGenerationProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.comfyui_base_url.rstrip("/")
        self.timeout = httpx.Timeout(
            settings.comfyui_timeout_seconds,
            connect=min(10, settings.comfyui_timeout_seconds),
            read=settings.comfyui_timeout_seconds,
        )

    async def check_health(self) -> GenerationProviderHealth:
        try:
            async with self._client() as client:
                response = await client.get("/system_stats")
                response.raise_for_status()
                if not isinstance(response.json(), dict):
                    raise ValueError
        except Exception:
            return GenerationProviderHealth(False, "comfyui", "offline")
        return GenerationProviderHealth(True, "comfyui", "online")

    async def get_required_node_types(self) -> set[str]:
        try:
            async with self._client() as client:
                response = await client.get("/object_info")
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_UNAVAILABLE, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "Invalid ComfyUI object_info response.",
            )
        return {str(key) for key in data}

    async def upload_input_image(
        self,
        *,
        filename: str,
        content: bytes,
        mime_type: str | None,
    ) -> ProviderUploadedImage:
        try:
            async with self._client() as client:
                response = await client.post(
                    "/upload/image",
                    data={"type": "input", "overwrite": "true"},
                    files={"image": (filename, content, mime_type or "application/octet-stream")},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(VideoGenerationErrorCode.REFERENCE_UPLOAD_FAILED, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "Invalid ComfyUI upload response.",
            )
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            name = data.get("filename")
        if not isinstance(name, str) or not name.strip():
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "ComfyUI upload response did not include a file name.",
            )
        subfolder = data.get("subfolder")
        input_type = data.get("type")
        return ProviderUploadedImage(
            filename=name,
            subfolder=subfolder if isinstance(subfolder, str) else "",
            input_type=input_type if isinstance(input_type, str) else "input",
        )

    async def submit(self, request: VideoProviderRequest) -> ProviderSubmission:
        try:
            async with self._client() as client:
                response = await client.post(
                    "/prompt",
                    json={"prompt": request.workflow, "client_id": request.client_id},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_SUBMISSION_FAILED, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "Invalid ComfyUI prompt response.",
            )
        node_errors = data.get("node_errors")
        if isinstance(node_errors, dict) and node_errors:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_NODE_ERROR,
                "ComfyUI node validation failed.",
            )
        prompt_id = data.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id.strip():
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "ComfyUI prompt response did not include prompt_id.",
            )
        return ProviderSubmission(prompt_id)

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus:
        history = await self._get_history(provider_job_id)
        history_item = self._history_item(history, provider_job_id)
        if history_item is not None:
            if self._history_failed(history_item):
                return ProviderJobStatus(
                    "failed",
                    VideoGenerationErrorCode.COMFYUI_EXECUTION_FAILED,
                    "ComfyUI execution failed.",
                )
            if self._history_has_outputs(history_item):
                return ProviderJobStatus("completed")
        queue = await self._get_queue()
        if self._queue_contains(queue.get("queue_running"), provider_job_id):
            return ProviderJobStatus("running")
        if self._queue_contains(queue.get("queue_pending"), provider_job_id):
            return ProviderJobStatus("queued")
        return ProviderJobStatus("waiting")

    async def fetch_video_outputs(
        self,
        provider_job_id: str,
        *,
        output_file_keys: list[str],
        allowed_extensions: list[str],
    ) -> list[ProviderOutputFile]:
        history = await self._get_history(provider_job_id)
        history_item = self._history_item(history, provider_job_id)
        if history_item is None or not self._history_has_outputs(history_item):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.OUTPUT_MISSING,
                "ComfyUI output is missing.",
            )
        refs = self._output_file_refs(history_item, output_file_keys, allowed_extensions)
        if not refs:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.OUTPUT_MISSING,
                "ComfyUI did not return an allowed video output.",
            )
        outputs: list[ProviderOutputFile] = []
        async with self._client() as client:
            for ref in refs:
                try:
                    response = await client.get(
                        "/view",
                        params={
                            "filename": ref["filename"],
                            "subfolder": ref["subfolder"],
                            "type": ref["type"],
                        },
                    )
                    response.raise_for_status()
                except httpx.TimeoutException as exc:
                    raise self._error(VideoGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
                except Exception as exc:
                    raise self._error(VideoGenerationErrorCode.OUTPUT_DOWNLOAD_FAILED, exc) from exc
                content = response.content
                max_bytes = self.settings.generated_video_max_mb * 1024 * 1024
                if len(content) > max_bytes:
                    raise GenerationProviderRuntimeError(
                        VideoGenerationErrorCode.OUTPUT_SAVE_FAILED,
                        "Generated video exceeded the configured size limit.",
                    )
                outputs.append(
                    ProviderOutputFile(
                        filename=ref["filename"],
                        subfolder=ref["subfolder"],
                        output_type=ref["type"],
                        mime_type=response.headers.get("content-type", "").split(";")[0] or None,
                        content=content,
                    )
                )
        return outputs

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def _get_history(self, provider_job_id: str) -> dict[str, Any]:
        try:
            async with self._client() as client:
                response = await client.get(f"/history/{provider_job_id}")
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_UNAVAILABLE, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "Invalid ComfyUI history response.",
            )
        return data

    async def _get_queue(self) -> dict[str, Any]:
        try:
            async with self._client() as client:
                response = await client.get("/queue")
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(VideoGenerationErrorCode.COMFYUI_UNAVAILABLE, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "Invalid ComfyUI queue response.",
            )
        return data

    @staticmethod
    def _history_item(history: Mapping[str, Any], provider_job_id: str) -> dict[str, Any] | None:
        item = history.get(provider_job_id)
        return item if isinstance(item, dict) else None

    @staticmethod
    def _history_failed(history_item: Mapping[str, Any]) -> bool:
        status = history_item.get("status")
        if isinstance(status, dict) and status.get("status_str") in {"error", "failed"}:
            return True
        for message in history_item.get("messages", []) or []:
            if isinstance(message, list) and message and message[0] == "execution_error":
                return True
        return False

    @staticmethod
    def _history_has_outputs(history_item: Mapping[str, Any]) -> bool:
        outputs = history_item.get("outputs")
        return isinstance(outputs, dict) and any(
            isinstance(item, dict) for item in outputs.values()
        )

    @staticmethod
    def _output_file_refs(
        history_item: Mapping[str, Any],
        output_file_keys: list[str],
        allowed_extensions: list[str],
    ) -> list[dict[str, str]]:
        allowed = {item.lower().lstrip(".") for item in allowed_extensions}
        refs: list[dict[str, str]] = []
        outputs = history_item.get("outputs")
        if not isinstance(outputs, dict):
            return refs
        for output in outputs.values():
            if not isinstance(output, dict):
                continue
            for key in output_file_keys:
                files = output.get(key)
                if not isinstance(files, list):
                    continue
                for file_item in files:
                    if not isinstance(file_item, dict):
                        continue
                    filename = file_item.get("filename")
                    if not isinstance(filename, str) or not filename.strip():
                        continue
                    extension = Path(filename).suffix.lower().lstrip(".")
                    if extension not in allowed:
                        continue
                    subfolder = file_item.get("subfolder")
                    output_type = file_item.get("type")
                    refs.append(
                        {
                            "filename": filename,
                            "subfolder": subfolder if isinstance(subfolder, str) else "",
                            "type": output_type if isinstance(output_type, str) else "output",
                        }
                    )
        return refs

    def _queue_contains(self, value: object, provider_job_id: str) -> bool:
        if isinstance(value, str):
            return value == provider_job_id
        if isinstance(value, dict):
            return any(self._queue_contains(item, provider_job_id) for item in value.values())
        if isinstance(value, list):
            return any(self._queue_contains(item, provider_job_id) for item in value)
        return False

    @staticmethod
    def _error(
        code: VideoGenerationErrorCode,
        exc: Exception,
    ) -> GenerationProviderRuntimeError:
        return GenerationProviderRuntimeError(code, "ComfyUI communication failed.")
