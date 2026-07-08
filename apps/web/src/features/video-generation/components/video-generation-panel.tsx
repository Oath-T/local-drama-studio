import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Download, Edit, ExternalLink, Play, Plus, RefreshCw, RotateCcw, Save, Star, Trash2, Upload, Wand2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm, type Resolver } from "react-hook-form";

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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Textarea } from "@/components/ui/textarea";
import { AssetPickerDialog } from "@/features/asset-picker/components/asset-picker-dialog";
import { assetPickerCopy } from "@/features/asset-picker/copy";
import type { PickerOptionItem } from "@/features/asset-picker/types";
import { VideoShotContextSummary } from "@/features/asset-summaries/components/asset-summary-cards";
import { ConfirmDeleteDialog } from "@/features/characters/components/confirm-delete-dialog";
import { Badge } from "@/features/characters/components/status-badge";
import { fetchKeyframeRuns } from "@/features/keyframe-generation/api";
import { fetchSystemCapabilities } from "@/features/keyframe-generation/api";
import type { KeyframeOutput } from "@/features/keyframe-generation/types";
import { fetchKeyframeTasks } from "@/features/keyframe-tasks/api";
import { buildPromptDraft } from "@/features/prompt-builder/api";
import { hasVideoPromptConflict, videoFieldsFromPromptDraft } from "@/features/prompt-builder/apply";
import { promptBuilderCopy } from "@/features/prompt-builder/copy";
import type { Shot } from "@/features/shots/types";
import { shotKeys } from "@/features/shots/api";
import { ApiClientError } from "@/lib/api-client";

import {
  createVideoTask,
  deleteVideoTask,
  fetchVideoRuns,
  fetchVideoTasks,
  fetchVideoWorkflows,
  markVideoTaskDraft,
  markVideoTaskReady,
  selectVideoOutput,
  startVideoRun,
  unselectVideoOutput,
  updateVideoTask,
  uploadVideoInputImage
} from "../api";
import { videoGenerationCopy, videoMissingRequirementText } from "../copy";
import {
  type ParsedVideoTaskFormValues,
  videoTaskFormSchema,
  videoTaskFormValuesToPayload,
  type VideoTaskFormValues
} from "../schema";
import type {
  VideoInputRole,
  VideoOutput,
  VideoRun,
  VideoTask,
  VideoTaskInputPayload,
  VideoWorkflow
} from "../types";

const ACTIVE_STATUSES = new Set(["queued", "running"]);
const NONE = "__none";

