from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import Settings
from app.domain.keyframe_generation import KeyframeGenerationErrorCode
from app.infrastructure.generation.base import (
    GenerationProviderHealth,
    GenerationProviderRuntimeError,
    KeyframeProviderRequest,
    ProviderJobStatus,
    ProviderOutputImage,
    ProviderSubmission,
)


class ComfyUIKeyframeGenerationProvider:
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
            return GenerationProviderHealth(
                available=False,
                provider="comfyui",
                status="offline",
            )
        return GenerationProviderHealth(available=True, provider="comfyui", status="online")

    async def get_required_node_types(self) -> set[str]:
        try:
            async with self._client() as client:
                response = await client.get("/object_info")
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_UNAVAILABLE, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "Invalid ComfyUI object_info response.",
            )
        return {str(key) for key in data.keys()}

    async def submit(self, request: KeyframeProviderRequest) -> ProviderSubmission:
        try:
            async with self._client() as client:
                response = await client.post(
                    "/prompt",
                    json={"prompt": request.workflow, "client_id": request.client_id},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_SUBMISSION_FAILED, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "Invalid ComfyUI prompt response.",
            )
        node_errors = data.get("node_errors")
        if isinstance(node_errors, dict) and node_errors:
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_NODE_ERROR,
                "ComfyUI node validation failed.",
            )
        prompt_id = data.get("prompt_id")
        if not isinstance(prompt_id, str) or prompt_id.strip() == "":
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
                "ComfyUI prompt response did not include prompt_id.",
            )
        return ProviderSubmission(provider_job_id=prompt_id)

    async def get_status(self, provider_job_id: str) -> ProviderJobStatus:
        history = await self._get_history(provider_job_id)
        history_item = self._history_item(history, provider_job_id)
        if history_item is not None:
            if self._history_failed(history_item):
                return ProviderJobStatus(
                    status="failed",
                    error_code=KeyframeGenerationErrorCode.COMFYUI_EXECUTION_FAILED,
                    error_message="ComfyUI execution failed.",
                )
            if self._history_has_outputs(history_item):
                return ProviderJobStatus(status="completed")

        queue = await self._get_queue()
        if self._queue_contains(queue.get("queue_running"), provider_job_id):
            return ProviderJobStatus(status="running")
        if self._queue_contains(queue.get("queue_pending"), provider_job_id):
            return ProviderJobStatus(status="queued")
        return ProviderJobStatus(status="waiting")

    async def fetch_outputs(self, provider_job_id: str) -> list[ProviderOutputImage]:
        history = await self._get_history(provider_job_id)
        history_item = self._history_item(history, provider_job_id)
        if history_item is None or not self._history_has_outputs(history_item):
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_OUTPUT_MISSING,
                "ComfyUI output is missing.",
            )
        image_refs = self._output_image_refs(history_item)
        outputs: list[ProviderOutputImage] = []
        async with self._client() as client:
            for image in image_refs:
                try:
                    response = await client.get(
                        "/view",
                        params={
                            "filename": image["filename"],
                            "subfolder": image["subfolder"],
                            "type": image["type"],
                        },
                    )
                    response.raise_for_status()
                except httpx.TimeoutException as exc:
                    raise self._error(KeyframeGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
                except Exception as exc:
                    raise self._error(
                        KeyframeGenerationErrorCode.COMFYUI_OUTPUT_DOWNLOAD_FAILED, exc
                    ) from exc
                content = response.content
                max_bytes = self.settings.generated_output_max_mb * 1024 * 1024
                if len(content) > max_bytes:
                    raise GenerationProviderRuntimeError(
                        KeyframeGenerationErrorCode.GENERATED_MEDIA_SAVE_FAILED,
                        "Generated output exceeded the configured size limit.",
                    )
                outputs.append(
                    ProviderOutputImage(
                        filename=image["filename"],
                        subfolder=image["subfolder"],
                        output_type=image["type"],
                        mime_type=response.headers.get("content-type", "").split(";")[0] or None,
                        content=content,
                    )
                )
        return outputs

    async def cancel(self, provider_job_id: str) -> None:
        return None

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def _get_history(self, provider_job_id: str) -> dict[str, Any]:
        try:
            async with self._client() as client:
                response = await client.get(f"/history/{provider_job_id}")
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_UNAVAILABLE, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
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
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_TIMEOUT, exc) from exc
        except Exception as exc:
            raise self._error(KeyframeGenerationErrorCode.COMFYUI_UNAVAILABLE, exc) from exc
        if not isinstance(data, dict):
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.COMFYUI_INVALID_RESPONSE,
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
        if not isinstance(outputs, dict):
            return False
        return any(isinstance(output, dict) and output.get("images") for output in outputs.values())

    @staticmethod
    def _output_image_refs(history_item: Mapping[str, Any]) -> list[dict[str, str]]:
        images: list[dict[str, str]] = []
        outputs = history_item.get("outputs")
        if not isinstance(outputs, dict):
            return images
        for output in outputs.values():
            if not isinstance(output, dict):
                continue
            for image in output.get("images", []) or []:
                if not isinstance(image, dict):
                    continue
                filename = image.get("filename")
                if not isinstance(filename, str) or filename.strip() == "":
                    continue
                subfolder = image.get("subfolder")
                output_type = image.get("type")
                images.append(
                    {
                        "filename": filename,
                        "subfolder": subfolder if isinstance(subfolder, str) else "",
                        "type": output_type if isinstance(output_type, str) else "output",
                    }
                )
        return images

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
        code: KeyframeGenerationErrorCode,
        exc: Exception,
    ) -> GenerationProviderRuntimeError:
        return GenerationProviderRuntimeError(code, "ComfyUI communication failed.")
