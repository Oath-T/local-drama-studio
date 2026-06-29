import base64
import logging
from typing import Any

from pydantic import ValidationError

from app.api.schemas.vision_analysis import (
    CharacterVisionAnalysisSuggestion,
    SceneVisionAnalysisSuggestion,
)
from app.domain.vision_analysis import VisionAnalysisErrorCode, VisionProviderRuntimeError
from app.infrastructure.vision.base import (
    CharacterAnalysisContext,
    SceneAnalysisContext,
    VisionImageInput,
)

logger = logging.getLogger(__name__)


class OpenAIVisionAnalysisProvider:
    def __init__(self, api_key: str, model_name: str, timeout_seconds: int) -> None:
        self.model_name = model_name
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.PROVIDER_NOT_CONFIGURED,
                "OpenAI SDK is not installed.",
                retryable=False,
            ) from exc
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout_seconds)

    async def analyze_character_reference(
        self,
        image: VisionImageInput,
        context: CharacterAnalysisContext,
    ) -> CharacterVisionAnalysisSuggestion:
        return await self._parse_response(
            image=image,
            prompt=_character_prompt(context),
            schema=CharacterVisionAnalysisSuggestion,
        )

    async def analyze_scene_reference(
        self,
        image: VisionImageInput,
        context: SceneAnalysisContext,
    ) -> SceneVisionAnalysisSuggestion:
        return await self._parse_response(
            image=image,
            prompt=_scene_prompt(context),
            schema=SceneVisionAnalysisSuggestion,
        )

    async def _parse_response(
        self,
        image: VisionImageInput,
        prompt: str,
        schema: type[CharacterVisionAnalysisSuggestion] | type[SceneVisionAnalysisSuggestion],
    ) -> CharacterVisionAnalysisSuggestion | SceneVisionAnalysisSuggestion:
        data_url = _data_url(image)
        try:
            response = await self.client.responses.parse(
                model=self.model_name,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
                text_format=schema,
                store=False,
            )
        except Exception as exc:
            raise _wrap_openai_error(exc) from exc

        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            try:
                parsed = response.output[0].content[0].parsed
            except (AttributeError, IndexError, TypeError) as exc:
                logger.warning("OpenAI vision response did not include parsed output.")
                raise VisionProviderRuntimeError(
                    VisionAnalysisErrorCode.OUTPUT_INVALID,
                    "Vision provider did not return parsed structured output.",
                    retryable=False,
                ) from exc
        try:
            return schema.model_validate(parsed)
        except ValidationError as exc:
            raise VisionProviderRuntimeError(
                VisionAnalysisErrorCode.OUTPUT_INVALID,
                "Vision provider output failed local validation.",
                retryable=False,
            ) from exc


def _data_url(image: VisionImageInput) -> str:
    encoded = base64.b64encode(image.content).decode("ascii")
    return f"data:{image.mime_type};base64,{encoded}"


def _character_prompt(context: CharacterAnalysisContext) -> str:
    return f"""
你是本地短剧制作工具中的参考图元数据分析器。只根据图片中可见的信息输出结构化建议。

角色：{context.character_name}
造型：{context.look_name}
现有描述：{context.existing_description or "无"}

要求：
- 不识别真实身份或姓名。
- 不猜测种族、国籍、健康状况等敏感属性。
- 不与明星或公众人物做相似性比较。
- 不描述不可见或不确定事实，不确定时使用 unknown 或空摘要。
- 不输出推理过程。
- identity_anchor_recommended 只是建议，不能自动成为正式身份基准图。
""".strip()


def _scene_prompt(context: SceneAnalysisContext) -> str:
    return f"""
你是本地短剧制作工具中的场景参考图元数据分析器。只根据图片中可见的信息输出结构化建议。

场景：{context.scene_name}
场景状态：{context.state_name}
现有描述：{context.existing_description or "无"}

要求：
- 不推断私人地址。
- 不猜测画面外空间。
- 不把不确定地点描述为具体真实地点。
- 不输出推理过程。
- 时间、天气、灯光只作为 detected_* 建议展示，不自动修改场景状态。
- spatial_anchor_recommended 与 empty_plate_recommended 只是建议，不能自动成为正式标记。
""".strip()


def _wrap_openai_error(exc: Exception) -> VisionProviderRuntimeError:
    status_code = getattr(exc, "status_code", None)
    error_type = exc.__class__.__name__.lower()
    if status_code in (401, 403):
        code = VisionAnalysisErrorCode.PROVIDER_AUTH_FAILED
        retryable = False
    elif status_code == 429:
        code = VisionAnalysisErrorCode.PROVIDER_RATE_LIMITED
        retryable = True
    elif isinstance(status_code, int) and 500 <= status_code < 600:
        code = VisionAnalysisErrorCode.PROVIDER_UNAVAILABLE
        retryable = True
    elif "timeout" in error_type:
        code = VisionAnalysisErrorCode.PROVIDER_TIMEOUT
        retryable = True
    elif "refusal" in error_type or "content" in error_type:
        code = VisionAnalysisErrorCode.PROVIDER_REFUSED
        retryable = False
    else:
        code = VisionAnalysisErrorCode.ANALYSIS_FAILED
        retryable = False
    return VisionProviderRuntimeError(code, "Vision provider request failed.", retryable)


def validate_openai_sdk_shape() -> dict[str, Any]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key="validation-placeholder")
    responses = getattr(client, "responses", None)
    parse = getattr(responses, "parse", None)
    if responses is None or parse is None:
        raise RuntimeError("Installed OpenAI SDK does not expose AsyncOpenAI.responses.parse")
    return {"async_client": True, "responses_parse": True}
