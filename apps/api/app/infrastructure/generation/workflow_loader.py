import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import Settings, get_settings
from app.domain.keyframe_generation import KeyframeGenerationErrorCode
from app.infrastructure.generation.base import GenerationProviderRuntimeError


class WorkflowBinding(BaseModel):
    node_id: str
    input: str


class WorkflowManifest(BaseModel):
    workflow_id: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=120)
    version: str = Field(min_length=1, max_length=60)
    schema_version: int = 1
    workflow_file: str = Field(min_length=1, max_length=255)
    required_capabilities: list[str] = Field(default_factory=list)
    required_node_types: list[str] = Field(default_factory=list)
    required_models: list[dict[str, str]] = Field(default_factory=list)
    parameter_bindings: dict[str, WorkflowBinding]
    output_node_ids: list[str] = Field(min_length=1)
    allowed_samplers: list[str] = Field(default_factory=list)
    allowed_schedulers: list[str] = Field(default_factory=list)
    default_sampler_name: str | None = None
    default_scheduler_name: str | None = None
    uses_reference_inputs: bool = False

    @field_validator("workflow_file")
    @classmethod
    def workflow_file_must_be_relative(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("workflow_file must be a safe relative path")
        return value


class LoadedWorkflow(BaseModel):
    manifest: WorkflowManifest
    workflow: dict[str, Any]


class WorkflowRegistry:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def list_workflows(self) -> list[LoadedWorkflow]:
        workflows: list[LoadedWorkflow] = []
        for manifest_path in sorted(self._workflow_dir().glob("*.manifest.json")):
            if manifest_path.name.startswith("video_"):
                continue
            workflows.append(self._load_manifest_path(manifest_path))
        return workflows

    def get_workflow(self, workflow_id: str) -> LoadedWorkflow:
        for workflow in self.list_workflows():
            if workflow.manifest.workflow_id == workflow_id:
                return workflow
        raise GenerationProviderRuntimeError(
            KeyframeGenerationErrorCode.WORKFLOW_NOT_FOUND,
            "Workflow is not registered.",
        )

    def _load_manifest_path(self, manifest_path: Path) -> LoadedWorkflow:
        try:
            manifest = WorkflowManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
            workflow_path = (manifest_path.parent / manifest.workflow_file).resolve()
            if self._workflow_dir().resolve() not in workflow_path.parents:
                raise ValueError("workflow path escapes workflow directory")
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            if not isinstance(workflow, dict):
                raise ValueError("workflow must be a JSON object")
            self._ensure_no_absolute_paths(workflow)
            self._validate_workflow_shape(manifest, workflow)
            return LoadedWorkflow(manifest=manifest, workflow=workflow)
        except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.WORKFLOW_MANIFEST_INVALID,
                "Workflow manifest is invalid.",
            ) from exc

    def _workflow_dir(self) -> Path:
        return self.settings.resolved_comfyui_workflow_dir

    def _validate_workflow_shape(
        self, manifest: WorkflowManifest, workflow: dict[str, Any]
    ) -> None:
        for node_id, binding in [
            (binding.node_id, binding) for binding in manifest.parameter_bindings.values()
        ]:
            node = workflow.get(node_id)
            if not isinstance(node, dict):
                raise GenerationProviderRuntimeError(
                    KeyframeGenerationErrorCode.WORKFLOW_NODE_MISSING,
                    "Workflow node is missing.",
                )
            inputs = node.get("inputs")
            if not isinstance(inputs, dict) or binding.input not in inputs:
                raise GenerationProviderRuntimeError(
                    KeyframeGenerationErrorCode.WORKFLOW_INPUT_MISSING,
                    "Workflow input is missing.",
                )
        for node_id in manifest.output_node_ids:
            node = workflow.get(node_id)
            if not isinstance(node, dict):
                raise GenerationProviderRuntimeError(
                    KeyframeGenerationErrorCode.WORKFLOW_NODE_MISSING,
                    "Workflow output node is missing.",
                )

    def _ensure_no_absolute_paths(self, value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                self._ensure_no_absolute_paths(item)
            return
        if isinstance(value, list):
            for item in value:
                self._ensure_no_absolute_paths(item)
            return
        if isinstance(value, str):
            normalized = value.replace("\\", "/")
            if normalized.startswith("/") or ":/" in normalized:
                raise ValueError("workflow must not contain absolute paths")
