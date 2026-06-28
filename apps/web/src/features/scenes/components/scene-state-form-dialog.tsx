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
import { createSceneState, sceneKeys, updateSceneState } from "@/features/scenes/api";
import { sceneCopy } from "@/features/scenes/copy";
import {
  crowdLevels,
  lightings,
  sceneStateFormSchema,
  seasons,
  timeOfDays,
  weathers,
  type SceneStateFormSchema
} from "@/features/scenes/schema";
import type { SceneState, SceneStateCreateInput } from "@/features/scenes/types";

interface SceneStateFormDialogProps {
  projectId: string;
  sceneId: string;
  mode?: "create" | "edit";
  state?: SceneState;
  trigger: ReactNode;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function stateToFormValues(state?: SceneState): SceneStateFormSchema {
  return {
    name: state?.name ?? "",
    description: state?.description ?? "",
    time_of_day: state?.time_of_day ?? "unknown",
    weather: state?.weather ?? "unknown",
    custom_weather: state?.custom_weather ?? "",
    lighting: state?.lighting ?? "unknown",
    custom_lighting: state?.custom_lighting ?? "",
    season: state?.season ?? "unknown",
    environment_condition: state?.environment_condition ?? "",
    crowd_level: state?.crowd_level ?? "unknown",
    prompt_state: state?.prompt_state ?? ""
  };
}

function optionalText(value?: string): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function toPayload(values: SceneStateFormSchema): SceneStateCreateInput {
  return {
    name: values.name.trim(),
    description: optionalText(values.description),
    time_of_day: values.time_of_day,
    weather: values.weather,
    custom_weather: values.weather === "custom" ? optionalText(values.custom_weather) : null,
    lighting: values.lighting,
    custom_lighting: values.lighting === "custom" ? optionalText(values.custom_lighting) : null,
    season: values.season,
    environment_condition: optionalText(values.environment_condition),
    crowd_level: values.crowd_level,
    prompt_state: optionalText(values.prompt_state)
  };
}

export function SceneStateFormDialog({
  projectId,
  sceneId,
  mode = "create",
  state,
  trigger,
  onSuccess,
  onError
}: SceneStateFormDialogProps) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const form = useForm<SceneStateFormSchema>({
    resolver: zodResolver(sceneStateFormSchema),
    defaultValues: stateToFormValues(state)
  });
  const weather = form.watch("weather");
  const lighting = form.watch("lighting");

  useEffect(() => {
    if (open) {
      form.reset(stateToFormValues(state));
    }
  }, [form, open, state]);

  const mutation = useMutation({
    mutationFn: (values: SceneStateFormSchema) => {
      const payload = toPayload(values);
      if (mode === "edit" && state) {
        return updateSceneState(projectId, sceneId, state.id, payload);
      }
      return createSceneState(projectId, sceneId, payload);
    },
    onSuccess: async () => {
      await invalidateSceneStateScope(queryClient, projectId, sceneId);
      setOpen(false);
      onSuccess(mode === "edit" ? sceneCopy.stateUpdated : sceneCopy.stateCreated);
    },
    onError: () => onError(sceneCopy.stateSaveFailed)
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "edit" ? sceneCopy.editState : sceneCopy.newState}</DialogTitle>
          <DialogDescription>{sceneCopy.emptyStatesDescription}</DialogDescription>
        </DialogHeader>

        <form className="grid gap-4" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
          <div className="grid gap-2">
            <Label htmlFor="scene-state-name">{sceneCopy.fields.stateName}</Label>
            <Input id="scene-state-name" disabled={mutation.isPending} {...form.register("name")} />
            {form.formState.errors.name && (
              <p className="text-xs text-danger">{form.formState.errors.name.message}</p>
            )}
          </div>
          <TextAreaField id="scene-state-description" label={sceneCopy.fields.description} disabled={mutation.isPending} registration={form.register("description")} />
          <div className="grid gap-4 md:grid-cols-2">
            <SelectField control={form.control} name="time_of_day" label={sceneCopy.fields.timeOfDay} options={timeOfDays} labels={sceneCopy.timeOfDay} />
            <SelectField control={form.control} name="season" label={sceneCopy.fields.season} options={seasons} labels={sceneCopy.season} />
            <SelectField control={form.control} name="weather" label={sceneCopy.fields.weather} options={weathers} labels={sceneCopy.weather} />
            <SelectField control={form.control} name="lighting" label={sceneCopy.fields.lighting} options={lightings} labels={sceneCopy.lighting} />
          </div>
          {weather === "custom" && (
            <div className="grid gap-2">
              <Label htmlFor="custom-weather">{sceneCopy.fields.customWeather}</Label>
              <Input id="custom-weather" disabled={mutation.isPending} {...form.register("custom_weather")} />
              {form.formState.errors.custom_weather && (
                <p className="text-xs text-danger">{form.formState.errors.custom_weather.message}</p>
              )}
            </div>
          )}
          {lighting === "custom" && (
            <div className="grid gap-2">
              <Label htmlFor="custom-lighting">{sceneCopy.fields.customLighting}</Label>
              <Input id="custom-lighting" disabled={mutation.isPending} {...form.register("custom_lighting")} />
              {form.formState.errors.custom_lighting && (
                <p className="text-xs text-danger">{form.formState.errors.custom_lighting.message}</p>
              )}
            </div>
          )}
          <SelectField control={form.control} name="crowd_level" label={sceneCopy.fields.crowdLevel} options={crowdLevels} labels={sceneCopy.crowdLevel} />
          <TextAreaField id="scene-condition" label={sceneCopy.fields.environmentCondition} placeholder={sceneCopy.placeholders.environmentCondition} disabled={mutation.isPending} registration={form.register("environment_condition")} />
          <TextAreaField id="scene-state-prompt" label={sceneCopy.fields.promptState} placeholder={sceneCopy.placeholders.promptState} disabled={mutation.isPending} registration={form.register("prompt_state")} />

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

function SelectField({
  control,
  name,
  label,
  options,
  labels
}: {
  control: ReturnType<typeof useForm<SceneStateFormSchema>>["control"];
  name: keyof SceneStateFormSchema;
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

async function invalidateSceneStateScope(
  queryClient: ReturnType<typeof useQueryClient>,
  projectId: string,
  sceneId: string
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: sceneKeys.lists(projectId) }),
    queryClient.invalidateQueries({ queryKey: sceneKeys.detail(projectId, sceneId) }),
    queryClient.invalidateQueries({ queryKey: sceneKeys.states(projectId, sceneId) })
  ]);
}