export function VideoGenerationPanel({
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
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [editingTaskId, setEditingTaskId] = useState("");
  const tasksQuery = useQuery({
    queryKey: shot ? shotKeys.videoTasks(projectId, shot.id) : ["video-tasks", "none"],
    queryFn: () => fetchVideoTasks(projectId, shot?.id || ""),
    enabled: Boolean(projectId && shot?.id)
  });
  const workflowsQuery = useQuery({
    queryKey: shotKeys.videoWorkflows(projectId),
    queryFn: () => fetchVideoWorkflows(projectId),
    enabled: Boolean(projectId)
  });
  const capabilitiesQuery = useQuery({
    queryKey: shotKeys.systemCapabilities(),
    queryFn: fetchSystemCapabilities
  });
  const keyframeTasksQuery = useQuery({
    queryKey: shot ? shotKeys.keyframeTasks(projectId, shot.id) : ["keyframe-tasks", "none"],
    queryFn: () => fetchKeyframeTasks(projectId, shot?.id || ""),
    enabled: Boolean(projectId && shot?.id)
  });
  const keyframeRunQueries = useQueries({
    queries: (keyframeTasksQuery.data?.items ?? []).map((task) => ({
      queryKey: shotKeys.keyframeRuns(projectId, task.id),
      queryFn: () => fetchKeyframeRuns(projectId, task.id),
      enabled: Boolean(task.id)
    }))
  });

  const tasks = tasksQuery.data?.items ?? [];
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null;
  const editingTask = tasks.find((task) => task.id === editingTaskId) ?? null;
  const selectedKeyframeOutputs = useMemo(
    () =>
      keyframeRunQueries.flatMap((query) =>
        (query.data?.items ?? []).flatMap((run) =>
          run.outputs
            .filter((output) => output.is_selected)
            .map((output) => ({ output, keyframeTaskId: run.keyframe_task_id }))
        )
      ),
    [keyframeRunQueries]
  );

  useEffect(() => {
    if (!selectedTaskId && tasks[0]) {
      setSelectedTaskId(tasks[0].id);
    }
    if (selectedTaskId && tasks.every((task) => task.id !== selectedTaskId)) {
      setSelectedTaskId(tasks[0]?.id ?? "");
    }
  }, [selectedTaskId, tasks]);

  const invalidateVideoData = async (taskId?: string) => {
    await Promise.all([
      shot?.id
        ? queryClient.invalidateQueries({ queryKey: shotKeys.videoTasks(projectId, shot.id) })
        : Promise.resolve(),
      taskId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.videoTask(projectId, taskId) })
        : Promise.resolve(),
      taskId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.videoRuns(projectId, taskId) })
        : Promise.resolve(),
      invalidateShotData(shot?.id)
    ]);
  };

  const createMutation = useMutation({
    mutationFn: (payload: Parameters<typeof createVideoTask>[2]) =>
      createVideoTask(projectId, shot?.id || "", payload),
    onSuccess: async (task) => {
      setSelectedTaskId(task.id);
      setEditingTaskId(task.id);
      await invalidateVideoData(task.id);
      onMessage({ tone: "success", text: videoGenerationCopy.created });
    },
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "视频任务创建失败") })
  });
  const uploadMutation = useMutation({
    mutationFn: ({ file }: { file: File; role: VideoInputRole }) =>
      uploadVideoInputImage(projectId, file),
    onSuccess: async (result, variables) => {
      if (selectedTask) {
        await updateVideoTask(projectId, selectedTask.id, {
          inputs: nextTaskInputs(selectedTask, variables.role, {
            media_asset_id: result.media_asset.id
          })
        });
        await invalidateVideoData(selectedTask.id);
      } else if (shot) {
        const created = await createVideoTask(projectId, shot.id, {
          inputs: [
            {
              role: variables.role,
              media_asset_id: result.media_asset.id
            }
          ]
        });
        setSelectedTaskId(created.id);
        await invalidateVideoData(created.id);
      }
      onMessage({ tone: "success", text: videoGenerationCopy.saved });
    },
    onError: (error) =>
      onMessage({ tone: "error", text: getErrorText(error, videoGenerationCopy.uploadFailed) })
  });

  if (!shot) return null;
  if (tasksQuery.isLoading) return <Skeleton className="h-80" />;
  if (tasksQuery.isError) {
    return (
      <section className="grid gap-3 border-t border-border pt-4">
        <StatusMessage tone="error">{videoGenerationCopy.loadFailed}</StatusMessage>
        <Button type="button" variant="secondary" onClick={() => void tasksQuery.refetch()}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          重新加载
        </Button>
      </section>
    );
  }

  return (
    <section className="grid gap-4 border-t border-border pt-4">
      <div>
        <h3 className="text-sm font-semibold text-foreground">{videoGenerationCopy.title}</h3>
        <p className="mt-1 text-xs leading-5 text-muted">{videoGenerationCopy.localOnly}</p>
        <p className="mt-1 text-xs leading-5 text-muted">{videoGenerationCopy.description}</p>
      </div>

      <div className="grid gap-2 rounded-md border border-border bg-background p-3">
        <div className="flex flex-wrap gap-2">
          <Button type="button" onClick={() => createMutation.mutate({})} disabled={createMutation.isPending}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {createMutation.isPending ? videoGenerationCopy.creating : videoGenerationCopy.create}
          </Button>
          <label className="inline-flex">
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="sr-only"
              onChange={(event) => {
                const file = event.currentTarget.files?.[0];
                if (file) uploadMutation.mutate({ file, role: "start_frame" });
                event.currentTarget.value = "";
              }}
            />
            <Button type="button" variant="secondary" disabled={uploadMutation.isPending} asChild>
              <span>
                <Upload className="h-4 w-4" aria-hidden="true" />
                {videoGenerationCopy.uploadStartFrame}
              </span>
            </Button>
          </label>
        </div>

        {selectedKeyframeOutputs.length === 0 ? (
          <p className="text-xs text-muted">{videoGenerationCopy.noKeyframeOutput}</p>
        ) : (
          <div className="grid gap-2">
            {selectedKeyframeOutputs.map(({ output, keyframeTaskId }) => (
              <KeyframeOutputButton
                key={output.id}
                output={output}
                disabled={createMutation.isPending}
                onUse={() =>
                  createMutation.mutate({
                    inputs: [
                      {
                        role: "start_frame",
                        source_keyframe_output_id: output.id,
                        source_keyframe_task_id: keyframeTaskId
                      }
                    ]
                  })
                }
              />
            ))}
          </div>
        )}
      </div>

      {tasks.length === 0 ? (
        <EmptyState
          title={videoGenerationCopy.noTasks}
          description={videoGenerationCopy.noTasksDescription}
        />
      ) : (
        <>
          <div className="grid gap-3">
            {tasks.map((task) => (
              <VideoTaskSummaryCard
                key={task.id}
                task={task}
                onOpen={() => {
                  setSelectedTaskId(task.id);
                  setEditingTaskId(task.id);
                }}
              />
            ))}
          </div>
          <Dialog open={Boolean(editingTask)} onOpenChange={(open) => !open && setEditingTaskId("")}>
            <DialogContent className="max-w-[920px]">
              <DialogHeader>
                <DialogTitle>{videoGenerationCopy.edit}</DialogTitle>
                <DialogDescription>
                  保存、标记就绪、开始生成、运行记录和视频输出都在这里处理。
                </DialogDescription>
              </DialogHeader>
              {editingTask && (
                <VideoTaskEditor
                  projectId={projectId}
                  shot={shot}
                  task={editingTask}
                  workflows={workflowsQuery.data?.items ?? []}
                  workflowsLoading={workflowsQuery.isLoading}
                  workflowsError={workflowsQuery.isError}
                  providerOnline={
                    capabilitiesQuery.data?.video_generation?.available === true &&
                    capabilitiesQuery.data.video_generation.status === "online"
                  }
                  onMessage={onMessage}
                  invalidateVideoData={invalidateVideoData}
                  onDeleted={() => {
                    setSelectedTaskId("");
                    setEditingTaskId("");
                  }}
                />
              )}
            </DialogContent>
          </Dialog>
        </>
      )}
    </section>
  );
}

