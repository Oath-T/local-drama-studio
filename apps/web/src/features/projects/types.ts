export type AspectRatio = "9:16" | "16:9" | "1:1" | "4:3";
export type DefaultLanguage = "zh-CN" | "en-US";
export type DefaultFps = 24 | 25 | 30;

export interface Project {
  id: string;
  name: string;
  description: string | null;
  aspect_ratio: AspectRatio;
  default_style: string | null;
  default_language: DefaultLanguage;
  default_fps: DefaultFps;
  cover_image_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: Project[];
  total: number;
}

export interface ProjectFormValues {
  name: string;
  description: string;
  aspect_ratio: AspectRatio;
  default_style: string;
  default_language: DefaultLanguage;
  default_fps: DefaultFps;
}

export interface ProjectCreateInput {
  name: string;
  description?: string | null;
  aspect_ratio?: AspectRatio;
  default_style?: string | null;
  default_language?: DefaultLanguage;
  default_fps?: DefaultFps;
}

export type ProjectUpdateInput = Partial<ProjectCreateInput>;
