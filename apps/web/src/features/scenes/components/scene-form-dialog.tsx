import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { Controller, useForm, type UseFormRegisterReturn } from "react-hook-form";

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
import { createScene, sceneKeys, updateScene } from "@/features/scenes/api";
import { sceneCopy } from "@/features/scenes/copy";
import {
  sceneFormSchema,
  sceneTypes,
  type SceneFormSchema
} from "@/features/scenes/schema";
import type { Scene, SceneCreateInput } from "@/features/scenes/types";

interface SceneFormDialogProps {
  projectId: string;
  mode?: "create" | "edit";
  scene?: Scene;
  trigger: ReactNode;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function sceneToFormValues(scene?: Scene): SceneFormSchema {
  return {
    name: scene?.name ?? "",
    scene_type: scene?.scene_type ?? "other",
    description: scene?.description ?? "",
    fixed_environment_description: scene?.fixed_environment_description ?? "",
    spatial_layout_description: scene?.spatial_layout_description ?? "",
    visual_style_description: scene?.visual_style_description ?? "",
    prompt_environment: scene?.prompt_environment ?? "",
    notes: scene?.notes ?? ""
  };
}

function optionalText(value?: string): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function toPayload(values: SceneFormSchema): SceneCreateInput {
  return {
    name: values.name.trim(),
    scene_type: values.scene_type,
    description: optionalText(values.description),
    fixed_environment_description: optionalText(values.fixed_environment_description),
    spatial_layout_description: optionalText(values.spatial_layout_description),
    visual_style_description: optionalText(values.visual_style_description),
    prompt_environment: optionalText(values.prompt_environment),
    notes: optionalText(values.notes)
  };
}

export function SceneFormDialog({
  projectId,
  mode = "create",
  scene,
  trigger,
  onSuccess,
  onError
}: SceneFormDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const form = useForm<SceneFormSchema>({
    resolver: zodResolver(sceneFormSchema),
    defaultValues: sceneToFormValues(scene)
  });

  useEffect(() => {
    if (open) {
      form.reset(sceneToFormValues(scene));
    }
  }, [form, open, scene]);

  const mutation = useMutation({
    mutationFn: (values: SceneFormSchema) => {
      const payload = toPayload(values);
      if (mode === "edit" && scene) {
        return updateScene(projectId, scene.id, payload);
      }
      return createScene(projectId, payload);
    },
    onSuccess: async (savedScene) => {
      await queryClient.invalidateQueries({ queryKey: sceneKeys.lists(projectId) });
      await queryClient.invalidateQueries({ queryKey: sceneKeys.detail(projectId, savedScene.id) });
      setOpen(false);
      onSuccess(mode === "edit" ? sceneCopy.updated : sceneCopy.created);
    },
    onError: () => onError(sceneCopy.saveFailed)
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? sceneCopy.editScene : sceneCopy.newScene}</DialogTitle>
          <DialogDescription>{sceneCopy.description}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-2">
            <Label htmlFor="scene-name">{sceneCopy.fields.name}</Label>
            <Input id="scene-name" disabled={mutation.isPending} {...form.register("name")} />
            {form.formState.errors.name && (
              <p className="text-xs text-danger">{form.formState.errors.name.message}</p>
            )}
          </div>
          <div className="grid gap-2">
            <Label>{sceneCopy.fields.sceneType}</Label>
            <Controller
              control={form.control}
              name="scene_type"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {sceneTypes.map((type) => (
                      <SelectItem key={type} value={type}>
                        {sceneCopy.sceneType[type]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
          </div>
          <TextAreaField id="scene-description" label={sceneCopy.fields.description} disabled={mutation.isPending} registration={form.register("description")} />
          <TextAreaField id="scene-fixed" label={sceneCopy.fields.fixedEnvironment} placeholder={sceneCopy.placeholders.fixedEnvironment} disabled={mutation.isPending} registration={form.register("fixed_environment_description")} />
          <TextAreaField id="scene-layout" label={sceneCopy.fields.spatialLayout} placeholder={sceneCopy.placeholders.spatialLayout} disabled={mutation.isPending} registration={form.register("spatial_layout_description")} />
          <TextAreaField id="scene-style" label={sceneCopy.fields.visualStyle} placeholder={sceneCopy.placeholders.visualStyle} disabled={mutation.isPending} registration={form.register("visual_style_description")} />
          <TextAreaField id="scene-prompt" label={sceneCopy.fields.promptEnvironment} placeholder={sceneCopy.placeholders.promptEnvironment} disabled={mutation.isPending} registration={form.register("prompt_environment")} />
          <TextAreaField id="scene-notes" label={sceneCopy.fields.notes} placeholder={sceneCopy.placeholders.notes} disabled={mutation.isPending} registration={form.register("notes")} />

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" disabled={mutation.isPending} onClick={() => setOpen(false)}>
              {sceneCopy.cancel}
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? sceneCopy.saving : sceneCopy.save}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function TextAreaField({
  id,
  label,
  placeholder,
  disabled,
  registration
}: {
  id: string;
  label: string;
  placeholder?: string;
  disabled: boolean;
  registration: UseFormRegisterReturn;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Textarea id={id} placeholder={placeholder} disabled={disabled} {...registration} />
    </div>
  );
}
