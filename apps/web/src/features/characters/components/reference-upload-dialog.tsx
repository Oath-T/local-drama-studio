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
import { characterKeys, uploadReference } from "@/features/characters/api";
import { characterCopy } from "@/features/characters/copy";
import {
  expressions,
  poseTypes,
  referenceUploadSchema,
  shotTypes,
  type ReferenceUploadSchema,
  viewAngles
} from "@/features/characters/schema";

interface ReferenceUploadDialogProps {
  projectId: string;
  characterId: string;
  lookId: string;
  trigger: ReactNode;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

const defaultValues: Omit<ReferenceUploadSchema, "file"> = {
  shot_type: "unknown",
  view_angle: "unknown",
  expression: "unknown",
  pose_type: "unknown",
  tags: "",
  description: "",
  is_identity_anchor: false
};

export function ReferenceUploadDialog({
  projectId,
  characterId,
  lookId,
  trigger,
  onSuccess,
  onError
}: ReferenceUploadDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const form = useForm<ReferenceUploadSchema>({
    resolver: zodResolver(referenceUploadSchema),
    defaultValues: defaultValues as ReferenceUploadSchema
  });

  useEffect(() => {
    if (open) {
      form.reset(defaultValues as ReferenceUploadSchema);
    }
  }, [form, open]);

  const mutation = useMutation({
    mutationFn: (values: ReferenceUploadSchema) =>
      uploadReference(projectId, characterId, lookId, {
        ...values,
        tags: values.tags ?? "",
        description: values.description ?? ""
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: characterKeys.references(projectId, characterId, lookId)
      });
      await queryClient.invalidateQueries({ queryKey: characterKeys.looks(projectId, characterId) });
      await queryClient.invalidateQueries({
        queryKey: characterKeys.detail(projectId, characterId)
      });
      await queryClient.invalidateQueries({ queryKey: characterKeys.lists(projectId) });
      setOpen(false);
      onSuccess(characterCopy.referenceUploaded);
    },
    onError: () => onError(characterCopy.uploadFailed)
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{characterCopy.uploadReference}</DialogTitle>
          <DialogDescription>{characterCopy.emptyReferencesDescription}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-2">
            <Label htmlFor="reference-file">{characterCopy.fields.file}</Label>
            <Controller
              control={form.control}
              name="file"
              render={({ field: { onChange, ref } }) => (
                <Input
                  id="reference-file"
                  ref={ref}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  disabled={mutation.isPending}
                  onChange={(event) => onChange(event.target.files?.[0])}
                />
              )}
            />
            {form.formState.errors.file && (
              <p className="text-xs text-danger">{form.formState.errors.file.message}</p>
            )}
          </div>

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
              placeholder={characterCopy.placeholders.referenceDescription}
              disabled={mutation.isPending}
              {...form.register("description")}
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-border bg-background"
              disabled={mutation.isPending}
              {...form.register("is_identity_anchor")}
            />
            {characterCopy.fields.isIdentityAnchor}
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
              {mutation.isPending ? characterCopy.uploading : characterCopy.uploadReference}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface SelectFieldProps<TValue extends string> {
  label: string;
  valueName: keyof ReferenceUploadSchema;
  control: ReturnType<typeof useForm<ReferenceUploadSchema>>["control"];
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
