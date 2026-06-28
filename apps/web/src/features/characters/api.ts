import { apiDelete, apiGet, apiPatch, apiPost, apiPostForm } from "@/lib/api-client";

import type {
  Character,
  CharacterCreateInput,
  CharacterListResponse,
  CharacterLook,
  CharacterLookCreateInput,
  CharacterLookListResponse,
  CharacterLookUpdateInput,
  CharacterReference,
  CharacterReferenceListResponse,
  CharacterReferenceUpdateInput,
  CharacterUpdateInput,
  Expression,
  PoseType,
  ShotType,
  ViewAngle
} from "./types";

export const characterKeys = {
  all: (projectId: string) => ["projects", projectId, "characters"] as const,
  lists: (projectId: string) => [...characterKeys.all(projectId), "list"] as const,
  detail: (projectId: string, characterId: string) =>
    [...characterKeys.all(projectId), "detail", characterId] as const,
  looks: (projectId: string, characterId: string) =>
    [...characterKeys.detail(projectId, characterId), "looks"] as const,
  references: (projectId: string, characterId: string, lookId: string) =>
    [...characterKeys.looks(projectId, characterId), lookId, "references"] as const
};

export function fetchCharacters(projectId: string): Promise<CharacterListResponse> {
  return apiGet<CharacterListResponse>(`/api/projects/${projectId}/characters`);
}

export function fetchCharacter(projectId: string, characterId: string): Promise<Character> {
  return apiGet<Character>(`/api/projects/${projectId}/characters/${characterId}`);
}

export function createCharacter(
  projectId: string,
  payload: CharacterCreateInput
): Promise<Character> {
  return apiPost<Character, CharacterCreateInput>(
    `/api/projects/${projectId}/characters`,
    payload
  );
}

export function updateCharacter(
  projectId: string,
  characterId: string,
  payload: CharacterUpdateInput
): Promise<Character> {
  return apiPatch<Character, CharacterUpdateInput>(
    `/api/projects/${projectId}/characters/${characterId}`,
    payload
  );
}

export function deleteCharacter(projectId: string, characterId: string): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/characters/${characterId}`);
}

export function fetchLooks(
  projectId: string,
  characterId: string
): Promise<CharacterLookListResponse> {
  return apiGet<CharacterLookListResponse>(
    `/api/projects/${projectId}/characters/${characterId}/looks`
  );
}

export function createLook(
  projectId: string,
  characterId: string,
  payload: CharacterLookCreateInput
): Promise<CharacterLook> {
  return apiPost<CharacterLook, CharacterLookCreateInput>(
    `/api/projects/${projectId}/characters/${characterId}/looks`,
    payload
  );
}

export function updateLook(
  projectId: string,
  characterId: string,
  lookId: string,
  payload: CharacterLookUpdateInput
): Promise<CharacterLook> {
  return apiPatch<CharacterLook, CharacterLookUpdateInput>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}`,
    payload
  );
}

export function setDefaultLook(
  projectId: string,
  characterId: string,
  lookId: string
): Promise<CharacterLook> {
  return apiPost<CharacterLook, Record<string, never>>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/set-default`,
    {}
  );
}

export function deleteLook(
  projectId: string,
  characterId: string,
  lookId: string
): Promise<void> {
  return apiDelete(`/api/projects/${projectId}/characters/${characterId}/looks/${lookId}`);
}

export function fetchReferences(
  projectId: string,
  characterId: string,
  lookId: string
): Promise<CharacterReferenceListResponse> {
  return apiGet<CharacterReferenceListResponse>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references`
  );
}

export interface UploadReferenceInput {
  file: File;
  shot_type: ShotType;
  view_angle: ViewAngle;
  expression: Expression;
  pose_type: PoseType;
  tags: string;
  description: string;
  is_identity_anchor: boolean;
}

export function uploadReference(
  projectId: string,
  characterId: string,
  lookId: string,
  input: UploadReferenceInput
): Promise<CharacterReference> {
  const formData = new FormData();
  formData.append("file", input.file);
  formData.append("shot_type", input.shot_type);
  formData.append("view_angle", input.view_angle);
  formData.append("expression", input.expression);
  formData.append("pose_type", input.pose_type);
  formData.append("tags", input.tags);
  formData.append("description", input.description);
  formData.append("is_identity_anchor", String(input.is_identity_anchor));

  return apiPostForm<CharacterReference>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references`,
    formData
  );
}

export function updateReference(
  projectId: string,
  characterId: string,
  lookId: string,
  referenceId: string,
  payload: CharacterReferenceUpdateInput
): Promise<CharacterReference> {
  return apiPatch<CharacterReference, CharacterReferenceUpdateInput>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references/${referenceId}`,
    payload
  );
}

export function setPrimaryReference(
  projectId: string,
  characterId: string,
  lookId: string,
  referenceId: string
): Promise<CharacterReference> {
  return apiPost<CharacterReference, Record<string, never>>(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references/${referenceId}/set-primary`,
    {}
  );
}

export function deleteReference(
  projectId: string,
  characterId: string,
  lookId: string,
  referenceId: string
): Promise<void> {
  return apiDelete(
    `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references/${referenceId}`
  );
}
