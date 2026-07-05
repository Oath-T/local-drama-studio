import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from app.core.config import Settings
from app.domain.video_generation import VideoGenerationErrorCode, VideoInputRole, VideoWorkflowMode
from app.infrastructure.generation.base import GenerationProviderRuntimeError, ProviderUploadedImage

MAX_WORKFLOW_STRING_LENGTH = 10000
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"[A-Za-z]:\\")
UNIX_USER_PATH_RE = re.compile(r"(^|[\s\"'])/(Users|home)/")
DATA_URI_RE = re.compile(r"data:(image|video)/", re.IGNORECASE)


class VideoWorkflowBinding(BaseModel):
    node_id: str
    input_name: str = Field(validation_alias=AliasChoices("input_name", "input"))


class VideoWorkflowComputedBinding(VideoWorkflowBinding):
    type: Literal["duration_seconds_times_fps_plus_one"]


class VideoWorkflowManifest(BaseModel):
    schema_version: int = 1
    workflow_id: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    workflow_file: str = Field(min_length=1, max_length=200)
    provider: str = "comfyui"
    mode: VideoWorkflowMode = VideoWorkflowMode.SINGLE_IMAGE_TO_VIDEO
    required_input_roles: list[VideoInputRole] = Field(
        default_factory=lambda: [VideoInputRole.START_FRAME]
    )
    image_input_bindings: dict[VideoInputRole, VideoWorkflowBinding] = Field(default_factory=dict)
    image_input_subfolder_bindings: dict[VideoInputRole, VideoWorkflowBinding] = Field(
        default_factory=dict
    )
    image_input_type_bindings: dict[VideoInputRole, VideoWorkflowBinding] = Field(
        default_factory=dict
    )
    required_node_types: list[str] = Field(default_factory=list)
    parameter_bindings: dict[str, VideoWorkflowBinding] = Field(default_factory=dict)
    computed_parameter_bindings: dict[str, VideoWorkflowComputedBinding] = Field(
        default_factory=dict
    )
    input_image_binding: VideoWorkflowBinding | None = None
    input_image_subfolder_binding: VideoWorkflowBinding | None = None
    input_image_type_binding: VideoWorkflowBinding | None = None
    output_node_ids: list[str] = Field(default_factory=list)
    output_file_keys: list[str] = Field(
        default_factory=lambda: ["videos", "gifs", "files", "images"]
    )
    allowed_output_extensions: list[str] = Field(
        default_factory=lambda: ["mp4", "webm", "mov", "gif"]
    )

    @field_validator("workflow_file")
    @classmethod
    def workflow_file_must_be_relative(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("workflow_file must be a relative filename")
        return value

    @model_validator(mode="after")
    def normalize_legacy_input_binding(self) -> "VideoWorkflowManifest":
        if self.input_image_binding and VideoInputRole.START_FRAME not in self.image_input_bindings:
            self.image_input_bindings[VideoInputRole.START_FRAME] = self.input_image_binding
        if (
            self.input_image_subfolder_binding
            and VideoInputRole.START_FRAME not in self.image_input_subfolder_bindings
        ):
            self.image_input_subfolder_bindings[VideoInputRole.START_FRAME] = (
                self.input_image_subfolder_binding
            )
        if (
            self.input_image_type_binding
            and VideoInputRole.START_FRAME not in self.image_input_type_bindings
        ):
            self.image_input_type_bindings[VideoInputRole.START_FRAME] = (
                self.input_image_type_binding
            )
        return self


@dataclass(frozen=True)
class LoadedVideoWorkflow:
    manifest: VideoWorkflowManifest
    workflow: dict[str, Any] | None
    workflow_path: Path | None
    missing_requirements: list[str] = field(default_factory=list)

    @property
    def available_locally(self) -> bool:
        return self.workflow is not None and not self.missing_requirements


@dataclass(frozen=True)
class VideoWorkflowMappingValues:
    positive_prompt: str
    negative_prompt: str | None
    width: int
    height: int
    duration_seconds: int
    fps: int
    seed: int
    motion_strength: float | None
    camera_motion: str | None
    input_images: dict[VideoInputRole, ProviderUploadedImage]


class VideoWorkflowRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.workflow_dir = settings.resolved_comfyui_workflow_dir

    def list_workflows(self) -> list[LoadedVideoWorkflow]:
        manifests = sorted(
            self.workflow_dir.glob("video_*.manifest.json"),
            key=lambda path: path.name,
        )
        return [self._load_manifest(path) for path in manifests]

    def get_workflow(self, workflow_id: str) -> LoadedVideoWorkflow:
        for workflow in self.list_workflows():
            if workflow.manifest.workflow_id == workflow_id:
                return workflow
        raise GenerationProviderRuntimeError(
            VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
            "Video workflow was not found.",
        )

    def build_workflow(
        self,
        workflow: LoadedVideoWorkflow,
        values: VideoWorkflowMappingValues,
    ) -> dict[str, object]:
        if workflow.workflow is None:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                "Video workflow file is missing.",
            )
        payload = copy.deepcopy(workflow.workflow)
        for role in workflow.manifest.required_input_roles:
            uploaded = values.input_images.get(role)
            if uploaded is None:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                    "Video workflow input image is missing.",
                )
            self._apply(
                payload,
                workflow.manifest.image_input_bindings.get(role),
                uploaded.filename,
            )
            self._apply(
                payload,
                workflow.manifest.image_input_subfolder_bindings.get(role),
                uploaded.subfolder,
            )
            self._apply(
                payload,
                workflow.manifest.image_input_type_bindings.get(role),
                uploaded.input_type,
            )
        scalar_values: dict[str, object] = {
            "positive_prompt": values.positive_prompt,
            "width": values.width,
            "height": values.height,
            "duration_seconds": values.duration_seconds,
            "fps": values.fps,
            "seed": values.seed,
            "motion_strength": values.motion_strength if values.motion_strength is not None else 0,
            "camera_motion": values.camera_motion or "",
        }
        if values.negative_prompt is not None:
            scalar_values["negative_prompt"] = values.negative_prompt
        for key, binding in workflow.manifest.parameter_bindings.items():
            if key in scalar_values:
                self._apply(payload, binding, scalar_values[key])
        for binding in workflow.manifest.computed_parameter_bindings.values():
            self._apply(payload, binding, self._computed_value(binding.type, values))
        return payload

    def _load_manifest(self, path: Path) -> LoadedVideoWorkflow:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            manifest = VideoWorkflowManifest.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                "Video workflow manifest is invalid.",
            ) from exc
        workflow_path = self.workflow_dir / manifest.workflow_file
        if not workflow_path.exists():
            return LoadedVideoWorkflow(
                manifest=manifest,
                workflow=None,
                workflow_path=None,
                missing_requirements=["workflow_file_missing"],
            )
        try:
            workflow_raw = json.loads(workflow_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                "Video workflow JSON is invalid.",
            ) from exc
        if not isinstance(workflow_raw, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                "Video workflow JSON must be an object.",
            )
        missing = [
            *self._workflow_safety_issues(workflow_raw),
            *self._missing_bindings(workflow_raw, manifest),
        ]
        return LoadedVideoWorkflow(
            manifest=manifest,
            workflow=workflow_raw,
            workflow_path=workflow_path,
            missing_requirements=missing,
        )

    @staticmethod
    def _missing_bindings(
        workflow: dict[str, Any],
        manifest: VideoWorkflowManifest,
    ) -> list[str]:
        missing: list[str] = []
        if (
            manifest.mode == VideoWorkflowMode.FIRST_LAST_FRAME_TO_VIDEO
            and VideoInputRole.END_FRAME not in manifest.required_input_roles
        ):
            missing.append("workflow_required_role_missing:end_frame")
        for role in manifest.required_input_roles:
            if role not in manifest.image_input_bindings:
                missing.append(f"workflow_input_role_binding_missing:{role.value}")
        bindings = list(manifest.parameter_bindings.items())
        bindings.extend(
            (f"computed_parameter:{name}", binding)
            for name, binding in manifest.computed_parameter_bindings.items()
        )
        for role, binding in manifest.image_input_bindings.items():
            bindings.append((f"image_input:{role.value}", binding))
        for role, binding in manifest.image_input_subfolder_bindings.items():
            bindings.append((f"image_input_subfolder:{role.value}", binding))
        for role, binding in manifest.image_input_type_bindings.items():
            bindings.append((f"image_input_type:{role.value}", binding))
        optional_bindings = [
            ("input_image", manifest.input_image_binding),
            ("input_image_subfolder", manifest.input_image_subfolder_binding),
            ("input_image_type", manifest.input_image_type_binding),
        ]
        bindings.extend((name, binding) for name, binding in optional_bindings if binding)
        for name, binding in bindings:
            if binding.node_id not in workflow:
                missing.append(f"workflow_node_missing:{binding.node_id}")
                continue
            inputs = workflow.get(binding.node_id, {}).get("inputs")
            if not isinstance(inputs, dict) or binding.input_name not in inputs:
                missing.append(f"workflow_input_missing:{name}")
        for node_id in manifest.output_node_ids:
            if node_id not in workflow:
                missing.append(f"workflow_output_node_missing:{node_id}")
                continue
            if "SaveVideo" in manifest.required_node_types:
                class_type = workflow.get(node_id, {}).get("class_type")
                if class_type != "SaveVideo":
                    missing.append(f"workflow_output_node_type_invalid:{node_id}")
        class_types = {
            node.get("class_type")
            for node in workflow.values()
            if isinstance(node, dict) and isinstance(node.get("class_type"), str)
        }
        for node_type in manifest.required_node_types:
            if node_type not in class_types:
                missing.append(f"workflow_required_node_type_missing:{node_type}")
        return sorted(set(missing))

    @staticmethod
    def _workflow_safety_issues(workflow: dict[str, Any]) -> list[str]:
        issues: list[str] = []
        if any(key in workflow for key in ("nodes", "links", "groups")):
            issues.append("workflow_ui_format")
        for value in _walk_workflow_values(workflow):
            if not isinstance(value, str):
                continue
            if len(value) > MAX_WORKFLOW_STRING_LENGTH:
                issues.append("workflow_unsafe_long_string")
            if WINDOWS_ABSOLUTE_PATH_RE.search(value) or UNIX_USER_PATH_RE.search(value):
                issues.append("workflow_unsafe_absolute_path")
            if "base64," in value.lower() or DATA_URI_RE.search(value):
                issues.append("workflow_unsafe_data_uri")
        return sorted(set(issues))

    @staticmethod
    def _computed_value(
        binding_type: str,
        values: VideoWorkflowMappingValues,
    ) -> int:
        if binding_type == "duration_seconds_times_fps_plus_one":
            if values.duration_seconds <= 0 or values.fps <= 0:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                    "Video workflow computed parameter is invalid.",
                )
            length = values.duration_seconds * values.fps + 1
            if not isinstance(length, int) or length <= 1:
                raise GenerationProviderRuntimeError(
                    VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                    "Video workflow computed parameter is invalid.",
                )
            return length
        raise GenerationProviderRuntimeError(
            VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
            "Video workflow computed parameter type is unsupported.",
        )

    @staticmethod
    def _apply(
        payload: dict[str, Any],
        binding: VideoWorkflowBinding | VideoWorkflowComputedBinding | None,
        value: object,
    ) -> None:
        if binding is None:
            return
        node = payload.get(binding.node_id)
        if not isinstance(node, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                "Video workflow node is missing.",
            )
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            raise GenerationProviderRuntimeError(
                VideoGenerationErrorCode.WORKFLOW_UNAVAILABLE,
                "Video workflow input map is missing.",
            )
        inputs[binding.input_name] = value


def _walk_workflow_values(value: object) -> list[object]:
    if isinstance(value, dict):
        values: list[object] = []
        for item in value.values():
            values.extend(_walk_workflow_values(item))
        return values
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_walk_workflow_values(item))
        return values
    return [value]
