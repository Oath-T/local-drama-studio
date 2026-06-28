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
import { characterKeys, createCharacter, updateCharacter } from "@/features/characters/api";
import { characterCopy } from "@/features/characters/copy";
import {
  characterFormSchema,
  roleTypes,
  type CharacterFormSchema
} from "@/features/characters/schema";
import type { Character, CharacterCreateInput } from "@/features/characters/types";

interface CharacterFormDialogProps {
  projectId: string;
  mode?: "create" | "edit";
  character?: Character;
  trigger: ReactNode;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function characterToFormValues(character?: Character): CharacterFormSchema {
  return {
    name: character?.name ?? "",
    aliases: character?.aliases ?? "",
    role_type: character?.role_type ?? "supporting",
    description: character?.description ?? "",
    appearance_description: character?.appearance_description ?? "",
    personality_description: character?.personality_description ?? "",
    prompt_identity: character?.prompt_identity ?? ""
  };
}

function optionalText(value?: string): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function toPayload(values: CharacterFormSchema): CharacterCreateInput {
  return {
    name: values.name.trim(),
    aliases: optionalText(values.aliases),
    role_type: values.role_type,
    description: optionalText(values.description),
    appearance_description: optionalText(values.appearance_description),
    personality_description: optionalText(values.personality_description),
    prompt_identity: optionalText(values.prompt_identity)
  };
}

export function CharacterFormDialog({
  projectId,
  mode = "create",
  character,
  trigger,
  onSuccess,
  onError
}: CharacterFormDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const form = useForm<CharacterFormSchema>({
    resolver: zodResolver(characterFormSchema),
    defaultValues: characterToFormValues(character)
  });

  useEffect(() => {
    if (open) {
      form.reset(characterToFormValues(character));
    }
  }, [character, form, open]);

  const mutation = useMutation({
    mutationFn: (values: CharacterFormSchema) => {
      const payload = toPayload(values);
      if (mode === "edit" && character) {
        return updateCharacter(projectId, character.id, payload);
      }
      return createCharacter(projectId, payload);
    },
    onSuccess: async (savedCharacter) => {
      await queryClient.invalidateQueries({ queryKey: characterKeys.lists(projectId) });
      await queryClient.invalidateQueries({
        queryKey: characterKeys.detail(projectId, savedCharacter.id)
      });
      setOpen(false);
      onSuccess(mode === "edit" ? characterCopy.updated : characterCopy.created);
    },
    onError: () => onError(characterCopy.saveFailed)
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {mode === "edit" ? characterCopy.editCharacter : characterCopy.newCharacter}
          </DialogTitle>
          <DialogDescription>{characterCopy.description}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-2">
            <Label htmlFor="character-name">{characterCopy.fields.name}</Label>
            <Input
              id="character-name"
              placeholder={characterCopy.placeholders.name}
              disabled={mutation.isPending}
              {...form.register("name")}
            />
            {form.formState.errors.name && (
              <p className="text-xs text-danger">{form.formState.errors.name.message}</p>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="character-aliases">{characterCopy.fields.aliases}</Label>
              <Input
                id="character-aliases"
                placeholder={characterCopy.placeholders.aliases}
                disabled={mutation.isPending}
                {...form.register("aliases")}
              />
            </div>
            <div className="grid gap-2">
              <Label>{characterCopy.fields.roleType}</Label>
              <Controller
                control={form.control}
                name="role_type"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {roleTypes.map((role) => (
                        <SelectItem key={role} value={role}>
                          {characterCopy.role[role]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          <TextAreaField
            id="character-description"
            label={characterCopy.fields.description}
            placeholder={characterCopy.placeholders.description}
            disabled={mutation.isPending}
            registration={form.register("description")}
          />
          <TextAreaField
            id="character-appearance"
            label={characterCopy.fields.appearanceDescription}
            placeholder={characterCopy.placeholders.appearance}
            disabled={mutation.isPending}
            registration={form.register("appearance_description")}
          />
          <TextAreaField
            id="character-personality"
            label={characterCopy.fields.personalityDescription}
            placeholder={characterCopy.placeholders.personality}
            disabled={mutation.isPending}
            registration={form.register("personality_description")}
          />
          <TextAreaField
            id="character-prompt"
            label={characterCopy.fields.promptIdentity}
            placeholder={characterCopy.placeholders.promptIdentity}
            disabled={mutation.isPending}
            registration={form.register("prompt_identity")}
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
                  ? characterCopy.editCharacter
                  : characterCopy.newCharacter}
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
  placeholder: string;
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
