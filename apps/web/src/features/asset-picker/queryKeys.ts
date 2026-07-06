import type { PickerOptionsParams } from "./types";

export const assetPickerKeys = {
  all: (projectId: string) => ["projects", projectId, "asset-picker"] as const,
  options: (params: PickerOptionsParams) =>
    [
      ...assetPickerKeys.all(params.projectId),
      "options",
      params.scope,
      params.assetType,
      params.shotId ?? "",
      params.q ?? "",
      params.limit ?? ""
    ] as const
};
