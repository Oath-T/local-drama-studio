import { apiGet } from "@/lib/api-client";

import type { PickerOptionListResponse, PickerOptionsParams } from "./types";

export function fetchPickerOptions(
  params: PickerOptionsParams
): Promise<PickerOptionListResponse> {
  const query = new URLSearchParams({
    scope: params.scope,
    asset_type: params.assetType
  });
  if (params.shotId) query.set("shot_id", params.shotId);
  if (params.characterId) query.set("character_id", params.characterId);
  if (params.sceneId) query.set("scene_id", params.sceneId);
  if (params.shotCharacterId) query.set("shot_character_id", params.shotCharacterId);
  if (params.taskId) query.set("task_id", params.taskId);
  if (params.source) query.set("source", params.source);
  if (params.q?.trim()) query.set("q", params.q.trim());
  if (params.limit) query.set("limit", String(params.limit));

  return apiGet<PickerOptionListResponse>(
    `/api/projects/${params.projectId}/assets/picker-options?${query.toString()}`
  );
}
