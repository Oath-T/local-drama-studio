import { apiGet, apiPost } from "@/lib/api-client";

import type {
  AnalysisConfirmInput,
  AnalysisConfirmResponse,
  LatestVisionAnalysisTaskResponse,
  VisionAnalysisTask
} from "./types";

export const visionAnalysisKeys = {
  task: (projectId: string, taskId: string) =>
    ["projects", projectId, "vision-analysis", "tasks", taskId] as const,
  characterLatest: (
    projectId: string,
    characterId: string,
    lookId: string,
    referenceId: string
  ) =>
    [
      "projects",
      projectId,
      "characters",
      characterId,
      "looks",
      lookId,
      "references",
      referenceId,
      "analysis",
      "latest-task"
    ] as const,
  sceneLatest: (projectId: string, sceneId: string, stateId: string, referenceId: string) =>
    [
      "projects",
      projectId,
      "scenes",
      sceneId,
      "states",
      stateId,
      "references",
      referenceId,
      "analysis",
      "latest-task"
    ] as const
};

export function fetchVisionAnalysisTask(
  projectId: string,
  taskId: string
): Promise<VisionAnalysisTask> {
  return apiGet<VisionAnalysisTask>(`/api/projects/${projectId}/vision-analysis/tasks/${taskId}`);
}

export function startCharacterReferenceAnalysis(
  projectId: string,
  characterId: string,
  lookId: string,
  referenceId: string
): Promise<VisionAnalysisTask> {
  return apiPost<VisionAnalysisTask, Record<string, never>>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references/${referenceId}/analysis/tasks`,
    {}
  );
}

export function fetchLatestCharacterReferenceAnalysisTask(
  projectId: string,
  characterId: string,
  lookId: string,
  referenceId: string
): Promise<LatestVisionAnalysisTaskResponse> {
  return apiGet<LatestVisionAnalysisTaskResponse>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references/${referenceId}/analysis/latest-task`
  );
}

export function confirmCharacterReferenceAnalysis(
  projectId: string,
  characterId: string,
  lookId: string,
  referenceId: string,
  payload: AnalysisConfirmInput
): Promise<AnalysisConfirmResponse> {
  return apiPost<AnalysisConfirmResponse, AnalysisConfirmInput>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references/${referenceId}/analysis/confirm`,
    payload
  );
}

export function rejectCharacterReferenceAnalysis(
  projectId: string,
  characterId: string,
  lookId: string,
  referenceId: string
): Promise<AnalysisConfirmResponse> {
  return apiPost<AnalysisConfirmResponse, Record<string, never>>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references/${referenceId}/analysis/reject`,
    {}
  );
}

export function startSceneReferenceAnalysis(
  projectId: string,
  sceneId: string,
  stateId: string,
  referenceId: string
): Promise<VisionAnalysisTask> {
  return apiPost<VisionAnalysisTask, Record<string, never>>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references/${referenceId}/analysis/tasks`,
    {}
  );
}

export function fetchLatestSceneReferenceAnalysisTask(
  projectId: string,
  sceneId: string,
  stateId: string,
  referenceId: string
): Promise<LatestVisionAnalysisTaskResponse> {
  return apiGet<LatestVisionAnalysisTaskResponse>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references/${referenceId}/analysis/latest-task`
  );
}

export function confirmSceneReferenceAnalysis(
  projectId: string,
  sceneId: string,
  stateId: string,
  referenceId: string,
  payload: AnalysisConfirmInput
): Promise<AnalysisConfirmResponse> {
  return apiPost<AnalysisConfirmResponse, AnalysisConfirmInput>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references/${referenceId}/analysis/confirm`,
    payload
  );
}

export function rejectSceneReferenceAnalysis(
  projectId: string,
  sceneId: string,
  stateId: string,
  referenceId: string
): Promise<AnalysisConfirmResponse> {
  return apiPost<AnalysisConfirmResponse, Record<string, never>>(
    `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references/${referenceId}/analysis/reject`,
    {}
  );
}
