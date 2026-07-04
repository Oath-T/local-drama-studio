import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import Settings
from app.domain.video_generation import VideoGenerationErrorCode
from app.infrastructure.generation.base import GenerationProviderRuntimeError, ProviderUploadedImage


class VideoWorkflowBinding(BaseModel):
    node_id: str
    input_name: str


class VideoWorkflowManifest(BaseModel):
    schema_version: int = 1
    workflow_id: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    workflow_file: str = Field(min_length=1, max_length=200)
    provider: str = "comfyui"
    required_node_types: list[str] = Field(default_factory=list)
    parameter_bindings: dict[str, VideoWorkflowBinding] = Field(default_factory=dict)
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
    input_image: ProviderUploadedImage


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
        self._apply(payload, workflow.manifest.input_image_binding, values.input_image.filename)
        self._apply(
            payload,
            workflow.manifest.input_image_subfolder_binding,
            values.input_image.subfolder,
        )
        self._apply(
            payload,
            workflow.manifest.input_image_type_binding,
            values.input_image.input_type,
        )
        scalar_values: dict[str, object] = {
            "positive_prompt": values.positive_prompt,
            "negative_prompt": values.negative_prompt or "",
            "width": values.width,
            "height": values.height,
            "duration_seconds": values.duration_seconds,
            "fps": values.fps,
            "seed": values.seed,
            "motion_strength": values.motion_strength if values.motion_strength is not None else 0,
            "camera_motion": values.camera_motion or "",
        }
        for key, binding in workflow.manifest.parameter_bindings.items():
            if key in scalar_values:
                self._apply(payload, binding, scalar_values[key])
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
        missing = self._missing_bindings(workflow_raw, manifest)
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
        bindings = list(manifest.parameter_bindings.items())
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
        return sorted(set(missing))

    @staticmethod
    def _apply(
        payload: dict[str, Any],
        binding: VideoWorkflowBinding | None,
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
