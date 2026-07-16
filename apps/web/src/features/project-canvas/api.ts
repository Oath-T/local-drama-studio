import {
  apiDeleteJson,
  apiDeleteWithBody,
  apiGet,
  apiPatch,
  apiPost,
  apiPut
} from "@/lib/api-client";

import type {
  CanvasBindingApplyInput,
  CanvasBindingDeleteInput,
  CanvasBindingPreview,
  CanvasBindingPreviewInput,
  CanvasBusinessRelationsPreview,
  CanvasEdgeCreateInput,
  CanvasEntityBatchInput,
  CanvasEntityBatchPreview,
  CanvasNodeCreateInput,
  CanvasNodePatchInput,
  ProjectCanvas,
  ProjectCanvasSaveInput
} from "./types";

export const projectCanvasKeys = {
  all: (projectId: string) => ["projects", projectId, "canvas"] as const,
  detail: (projectId: string) => [...projectCanvasKeys.all(projectId), "detail"] as const,
  batchPreview: (projectId: string) =>
    [...projectCanvasKeys.all(projectId), "entity-batch-preview"] as const,
  businessRelationsPreview: (projectId: string) =>
    [...projectCanvasKeys.all(projectId), "business-relations-preview"] as const
};

export function fetchProjectCanvas(projectId: string): Promise<ProjectCanvas> {
  return apiGet<ProjectCanvas>(`/api/projects/${projectId}/canvas`);
}

export function saveProjectCanvas(
  projectId: string,
  payload: ProjectCanvasSaveInput
): Promise<ProjectCanvas> {
  return apiPut<ProjectCanvas, ProjectCanvasSaveInput>(
    `/api/projects/${projectId}/canvas`,
    payload
  );
}

export function createCanvasNode(
  projectId: string,
  payload: CanvasNodeCreateInput
): Promise<ProjectCanvas> {
  return apiPost<ProjectCanvas, CanvasNodeCreateInput>(
    `/api/projects/${projectId}/canvas/nodes`,
    payload
  );
}

export function patchCanvasNode(
  projectId: string,
  nodeId: string,
  payload: CanvasNodePatchInput
): Promise<ProjectCanvas> {
  return apiPatch<ProjectCanvas, CanvasNodePatchInput>(
    `/api/projects/${projectId}/canvas/nodes/${nodeId}`,
    payload
  );
}

export function deleteCanvasNode(
  projectId: string,
  nodeId: string,
  expectedRevision: number
): Promise<ProjectCanvas> {
  return apiDeleteJson<ProjectCanvas>(
    `/api/projects/${projectId}/canvas/nodes/${nodeId}?expected_revision=${expectedRevision}`
  );
}

export function createCanvasEdge(
  projectId: string,
  payload: CanvasEdgeCreateInput
): Promise<ProjectCanvas> {
  return apiPost<ProjectCanvas, CanvasEdgeCreateInput>(
    `/api/projects/${projectId}/canvas/edges`,
    payload
  );
}

export function deleteCanvasEdge(
  projectId: string,
  edgeId: string,
  expectedRevision: number
): Promise<ProjectCanvas> {
  return apiDeleteJson<ProjectCanvas>(
    `/api/projects/${projectId}/canvas/edges/${edgeId}?expected_revision=${expectedRevision}`
  );
}

export function fetchCanvasEntityBatchPreview(
  projectId: string
): Promise<CanvasEntityBatchPreview> {
  return apiGet<CanvasEntityBatchPreview>(
    `/api/projects/${projectId}/canvas/entity-batch-preview`
  );
}

export function addCanvasEntityBatch(
  projectId: string,
  payload: CanvasEntityBatchInput
): Promise<ProjectCanvas> {
  return apiPost<ProjectCanvas, CanvasEntityBatchInput>(
    `/api/projects/${projectId}/canvas/entity-batch`,
    payload
  );
}

export function previewCanvasBinding(
  projectId: string,
  payload: CanvasBindingPreviewInput
): Promise<CanvasBindingPreview> {
  return apiPost<CanvasBindingPreview, CanvasBindingPreviewInput>(
    `/api/projects/${projectId}/canvas/bindings/preview`,
    payload
  );
}

export function applyCanvasBinding(
  projectId: string,
  payload: CanvasBindingApplyInput
): Promise<ProjectCanvas> {
  return apiPost<ProjectCanvas, CanvasBindingApplyInput>(
    `/api/projects/${projectId}/canvas/bindings/apply`,
    payload
  );
}

export function deleteCanvasBinding(
  projectId: string,
  edgeId: string,
  payload: CanvasBindingDeleteInput
): Promise<ProjectCanvas> {
  return apiDeleteWithBody<ProjectCanvas, CanvasBindingDeleteInput>(
    `/api/projects/${projectId}/canvas/bindings/${edgeId}`,
    payload
  );
}

export function fetchCanvasBusinessRelationsPreview(
  projectId: string
): Promise<CanvasBusinessRelationsPreview> {
  return apiGet<CanvasBusinessRelationsPreview>(
    `/api/projects/${projectId}/canvas/import-business-relations/preview`
  );
}

export function importCanvasBusinessRelations(
  projectId: string,
  expectedRevision: number
): Promise<ProjectCanvas> {
  return apiPost<ProjectCanvas, Record<string, never>>(
    `/api/projects/${projectId}/canvas/import-business-relations?expected_revision=${expectedRevision}`,
    {}
  );
}
