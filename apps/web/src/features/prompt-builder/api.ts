import { apiPost } from "@/lib/api-client";
import { shotKeys } from "@/features/shots/api";

import type { PromptDraftRequest, PromptDraftResponse } from "./types";

export const promptDraftKeys = {
  draft: (projectId: string, shotId: string) => shotKeys.promptDraft(projectId, shotId)
};

export function buildPromptDraft(
  projectId: string,
  shotId: string,
  payload: PromptDraftRequest = {}
): Promise<PromptDraftResponse> {
  return apiPost<PromptDraftResponse, PromptDraftRequest>(
    `/api/projects/${projectId}/shots/${shotId}/prompt-draft`,
    payload
  );
}
