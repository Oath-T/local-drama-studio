import { z } from "zod";

import type { KeyframeTaskAspectRatio, KeyframeTaskUpdateInput } from "./types";

export const keyframeAspectRatioOptions = ["9:16", "16:9", "1:1", "4:3", "3:4", "custom"] as const;

const integerString = z.string().trim().regex(/^\d+$/, "请输入整数");
const numberString = z.string().trim().regex(/^\d+(\.\d+)?$/, "请输入数字");

function dimensionSchema(label: string) {
  return integerString
    .transform((value) => Number(value))
    .refine((value) => value >= 256 && value <= 4096, `${label}必须在 256 到 4096 之间`)
    .refine((value) => value % 8 === 0, `${label}必须是 8 的倍数`)
    .transform((value) => String(value));
}

export const keyframeTaskFormSchema = z.object({
  name: z.string().trim().min(1, "请输入任务名称").max(120, "任务名称不能超过 120 个字符"),
  prompt_zh: z.string().max(8000, "中文提示词不能超过 8000 个字符"),
  prompt_en: z.string().max(8000, "英文提示词不能超过 8000 个字符"),
  negative_prompt: z.string().max(4000, "负面提示词不能超过 4000 个字符"),
  aspect_ratio: z.enum(keyframeAspectRatioOptions),
  width: dimensionSchema("宽度"),
  height: dimensionSchema("高度"),
  seed: z
    .string()
    .trim()
    .refine((value) => value === "" || /^\d+$/.test(value), "随机种子必须为空或非负整数"),
  steps: integerString
    .transform((value) => Number(value))
    .refine((value) => value >= 1 && value <= 150, "推理步数必须在 1 到 150 之间")
    .transform((value) => String(value)),
  guidance_scale: numberString
    .transform((value) => Number(value))
    .refine((value) => value >= 0 && value <= 30, "引导强度必须在 0 到 30 之间")
    .transform((value) => String(value)),
  sampler_name: z.string().max(120, "采样器名称不能超过 120 个字符"),
  scheduler_name: z.string().max(120, "调度器名称不能超过 120 个字符"),
  model_provider: z.string().max(120, "模型提供方不能超过 120 个字符"),
  model_name: z.string().max(200, "模型名称不能超过 200 个字符"),
  model_version: z.string().max(120, "模型版本不能超过 120 个字符"),
  output_count: integerString
    .transform((value) => Number(value))
    .refine((value) => value >= 1 && value <= 8, "输出数量必须在 1 到 8 之间")
    .transform((value) => String(value))
});

export type KeyframeTaskFormValues = z.infer<typeof keyframeTaskFormSchema>;

export function taskFormValuesToPayload(values: KeyframeTaskFormValues): KeyframeTaskUpdateInput {
  return {
    name: values.name.trim(),
    prompt_zh: emptyToNull(values.prompt_zh),
    prompt_en: emptyToNull(values.prompt_en),
    negative_prompt: emptyToNull(values.negative_prompt),
    aspect_ratio: values.aspect_ratio as KeyframeTaskAspectRatio,
    width: Number(values.width),
    height: Number(values.height),
    seed: values.seed.trim() === "" ? null : Number(values.seed),
    steps: Number(values.steps),
    guidance_scale: Number(values.guidance_scale),
    sampler_name: emptyToNull(values.sampler_name),
    scheduler_name: emptyToNull(values.scheduler_name),
    model_provider: emptyToNull(values.model_provider),
    model_name: emptyToNull(values.model_name),
    model_version: emptyToNull(values.model_version),
    output_count: Number(values.output_count)
  };
}

function emptyToNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}
