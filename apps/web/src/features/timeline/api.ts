import { apiGet, apiPost } from "@/lib/api-client";

import type {
  ProjectExport,
  ProjectExportCreateRequest,
  ProjectExportListResponse,
  ProjectExportStartResponse,
  ProjectTimeline
} from "./types";

export const timelineKeys = {
  all: (projectId: string) => ["projects", projectId, "timeline-export"] as const,
  timeline: (projectId: string) => [...timelineKeys.all(projectId), "timeline"] as const,
  exports: (projectId: string) => [...timelineKeys.all(projectId), "exports"] as const
};

export function fetchProjectTimeline(projectId: string): Promise<ProjectTimeline> {
  return apiGet<ProjectTimeline>(`/api/projects/${projectId}/timeline`);
}

export function fetchProjectExports(projectId: string): Promise<ProjectExportListResponse> {
  return apiGet<ProjectExportListResponse>(`/api/projects/${projectId}/exports`);
}

export function createProjectExport(
  projectId: string,
  payload: ProjectExportCreateRequest
): Promise<ProjectExport> {
  return apiPost<ProjectExport, ProjectExportCreateRequest>(
    `/api/projects/${projectId}/exports`,
    payload
  );
}

export function markProjectExportReady(
  projectId: string,
  exportId: string
): Promise<ProjectExport> {
  return apiPost<ProjectExport, Record<string, never>>(
    `/api/projects/${projectId}/exports/${exportId}/mark-ready`,
    {}
  );
}

export function startProjectExport(
  projectId: string,
  exportId: string
): Promise<ProjectExportStartResponse> {
  return apiPost<ProjectExportStartResponse, Record<string, never>>(
    `/api/projects/${projectId}/exports/${exportId}/start`,
    {}
  );
}
