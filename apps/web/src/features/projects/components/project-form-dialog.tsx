import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createProject, projectKeys, updateProject } from "@/features/projects/api";
import {
  aspectRatios,
  defaultFpsValues,
  defaultLanguages,
  projectFormSchema,
  type ProjectFormSchema
} from "@/features/projects/schema";
import type { DefaultFps, Project, ProjectCreateInput } from "@/features/projects/types";
import { copy } from "@/locales";

interface ProjectFormDialogProps {
  mode: "create" | "edit";
  project?: Project;
  trigger?: ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function projectToFormValues(project?: Project): ProjectFormSchema {
  return {
    name: project?.name ?? "",
    description: project?.description ?? "",
    aspect_ratio: project?.aspect_ratio ?? "9:16",
    default_style: project?.default_style ?? "",
    default_language: project?.default_language ?? "zh-CN",
    default_fps: project?.default_fps ?? 24
  };
}

function toPayload(values: ProjectFormSchema): ProjectCreateInput {
  return {
    name: values.name.trim(),
    description: values.description?.trim() ? values.description.trim() : null,
    aspect_ratio: values.aspect_ratio,
    default_style: values.default_style?.trim() ? values.default_style.trim() : null,
    default_language: values.default_language,
    default_fps: values.default_fps as DefaultFps
  };
}

export function ProjectFormDialog({
  mode,
  project,
  trigger,
  open: controlledOpen,
  onOpenChange,
  onSuccess,
  onError
}: ProjectFormDialogProps) {
  const queryClient = useQueryClient();
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen ?? internalOpen;
  const setOpen = onOpenChange ?? setInternalOpen;
  const form = useForm<ProjectFormSchema>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: projectToFormValues(project)
  });

  useEffect(() => {
    if (open) {
      form.reset(projectToFormValues(project));
    }
  }, [form, open, project]);

  const mutation = useMutation({
    mutationFn: async (values: ProjectFormSchema) => {
      const payload = toPayload(values);
      if (mode === "edit" && project) {
        return updateProject(project.id, payload);
      }
      return createProject(payload);
    },
    onSuccess: async (savedProject) => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      await queryClient.invalidateQueries({ queryKey: projectKeys.detail(savedProject.id) });
      setOpen(false);
      form.reset(projectToFormValues(mode === "edit" ? savedProject : undefined));
      onSuccess(mode === "edit" ? copy.projects.updated : copy.projects.created);
    },
    onError: () => {
      onError(copy.projects.saveFailed);
    }
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? copy.projects.editProject : copy.projects.newProject}</DialogTitle>
          <DialogDescription>{copy.projects.description}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-2">
            <Label htmlFor="project-name">{copy.form.name}</Label>
            <Input
              id="project-name"
              placeholder={copy.form.namePlaceholder}
              disabled={mutation.isPending}
              {...form.register("name")}
            />
            {form.formState.errors.name && (
              <p className="text-xs text-danger">{form.formState.errors.name.message}</p>
            )}
          </div>

          <div className="grid gap-2">
            <Label htmlFor="project-description">{copy.form.description}</Label>
            <Textarea
              id="project-description"
              placeholder={copy.form.descriptionPlaceholder}
              disabled={mutation.isPending}
              {...form.register("description")}
            />
            {form.formState.errors.description && (
              <p className="text-xs text-danger">{form.formState.errors.description.message}</p>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="grid gap-2">
              <Label>{copy.form.aspectRatio}</Label>
              <Controller
                control={form.control}
                name="aspect_ratio"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={mutation.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {aspectRatios.map((option) => (
                        <SelectItem key={option} value={option}>
                          {copy.options.aspectRatio[option]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="grid gap-2">
              <Label>{copy.form.defaultLanguage}</Label>
              <Controller
                control={form.control}
                name="default_language"
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={mutation.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {defaultLanguages.map((option) => (
                        <SelectItem key={option} value={option}>
                          {copy.options.language[option]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            <div className="grid gap-2">
              <Label>{copy.form.defaultFps}</Label>
              <Controller
                control={form.control}
                name="default_fps"
                render={({ field }) => (
                  <Select
                    value={String(field.value)}
                    onValueChange={(value) => field.onChange(Number(value))}
                    disabled={mutation.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {defaultFpsValues.map((option) => (
                        <SelectItem key={option} value={String(option)}>
                          {copy.options.fps[option]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="project-style">{copy.form.defaultStyle}</Label>
            <Input
              id="project-style"
              placeholder={copy.form.stylePlaceholder}
              disabled={mutation.isPending}
              {...form.register("default_style")}
            />
            {form.formState.errors.default_style && (
              <p className="text-xs text-danger">{form.formState.errors.default_style.message}</p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              disabled={mutation.isPending}
              onClick={() => setOpen(false)}
            >
              {copy.common.cancel}
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending
                ? mode === "edit"
                  ? copy.form.saving
                  : copy.form.creating
                : mode === "edit"
                  ? copy.form.saveSubmit
                  : copy.form.createSubmit}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
