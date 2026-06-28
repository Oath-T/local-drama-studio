import { z } from "zod";

export const sceneTypes = ["interior", "exterior", "mixed", "vehicle", "virtual", "other"] as const;
export const timeOfDays = [
  "dawn",
  "morning",
  "noon",
  "afternoon",
  "dusk",
  "night",
  "late_night",
  "unknown"
] as const;
export const weathers = [
  "clear",
  "cloudy",
  "overcast",
  "light_rain",
  "heavy_rain",
  "storm",
  "snow",
  "fog",
  "indoor",
  "custom",
  "unknown"
] as const;
export const lightings = [
  "natural_soft",
  "natural_hard",
  "warm_indoor",
  "cool_indoor",
  "neon",
  "low_key",
  "high_key",
  "backlight",
  "mixed",
  "custom",
  "unknown"
] as const;
export const seasons = ["spring", "summer", "autumn", "winter", "not_applicable", "unknown"] as const;
export const crowdLevels = ["empty", "sparse", "normal", "crowded", "packed", "unknown"] as const;
export const shotScales = [
  "extreme_wide",
  "wide",
  "full",
  "medium_wide",
  "medium",
  "close",
  "detail",
  "unknown"
] as const;
export const cameraPositions = [
  "eye_level",
  "low_angle",
  "high_angle",
  "ground_level",
  "overhead",
  "aerial",
  "doorway",
  "corner",
  "custom",
  "unknown"
] as const;
export const viewDirections = [
  "front",
  "left",
  "right",
  "back",
  "diagonal_left",
  "diagonal_right",
  "inward",
  "outward",
  "custom",
  "unknown"
] as const;
export const compositionTypes = [
  "centered",
  "symmetrical",
  "rule_of_thirds",
  "leading_lines",
  "frame_within_frame",
  "deep_focus",
  "layered",
  "custom",
  "unknown"
] as const;

export const sceneFormSchema = z.object({
  name: z.string().trim().min(1, "请输入场景名称").max(120, "场景名称不能超过 120 个字符"),
  scene_type: z.enum(sceneTypes),
  description: z.string().max(1000).optional(),
  fixed_environment_description: z.string().max(2000).optional(),
  spatial_layout_description: z.string().max(2000).optional(),
  visual_style_description: z.string().max(2000).optional(),
  prompt_environment: z.string().max(3000).optional(),
  notes: z.string().max(2000).optional()
});

export const sceneStateFormSchema = z
  .object({
    name: z.string().trim().min(1, "请输入状态名称").max(120, "状态名称不能超过 120 个字符"),
    description: z.string().max(1000).optional(),
    time_of_day: z.enum(timeOfDays),
    weather: z.enum(weathers),
    custom_weather: z.string().max(120).optional(),
    lighting: z.enum(lightings),
    custom_lighting: z.string().max(120).optional(),
    season: z.enum(seasons),
    environment_condition: z.string().max(2000).optional(),
    crowd_level: z.enum(crowdLevels),
    prompt_state: z.string().max(3000).optional()
  })
  .superRefine((value, ctx) => {
    if (value.weather === "custom" && !value.custom_weather?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["custom_weather"],
        message: "选择自定义天气时，请填写天气说明"
      });
    }
    if (value.lighting === "custom" && !value.custom_lighting?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["custom_lighting"],
        message: "选择自定义灯光时，请填写灯光说明"
      });
    }
  });

export const sceneReferenceFormSchema = z
  .object({
    file: z.instanceof(File).optional(),
    shot_scale: z.enum(shotScales),
    camera_position: z.enum(cameraPositions),
    custom_camera_position: z.string().max(120).optional(),
    view_direction: z.enum(viewDirections),
    custom_view_direction: z.string().max(120).optional(),
    composition_type: z.enum(compositionTypes),
    custom_composition: z.string().max(120).optional(),
    is_empty_plate: z.boolean(),
    is_spatial_anchor: z.boolean(),
    tags: z.string().max(500).optional(),
    description: z.string().max(1000).optional(),
    notes: z.string().max(1000).optional()
  })
  .superRefine((value, ctx) => {
    if (value.camera_position === "custom" && !value.custom_camera_position?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["custom_camera_position"],
        message: "选择自定义机位时，请填写机位说明"
      });
    }
    if (value.view_direction === "custom" && !value.custom_view_direction?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["custom_view_direction"],
        message: "选择自定义朝向时，请填写朝向说明"
      });
    }
    if (value.composition_type === "custom" && !value.custom_composition?.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["custom_composition"],
        message: "选择自定义构图时，请填写构图说明"
      });
    }
  });

export type SceneFormSchema = z.infer<typeof sceneFormSchema>;
export type SceneStateFormSchema = z.infer<typeof sceneStateFormSchema>;
export type SceneReferenceFormSchema = z.infer<typeof sceneReferenceFormSchema>;
