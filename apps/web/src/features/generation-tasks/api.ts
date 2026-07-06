import { apiGet } from "@/lib/api-client";

import type { GenerationTaskSummaryListResponse } from "./types";

export const generationTaskKeys = {
  all: (projectId: string) => ["projects", projectId, "generation-tasks"] as const,
  lists: (projectId: string) => [...generationTaskKeys.all(projectId), "list"] as const
};

export function fetchGenerationTasks(
  projectId: string
): Promise<GenerationTaskSummaryListResponse> {
  return apiGet<GenerationTaskSummaryListResponse>(
    `/api/projects/${projectId}/generation-tasks`
  );
}
