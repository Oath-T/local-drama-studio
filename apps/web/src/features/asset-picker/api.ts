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
  if (params.q?.trim()) query.set("q", params.q.trim());
  if (params.limit) query.set("limit", String(params.limit));

  return apiGet<PickerOptionListResponse>(
    `/api/projects/${params.projectId}/assets/picker-options?${query.toString()}`
  );
}
