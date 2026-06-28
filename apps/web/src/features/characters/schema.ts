import { z } from "zod";

export const roleTypes = ["protagonist", "antagonist", "supporting", "extra", "other"] as const;
export const shotTypes = [
  "unknown",
  "face_closeup",
  "closeup",
  "upper_body",
  "half_body",
  "three_quarter",
  "full_body"
] as const;
export const viewAngles = [
  "unknown",
  "front",
  "left_45",
  "right_45",
  "left_profile",
  "right_profile",
  "back",
  "high_angle",
  "low_angle"
] as const;
export const expressions = [
  "unknown",
  "neutral",
  "happy",
  "smile",
  "sad",
  "angry",
  "shocked",
  "fearful",
  "crying",
  "cold_smirk",
  "serious",
  "custom"
] as const;
export const poseTypes = [
  "unknown",
  "standing",
  "sitting",
  "walking",
  "looking_camera",
  "looking_away",
  "holding_object",
  "custom"
] as const;

export const characterFormSchema = z.object({
  name: z.string().trim().min(1, "请输入角色名称。").max(100, "角色名称不能超过 100 个字符。"),
  aliases: z.string().trim().max(200, "别名不能超过 200 个字符。").optional(),
  role_type: z.enum(roleTypes),
  description: z.string().trim().max(1000, "角色简介不能超过 1000 个字符。").optional(),
  appearance_description: z
    .string()
    .trim()
    .max(2000, "外貌描述不能超过 2000 个字符。")
    .optional(),
  personality_description: z
    .string()
    .trim()
    .max(2000, "性格描述不能超过 2000 个字符。")
    .optional(),
  prompt_identity: z.string().trim().max(2000, "身份提示词不能超过 2000 个字符。").optional()
});

export const lookFormSchema = z.object({
  name: z.string().trim().min(1, "请输入造型名称。").max(100, "造型名称不能超过 100 个字符。"),
  description: z.string().trim().max(1000, "造型说明不能超过 1000 个字符。").optional(),
  costume_description: z
    .string()
    .trim()
    .max(2000, "服装描述不能超过 2000 个字符。")
    .optional(),
  hair_description: z.string().trim().max(1000, "发型描述不能超过 1000 个字符。").optional(),
  makeup_description: z.string().trim().max(1000, "妆容描述不能超过 1000 个字符。").optional(),
  condition_description: z
    .string()
    .trim()
    .max(1000, "特殊状态不能超过 1000 个字符。")
    .optional(),
  prompt_appearance: z
    .string()
    .trim()
    .max(3000, "完整造型提示描述不能超过 3000 个字符。")
    .optional()
});

export const referenceUploadSchema = z.object({
  file: z.instanceof(File, { message: "请选择参考图片。" }),
  shot_type: z.enum(shotTypes),
  view_angle: z.enum(viewAngles),
  expression: z.enum(expressions),
  pose_type: z.enum(poseTypes),
  tags: z.string().trim().max(300, "标签内容不能超过 300 个字符。").optional(),
  description: z.string().trim().max(1000, "描述不能超过 1000 个字符。").optional(),
  is_identity_anchor: z.boolean()
});

export const referenceMetadataSchema = z.object({
  shot_type: z.enum(shotTypes),
  view_angle: z.enum(viewAngles),
  expression: z.enum(expressions),
  custom_expression: z.string().trim().max(100, "自定义表情不能超过 100 个字符。").optional(),
  pose_type: z.enum(poseTypes),
  custom_pose: z.string().trim().max(100, "自定义姿势不能超过 100 个字符。").optional(),
  tags: z.string().trim().max(300, "标签内容不能超过 300 个字符。").optional(),
  description: z.string().trim().max(1000, "描述不能超过 1000 个字符。").optional(),
  notes: z.string().trim().max(1000, "备注不能超过 1000 个字符。").optional(),
  is_identity_anchor: z.boolean()
});

export type CharacterFormSchema = z.infer<typeof characterFormSchema>;
export type LookFormSchema = z.infer<typeof lookFormSchema>;
export type ReferenceUploadSchema = z.infer<typeof referenceUploadSchema>;
export type ReferenceMetadataSchema = z.infer<typeof referenceMetadataSchema>;
