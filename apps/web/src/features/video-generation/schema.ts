import { z } from "zod";

import type { VideoTaskUpdateInput } from "./types";

const emptyToNull = (value: string): string | null => {
  const normalized = value.trim();
  return normalized === "" ? null : normalized;
};

const positiveNumber = (message: string) =>
  z
    .string()
    .transform((value, ctx) => {
      const normalized = value.trim();
      if (normalized === "") {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message });
        return z.NEVER;
      }
      const parsed = Number(normalized);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, message });
        return z.NEVER;
      }
      return parsed;
    });

const optionalInteger = (message: string) =>
  z.string().transform((value, ctx) => {
    const normalized = value.trim();
    if (normalized === "") return null;
    const parsed = Number(normalized);
    if (!Number.isInteger(parsed) || parsed < 0) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message });
      return z.NEVER;
    }
    return parsed;
  });

const dimension = z.string().transform((value, ctx) => {
  const parsed = Number(value.trim());
  if (!Number.isInteger(parsed) || parsed < 256 || parsed > 2048 || parsed % 8 !== 0) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "尺寸必须在 256 到 2048 之间，且为 8 的倍数"
    });
    return z.NEVER;
  }
  return parsed;
});

export const videoTaskFormSchema = z.object({
  name: z.string().trim().min(1, "请输入任务名称").max(120, "任务名称不能超过 120 个字符"),
  prompt: z.string().trim().min(1, "请输入视频提示词").max(4000, "提示词不能超过 4000 个字符"),
  negative_prompt: z.string().max(2000, "反向提示词不能超过 2000 个字符"),
  duration_seconds: positiveNumber("时长必须大于 0 秒"),
  fps: positiveNumber("帧率必须大于 0").refine((value) => Number.isInteger(value), "帧率必须是整数"),
  width: dimension,
  height: dimension,
  seed: optionalInteger("随机种子必须为空或非负整数"),
  motion_strength: z.string().transform((value, ctx) => {
    const normalized = value.trim();
    if (normalized === "") return null;
    const parsed = Number(normalized);
    if (!Number.isFinite(parsed) || parsed < 0 || parsed > 1) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: "运动强度必须在 0 到 1 之间" });
      return z.NEVER;
    }
    return parsed;
  }),
  camera_motion: z.string().max(200, "镜头运动不能超过 200 个字符"),
  workflow_id: z.string().nullable()
});

export type VideoTaskFormValues = z.input<typeof videoTaskFormSchema>;
export type ParsedVideoTaskFormValues = z.output<typeof videoTaskFormSchema>;

export function videoTaskFormValuesToPayload(
  values: ParsedVideoTaskFormValues
): VideoTaskUpdateInput {
  return {
    name: values.name,
    prompt: values.prompt,
    negative_prompt: emptyToNull(values.negative_prompt),
    duration_seconds: values.duration_seconds,
    fps: values.fps,
    width: values.width,
    height: values.height,
    seed: values.seed,
    motion_strength: values.motion_strength,
    camera_motion: emptyToNull(values.camera_motion),
    workflow_id: values.workflow_id
  };
}
