import { apiGet } from "@/lib/api-client";

import type { ProjectProductionStatus, ShotProductionStatus } from "./types";

export const productionStatusKeys = {
  all: (projectId: string) => ["projects", projectId, "production-status"] as const,
  project: (projectId: string) => [...productionStatusKeys.all(projectId), "project"] as const,
  shot: (projectId: string, shotId: string) =>
    [...productionStatusKeys.all(projectId), "shot", shotId] as const
};

export function fetchProjectProductionStatus(
  projectId: string
): Promise<ProjectProductionStatus> {
  return apiGet<ProjectProductionStatus>(`/api/projects/${projectId}/production-status`);
}

export function fetchShotProductionStatus(
  projectId: string,
  shotId: string
): Promise<ShotProductionStatus> {
  return apiGet<ShotProductionStatus>(
    `/api/projects/${projectId}/shots/${shotId}/production-status`
  );
}
