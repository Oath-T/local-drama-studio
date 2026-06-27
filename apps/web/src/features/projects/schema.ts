import { z } from "zod";

import { copy } from "@/locales";

export const aspectRatios = ["9:16", "16:9", "1:1", "4:3"] as const;
export const defaultLanguages = ["zh-CN", "en-US"] as const;
export const defaultFpsValues = [24, 25, 30] as const;

export const projectFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, copy.form.errors.nameRequired)
    .max(100, copy.form.errors.nameTooLong),
  description: z.string().trim().max(1000, copy.form.errors.descriptionTooLong).optional(),
  aspect_ratio: z.enum(aspectRatios, {
    errorMap: () => ({ message: copy.form.errors.invalidAspectRatio })
  }),
  default_style: z.string().trim().max(200, copy.form.errors.styleTooLong).optional(),
  default_language: z.enum(defaultLanguages, {
    errorMap: () => ({ message: copy.form.errors.invalidLanguage })
  }),
  default_fps: z.coerce.number().refine((value) => defaultFpsValues.includes(value as never), {
    message: copy.form.errors.invalidFps
  })
});

export type ProjectFormSchema = z.infer<typeof projectFormSchema>;
