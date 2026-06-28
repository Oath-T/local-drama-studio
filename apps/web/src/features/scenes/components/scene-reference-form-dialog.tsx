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
import {
  sceneKeys,
  updateSceneReference,
  uploadSceneReference,
  type UploadSceneReferenceInput
} from "@/features/scenes/api";
import { sceneCopy } from "@/features/scenes/copy";
import {
  cameraPositions,
  compositionTypes,
  sceneReferenceFormSchema,
  shotScales,
  viewDirections,
  type SceneReferenceFormSchema
} from "@/features/scenes/schema";
import type { SceneReference, SceneReferenceUpdateInput } from "@/features/scenes/types";

interface SceneReferenceFormDialogProps {
  projectId: string;
  sceneId: string;
  stateId: string;
  mode?: "upload" | "edit";
  reference?: SceneReference;
  trigger: ReactNode;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function referenceToFormValues(reference?: SceneReference): SceneReferenceFormSchema {
  return {
    shot_scale: reference?.shot_scale ?? "unknown",
    camera_position: reference?.camera_position ?? "unknown",
    custom_camera_position: reference?.custom_camera_position ?? "",
    view_direction: reference?.view_direction ?? "unknown",
    custom_view_direction: reference?.custom_view_direction ?? "",
    composition_type: reference?.composition_type ?? "unknown",
    custom_composition: reference?.custom_composition ?? "",
    is_empty_plate: reference?.is_empty_plate ?? false,
    is_spatial_anchor: reference?.is_spatial_anchor ?? false,
    tags: reference?.tags.join(", ") ?? "",
    description: reference?.description ?? "",
    notes: reference?.notes ?? ""
  };
}

function optionalText(value?: string): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function tagsFromText(value?: string): string[] {
  return (value ?? "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function toUpdatePayload(values: SceneReferenceFormSchema): SceneReferenceUpdateInput {
  return {
    shot_scale: values.shot_scale,
    camera_position: values.camera_position,
    custom_camera_position:
      values.camera_position === "custom" ? optionalText(values.custom_camera_position) : null,
    view_direction: values.view_direction,
    custom_view_direction:
      values.view_direction === "custom" ? optionalText(values.custom_view_direction) : null,
    composition_type: values.composition_type,
    custom_composition:
      values.composition_type === "custom" ? optionalText(values.custom_composition) : null,
    is_empty_plate: values.is_empty_plate,
    is_spatial_anchor: values.is_spatial_anchor,
    tags: tagsFromText(values.tags),
    description: optionalText(values.description),
    notes: optionalText(values.notes)
  };
}

export function SceneReferenceFormDialog({
  projectId,
  sceneId,
  stateId,
  mode = "upload",
  reference,
  trigger,
  onSuccess,
  onError
}: SceneReferenceFormDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const form = useForm<SceneReferenceFormSchema>({
    resolver: zodResolver(sceneReferenceFormSchema),
    defaultValues: referenceToFormValues(reference)
  });
  const cameraPosition = form.watch("camera_position");
  const viewDirection = form.watch("view_direction");
  const compositionType = form.watch("composition_type");

  useEffect(() => {
    if (open) {
      form.reset(referenceToFormValues(reference));
      setFile(null);
      setFileError(null);
    }
  }, [form, open, reference]);

  const mutation = useMutation({
    mutationFn: (values: SceneReferenceFormSchema) => {
      const payload = toUpdatePayload(values);
      if (mode === "edit" && reference) {
        return updateSceneReference(projectId, sceneId, stateId, reference.id, payload);
      }
      if (!file) {
        setFileError("请选择参考图片");
        throw new Error("missing-file");
      }
      const input: UploadSceneReferenceInput = {
        file,
        shot_scale: values.shot_scale,
        camera_position: values.camera_position,
        custom_camera_position: values.custom_camera_position ?? "",
        view_direction: values.view_direction,
        custom_view_direction: values.custom_view_direction ?? "",
        composition_type: values.composition_type,
        custom_composition: values.custom_composition ?? "",
        is_empty_plate: values.is_empty_plate,
        is_spatial_anchor: values.is_spatial_anchor,
        tags: values.tags ?? "",
        description: values.description ?? "",
        notes: values.notes ?? ""
      };
      return uploadSceneReference(projectId, sceneId, stateId, input);
    },
    onSuccess: async () => {
      await invalidateSceneReferenceScope(queryClient, projectId, sceneId, stateId);
      setOpen(false);
      onSuccess(mode === "edit" ? sceneCopy.referenceUpdated : sceneCopy.referenceUploaded);
    },
    onError: (error) => {
      if (error instanceof Error && error.message === "missing-file") {
        return;
      }
      onError(mode === "edit" ? sceneCopy.referenceSaveFailed : sceneCopy.uploadFailed);
    }
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? sceneCopy.editReference : sceneCopy.uploadReference}</DialogTitle>
          <DialogDescription>{sceneCopy.emptyReferencesDescription}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          {mode === "upload" && (
            <div className="grid gap-2">
              <Label htmlFor="scene-reference-file">{sceneCopy.fields.file}</Label>
              <Input
                id="scene-reference-file"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                disabled={mutation.isPending}
                onChange={(event) => {
                  setFile(event.target.files?.[0] ?? null);
                  setFileError(null);
                }}
              />
              {fileError && <p className="text-xs text-danger">{fileError}</p>}
            </div>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            <SelectField control={form.control} name="shot_scale" label={sceneCopy.fields.shotScale} options={shotScales} labels={sceneCopy.shotScale} />
            <SelectField control={form.control} name="camera_position" label={sceneCopy.fields.cameraPosition} options={cameraPositions} labels={sceneCopy.cameraPosition} />
            <SelectField control={form.control} name="view_direction" label={sceneCopy.fields.viewDirection} options={viewDirections} labels={sceneCopy.viewDirection} />
            <SelectField control={form.control} name="composition_type" label={sceneCopy.fields.compositionType} options={compositionTypes} labels={sceneCopy.compositionType} />
          </div>
          {cameraPosition === "custom" && <InputField id="custom-camera" label={sceneCopy.fields.customCameraPosition} disabled={mutation.isPending} registration={form.register("custom_camera_position")} error={form.formState.errors.custom_camera_position?.message} />}
          {viewDirection === "custom" && <InputField id="custom-view" label={sceneCopy.fields.customViewDirection} disabled={mutation.isPending} registration={form.register("custom_view_direction")} error={form.formState.errors.custom_view_direction?.message} />}
          {compositionType === "custom" && <InputField id="custom-composition" label={sceneCopy.fields.customComposition} disabled={mutation.isPending} registration={form.register("custom_composition")} error={form.formState.errors.custom_composition?.message} />}
          <div className="grid gap-3 rounded-md border border-border bg-background p-3">
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input type="checkbox" className="h-4 w-4 accent-primary" disabled={mutation.isPending} {...form.register("is_spatial_anchor")} />
              {sceneCopy.spatialAnchor}
            </label>
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input type="checkbox" className="h-4 w-4 accent-primary" disabled={mutation.isPending} {...form.register("is_empty_plate")} />
              {sceneCopy.emptyPlate}
            </label>
          </div>
          <InputField id="reference-tags" label={sceneCopy.fields.tags} placeholder={sceneCopy.placeholders.referenceTags} disabled={mutation.isPending} registration={form.register("tags")} />
          <TextAreaField id="reference-description" label={sceneCopy.fields.referenceDescription} placeholder={sceneCopy.placeholders.referenceDescription} disabled={mutation.isPending} registration={form.register("description")} />
          <TextAreaField id="reference-notes" label={sceneCopy.fields.notes} placeholder={sceneCopy.placeholders.notes} disabled={mutation.isPending} registration={form.register("notes")} />

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" disabled={mutation.isPending} onClick={() => setOpen(false)}>
              {sceneCopy.cancel}
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? (mode === "upload" ? sceneCopy.uploading : sceneCopy.saving) : sceneCopy.save}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SelectField({
  control,
  name,
  label,
  options,
  labels
}: {
  control: ReturnType<typeof useForm<SceneReferenceFormSchema>>["control"];
  name: keyof SceneReferenceFormSchema;
  label: string;
  options: readonly string[];
  labels: Record<string, string>;
}) {
  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      <Controller
        control={control}
        name={name}
        render={({ field }) => (
          <Select value={String(field.value)} onValueChange={field.onChange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {options.map((option) => (
                <SelectItem key={option} value={option}>
                  {labels[option]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      />
    </div>
  );
}

function InputField({
  id,
  label,
  placeholder,
  disabled,
  registration,
  error
}: {
  id: string;
  label: string;
  placeholder?: string;
  disabled: boolean;
  registration: UseFormRegisterReturn;
  error?: string;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} placeholder={placeholder} disabled={disabled} {...registration} />
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
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

async function invalidateSceneReferenceScope(
  queryClient: ReturnType<typeof useQueryClient>,
  projectId: string,
  sceneId: string,
  stateId: string
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: sceneKeys.lists(projectId) }),
    queryClient.invalidateQueries({ queryKey: sceneKeys.detail(projectId, sceneId) }),
    queryClient.invalidateQueries({ queryKey: sceneKeys.states(projectId, sceneId) }),
    queryClient.invalidateQueries({ queryKey: sceneKeys.references(projectId, sceneId, stateId) })
  ]);
}
