import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Copy,
  Edit,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Trash2
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Textarea } from "@/components/ui/textarea";
import { ConfirmDeleteDialog } from "@/features/characters/components/confirm-delete-dialog";
import { Badge } from "@/features/characters/components/status-badge";
import { KeyframeGenerationSection } from "@/features/keyframe-generation/components/keyframe-generation-section";
import { shotKeys } from "@/features/shots/api";
import { shotCopy } from "@/features/shots/copy";
import type {
  CharacterReferencePurpose,
  SceneReferencePurpose,
  Shot,
  ShotReference
} from "@/features/shots/types";
import { copy } from "@/locales";
import { ApiClientError } from "@/lib/api-client";

import {
  addKeyframeTaskReference,
  createKeyframeTask,
  deleteKeyframeTask,
  deleteKeyframeTaskReference,
  duplicateKeyframeTask,
  fetchKeyframeTask,
  fetchKeyframeTasks,
  markKeyframeTaskDraft,
  markKeyframeTaskReady,
  updateKeyframeTask,
  updateKeyframeTaskReference
} from "../api";
import { keyframeTaskCopy } from "../copy";
import {
  keyframeAspectRatioOptions,
  keyframeTaskFormSchema,
  taskFormValuesToPayload,
  type KeyframeTaskFormValues
} from "../schema";
import type {
  KeyframeTask,
  KeyframeTaskAspectRatio,
  KeyframeTaskReference,
  KeyframeTaskReferencePurpose
} from "../types";

const NONE = "__none";
const characterPurposes: CharacterReferencePurpose[] = [
  "identity",
  "appearance",
  "expression",
  "pose",
  "framing",
  "general"
];
const scenePurposes: SceneReferencePurpose[] = [
  "environment",
  "spatial",
  "composition",
  "lighting",
  "camera_reference",
  "general"
];
const aspectDefaults: Record<Exclude<KeyframeTaskAspectRatio, "custom">, [number, number]> = {
  "9:16": [768, 1360],
  "16:9": [1360, 768],
  "1:1": [1024, 1024],
  "4:3": [1024, 768],
  "3:4": [768, 1024]
};

