import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { Controller, useForm } from "react-hook-form";

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
import { characterKeys, updateReference } from "@/features/characters/api";
import { characterCopy } from "@/features/characters/copy";
import {
  expressions,
  poseTypes,
  referenceMetadataSchema,
  shotTypes,
  type ReferenceMetadataSchema,
  viewAngles
} from "@/features/characters/schema";
import type { CharacterReference, CharacterReferenceUpdateInput } from "@/features/characters/types";

interface ReferenceMetadataDialogProps {
  projectId: string;
  characterId: string;
  reference: CharacterReference;
  trigger: ReactNode;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function referenceToFormValues(reference: CharacterReference): ReferenceMetadataSchema {
  return {
    shot_type: reference.shot_type,
    view_angle: reference.view_angle,
    expression: reference.expression,
    custom_expression: reference.custom_expression ?? "",
    pose_type: reference.pose_type,
    custom_pose: reference.custom_pose ?? "",
    tags: reference.tags.join(", "),
    description: reference.description ?? "",
    notes: reference.notes ?? "",
    is_identity_anchor: reference.is_identity_anchor
  };
}

function optionalText(value?: string): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function parseTags(value?: string): string[] {
  const trimmed = value?.trim();
  if (!trimmed) {
    return [];
  }
  return trimmed
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function toPayload(values: ReferenceMetadataSchema): CharacterReferenceUpdateInput {
  return {
    shot_type: values.shot_type,
    view_angle: values.view_angle,
    expression: values.expression,
    custom_expression: optionalText(values.custom_expression),
    pose_type: values.pose_type,
    custom_pose: optionalText(values.custom_pose),
    tags: parseTags(values.tags),
    description: optionalText(values.description),
    notes: optionalText(values.notes),
    is_identity_anchor: values.is_identity_anchor
  };
}

export function ReferenceMetadataDialog({
  projectId,
  characterId,
  reference,
  trigger,
  onSuccess,
  onError
}: ReferenceMetadataDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const form = useForm<ReferenceMetadataSchema>({
    resolver: zodResolver(referenceMetadataSchema),
    defaultValues: referenceToFormValues(reference)
  });

  useEffect(() => {
    if (open) {
      form.reset(referenceToFormValues(reference));
    }
  }, [form, open, reference]);

  const mutation = useMutation({
    mutationFn: (values: ReferenceMetadataSchema) =>
      updateReference(projectId, characterId, reference.look_id, reference.id, toPayload(values)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: characterKeys.references(projectId, characterId, reference.look_id)
      });
      await queryClient.invalidateQueries({ queryKey: characterKeys.looks(projectId, characterId) });
      await queryClient.invalidateQueries({
        queryKey: characterKeys.detail(projectId, characterId)
      });
      await queryClient.invalidateQueries({ queryKey: characterKeys.lists(projectId) });
      setOpen(false);
      onSuccess(characterCopy.referenceUpdated);
    },
    onError: () => onError(characterCopy.referenceSaveFailed)
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{characterCopy.editReference}</DialogTitle>
          <DialogDescription>{reference.media_asset.original_filename}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-4 md:grid-cols-2">
            <SelectField
              label={characterCopy.fields.shotType}
              valueName="shot_type"
              control={form.control}
              options={shotTypes}
              getLabel={(value) => characterCopy.shotType[value]}
            />
            <SelectField
              label={characterCopy.fields.viewAngle}
              valueName="view_angle"
              control={form.control}
              options={viewAngles}
              getLabel={(value) => characterCopy.viewAngle[value]}
            />
            <SelectField
              label={characterCopy.fields.expression}
              valueName="expression"
              control={form.control}
              options={expressions}
              getLabel={(value) => characterCopy.expression[value]}
            />
            <SelectField
              label={characterCopy.fields.poseType}
              valueName="pose_type"
              control={form.control}
              options={poseTypes}
              getLabel={(value) => characterCopy.poseType[value]}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="reference-custom-expression">
                {characterCopy.fields.customExpression}
              </Label>
              <Input
                id="reference-custom-expression"
                disabled={mutation.isPending}
                {...form.register("custom_expression")}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="reference-custom-pose">{characterCopy.fields.customPose}</Label>
              <Input
                id="reference-custom-pose"
                disabled={mutation.isPending}
                {...form.register("custom_pose")}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="reference-tags">{characterCopy.fields.tags}</Label>
            <Input
              id="reference-tags"
              placeholder={characterCopy.placeholders.referenceTags}
              disabled={mutation.isPending}
              {...form.register("tags")}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="reference-description">
              {characterCopy.fields.referenceDescription}
            </Label>
            <Textarea
              id="reference-description"
              disabled={mutation.isPending}
              {...form.register("description")}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="reference-notes">{characterCopy.fields.notes}</Label>
            <Textarea
              id="reference-notes"
              placeholder={characterCopy.placeholders.notes}
              disabled={mutation.isPending}
              {...form.register("notes")}
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border bg-background"
              disabled={mutation.isPending}
              {...form.register("is_identity_anchor")}
            />
            {characterCopy.setIdentityAnchor}
          </label>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              disabled={mutation.isPending}
              onClick={() => setOpen(false)}
            >
              {characterCopy.cancel}
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? characterCopy.saving : characterCopy.editReference}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface SelectFieldProps<TValue extends string> {
  label: string;
  valueName: keyof ReferenceMetadataSchema;
  control: ReturnType<typeof useForm<ReferenceMetadataSchema>>["control"];
  options: readonly TValue[];
  getLabel: (value: TValue) => string;
}

function SelectField<TValue extends string>({
  label,
  valueName,
  control,
  options,
  getLabel
}: SelectFieldProps<TValue>) {
  return (
    <div className="grid gap-2">
      <Label>{label}</Label>
      <Controller
        control={control}
        name={valueName}
        render={({ field }) => (
          <Select value={String(field.value)} onValueChange={field.onChange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {options.map((option) => (
                <SelectItem key={option} value={option}>
                  {getLabel(option)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      />
    </div>
  );
}
