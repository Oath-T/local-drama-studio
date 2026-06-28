import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { useForm, type UseFormRegisterReturn } from "react-hook-form";

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
import { Textarea } from "@/components/ui/textarea";
import { characterKeys, createLook, updateLook } from "@/features/characters/api";
import { characterCopy } from "@/features/characters/copy";
import { lookFormSchema, type LookFormSchema } from "@/features/characters/schema";
import type { CharacterLook, CharacterLookCreateInput } from "@/features/characters/types";

interface LookFormDialogProps {
  projectId: string;
  characterId: string;
  mode?: "create" | "edit";
  look?: CharacterLook;
  trigger: ReactNode;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function lookToFormValues(look?: CharacterLook): LookFormSchema {
  return {
    name: look?.name ?? "",
    description: look?.description ?? "",
    costume_description: look?.costume_description ?? "",
    hair_description: look?.hair_description ?? "",
    makeup_description: look?.makeup_description ?? "",
    condition_description: look?.condition_description ?? "",
    prompt_appearance: look?.prompt_appearance ?? ""
  };
}

function optionalText(value?: string): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function toPayload(values: LookFormSchema): CharacterLookCreateInput {
  return {
    name: values.name.trim(),
    description: optionalText(values.description),
    costume_description: optionalText(values.costume_description),
    hair_description: optionalText(values.hair_description),
    makeup_description: optionalText(values.makeup_description),
    condition_description: optionalText(values.condition_description),
    prompt_appearance: optionalText(values.prompt_appearance)
  };
}

export function LookFormDialog({
  projectId,
  characterId,
  mode = "create",
  look,
  trigger,
  onSuccess,
  onError
}: LookFormDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const form = useForm<LookFormSchema>({
    resolver: zodResolver(lookFormSchema),
    defaultValues: lookToFormValues(look)
  });

  useEffect(() => {
    if (open) {
      form.reset(lookToFormValues(look));
    }
  }, [form, look, open]);

  const mutation = useMutation({
    mutationFn: (values: LookFormSchema) => {
      const payload = toPayload(values);
      if (mode === "edit" && look) {
        return updateLook(projectId, characterId, look.id, payload);
      }
      return createLook(projectId, characterId, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: characterKeys.looks(projectId, characterId) });
      await queryClient.invalidateQueries({
        queryKey: characterKeys.detail(projectId, characterId)
      });
      await queryClient.invalidateQueries({ queryKey: characterKeys.lists(projectId) });
      setOpen(false);
      onSuccess(mode === "edit" ? characterCopy.lookUpdated : characterCopy.lookCreated);
    },
    onError: () => onError(characterCopy.lookSaveFailed)
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? characterCopy.editLook : characterCopy.newLook}</DialogTitle>
          <DialogDescription>{characterCopy.description}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-2">
            <Label htmlFor="look-name">{characterCopy.fields.lookName}</Label>
            <Input
              id="look-name"
              placeholder={characterCopy.placeholders.lookName}
              disabled={mutation.isPending}
              {...form.register("name")}
            />
            {form.formState.errors.name && (
              <p className="text-xs text-danger">{form.formState.errors.name.message}</p>
            )}
          </div>

          <TextAreaField
            id="look-description"
            label={characterCopy.fields.lookDescription}
            disabled={mutation.isPending}
            registration={form.register("description")}
          />
          <TextAreaField
            id="look-costume"
            label={characterCopy.fields.costumeDescription}
            placeholder={characterCopy.placeholders.costume}
            disabled={mutation.isPending}
            registration={form.register("costume_description")}
          />

          <div className="grid gap-4 md:grid-cols-2">
            <TextAreaField
              id="look-hair"
              label={characterCopy.fields.hairDescription}
              placeholder={characterCopy.placeholders.hair}
              disabled={mutation.isPending}
              registration={form.register("hair_description")}
            />
            <TextAreaField
              id="look-makeup"
              label={characterCopy.fields.makeupDescription}
              placeholder={characterCopy.placeholders.makeup}
              disabled={mutation.isPending}
              registration={form.register("makeup_description")}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="look-condition">{characterCopy.fields.conditionDescription}</Label>
            <Input
              id="look-condition"
              placeholder={characterCopy.placeholders.condition}
              disabled={mutation.isPending}
              {...form.register("condition_description")}
            />
          </div>

          <TextAreaField
            id="look-prompt"
            label={characterCopy.fields.promptAppearance}
            placeholder={characterCopy.placeholders.promptAppearance}
            disabled={mutation.isPending}
            registration={form.register("prompt_appearance")}
          />

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
              {mutation.isPending
                ? characterCopy.saving
                : mode === "edit"
                  ? characterCopy.editLook
                  : characterCopy.newLook}
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
