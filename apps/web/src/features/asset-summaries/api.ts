import { apiGet } from "@/lib/api-client";

import type {
  CharacterAssetSummary,
  SceneAssetSummary,
  ShotAssetSummary
} from "./types";

export const assetSummaryKeys = {
  character: (projectId: string, characterId: string) =>
    ["projects", projectId, "asset-summary", "character", characterId] as const,
  scene: (projectId: string, sceneId: string) =>
    ["projects", projectId, "asset-summary", "scene", sceneId] as const,
  shot: (projectId: string, shotId: string) =>
    ["projects", projectId, "asset-summary", "shot", shotId] as const
};

export function fetchCharacterAssetSummary(
  projectId: string,
  characterId: string
): Promise<CharacterAssetSummary> {
  return apiGet<CharacterAssetSummary>(
    `/api/projects/${projectId}/characters/${characterId}/asset-summary`
  );
}

export function fetchSceneAssetSummary(
  projectId: string,
  sceneId: string
): Promise<SceneAssetSummary> {
  return apiGet<SceneAssetSummary>(
    `/api/projects/${projectId}/scenes/${sceneId}/asset-summary`
  );
}

export function fetchShotAssetSummary(
  projectId: string,
  shotId: string
): Promise<ShotAssetSummary> {
  return apiGet<ShotAssetSummary>(`/api/projects/${projectId}/shots/${shotId}/asset-summary`);
}
