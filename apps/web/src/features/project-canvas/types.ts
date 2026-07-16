export type CanvasViewMode = "workflow" | "storyboard";

export type CanvasNodeType =
  | "text"
  | "character"
  | "scene"
  | "shot"
  | "image"
  | "video"
  | "export";

export type CanvasEdgeType =
  | "uses_character"
  | "uses_scene"
  | "identity_reference"
  | "look_reference"
  | "scene_reference"
  | "pose_reference"
  | "start_frame"
  | "end_frame"
  | "continuity_from"
  | "generated_from"
  | "included_in_export";

export type CanvasEdgeStatus = "draft" | "applied" | "failed";

export interface CanvasViewport {
  x: number;
  y: number;
  zoom: number;
}

export interface CanvasNodeData {
  collapsed?: boolean | null;
  note?: string | null;
  display_variant?: string | null;
  thumbnail_override?: string | null;
  temporary_label?: string | null;
}

export interface CanvasEdgeData {
  note?: string | null;
  status?: CanvasEdgeStatus | null;
  business_entity_type?: string | null;
  business_entity_id?: string | null;
  error_message?: string | null;
  applied_at?: string | null;
  binding_payload?: Record<string, string | number | boolean | null> | null;
}

export interface ProjectCanvasNode {
  id: string;
  node_type: CanvasNodeType;
  title: string;
  position_x: number;
  position_y: number;
  width: number;
  height: number;
  z_index: number;
  entity_type: string | null;
  entity_id: string | null;
  data: CanvasNodeData;
  created_at: string;
  updated_at: string;
}

export interface ProjectCanvasEdge {
  id: string;
  source_node_id: string;
  target_node_id: string;
  source_handle: string | null;
  target_handle: string | null;
  semantic_type: CanvasEdgeType;
  data: CanvasEdgeData;
  created_at: string;
  updated_at: string;
}

export interface ProjectCanvas {
  id: string;
  project_id: string;
  view_mode: CanvasViewMode;
  viewport: CanvasViewport;
  layout_version: number;
  revision: number;
  nodes: ProjectCanvasNode[];
  edges: ProjectCanvasEdge[];
  created_at: string;
  updated_at: string;
}

export interface CanvasNodeInput {
  id?: string | null;
  node_type: CanvasNodeType;
  title?: string | null;
  position_x?: number;
  position_y?: number;
  width?: number;
  height?: number;
  z_index?: number;
  entity_type?: string | null;
  entity_id?: string | null;
  data?: CanvasNodeData;
}

export interface CanvasNodeCreateInput extends CanvasNodeInput {
  expected_revision: number;
}

export interface CanvasNodePatchInput {
  expected_revision: number;
  title?: string | null;
  position_x?: number;
  position_y?: number;
  width?: number;
  height?: number;
  z_index?: number;
  data?: CanvasNodeData;
}

export interface CanvasEdgeInput {
  id?: string | null;
  source_node_id: string;
  target_node_id: string;
  source_handle?: string | null;
  target_handle?: string | null;
  semantic_type: CanvasEdgeType;
  data?: CanvasEdgeData;
}

export interface CanvasEdgeCreateInput extends CanvasEdgeInput {
  expected_revision: number;
}

export interface ProjectCanvasSaveInput {
  expected_revision: number;
  view_mode: CanvasViewMode;
  viewport: CanvasViewport;
  nodes: CanvasNodeInput[];
  edges: CanvasEdgeInput[];
}

export interface CanvasEntityBatchPreview {
  character_count: number;
  scene_count: number;
  shot_count: number;
  total: number;
}

export interface CanvasEntityBatchInput {
  expected_revision: number;
  include_characters?: boolean;
  include_scenes?: boolean;
  include_shots?: boolean;
}

export interface CanvasBindingPayload {
  look_id?: string | null;
  action_description?: string | null;
  expression_description?: string | null;
  position_description?: string | null;
  is_primary_subject?: boolean | null;
  notes?: string | null;
  scene_state_id?: string | null;
  replace_existing_scene?: boolean;
  shot_character_id?: string | null;
  character_reference_id?: string | null;
  scene_reference_id?: string | null;
  purpose?: string | null;
  video_task_id?: string | null;
  role?: string | null;
  media_asset_id?: string | null;
}

export interface CanvasBindingPreviewInput {
  source_node_id: string;
  target_node_id: string;
  semantic_type: CanvasEdgeType;
  payload?: CanvasBindingPayload;
}

export interface CanvasBindingPreview {
  semantic_type: CanvasEdgeType;
  can_apply: boolean;
  title: string;
  summary: string;
  warnings: string[];
  required_fields: string[];
}

export interface CanvasBindingApplyInput extends CanvasBindingPreviewInput {
  expected_revision: number;
  edge_id?: string | null;
  apply_business?: boolean;
}

export interface CanvasBindingDeleteInput {
  expected_revision: number;
  mode: "hide_only" | "unbind_business";
}

export interface CanvasBusinessRelationsPreview {
  character_edges: number;
  scene_edges: number;
  reference_edges: number;
  total_edges: number;
}
