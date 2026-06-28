import { z } from "zod";

const durationMessage = "预计时长必须大于 0 秒";

const durationSecondsSchema = z
  .union([z.literal(""), z.number(), z.string()])
  .superRefine((value, context) => {
    if (value === "") return;
    const parsed = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: durationMessage });
      return;
    }
    if (parsed > 3600) {
      context.addIssue({ code: z.ZodIssueCode.custom, message: "预计时长不能超过 3600 秒" });
    }
  })
  .transform((value) => (value === "" ? "" : Number(value)));

export const shotFormSchema = z.object({
  name: z.string().trim().min(1, "请输入镜头名称").max(120, "镜头名称不能超过 120 个字符"),
  story_description: z.string().trim().optional(),
  visual_description: z.string().trim().optional(),
  dialogue: z.string().trim().optional(),
  action_summary: z.string().trim().optional(),
  duration_seconds: durationSecondsSchema,
  shot_scale: z.string(),
  camera_height: z.string(),
  custom_camera_height: z.string().trim().optional(),
  camera_angle: z.string(),
  custom_camera_angle: z.string().trim().optional(),
  composition_type: z.string(),
  custom_composition: z.string().trim().optional(),
  camera_movement: z.string(),
  custom_camera_movement: z.string().trim().optional(),
  focal_subject: z.string().trim().optional(),
  mood_description: z.string().trim().optional(),
  scene_id: z.string().optional(),
  scene_state_id: z.string().optional(),
  notes: z.string().trim().optional()
});

export type ShotFormValues = z.infer<typeof shotFormSchema>;