function KeyframeOutputButton({
  output,
  disabled,
  onUse
}: {
  output: KeyframeOutput;
  disabled: boolean;
  onUse: () => void;
}) {
  const media = output.media_asset;
  return (
    <button
      type="button"
      className="grid grid-cols-[72px_minmax(0,1fr)] gap-2 rounded-md border border-border bg-panel p-2 text-left hover:border-primary disabled:opacity-60"
      disabled={disabled}
      onClick={onUse}
    >
      {media ? (
        <img src={media.thumbnail_url ?? media.content_url} alt="" className="aspect-video w-full rounded object-cover" />
      ) : (
        <div className="aspect-video rounded border border-dashed border-border" />
      )}
      <span className="text-xs text-foreground">{videoGenerationCopy.useKeyframeOutput}</span>
    </button>
  );
}

function VideoTaskSummaryCard({
  task,
  onOpen
}: {
  task: VideoTask;
  onOpen: () => void;
}) {
  const ready = task.status === "ready" && task.readiness.readiness_status === "ready";
  const activeRun = task.latest_run_status === "queued" || task.latest_run_status === "running";
  const startFrame = inputForRole(task, "start_frame");
  const endFrame = inputForRole(task, "end_frame");
  return (
    <article className="rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={task.status === "ready" ? "success" : "default"}>
              {videoGenerationCopy.status[task.status]}
            </Badge>
            <Badge tone={ready ? "success" : "primary"}>
              {videoGenerationCopy.readiness[task.readiness.readiness_status]}
            </Badge>
            {task.latest_run_status && (
              <Badge
                tone={
                  activeRun
                    ? "primary"
                    : task.latest_run_status === "completed"
                      ? "success"
                      : "default"
                }
              >
                {videoGenerationCopy.runStatus[task.latest_run_status]}
              </Badge>
            )}
            {task.selected_output && <Badge tone="success">{videoGenerationCopy.selected}</Badge>}
          </div>
          <h4 className="mt-2 truncate text-sm font-semibold text-foreground">{task.name}</h4>
          <p className="mt-1 line-clamp-2 text-xs text-muted">
            {task.prompt || "尚未填写视频提示词"}
          </p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
            <span>{task.duration_seconds}s</span>
            <span>{task.fps} fps</span>
            <span>
              {task.width}×{task.height}
            </span>
            <span>{task.workflow_id || "未选择工作流"}</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
            <span>{startFrame?.media_asset ? "起始帧已选" : "缺少起始帧"}</span>
            <span>{endFrame?.media_asset ? "结束帧已选" : "结束帧未选"}</span>
          </div>
        </div>
        <Button type="button" variant="secondary" onClick={onOpen}>
          <Edit className="h-4 w-4" aria-hidden="true" />
          查看 / 编辑
        </Button>
      </div>
    </article>
  );
}