export function KeyframeTaskPanel({
  projectId,
  shot,
  onMessage,
  invalidateShotData
}: {
  projectId: string;
  shot?: Shot;
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateShotData: (shotId?: string) => Promise<void>;
}) {
  const queryClient = useQueryClient();
  const [editingTask, setEditingTask] = useState<KeyframeTask | null>(null);
  const tasksQuery = useQuery({
    queryKey: shot ? shotKeys.keyframeTasks(projectId, shot.id) : ["keyframe-tasks", "none"],
    queryFn: () => fetchKeyframeTasks(projectId, shot?.id || ""),
    enabled: Boolean(projectId && shot?.id)
  });

  async function invalidateTaskData(taskId?: string) {
    await Promise.all([
      shot?.id
        ? queryClient.invalidateQueries({
            queryKey: shotKeys.keyframeTasks(projectId, shot.id)
          })
        : Promise.resolve(),
      taskId
        ? queryClient.invalidateQueries({
            queryKey: shotKeys.keyframeTask(projectId, taskId)
          })
        : Promise.resolve(),
      taskId
        ? queryClient.invalidateQueries({
            queryKey: shotKeys.keyframeTaskReferences(projectId, taskId)
          })
        : Promise.resolve(),
      invalidateShotData(shot?.id)
    ]);
  }

  const createMutation = useMutation({
    mutationFn: () =>
      createKeyframeTask(projectId, shot?.id || "", {
        copy_current_references: true
      }),
    onSuccess: async (task) => {
      await invalidateTaskData(task.id);
      setEditingTask(task);
      onMessage({ tone: "success", text: keyframeTaskCopy.created });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.saveFailed)
      })
  });
  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => deleteKeyframeTask(projectId, taskId),
    onSuccess: async () => {
      await invalidateTaskData();
      onMessage({ tone: "success", text: keyframeTaskCopy.deleted });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.deleteFailed)
      })
  });
  const duplicateMutation = useMutation({
    mutationFn: (taskId: string) => duplicateKeyframeTask(projectId, taskId),
    onSuccess: async (task) => {
      await invalidateTaskData(task.id);
      setEditingTask(task);
      onMessage({ tone: "success", text: keyframeTaskCopy.duplicated });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.saveFailed)
      })
  });
  const readyMutation = useMutation({
    mutationFn: (taskId: string) => markKeyframeTaskReady(projectId, taskId),
    onSuccess: async (task) => {
      await invalidateTaskData(task.id);
      onMessage({ tone: "success", text: keyframeTaskCopy.markedReady });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.saveFailed)
      })
  });
  const draftMutation = useMutation({
    mutationFn: (taskId: string) => markKeyframeTaskDraft(projectId, taskId),
    onSuccess: async (task) => {
      await invalidateTaskData(task.id);
      onMessage({ tone: "success", text: keyframeTaskCopy.markedDraft });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.saveFailed)
      })
  });

  const tasks = tasksQuery.data?.items ?? [];
  const busy =
    createMutation.isPending ||
    deleteMutation.isPending ||
    duplicateMutation.isPending ||
    readyMutation.isPending ||
    draftMutation.isPending;

  if (!shot) {
    return <p className="text-sm text-muted">{keyframeTaskCopy.emptyTitle}</p>;
  }

  if (tasksQuery.isLoading) {
    return <Skeleton className="h-80" />;
  }

  if (tasksQuery.isError) {
    return (
      <div className="grid gap-3 rounded-md border border-border bg-background p-3">
        <StatusMessage tone="error">{keyframeTaskCopy.loadFailed}</StatusMessage>
        <Button type="button" variant="secondary" onClick={() => void tasksQuery.refetch()}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          {copy.common.retry}
        </Button>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <div className="rounded-md border border-border bg-background p-3 text-xs leading-5 text-muted">
        <p>{keyframeTaskCopy.description}</p>
        <p className="mt-2">{keyframeTaskCopy.noGeneration}</p>
      </div>

      <Button type="button" onClick={() => createMutation.mutate()} disabled={busy}>
        <Plus className="h-4 w-4" aria-hidden="true" />
        {createMutation.isPending ? keyframeTaskCopy.creating : keyframeTaskCopy.create}
      </Button>

      {tasks.length === 0 ? (
        <EmptyState
          title={keyframeTaskCopy.emptyTitle}
          description={keyframeTaskCopy.emptyDescription}
        />
      ) : (
        <div className="grid gap-3">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              disabled={busy}
              onEdit={() => setEditingTask(task)}
              onReady={() => readyMutation.mutate(task.id)}
              onDraft={() => draftMutation.mutate(task.id)}
              onDuplicate={() => duplicateMutation.mutate(task.id)}
              onDelete={() => deleteMutation.mutateAsync(task.id)}
            />
          ))}
        </div>
      )}

      <KeyframeTaskEditorDialog
        projectId={projectId}
        shot={shot}
        task={editingTask}
        open={Boolean(editingTask)}
        onOpenChange={(open) => {
          if (!open) {
            setEditingTask(null);
          }
        }}
        onTaskUpdated={(task) => setEditingTask(task)}
        onMessage={onMessage}
        invalidateTaskData={invalidateTaskData}
      />
    </div>
  );
}

function TaskCard({
  task,
  disabled,
  onEdit,
  onReady,
  onDraft,
  onDuplicate,
  onDelete
}: {
  task: KeyframeTask;
  disabled: boolean;
  onEdit: () => void;
  onReady: () => void;
  onDraft: () => void;
  onDuplicate: () => void;
  onDelete: () => Promise<void>;
}) {
  const isReady = task.status === "ready";
  return (
    <article className="rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={isReady ? "success" : "default"}>{keyframeTaskCopy.status[task.status]}</Badge>
            <ReadinessBadge task={task} />
          </div>
          <h3 className="mt-2 break-words text-sm font-semibold text-foreground">{task.name}</h3>
          <p className="mt-1 text-xs text-muted">
            {task.aspect_ratio} · {task.width}×{task.height} · {task.reference_count} 张参考图
          </p>
        </div>
        <Button type="button" variant="secondary" size="icon" title={keyframeTaskCopy.edit} onClick={onEdit}>
          <Edit className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
      <IssueList task={task} />
      <div className="mt-3 flex flex-wrap gap-1">
        {isReady ? (
          <Button type="button" variant="secondary" size="sm" onClick={onDraft} disabled={disabled}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            {keyframeTaskCopy.markDraft}
          </Button>
        ) : (
          <Button type="button" variant="secondary" size="sm" onClick={onReady} disabled={disabled}>
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            {keyframeTaskCopy.markReady}
          </Button>
        )}
        <Button type="button" variant="secondary" size="sm" onClick={onDuplicate} disabled={disabled}>
          <Copy className="h-4 w-4" aria-hidden="true" />
          {keyframeTaskCopy.duplicate}
        </Button>
        <ConfirmDeleteDialog
          title={keyframeTaskCopy.delete}
          description={keyframeTaskCopy.deleteDescription(task.name)}
          onConfirm={onDelete}
          trigger={
            <Button type="button" variant="danger" size="sm" disabled={disabled}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {keyframeTaskCopy.delete}
            </Button>
          }
        />
      </div>
    </article>
  );
}

