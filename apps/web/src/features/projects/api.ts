import { apiDelete, apiGet, apiPatch, apiPost } from "@/lib/api-client";

import type {
  Project,
  ProjectCreateInput,
  ProjectListResponse,
  ProjectUpdateInput
} from "./types";

export const projectKeys = {
  all: ["projects"] as const,
  lists: () => [...projectKeys.all, "list"] as const,
  detail: (projectId: string) => [...projectKeys.all, "detail", projectId] as const
};

export function fetchProjects(): Promise<ProjectListResponse> {
  return apiGet<ProjectListResponse>("/api/projects");
}

export function fetchProject(projectId: string): Promise<Project> {
  return apiGet<Project>(`/api/projects/${projectId}`);
}

export function createProject(payload: ProjectCreateInput): Promise<Project> {
  return apiPost<Project, ProjectCreateInput>("/api/projects", payload);
}

export function updateProject(projectId: string, payload: ProjectUpdateInput): Promise<Project> {
  return apiPatch<Project, ProjectUpdateInput>(`/api/projects/${projectId}`, payload);
}

export function deleteProject(projectId: string): Promise<void> {
  return apiDelete(`/api/projects/${projectId}`);
}
