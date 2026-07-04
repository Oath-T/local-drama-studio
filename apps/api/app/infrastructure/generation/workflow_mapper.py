from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.domain.keyframe_generation import KeyframeGenerationErrorCode
from app.infrastructure.generation.base import GenerationProviderRuntimeError
from app.infrastructure.generation.workflow_loader import LoadedWorkflow, WorkflowManifest


@dataclass(frozen=True)
class WorkflowMappingValues:
    positive_prompt: str
    negative_prompt: str | None
    width: int
    height: int
    seed: int
    steps: int
    guidance_scale: float
    sampler_name: str | None
    scheduler_name: str | None
    checkpoint_name: str


class WorkflowMapper:
    def build_workflow(
        self,
        loaded_workflow: LoadedWorkflow,
        values: WorkflowMappingValues,
    ) -> dict[str, Any]:
        manifest = loaded_workflow.manifest
        workflow = deepcopy(loaded_workflow.workflow)
        sampler_name = self._resolve_sampler(manifest, values.sampler_name)
        scheduler_name = self._resolve_scheduler(manifest, values.scheduler_name)
        mapped_values: dict[str, object] = {
            "positive_prompt": values.positive_prompt,
            "negative_prompt": values.negative_prompt or "",
            "width": values.width,
            "height": values.height,
            "seed": values.seed,
            "steps": values.steps,
            "guidance_scale": values.guidance_scale,
            "sampler_name": sampler_name,
            "scheduler_name": scheduler_name,
            "checkpoint_name": values.checkpoint_name,
        }
        for parameter, value in mapped_values.items():
            binding = manifest.parameter_bindings.get(parameter)
            if binding is None:
                continue
            node = workflow.get(binding.node_id)
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
            inputs[binding.input] = value
        return workflow

    @staticmethod
    def _resolve_sampler(manifest: WorkflowManifest, value: str | None) -> str:
        if value is None or value.strip() == "":
            if manifest.default_sampler_name:
                return manifest.default_sampler_name
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.WORKFLOW_SAMPLER_UNSUPPORTED,
                "Workflow sampler is not configured.",
            )
        normalized = value.strip()
        if manifest.allowed_samplers and normalized not in manifest.allowed_samplers:
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.WORKFLOW_SAMPLER_UNSUPPORTED,
                "Workflow sampler is not supported.",
            )
        return normalized

    @staticmethod
    def _resolve_scheduler(manifest: WorkflowManifest, value: str | None) -> str:
        if value is None or value.strip() == "":
            if manifest.default_scheduler_name:
                return manifest.default_scheduler_name
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.WORKFLOW_SCHEDULER_UNSUPPORTED,
                "Workflow scheduler is not configured.",
            )
        normalized = value.strip()
        if manifest.allowed_schedulers and normalized not in manifest.allowed_schedulers:
            raise GenerationProviderRuntimeError(
                KeyframeGenerationErrorCode.WORKFLOW_SCHEDULER_UNSUPPORTED,
                "Workflow scheduler is not supported.",
            )
        return normalized