function VideoTaskEditor({
  projectId,
  shot,
  task,
  workflows,
  workflowsLoading,
  workflowsError,
  providerOnline,
  onMessage,
  invalidateVideoData,
  onDeleted
}: {
  projectId: string;
  shot: Shot;
  task: VideoTask;
  workflows: VideoWorkflow[];
  workflowsLoading: boolean;
  workflowsError: boolean;
  providerOnline: boolean;
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateVideoData: (taskId?: string) => Promise<void>;
  onDeleted: () => void;
}) {
  const form = useForm<VideoTaskFormValues, unknown, ParsedVideoTaskFormValues>({
    resolver: zodResolver(videoTaskFormSchema) as Resolver<
      VideoTaskFormValues,
      unknown,
      ParsedVideoTaskFormValues
    >,
    defaultValues: taskToFormValues(task)
  });
  const runsQuery = useQuery({
    queryKey: shotKeys.videoRuns(projectId, task.id),
    queryFn: () => fetchVideoRuns(projectId, task.id),
    refetchInterval: (query) => (query.state.data?.items.some(isActiveRun) ? 2000 : false)
  });
  const selectedWorkflow = workflows.find((workflow) => workflow.workflow_id === form.watch("workflow_id"));
  const activeRun = runsQuery.data?.items.find(isActiveRun);
  const disabledReasons = generationDisabledReasons(task, providerOnline, selectedWorkflow, Boolean(activeRun));

  useEffect(() => {
    form.reset(taskToFormValues(task));
  }, [form, task]);

  useEffect(() => {
    if (!form.getValues("workflow_id") && workflows[0]) {
      form.setValue("workflow_id", workflows[0].workflow_id);
    }
  }, [form, workflows]);

  const updateMutation = useMutation({
    mutationFn: (values: ParsedVideoTaskFormValues) =>
      updateVideoTask(projectId, task.id, videoTaskFormValuesToPayload(values)),
    onSuccess: async (updated) => {
      await invalidateVideoData(updated.id);
      onMessage({ tone: "success", text: videoGenerationCopy.saved });
    },
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "视频任务保存失败") })
  });
  const promptDraftMutation = useMutation({
    mutationFn: () =>
      buildPromptDraft(projectId, shot.id, {
        target: "video",
        style: "cinematic_short_drama",
        language: "en",
        include_negative_prompt: true
      }),
    onSuccess: (draft) => {
      if (
        hasVideoPromptConflict(form.getValues()) &&
        !window.confirm(promptBuilderCopy.overwriteConfirm)
      ) {
        return;
      }
      const values = videoFieldsFromPromptDraft(draft);
      form.setValue("prompt", values.prompt, { shouldDirty: true, shouldTouch: true });
      form.setValue("negative_prompt", values.negative_prompt, {
        shouldDirty: true,
        shouldTouch: true
      });
      form.setValue("camera_motion", values.camera_motion, {
        shouldDirty: true,
        shouldTouch: true
      });
      onMessage({ tone: "success", text: promptBuilderCopy.videoFilled });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: promptBuilderCopy.loadFailed
      })
  });
  const readyMutation = useMutation({
    mutationFn: () => markVideoTaskReady(projectId, task.id),
    onSuccess: async (updated) => {
      await invalidateVideoData(updated.id);
      onMessage({ tone: "success", text: videoGenerationCopy.markedReady });
    },
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "视频任务尚未就绪") })
  });
  const draftMutation = useMutation({
    mutationFn: () => markVideoTaskDraft(projectId, task.id),
    onSuccess: async (updated) => {
      await invalidateVideoData(updated.id);
      onMessage({ tone: "success", text: videoGenerationCopy.markedDraft });
    }
  });
  const startMutation = useMutation({
    mutationFn: () => startVideoRun(projectId, task.id, { workflow_id: form.getValues("workflow_id") ?? "" }),
    onSuccess: async () => {
      await invalidateVideoData(task.id);
      onMessage({ tone: "success", text: videoGenerationCopy.generated });
    },
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, videoGenerationCopy.startFailed) })
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteVideoTask(projectId, task.id),
    onSuccess: async () => {
      onDeleted();
      await invalidateVideoData();
      onMessage({ tone: "success", text: videoGenerationCopy.deleted });
    }
  });
  const frameUploadMutation = useMutation({
    mutationFn: ({ file }: { file: File; role: VideoInputRole }) =>
      uploadVideoInputImage(projectId, file),
    onSuccess: async (result, variables) => {
      const updated = await updateVideoTask(projectId, task.id, {
        inputs: nextTaskInputs(task, variables.role, {
          media_asset_id: result.media_asset.id
        })
      });
      await invalidateVideoData(updated.id);
      onMessage({ tone: "success", text: videoGenerationCopy.saved });
    },
    onError: (error) =>
      onMessage({ tone: "error", text: getErrorText(error, videoGenerationCopy.uploadFailed) })
  });

  async function handleFrameAssetSelect(role: VideoInputRole, item: PickerOptionItem) {
    const keyframeOutputId =
      typeof item.metadata.keyframe_output_id === "string" ? item.metadata.keyframe_output_id : null;
    const keyframeTaskId =
      typeof item.metadata.keyframe_task_id === "string" ? item.metadata.keyframe_task_id : null;
    const mediaAssetId =
      typeof item.metadata.media_asset_id === "string" ? item.metadata.media_asset_id : item.id;
    try {
      const updated = await updateVideoTask(projectId, task.id, {
        inputs: nextTaskInputs(task, role, {
          media_asset_id: keyframeOutputId ? null : mediaAssetId,
          source_keyframe_output_id: keyframeOutputId,
          source_keyframe_task_id: keyframeTaskId
        })
      });
      await invalidateVideoData(updated.id);
      onMessage({ tone: "success", text: videoGenerationCopy.saved });
    } catch (error) {
      onMessage({ tone: "error", text: getErrorText(error, "视频任务保存失败") });
    }
  }

  const runs = runsQuery.data?.items ?? [];
  const outputs = runs.flatMap((run) => run.outputs.map((output) => ({ run, output })));
  const canStart = disabledReasons.length === 0 && !startMutation.isPending;

  return (
    <div className="grid gap-4 rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={task.status === "ready" ? "success" : "default"}>{videoGenerationCopy.status[task.status]}</Badge>
          <Badge tone={task.readiness.readiness_status === "ready" ? "success" : "primary"}>
            {videoGenerationCopy.readiness[task.readiness.readiness_status]}
          </Badge>
        </div>
        <ConfirmDeleteDialog
          title={videoGenerationCopy.delete}
          description={videoGenerationCopy.deleteDescription(task.name)}
          onConfirm={() => deleteMutation.mutateAsync()}
          trigger={
            <Button type="button" variant="danger" size="sm" disabled={deleteMutation.isPending}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {videoGenerationCopy.delete}
            </Button>
          }
        />
      </div>

      <VideoShotContextSummary shot={shot} task={task} />

      <FrameInputSlots
        projectId={projectId}
        shotId={shot.id}
        task={task}
        uploadingRole={frameUploadMutation.variables?.role}
        isUploading={frameUploadMutation.isPending}
        onUpload={(role, file) => frameUploadMutation.mutate({ role, file })}
        onSelectAsset={(role, item) => {
          void handleFrameAssetSelect(role, item);
        }}
      />

      <form className="grid gap-3" onSubmit={form.handleSubmit((values) => updateMutation.mutate(values))}>
        <Field label={videoGenerationCopy.fields.name}>
          <Input {...form.register("name")} />
          <FormError>{form.formState.errors.name?.message}</FormError>
        </Field>
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-border bg-background p-3">
          <div>
            <div className="text-sm font-medium text-foreground">
              {promptBuilderCopy.generateFromShot}
            </div>
            <p className="mt-1 text-xs text-muted">{promptBuilderCopy.safeNote}</p>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => promptDraftMutation.mutate()}
            disabled={promptDraftMutation.isPending}
          >
            <Wand2 className="h-4 w-4" aria-hidden="true" />
            {promptDraftMutation.isPending
              ? promptBuilderCopy.generating
              : promptBuilderCopy.fillVideo}
          </Button>
        </div>
        <Field label={videoGenerationCopy.fields.prompt}>
          <Textarea rows={4} {...form.register("prompt")} />
          <FormError>{form.formState.errors.prompt?.message}</FormError>
        </Field>
        <Field label={videoGenerationCopy.fields.negativePrompt}>
          <Textarea rows={2} {...form.register("negative_prompt")} />
        </Field>
        <div className="grid gap-2 md:grid-cols-2">
          <Field label={videoGenerationCopy.fields.duration}>
            <Input inputMode="decimal" {...form.register("duration_seconds")} />
            <FormError>{form.formState.errors.duration_seconds?.message}</FormError>
          </Field>
          <Field label={videoGenerationCopy.fields.fps}>
            <Input inputMode="numeric" {...form.register("fps")} />
            <FormError>{form.formState.errors.fps?.message}</FormError>
          </Field>
          <Field label={videoGenerationCopy.fields.width}>
            <Input inputMode="numeric" {...form.register("width")} />
            <FormError>{form.formState.errors.width?.message}</FormError>
          </Field>
          <Field label={videoGenerationCopy.fields.height}>
            <Input inputMode="numeric" {...form.register("height")} />
            <FormError>{form.formState.errors.height?.message}</FormError>
          </Field>
          <Field label={videoGenerationCopy.fields.seed}>
            <Input inputMode="numeric" placeholder="random" {...form.register("seed")} />
            <FormError>{form.formState.errors.seed?.message}</FormError>
          </Field>
          <Field label={videoGenerationCopy.fields.motionStrength}>
            <Input inputMode="decimal" placeholder="0-1" {...form.register("motion_strength")} />
            <FormError>{form.formState.errors.motion_strength?.message}</FormError>
          </Field>
        </div>
        <Field label={videoGenerationCopy.fields.cameraMotion}>
          <Input {...form.register("camera_motion")} />
        </Field>
        <Field label={videoGenerationCopy.workflow}>
          <Select value={form.watch("workflow_id") ?? NONE} onValueChange={(value) => form.setValue("workflow_id", value === NONE ? null : value, { shouldDirty: true })}>
            <SelectTrigger aria-label={videoGenerationCopy.workflow}><SelectValue /></SelectTrigger>
            <SelectContent>
              {workflows.map((workflow) => (
                <SelectItem key={workflow.workflow_id} value={workflow.workflow_id}>
                  {workflow.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {workflowsLoading && <span className="text-xs text-muted">正在加载工作流...</span>}
          {workflowsError && <span className="text-xs text-danger">{videoGenerationCopy.workflowLoadFailed}</span>}
          <WorkflowStatus workflow={selectedWorkflow} />
        </Field>
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={updateMutation.isPending}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {updateMutation.isPending ? videoGenerationCopy.saving : videoGenerationCopy.save}
          </Button>
          {task.status === "ready" ? (
            <Button type="button" variant="secondary" onClick={() => draftMutation.mutate()}>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              {videoGenerationCopy.markDraft}
            </Button>
          ) : (
            <Button type="button" variant="secondary" onClick={() => readyMutation.mutate()}>
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              {videoGenerationCopy.markReady}
            </Button>
          )}
          <Button type="button" onClick={() => startMutation.mutate()} disabled={!canStart}>
            <Play className="h-4 w-4" aria-hidden="true" />
            {startMutation.isPending ? videoGenerationCopy.starting : videoGenerationCopy.start}
          </Button>
        </div>
      </form>

      <IssueList task={task} disabledReasons={disabledReasons} providerOnline={providerOnline} />
      <RunList runs={runs} isLoading={runsQuery.isLoading} isError={runsQuery.isError} onRetry={() => void runsQuery.refetch()} />
      <OutputGallery projectId={projectId} taskId={task.id} items={outputs} onMessage={onMessage} invalidateVideoData={invalidateVideoData} />
    </div>
  );
}

function WorkflowStatus({ workflow }: { workflow?: VideoWorkflow }) {
  if (!workflow) return null;
  if (workflow.available) return <span className="text-xs text-success">{workflow.display_name} v{workflow.version} 可用</span>;
  return (
    <div className="grid gap-1 text-xs text-danger">
      {workflow.missing_requirements.map((item) => (
        <p key={item}>{videoMissingRequirementText(item)}</p>
      ))}
    </div>
  );
}

function FrameInputSlots({
  projectId,
  shotId,
  task,
  uploadingRole,
  isUploading,
  onUpload,
  onSelectAsset
}: {
  projectId: string;
  shotId: string;
  task: VideoTask;
  uploadingRole?: VideoInputRole;
  isUploading: boolean;
  onUpload: (role: VideoInputRole, file: File) => void;
  onSelectAsset: (role: VideoInputRole, item: PickerOptionItem) => void;
}) {
  const startInput = inputForRole(task, "start_frame");
  const endInput = inputForRole(task, "end_frame");
  return (
    <section className="grid gap-2 rounded-md border border-border bg-panel p-3">
      <div>
        <h4 className="text-xs font-semibold text-foreground">{videoGenerationCopy.frameInputs}</h4>
        <p className="mt-1 text-xs text-muted">{videoGenerationCopy.frameInputDescription}</p>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        <FrameInputSlot
          projectId={projectId}
          shotId={shotId}
          label={videoGenerationCopy.startFrame}
          taskInput={startInput}
          role="start_frame"
          uploadLabel={videoGenerationCopy.uploadStartFrame}
          isUploading={isUploading && uploadingRole === "start_frame"}
          onUpload={onUpload}
          onSelectAsset={onSelectAsset}
        />
        <FrameInputSlot
          projectId={projectId}
          shotId={shotId}
          label={videoGenerationCopy.endFrame}
          taskInput={endInput}
          role="end_frame"
          uploadLabel={videoGenerationCopy.uploadEndFrame}
          isUploading={isUploading && uploadingRole === "end_frame"}
          onUpload={onUpload}
          onSelectAsset={onSelectAsset}
        />
      </div>
    </section>
  );
}

function FrameInputSlot({
  projectId,
  shotId,
  label,
  taskInput,
  role,
  uploadLabel,
  isUploading,
  onUpload,
  onSelectAsset
}: {
  projectId: string;
  shotId: string;
  label: string;
  taskInput: VideoTask["inputs"][number] | undefined;
  role: VideoInputRole;
  uploadLabel: string;
  isUploading: boolean;
  onUpload: (role: VideoInputRole, file: File) => void;
  onSelectAsset: (role: VideoInputRole, item: PickerOptionItem) => void;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const media = taskInput?.media_asset ?? null;
  const pickerTitle =
    role === "start_frame" ? assetPickerCopy.chooseStartFrame : assetPickerCopy.chooseEndFrame;
  return (
    <div className="grid gap-2 rounded-md border border-border bg-background p-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-foreground">{label}</span>
        <div className="flex flex-wrap justify-end gap-1">
        <Button type="button" variant="secondary" size="sm" onClick={() => setPickerOpen(true)}>
          从资产选择
        </Button>
        <label className="inline-flex">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            aria-label={uploadLabel}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onUpload(role, file);
              event.currentTarget.value = "";
            }}
          />
          <Button type="button" variant="secondary" size="sm" disabled={isUploading} asChild>
            <span>
              <Upload className="h-4 w-4" aria-hidden="true" />
              {uploadLabel}
            </span>
          </Button>
        </label>
        </div>
      </div>
      <p className="text-xs leading-5 text-muted">{assetPickerCopy.frameDescription}</p>
      <AssetPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        projectId={projectId}
        scope="shot"
        assetType="frame_image"
        shotId={shotId}
        title={pickerTitle}
        description={assetPickerCopy.frameDescription}
        onConfirm={(item) => onSelectAsset(role, item)}
      />
      {media ? (
        <div className="grid grid-cols-[88px_minmax(0,1fr)] gap-2">
          <img
            src={media.thumbnail_url ?? media.content_url}
            alt=""
            className="aspect-video w-full rounded object-cover"
          />
          <div className="min-w-0 text-xs text-muted">
            <p className="truncate font-medium text-foreground">{media.original_filename}</p>
            <p>{media.width && media.height ? `${media.width} × ${media.height}` : media.mime_type}</p>
          </div>
        </div>
      ) : (
        <StatusMessage tone="neutral">{videoGenerationCopy.noFrameImage}</StatusMessage>
      )}
    </div>
  );
}

function IssueList({ task, disabledReasons, providerOnline }: { task: VideoTask; disabledReasons: string[]; providerOnline: boolean }) {
  const blocking = task.readiness.blocking_issues;
  const warnings = task.readiness.warnings;
  return (
    <div className="grid gap-2 text-xs">
      <Badge tone={providerOnline ? "success" : "default"}>
        {providerOnline ? videoGenerationCopy.providerStatus.online : videoGenerationCopy.providerStatus.offline}
      </Badge>
      {blocking.length > 0 && (
        <div className="rounded-md border border-danger/40 bg-danger/10 p-2 text-danger">
          {blocking.map((issue) => videoGenerationCopy.blockingIssues[issue]).join(" / ")}
        </div>
      )}
      {warnings.length > 0 && (
        <div className="rounded-md border border-border bg-panel p-2 text-muted">
          {warnings.map((issue) => videoGenerationCopy.warnings[issue]).join(" / ")}
        </div>
      )}
      {disabledReasons.length > 0 && <div className="text-muted">{disabledReasons.join(" / ")}</div>}
    </div>
  );
}

function RunList({ runs, isLoading, isError, onRetry }: { runs: VideoRun[]; isLoading: boolean; isError: boolean; onRetry: () => void }) {
  if (isLoading) return <Skeleton className="h-24" />;
  if (isError) return <StatusMessage tone="error">视频运行记录加载失败</StatusMessage>;
  return (
    <section className="grid gap-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-muted">{videoGenerationCopy.runList}</h4>
        <Button type="button" variant="secondary" size="sm" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          刷新
        </Button>
      </div>
      {runs.length === 0 ? (
        <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted">{videoGenerationCopy.noRuns}</p>
      ) : (
        runs.map((run) => (
          <article key={run.id} className="rounded-md border border-border bg-panel p-2 text-xs text-muted">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={run.status === "completed" ? "success" : "default"}>{videoGenerationCopy.runStatus[run.status]}</Badge>
              <span>#{run.run_number}</span>
              <span>seed {run.submitted_payload_snapshot.seed}</span>
            </div>
            {run.error_message_safe && <p className="mt-2 text-danger">{run.error_message_safe}</p>}
          </article>
        ))
      )}
    </section>
  );
}

function OutputGallery({
  projectId,
  taskId,
  items,
  onMessage,
  invalidateVideoData
}: {
  projectId: string;
  taskId: string;
  items: Array<{ run: VideoRun; output: VideoOutput }>;
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateVideoData: (taskId?: string) => Promise<void>;
}) {
  const selectMutation = useMutation({
    mutationFn: ({ output, selected }: { output: VideoOutput; selected: boolean }) =>
      selected ? unselectVideoOutput(projectId, output.id) : selectVideoOutput(projectId, output.id),
    onSuccess: async () => {
      await invalidateVideoData(taskId);
      onMessage({ tone: "success", text: videoGenerationCopy.selectUpdated });
    },
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, videoGenerationCopy.selectFailed) })
  });
  return (
    <section className="grid gap-2">
      <h4 className="text-xs font-semibold text-muted">{videoGenerationCopy.outputGallery}</h4>
      {items.length === 0 ? (
        <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted">{videoGenerationCopy.noOutputs}</p>
      ) : (
        <div className="grid gap-3">
          {items.map(({ output, run }) => (
            <article key={output.id} className="rounded-md border border-border bg-panel p-2">
              {output.media_asset ? (
                <video src={output.media_asset.content_url} controls className="aspect-video w-full rounded bg-black" />
              ) : (
                <div className="aspect-video rounded border border-dashed border-border" />
              )}
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                {output.is_selected && <Badge tone="success">{videoGenerationCopy.selected}</Badge>}
                <span>Run #{run.run_number}</span>
                <span>{output.duration_seconds ?? run.submitted_payload_snapshot.duration_seconds}s</span>
                <span>{output.fps ?? run.submitted_payload_snapshot.fps} fps</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1">
                <Button type="button" variant="secondary" size="sm" disabled={selectMutation.isPending} onClick={() => selectMutation.mutate({ output, selected: output.is_selected })}>
                  <Star className="h-4 w-4" aria-hidden="true" />
                  {output.is_selected ? videoGenerationCopy.unselect : videoGenerationCopy.useVersion}
                </Button>
                {output.media_asset && (
                  <>
                    <Button type="button" variant="secondary" size="sm" asChild>
                      <a href={output.media_asset.content_url} target="_blank" rel="noreferrer">
                        <ExternalLink className="h-4 w-4" aria-hidden="true" />
                        {videoGenerationCopy.openOriginal}
                      </a>
                    </Button>
                    <Button type="button" variant="secondary" size="sm" asChild>
                      <a href={output.media_asset.content_url} download>
                        <Download className="h-4 w-4" aria-hidden="true" />
                        {videoGenerationCopy.download}
                      </a>
                    </Button>
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function generationDisabledReasons(
  task: VideoTask,
  providerOnline: boolean,
  workflow: VideoWorkflow | undefined,
  hasActiveRun: boolean
): string[] {
  const reasons: string[] = [];
  if (task.status !== "ready") reasons.push(videoGenerationCopy.disabledReasons.notReadyStatus);
  if (task.readiness.readiness_status !== "ready") reasons.push(videoGenerationCopy.disabledReasons.notReadyReadiness);
  if (!providerOnline) reasons.push(videoGenerationCopy.disabledReasons.providerOffline);
  if (!workflow) reasons.push(videoGenerationCopy.disabledReasons.workflowMissing);
  if (workflow && !workflow.available) reasons.push(videoGenerationCopy.disabledReasons.workflowUnavailable);
  if (hasActiveRun) reasons.push(videoGenerationCopy.disabledReasons.activeRun);
  return reasons;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm">
      <span className="text-xs text-muted">{label}</span>
      {children}
    </label>
  );
}

function FormError({ children }: { children?: string }) {
  return children ? <span className="text-xs text-danger">{children}</span> : null;
}

function taskToFormValues(task: VideoTask): VideoTaskFormValues {
  return {
    name: task.name,
    prompt: task.prompt ?? "",
    negative_prompt: task.negative_prompt ?? "",
    duration_seconds: String(task.duration_seconds),
    fps: String(task.fps),
    width: String(task.width),
    height: String(task.height),
    seed: task.seed === null ? "" : String(task.seed),
    motion_strength: task.motion_strength === null ? "" : String(task.motion_strength),
    camera_motion: task.camera_motion ?? "",
    workflow_id: task.workflow_id
  };
}

function inputForRole(task: VideoTask, role: VideoInputRole) {
  return task.inputs.find((input) => input.role === role);
}

function nextTaskInputs(
  task: VideoTask,
  role: VideoInputRole,
  nextInput: Omit<VideoTaskInputPayload, "role">
): VideoTaskInputPayload[] {
  const byRole = new Map<VideoInputRole, VideoTaskInputPayload>();
  for (const input of task.inputs) {
    if (
      input.media_asset_id ||
      input.source_keyframe_output_id ||
      input.source_keyframe_task_id
    ) {
      byRole.set(input.role, {
        role: input.role,
        media_asset_id: input.media_asset_id,
        source_keyframe_output_id: input.source_keyframe_output_id,
        source_keyframe_task_id: input.source_keyframe_task_id
      });
    }
  }
  byRole.set(role, {
    role,
    media_asset_id: nextInput.media_asset_id ?? null,
    source_keyframe_output_id: nextInput.source_keyframe_output_id ?? null,
    source_keyframe_task_id: nextInput.source_keyframe_task_id ?? null
  });
  return Array.from(byRole.values()).sort((left, right) => roleOrder(left.role) - roleOrder(right.role));
}

function roleOrder(role: VideoInputRole): number {
  return role === "start_frame" ? 1 : 2;
}

function isActiveRun(run: VideoRun): boolean {
  return ACTIVE_STATUSES.has(run.status);
}

function getErrorText(error: unknown, fallback: string) {
  return error instanceof ApiClientError ? error.message : fallback;
}
