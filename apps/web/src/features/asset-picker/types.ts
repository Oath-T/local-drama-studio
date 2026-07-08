export type PickerScope = "project" | "shot";
export type PickerAssetType =
  | "character"
  | "scene"
  | "frame_image"
  | "character_look"
  | "scene_state"
  | "reference_image";
export type PickerSourceKind =
  | "character"
  | "scene"
  | "character_look"
  | "scene_state"
  | "character_reference"
  | "scene_reference"
  | "shot_reference"
  | "keyframe_output"
  | "media_asset";

export interface PickerOptionSource {
  kind: PickerSourceKind;
  label: string;
}

export interface PickerOptionItem {
  id: string;
  type: PickerAssetType;
  name: string;
  description: string | null;
  thumbnail_url: string | null;
  content_url: string | null;
  badges: string[];
  source: PickerOptionSource;
  is_selected: boolean;
  is_adopted: boolean;
  metadata: Record<string, string | number | boolean | null>;
}

export interface PickerOptionListResponse {
  items: PickerOptionItem[];
  total: number;
}

export interface PickerOptionsParams {
  projectId: string;
  scope: PickerScope;
  assetType: PickerAssetType;
  shotId?: string;
  characterId?: string;
  sceneId?: string;
  shotCharacterId?: string;
  taskId?: string;
  source?: "shot_context";
  q?: string;
  limit?: number;
}