function KeyframeTaskEditorDialog({
  projectId,
  shot,
  task,
  open,
  onOpenChange,
  onTaskUpdated,
  onMessage,
  invalidateTaskData
}: {
  projectId: string;
  shot: Shot;
  task: KeyframeTask | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTaskUpdated: (task: KeyframeTask) => void;
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateTaskData: (taskId?: string) => Promise<void>;
}) {
  const queryClient = useQueryClient();
  const form = useForm<KeyframeTaskFormValues>({
    resolver: zodResolver(keyframeTaskFormSchema),
    defaultValues: taskToFormValues(task)
  });
  const [selectedShotReferenceId, setSelectedShotReferenceId] = useState(NONE);
  const selectedShotReference = useMemo(
    () => shot.references.find((reference) => reference.id === selectedShotReferenceId),
    [selectedShotReferenceId, shot.references]
  );
  const [selectedPurpose, setSelectedPurpose] = useState<KeyframeTaskReferencePurpose>("general");
  const purposeOptions = selectedShotReference?.reference_type === "scene" ? scenePurposes : characterPurposes;

  useEffect(() => {
    form.reset(taskToFormValues(task));
  }, [form, task]);

  useEffect(() => {
    const firstReference = shot.references[0];
    setSelectedShotReferenceId(firstReference?.id ?? NONE);
    setSelectedPurpose((firstReference?.purpose as KeyframeTaskReferencePurpose | undefined) ?? "general");
  }, [shot.references, task?.id]);

  const updateMutation = useMutation({
    mutationFn: (values: KeyframeTaskFormValues) =>
      updateKeyframeTask(projectId, task?.id || "", taskFormValuesToPayload(values)),
    onSuccess: async (updated) => {
      await invalidateTaskData(updated.id);
      onTaskUpdated(updated);
      onMessage({ tone: "success", text: keyframeTaskCopy.saved });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.saveFailed)
      })
  });
  const addReferenceMutation = useMutation({
    mutationFn: () =>
      addKeyframeTaskReference(projectId, task?.id || "", {
        shot_reference_id: selectedShotReferenceId,
        purpose: selectedPurpose
      }),
    onSuccess: async (updated) => {
      await invalidateTaskData(updated.id);
      onTaskUpdated(updated);
      onMessage({ tone: "success", text: keyframeTaskCopy.saved });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.referenceSaveFailed)
      })
  });
  const updateReferenceMutation = useMutation({
    mutationFn: ({
      reference,
      purpose,
      orderIndex
    }: {
      reference: KeyframeTaskReference;
      purpose?: KeyframeTaskReferencePurpose;
      orderIndex?: number;
    }) =>
      updateKeyframeTaskReference(projectId, task?.id || "", reference.id, {
        purpose,
        order_index: orderIndex
      }),
    onSuccess: async (updated) => {
      await invalidateTaskData(updated.id);
      onTaskUpdated(updated);
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.referenceSaveFailed)
      })
  });
  const deleteReferenceMutation = useMutation({
    mutationFn: (referenceId: string) =>
      deleteKeyframeTaskReference(projectId, task?.id || "", referenceId),
    onSuccess: async () => {
      await invalidateTaskData(task?.id);
      if (task?.id) {
        const refreshed = await queryClient.fetchQuery({
          queryKey: shotKeys.keyframeTask(projectId, task.id),
          queryFn: () => fetchKeyframeTask(projectId, task.id)
        });
        onTaskUpdated(refreshed);
      }
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeTaskCopy.referenceDeleteFailed)
      })
  });

  if (!task) {
    return null;
  }

  function handleAspectChange(value: string) {
    const aspectRatio = value as KeyframeTaskAspectRatio;
    form.setValue("aspect_ratio", aspectRatio, { shouldDirty: true });
    if (aspectRatio !== "custom") {
      const [width, height] = aspectDefaults[aspectRatio];
      form.setValue("width", String(width), { shouldDirty: true });
      form.setValue("height", String(height), { shouldDirty: true });
    }
  }

  function handleShotReferenceChange(value: string) {
    setSelectedShotReferenceId(value);
    const reference = shot.references.find((item) => item.id === value);
    setSelectedPurpose((reference?.purpose as KeyframeTaskReferencePurpose | undefined) ?? "general");
  }

  const canAddReference = selectedShotReferenceId !== NONE && !addReferenceMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[880px]">
        <DialogHeader>
          <DialogTitle>{keyframeTaskCopy.edit}</DialogTitle>
          <DialogDescription>{keyframeTaskCopy.hints.snapshot}</DialogDescription>
        </DialogHeader>
        <form
          className="grid gap-4"
          onSubmit={form.handleSubmit((values) => updateMutation.mutate(values))}
        >
          <div className="grid gap-3 md:grid-cols-2">
            <Field label={keyframeTaskCopy.fields.name}>
              <Input aria-label={keyframeTaskCopy.fields.name} {...form.register("name")} />
              <FormError>{form.formState.errors.name?.message}</FormError>
            </Field>
            <Field label={keyframeTaskCopy.fields.aspectRatio}>
              <Select value={form.watch("aspect_ratio")} onValueChange={handleAspectChange}>
                <SelectTrigger aria-label={keyframeTaskCopy.fields.aspectRatio}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {keyframeAspectRatioOptions.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label={keyframeTaskCopy.fields.width}>
              <Input aria-label={keyframeTaskCopy.fields.width} inputMode="numeric" {...form.register("width")} />
              <FormError>{form.formState.errors.width?.message}</FormError>
            </Field>
            <Field label={keyframeTaskCopy.fields.height}>
              <Input aria-label={keyframeTaskCopy.fields.height} inputMode="numeric" {...form.register("height")} />
              <FormError>{form.formState.errors.height?.message}</FormError>
            </Field>
            <Field label={keyframeTaskCopy.fields.seed}>
              <Input
                aria-label={keyframeTaskCopy.fields.seed}
                inputMode="numeric"
                placeholder="random"
                {...form.register("seed")}
              />
              <FieldHint>{keyframeTaskCopy.hints.seed}</FieldHint>
              <FormError>{form.formState.errors.seed?.message}</FormError>
            </Field>
            <Field label={keyframeTaskCopy.fields.steps}>
              <Input aria-label={keyframeTaskCopy.fields.steps} inputMode="numeric" {...form.register("steps")} />
              <FormError>{form.formState.errors.steps?.message}</FormError>
            </Field>
            <Field label={keyframeTaskCopy.fields.guidance}>
              <Input aria-label={keyframeTaskCopy.fields.guidance} inputMode="decimal" {...form.register("guidance_scale")} />
              <FormError>{form.formState.errors.guidance_scale?.message}</FormError>
            </Field>
            <Field label={keyframeTaskCopy.fields.outputCount}>
              <Input aria-label={keyframeTaskCopy.fields.outputCount} inputMode="numeric" {...form.register("output_count")} />
              <FormError>{form.formState.errors.output_count?.message}</FormError>
            </Field>
          </div>
          <Field label={keyframeTaskCopy.fields.promptZh}>
            <Textarea rows={5} {...form.register("prompt_zh")} />
            <FormError>{form.formState.errors.prompt_zh?.message}</FormError>
          </Field>
          <Field label={keyframeTaskCopy.fields.promptEn}>
            <Textarea rows={4} {...form.register("prompt_en")} />
            <FormError>{form.formState.errors.prompt_en?.message}</FormError>
          </Field>
          <Field label={keyframeTaskCopy.fields.negativePrompt}>
            <Textarea rows={3} {...form.register("negative_prompt")} />
            <FormError>{form.formState.errors.negative_prompt?.message}</FormError>
          </Field>
          <div className="grid gap-3 md:grid-cols-3">
            <Field label={keyframeTaskCopy.fields.provider}>
              <Input {...form.register("model_provider")} />
            </Field>
            <Field label={keyframeTaskCopy.fields.model}>
              <Input {...form.register("model_name")} />
            </Field>
            <Field label={keyframeTaskCopy.fields.modelVersion}>
              <Input {...form.register("model_version")} />
            </Field>
            <Field label={keyframeTaskCopy.fields.sampler}>
              <Input {...form.register("sampler_name")} />
            </Field>
            <Field label={keyframeTaskCopy.fields.scheduler}>
              <Input {...form.register("scheduler_name")} />
            </Field>
          </div>
          <FieldHint>{keyframeTaskCopy.hints.dimensions}</FieldHint>
          <FieldHint>{keyframeTaskCopy.hints.provider}</FieldHint>
          <div className="flex justify-end">
            <Button type="submit" disabled={updateMutation.isPending}>
              <Save className="h-4 w-4" aria-hidden="true" />
              {updateMutation.isPending ? keyframeTaskCopy.saving : keyframeTaskCopy.save}
            </Button>
          </div>
        </form>

        <KeyframeGenerationSection
          projectId={projectId}
          task={task}
          onMessage={onMessage}
          invalidateTaskData={invalidateTaskData}
        />

        <section className="grid gap-3 border-t border-border pt-4">
          <div>
            <h3 className="text-sm font-semibold text-foreground">{keyframeTaskCopy.addReferenceTitle}</h3>
            <p className="mt-1 text-xs text-muted">{keyframeTaskCopy.currentShotReferencesOnly}</p>
          </div>
          {shot.references.length === 0 ? (
            <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted">
              {keyframeTaskCopy.noShotReferences}
            </p>
          ) : (
            <div className="grid gap-2 md:grid-cols-[1fr_160px_auto]">
              <Select value={selectedShotReferenceId} onValueChange={handleShotReferenceChange}>
                <SelectTrigger aria-label={keyframeTaskCopy.fields.reference}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {shot.references.map((reference) => (
                    <SelectItem key={reference.id} value={reference.id}>
                      {shotReferenceLabel(reference)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={selectedPurpose}
                onValueChange={(value) => setSelectedPurpose(value as KeyframeTaskReferencePurpose)}
              >
                <SelectTrigger aria-label={keyframeTaskCopy.fields.purpose}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {purposeOptions.map((purpose) => (
                    <SelectItem key={purpose} value={purpose}>
                      {shotCopy.purposes[purpose]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                onClick={() => addReferenceMutation.mutate()}
                disabled={!canAddReference}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                {keyframeTaskCopy.addReference}
              </Button>
            </div>
          )}
        </section>

        <section className="grid gap-3 border-t border-border pt-4">
          <h3 className="text-sm font-semibold text-foreground">{keyframeTaskCopy.fields.reference}</h3>
          {task.references.length === 0 ? (
            <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted">
              {keyframeTaskCopy.noReferences}
            </p>
          ) : (
            <div className="grid gap-2">
              {task.references.map((reference) => (
                <TaskReferenceRow
                  key={reference.id}
                  reference={reference}
                  total={task.references.length}
                  disabled={updateReferenceMutation.isPending || deleteReferenceMutation.isPending}
                  onPurposeChange={(purpose) =>
                    updateReferenceMutation.mutate({ reference, purpose })
                  }
                  onMove={(orderIndex) =>
                    updateReferenceMutation.mutate({ reference, orderIndex })
                  }
                  onDelete={() => deleteReferenceMutation.mutateAsync(reference.id)}
                />
              ))}
            </div>
          )}
        </section>
      </DialogContent>
    </Dialog>
  );
}

function TaskReferenceRow({
  reference,
  total,
  disabled,
  onPurposeChange,
  onMove,
  onDelete
}: {
  reference: KeyframeTaskReference;
  total: number;
  disabled: boolean;
  onPurposeChange: (purpose: KeyframeTaskReferencePurpose) => void;
  onMove: (orderIndex: number) => void;
  onDelete: () => Promise<void>;
}) {
  const purposes = reference.reference_type === "scene" ? scenePurposes : characterPurposes;
  return (
    <article className="grid gap-3 rounded-md border border-border bg-background p-2 md:grid-cols-[96px_minmax(0,1fr)]">
      {reference.media_asset ? (
        <img
          src={reference.media_asset.thumbnail_url}
          alt=""
          className="aspect-video w-full rounded object-cover"
        />
      ) : (
        <div className="aspect-video rounded border border-dashed border-border" />
      )}
      <div className="grid gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>{reference.reference_type === "character" ? "人物" : "场景"}</Badge>
          {reference.source_reference_deleted && <Badge>{keyframeTaskCopy.sourceDeleted}</Badge>}
          <span className="text-xs text-muted">#{reference.order_index}</span>
        </div>
        <div className="grid gap-2 md:grid-cols-[1fr_auto]">
          <Select
            value={reference.purpose}
            onValueChange={(value) => onPurposeChange(value as KeyframeTaskReferencePurpose)}
            disabled={disabled}
          >
            <SelectTrigger aria-label={keyframeTaskCopy.fields.purpose}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {purposes.map((purpose) => (
                <SelectItem key={purpose} value={purpose}>
                  {shotCopy.purposes[purpose]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex gap-1">
            <Button
              type="button"
              variant="secondary"
              size="icon"
              title="上移"
              disabled={disabled || reference.order_index <= 1}
              onClick={() => onMove(reference.order_index - 1)}
            >
              <ArrowUp className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="icon"
              title="下移"
              disabled={disabled || reference.order_index >= total}
              onClick={() => onMove(reference.order_index + 1)}
            >
              <ArrowDown className="h-4 w-4" aria-hidden="true" />
            </Button>
            <ConfirmDeleteDialog
              title="移除任务参考图"
              description="确定从关键帧任务中移除这张参考图吗？原始资产和媒体文件不会被删除。"
              onConfirm={onDelete}
              trigger={
                <Button type="button" variant="danger" size="icon" title="移除参考图" disabled={disabled}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              }
            />
          </div>
        </div>
      </div>
    </article>
  );
}

function ReadinessBadge({ task }: { task: KeyframeTask }) {
  const ready = task.readiness.readiness_status === "ready";
  return (
    <Badge tone={ready ? "success" : "primary"}>
      {keyframeTaskCopy.readiness[task.readiness.readiness_status]}
    </Badge>
  );
}

function IssueList({ task }: { task: KeyframeTask }) {
  const blocking = task.readiness.blocking_issues;
  const warnings = task.readiness.warnings;
  if (blocking.length === 0 && warnings.length === 0) {
    return null;
  }
  return (
    <div className="mt-3 grid gap-2 text-xs">
      {blocking.length > 0 && (
        <div className="rounded-md border border-danger/40 bg-danger/10 p-2 text-danger">
          {blocking.map((issue) => keyframeTaskCopy.blockingIssues[issue]).join(" / ")}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="rounded-md border border-border bg-panel p-2 text-muted">
          {warnings.map((issue) => keyframeTaskCopy.warnings[issue]).join(" / ")}
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm">
      <span className="text-xs text-muted">{label}</span>
      {children}
    </label>
  );
}

function FieldHint({ children }: { children: ReactNode }) {
  return <span className="text-xs leading-5 text-muted">{children}</span>;
}

function FormError({ children }: { children?: string }) {
  return children ? <span className="text-xs text-danger">{children}</span> : null;
}

function taskToFormValues(task: KeyframeTask | null): KeyframeTaskFormValues {
  return {
    name: task?.name ?? "",
    prompt_zh: task?.prompt_zh ?? "",
    prompt_en: task?.prompt_en ?? "",
    negative_prompt: task?.negative_prompt ?? "",
    aspect_ratio: task?.aspect_ratio ?? "9:16",
    width: String(task?.width ?? 768),
    height: String(task?.height ?? 1360),
    seed: task?.seed === null || task?.seed === undefined ? "" : String(task.seed),
    steps: String(task?.steps ?? 30),
    guidance_scale: String(task?.guidance_scale ?? 7),
    sampler_name: task?.sampler_name ?? "",
    scheduler_name: task?.scheduler_name ?? "",
    model_provider: task?.model_provider ?? "",
    model_name: task?.model_name ?? "",
    model_version: task?.model_version ?? "",
    output_count: String(task?.output_count ?? 1)
  };
}

function shotReferenceLabel(reference: ShotReference) {
  const kind = reference.reference_type === "character" ? "人物" : "场景";
  const purpose =
    shotCopy.purposes[reference.purpose as keyof typeof shotCopy.purposes] ?? reference.purpose;
  const name =
    reference.reference_type === "character"
      ? reference.character_reference?.description || reference.media_asset?.original_filename
      : reference.scene_reference?.description || reference.media_asset?.original_filename;
  return `${kind} · ${purpose}${name ? ` · ${name}` : ""}`;
}

function getErrorText(error: unknown, fallback: string) {
  return error instanceof ApiClientError ? error.message : fallback;
}
