export type RoleType = "protagonist" | "antagonist" | "supporting" | "extra" | "other";
export type ShotType =
  | "face_closeup"
  | "closeup"
  | "upper_body"
  | "half_body"
  | "three_quarter"
  | "full_body"
  | "unknown";
export type ViewAngle =
  | "front"
  | "left_45"
  | "right_45"
  | "left_profile"
  | "right_profile"
  | "back"
  | "high_angle"
  | "low_angle"
  | "unknown";
export type Expression =
  | "neutral"
  | "happy"
  | "smile"
  | "sad"
  | "angry"
  | "shocked"
  | "fearful"
  | "crying"
  | "cold_smirk"
  | "serious"
  | "custom"
  | "unknown";
export type PoseType =
  | "standing"
  | "sitting"
  | "walking"
  | "looking_camera"
  | "looking_away"
  | "holding_object"
  | "custom"
  | "unknown";
export type AnalysisStatus = "not_analyzed" | "pending" | "completed" | "failed";
export type SuggestionReviewStatus =
  | "not_reviewed"
  | "accepted"
  | "edited_and_accepted"
  | "rejected";

export interface VisionAnalysisSuggestion {
  shot_type: ShotType | null;
  view_angle: ViewAngle | null;
  expression: Expression | null;
  pose_type: PoseType | null;
  tags: string[];
  description: string | null;
  quality_notes: string | null;
  identity_anchor_recommended: boolean;
}

export interface MediaAsset {
  id: string;
  project_id: string;
  media_type: string;
  original_filename: string;
  mime_type: string;
  extension: string;
  size_bytes: number;
  width: number;
  height: number;
  sha256: string;
  thumbnail_url: string;
  content_url: string;
  created_at: string;
}

export interface CharacterReference {
  id: string;
  look_id: string;
  media_asset_id: string;
  shot_type: ShotType;
  view_angle: ViewAngle;
  expression: Expression;
  pose_type: PoseType;
  custom_expression: string | null;
  custom_pose: string | null;
  tags: string[];
  description: string | null;
  notes: string | null;
  is_primary: boolean;
  is_identity_anchor: boolean;
  analysis_status: AnalysisStatus;
  suggestion_review_status: SuggestionReviewStatus;
  analysis_suggestions: VisionAnalysisSuggestion | null;
  media_asset: MediaAsset;
  created_at: string;
  updated_at: string;
}

export interface CharacterLook {
  id: string;
  character_id: string;
  name: string;
  description: string | null;
  costume_description: string | null;
  hair_description: string | null;
  makeup_description: string | null;
  condition_description: string | null;
  prompt_appearance: string | null;
  is_default: boolean;
  reference_count: number;
  primary_reference: CharacterReference | null;
  created_at: string;
  updated_at: string;
}

export interface Character {
  id: string;
  project_id: string;
  name: string;
  aliases: string | null;
  role_type: RoleType;
  description: string | null;
  appearance_description: string | null;
  personality_description: string | null;
  prompt_identity: string | null;
  notes: string | null;
  default_look: CharacterLook | null;
  look_count: number;
  reference_count: number;
  created_at: string;
  updated_at: string;
}

export interface CharacterListResponse {
  items: Character[];
  total: number;
}

export interface CharacterLookListResponse {
  items: CharacterLook[];
  total: number;
}

export interface CharacterReferenceListResponse {
  items: CharacterReference[];
  total: number;
}

export interface CharacterCreateInput {
  name: string;
  aliases?: string | null;
  role_type?: RoleType;
  description?: string | null;
  appearance_description?: string | null;
  personality_description?: string | null;
  prompt_identity?: string | null;
  notes?: string | null;
}

export type CharacterUpdateInput = Partial<CharacterCreateInput>;

export interface CharacterLookCreateInput {
  name: string;
  description?: string | null;
  costume_description?: string | null;
  hair_description?: string | null;
  makeup_description?: string | null;
  condition_description?: string | null;
  prompt_appearance?: string | null;
}

export type CharacterLookUpdateInput = Partial<CharacterLookCreateInput>;

export interface CharacterReferenceUpdateInput {
  shot_type?: ShotType | null;
  view_angle?: ViewAngle | null;
  expression?: Expression | null;
  pose_type?: PoseType | null;
  custom_expression?: string | null;
  custom_pose?: string | null;
  tags?: string[] | null;
  description?: string | null;
  notes?: string | null;
  is_identity_anchor?: boolean | null;
}
