import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Film, Play, Save, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/features/characters/components/status-badge";
import {
  fetchKeyframeRuns,
  fetchKeyframeWorkflows,
  fetchSystemCapabilities,
  selectKeyframeOutput,
  startKeyframeRun
} from "@/features/keyframe-generation/api";
import type { KeyframeOutput, KeyframeRun } from "@/features/keyframe-generation/types";
import {
  addKeyframeTaskReference,
  createKeyframeTask,
  fetchKeyframeTasks,
  markKeyframeTaskReady,
  updateKeyframeTask
} from "@/features/keyframe-tasks/api";
import type {
  KeyframeTask,
  KeyframeTaskPurpose,
  KeyframeTaskReferencePurpose
} from "@/features/keyframe-tasks/types";
import { buildPromptDraft } from "@/features/prompt-builder/api";
import type { PromptDraftResponse } from "@/features/prompt-builder/types";
import { fetchShotReferences, shotKeys } from "@/features/shots/api";
import type { Shot } from "@/features/shots/types";
import {
  createVideoTask,
  fetchVideoRuns,
  fetchVideoTasks,
  fetchVideoWorkflows,
  markVideoTaskReady,
  selectVideoOutput,
  startVideoRun,
  updateVideoTask
} from "@/features/video-generation/api";
import type { VideoOutput, VideoRun, VideoTask, VideoWorkflow } from "@/features/video-generation/types";
import { ApiClientError } from "@/lib/api-client";

type MessageTone = "success" | "error" | "neutral";

const activeRunStatuses = new Set(["queued", "running"]);
const quickKeyframeDefaults = {
  width: 768,
  height: 1360,
  output_count: 1,
  steps: 28,
  guidance_scale: 6.5
};
const quickVideoDefaults = {
  duration_seconds: 2,
  fps: 16,
  width: 640,
  height: 640,
  motion_strength: 0.45
};

export function CanvasQuickGeneratePanel({ projectId, shot }: { projectId: string; shot: Shot }) {
  const queryClient = useQueryClient();
  const [firstPrompt, setFirstPrompt] = useState(shot.visual_description ?? "");
  const [endPrompt, setEndPrompt] = useState(shot.visual_description ?? "");
  const [videoPrompt, setVideoPrompt] = useState(shot.action_summary ?? shot.visual_description ?? "");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [cameraMotion, setCameraMotion] = useState(shot.custom_camera_movement ?? "");
  const [message, setMessage] = useState<{ tone: MessageTone; text: string } | null>(null);

  const capabilitiesQuery = useQuery({
    queryKey: shotKeys.systemCapabilities(),
    queryFn: fetchSystemCapabilities
  });
  const keyframeWorkflowsQuery = useQuery({
    queryKey: shotKeys.keyframeWorkflows(projectId),
    queryFn: () => fetchKeyframeWorkflows(projectId)
  });
  const videoWorkflowsQuery = useQuery({
    queryKey: shotKeys.videoWorkflows(projectId),
    queryFn: () => fetchVideoWorkflows(projectId)
  });
  const keyframeTasksQuery = useQuery({
    queryKey: shotKeys.keyframeTasks(projectId, shot.id),
    queryFn: () => fetchKeyframeTasks(projectId, shot.id)
  });
  const shotReferencesQuery = useQuery({
    queryKey: shotKeys.references(projectId, shot.id),
    queryFn: () => fetchShotReferences(projectId, shot.id)
  });
  const videoTasksQuery = useQuery({
    queryKey: shotKeys.videoTasks(projectId, shot.id),
    queryFn: () => fetchVideoTasks(projectId, shot.id)
  });

  const keyframeTasks = keyframeTasksQuery.data?.items ?? [];
  const videoTasks = videoTasksQuery.data?.items ?? [];
  const firstTask = keyframeTasks.find((task) => task.purpose === "first_frame") ?? null;
  const endTask = keyframeTasks.find((task) => task.purpose === "end_frame") ?? null;
  const videoTask = videoTasks[0] ?? null;

  const keyframeRunQueries = useQueries({
    queries: keyframeTasks.map((task) => ({
      queryKey: shotKeys.keyframeRuns(projectId, task.id),
      queryFn: () => fetchKeyframeRuns(projectId, task.id),
      enabled: Boolean(task.id),
      refetchInterval: (query: { state: { data?: { items: KeyframeRun[] } } }) =>
        query.state.data?.items.some(isActiveRun) ? 2000 : false
    }))
  });
  const videoRunQueries = useQueries({
    queries: videoTasks.map((task) => ({
      queryKey: shotKeys.videoRuns(projectId, task.id),
      queryFn: () => fetchVideoRuns(projectId, task.id),
      enabled: Boolean(task.id),
      refetchInterval: (query: { state: { data?: { items: VideoRun[] } } }) =>
        query.state.data?.items.some(isActiveRun) ? 2000 : false
    }))
  });

  const keyframeRunsByTask = useMemo(() => {
    const map = new Map<string, KeyframeRun[]>();
    keyframeTasks.forEach((task, index) => {
      map.set(task.id, keyframeRunQueries[index]?.data?.items ?? []);
    });
    return map;
  }, [keyframeRunQueries, keyframeTasks]);
  const videoRunsByTask = useMemo(() => {
    const map = new Map<string, VideoRun[]>();
    videoTasks.forEach((task, index) => {
      map.set(task.id, videoRunQueries[index]?.data?.items ?? []);
    });
    return map;
  }, [videoRunQueries, videoTasks]);

  const firstOutputs = outputsForTask(firstTask, keyframeRunsByTask);
  const endOutputs = outputsForTask(endTask, keyframeRunsByTask);
  const selectedFirstOutput = firstOutputs.find((output) => output.is_selected) ?? null;
  const selectedEndOutput = endOutputs.find((output) => output.is_selected) ?? null;
  const videoOutputs = videoTask ? (videoRunsByTask.get(videoTask.id) ?? []).flatMap((run) => run.outputs) : [];
  const selectedVideoOutput = videoOutputs.find((output) => output.is_selected) ?? videoTask?.selected_output ?? null;

  const promptDraftMutation = useMutation({
    mutationFn: () => buildPromptDraft(projectId, shot.id, { target: "all", include_negative_prompt: true }),
    onSuccess: (draft) => {
      applyPromptDraft(draft);
      setMessage({ tone: "success", text: "已根据镜头上下文生成可编辑 Prompt。" });
    },
    onError: (error) =>
      setMessage({ tone: "error", text: getErrorText(error, "Prompt 草稿生成失败。") })
  });
  const firstGenerateMutation = useMutation({
    mutationFn: () => generateKeyframe("first_frame", firstPrompt),
    onSuccess: () => setMessage({ tone: "success", text: "首帧生成已提交，请在候选区等待结果。" }),
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "首帧生成失败。") })
  });
  const endGenerateMutation = useMutation({
    mutationFn: () => generateKeyframe("end_frame", endPrompt),
    onSuccess: () => setMessage({ tone: "success", text: "尾帧生成已提交，请在候选区等待结果。" }),
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "尾帧生成失败。") })
  });
  const selectKeyframeMutation = useMutation({
    mutationFn: (outputId: string) => selectKeyframeOutput(projectId, outputId),
    onSuccess: async () => {
      await invalidateAll();
      setMessage({ tone: "success", text: "候选图已采用。" });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "采用候选图失败。") })
  });
  const videoGenerateMutation = useMutation({
    mutationFn: generateVideo,
    onSuccess: () => setMessage({ tone: "success", text: "视频生成已提交，请在候选区等待结果。" }),
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "视频生成失败。") })
  });
  const selectVideoMutation = useMutation({
    mutationFn: (outputId: string) => selectVideoOutput(projectId, outputId),
    onSuccess: async () => {
      await invalidateAll();
      setMessage({ tone: "success", text: "视频输出已采用。" });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "采用视频失败。") })
  });

  useEffect(() => {
    setFirstPrompt((value) => value || shot.visual_description || "");
    setEndPrompt((value) => value || shot.visual_description || "");
    setVideoPrompt((value) => value || shot.action_summary || shot.visual_description || "");
  }, [shot.action_summary, shot.visual_description]);

  const keyframeProviderOnline =
    capabilitiesQuery.data?.keyframe_generation?.available === true &&
    capabilitiesQuery.data.keyframe_generation.status === "online";
  const videoProviderOnline =
    capabilitiesQuery.data?.video_generation?.available === true &&
    capabilitiesQuery.data.video_generation.status === "online";
  const keyframeWorkflow = keyframeWorkflowsQuery.data?.items.find((workflow) => workflow.available) ?? null;
  const videoWorkflow = preferredVideoWorkflow(videoWorkflowsQuery.data?.items ?? []);
  const firstActive = firstTask ? (keyframeRunsByTask.get(firstTask.id) ?? []).some(isActiveRun) : false;
  const endActive = endTask ? (keyframeRunsByTask.get(endTask.id) ?? []).some(isActiveRun) : false;
  const videoActive = videoTask ? (videoRunsByTask.get(videoTask.id) ?? []).some(isActiveRun) : false;

  async function invalidateAll(taskId?: string) {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: shotKeys.keyframeTasks(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.videoTasks(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.detail(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.references(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.lists(projectId) }),
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "generation-tasks"] }),
      ...keyframeTasks.map((task) =>
        queryClient.invalidateQueries({ queryKey: shotKeys.keyframeRuns(projectId, task.id) })
      ),
      ...videoTasks.map((task) =>
        queryClient.invalidateQueries({ queryKey: shotKeys.videoRuns(projectId, task.id) })
      ),
      taskId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.keyframeRuns(projectId, taskId) })
        : Promise.resolve()
    ]);
  }

  function applyPromptDraft(draft: PromptDraftResponse) {
    setFirstPrompt(draft.first_frame_prompt_en);
    setEndPrompt(draft.end_frame_prompt_en);
    setVideoPrompt(draft.motion_prompt_en);
    setNegativePrompt(draft.negative_prompt_en);
    setCameraMotion(draft.camera_motion ?? "");
  }

  async function ensureKeyframeTask(purpose: KeyframeTaskPurpose) {
    const existing = keyframeTasks.find((task) => task.purpose === purpose);
    if (existing) return syncKeyframeTaskReferences(existing);
    const created = await createKeyframeTask(projectId, shot.id, {
      purpose,
      copy_current_references: true
    });
    await invalidateAll(created.id);
    return created;
  }

  async function syncKeyframeTaskReferences(task: KeyframeTask) {
    const shotReferences = shotReferencesQuery.data?.items ?? [];
    const existingShotReferenceIds = new Set(
      task.references.map((reference) => reference.shot_reference_id).filter(Boolean)
    );
    const missingReferences = shotReferences.filter(
      (reference) => !existingShotReferenceIds.has(reference.id)
    );
    let nextTask = task;
    for (const reference of missingReferences) {
      nextTask = await addKeyframeTaskReference(projectId, task.id, {
        shot_reference_id: reference.id,
        purpose: reference.purpose as KeyframeTaskReferencePurpose
      });
    }
    if (missingReferences.length > 0) await invalidateAll(task.id);
    return nextTask;
  }

  async function generateKeyframe(purpose: KeyframeTaskPurpose, prompt: string) {
    if (!keyframeProviderOnline) throw new Error("关键帧生成服务当前不可用。");
    if (!keyframeWorkflow) throw new Error("没有可用的关键帧工作流。");
    if (!prompt.trim()) throw new Error("请先填写 Prompt。");
    const task = await ensureKeyframeTask(purpose);
    const updated = await updateKeyframeTask(projectId, task.id, {
      name: purpose === "first_frame" ? `${shot.name} 首帧` : `${shot.name} 尾帧`,
      purpose,
      prompt_en: prompt.trim(),
      negative_prompt: negativePrompt.trim() || null,
      aspect_ratio: "9:16",
      ...quickKeyframeDefaults
    });
    await markKeyframeTaskReady(projectId, updated.id);
    await startKeyframeRun(projectId, updated.id, { workflow_id: keyframeWorkflow.workflow_id });
    await invalidateAll(updated.id);
  }

  async function generateVideo() {
    if (!videoProviderOnline) throw new Error("视频生成服务当前不可用。");
    if (!videoWorkflow) throw new Error("没有可用的视频工作流。");
    if (!selectedFirstOutput || !selectedEndOutput || !firstTask || !endTask) {
      throw new Error("请先采用首帧和尾帧候选。");
    }
    if (!videoPrompt.trim()) throw new Error("请先填写视频 Prompt。");
    const task =
      videoTask ??
      (await createVideoTask(projectId, shot.id, {
        inputs: [
          {
            role: "start_frame",
            source_keyframe_output_id: selectedFirstOutput.id,
            source_keyframe_task_id: firstTask.id
          },
          {
            role: "end_frame",
            source_keyframe_output_id: selectedEndOutput.id,
            source_keyframe_task_id: endTask.id
          }
        ]
      }));
    const updated = await updateVideoTask(projectId, task.id, {
      name: `${shot.name} 首尾帧视频`,
      inputs: [
        {
          role: "start_frame",
          source_keyframe_output_id: selectedFirstOutput.id,
          source_keyframe_task_id: firstTask.id
        },
        {
          role: "end_frame",
          source_keyframe_output_id: selectedEndOutput.id,
          source_keyframe_task_id: endTask.id
        }
      ],
      prompt: videoPrompt.trim(),
      negative_prompt: negativePrompt.trim() || null,
      duration_seconds: shot.duration_seconds && shot.duration_seconds > 0 ? shot.duration_seconds : quickVideoDefaults.duration_seconds,
      fps: quickVideoDefaults.fps,
      width: quickVideoDefaults.width,
      height: quickVideoDefaults.height,
      seed: null,
      motion_strength: quickVideoDefaults.motion_strength,
      camera_motion: cameraMotion.trim() || null,
      workflow_id: videoWorkflow.workflow_id
    });
    await markVideoTaskReady(projectId, updated.id);
    await startVideoRun(projectId, updated.id, { workflow_id: videoWorkflow.workflow_id });
    await invalidateAll();
  }

  const loading = keyframeTasksQuery.isLoading || shotReferencesQuery.isLoading || videoTasksQuery.isLoading;
  const busy =
    promptDraftMutation.isPending ||
    firstGenerateMutation.isPending ||
    endGenerateMutation.isPending ||
    selectKeyframeMutation.isPending ||
    videoGenerateMutation.isPending ||
    selectVideoMutation.isPending;

  if (loading) return <Skeleton className="h-80" />;

  return (
    <div className="grid gap-3">
      <StatusMessage tone="neutral">
        画布快速生成会复用现有关键帧和视频任务，不会修改 ComfyUI workflow，也不会自动采用结果。
      </StatusMessage>
      {message && <StatusMessage tone={message.tone}>{message.text}</StatusMessage>}

      <section className="grid gap-2 rounded-md border border-border bg-panel p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h4 className="text-sm font-semibold text-foreground">参考素材</h4>
            <p className="text-xs text-muted">
              已绑定 {shot.character_count} 个人物 / {shot.reference_count} 张参考图 / 场景：
              {shot.scene?.name ?? "未设置"}
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => promptDraftMutation.mutate()}
            disabled={promptDraftMutation.isPending}
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            生成 Prompt 草稿
          </Button>
        </div>
      </section>

      <FrameQuickSection
        title="首帧"
        promptLabel="首帧 Prompt"
        prompt={firstPrompt}
        onPromptChange={setFirstPrompt}
        providerOnline={keyframeProviderOnline}
        workflowName={keyframeWorkflow?.display_name ?? "暂无可用工作流"}
        active={firstActive}
        outputs={firstOutputs}
        selectedOutputId={selectedFirstOutput?.id ?? null}
        busy={busy}
        onGenerate={() => firstGenerateMutation.mutate()}
        onSelect={(outputId) => selectKeyframeMutation.mutate(outputId)}
      />

      <FrameQuickSection
        title="尾帧"
        promptLabel="尾帧 Prompt"
        prompt={endPrompt}
        onPromptChange={setEndPrompt}
        providerOnline={keyframeProviderOnline}
        workflowName={keyframeWorkflow?.display_name ?? "暂无可用工作流"}
        active={endActive}
        outputs={endOutputs}
        selectedOutputId={selectedEndOutput?.id ?? null}
        busy={busy}
        onGenerate={() => endGenerateMutation.mutate()}
        onSelect={(outputId) => selectKeyframeMutation.mutate(outputId)}
      />

      <section className="grid gap-3 rounded-md border border-border bg-background p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h4 className="text-sm font-semibold text-foreground">视频</h4>
            <p className="text-xs text-muted">
              {videoWorkflow
                ? `${videoWorkflow.display_name} v${videoWorkflow.version}`
                : "暂无可用视频工作流"}
            </p>
          </div>
          <Badge tone={videoProviderOnline ? "success" : "default"}>
            {videoProviderOnline ? "视频服务可用" : "视频服务不可用"}
          </Badge>
        </div>
        <Textarea
          aria-label="视频 Prompt"
          value={videoPrompt}
          onChange={(event) => setVideoPrompt(event.target.value)}
          rows={4}
        />
        <Textarea
          aria-label="反向 Prompt"
          value={negativePrompt}
          onChange={(event) => setNegativePrompt(event.target.value)}
          rows={3}
        />
        <Textarea
          aria-label="镜头运动"
          value={cameraMotion}
          onChange={(event) => setCameraMotion(event.target.value)}
          rows={2}
        />
        <div className="grid gap-1 text-xs text-muted">
          <p>首帧：{selectedFirstOutput ? "已采用" : "未采用"}</p>
          <p>尾帧：{selectedEndOutput ? "已采用" : "未采用"}</p>
        </div>
        <Button
          type="button"
          onClick={() => videoGenerateMutation.mutate()}
          disabled={busy || videoActive || !selectedFirstOutput || !selectedEndOutput || !videoProviderOnline || !videoWorkflow}
        >
          <Film className="h-4 w-4" aria-hidden="true" />
          {videoGenerateMutation.isPending ? "提交中" : videoActive ? "视频生成中" : "生成视频"}
        </Button>
        <OutputGrid
          outputs={videoOutputs}
          selectedOutputId={selectedVideoOutput?.id ?? null}
          busy={busy}
          emptyText="暂无视频候选"
          onSelect={(outputId) => selectVideoMutation.mutate(outputId)}
          mediaType="video"
        />
      </section>
    </div>
  );
}

function FrameQuickSection({
  title,
  promptLabel,
  prompt,
  onPromptChange,
  providerOnline,
  workflowName,
  active,
  outputs,
  selectedOutputId,
  busy,
  onGenerate,
  onSelect
}: {
  title: string;
  promptLabel: string;
  prompt: string;
  onPromptChange: (value: string) => void;
  providerOnline: boolean;
  workflowName: string;
  active: boolean;
  outputs: KeyframeOutput[];
  selectedOutputId: string | null;
  busy: boolean;
  onGenerate: () => void;
  onSelect: (outputId: string) => void;
}) {
  return (
    <section className="grid gap-3 rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-foreground">{title}</h4>
          <p className="text-xs text-muted">{workflowName}</p>
        </div>
        <Badge tone={providerOnline ? "success" : "default"}>
          {providerOnline ? "关键帧服务可用" : "关键帧服务不可用"}
        </Badge>
      </div>
      <Textarea
        aria-label={promptLabel}
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        rows={4}
      />
      <Button type="button" onClick={onGenerate} disabled={busy || active || !providerOnline}>
        <Play className="h-4 w-4" aria-hidden="true" />
        {active ? `${title}生成中` : `生成${title}`}
      </Button>
      <OutputGrid
        outputs={outputs}
        selectedOutputId={selectedOutputId}
        busy={busy}
        emptyText={`暂无${title}候选`}
        onSelect={onSelect}
        mediaType="image"
      />
    </section>
  );
}

function OutputGrid({
  outputs,
  selectedOutputId,
  busy,
  emptyText,
  onSelect,
  mediaType
}: {
  outputs: Array<KeyframeOutput | VideoOutput>;
  selectedOutputId: string | null;
  busy: boolean;
  emptyText: string;
  onSelect: (outputId: string) => void;
  mediaType: "image" | "video";
}) {
  if (outputs.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted">
        {emptyText}
      </div>
    );
  }
  return (
    <div className="grid gap-2">
      {outputs.map((output) => {
        const media = output.media_asset;
        const selected = output.id === selectedOutputId || output.is_selected;
        return (
          <article key={output.id} className="rounded-md border border-border bg-panel p-2">
            <div className="aspect-video overflow-hidden rounded border border-border bg-background">
              {media ? (
                mediaType === "video" ? (
                  <video src={media.content_url} className="h-full w-full object-cover" muted controls />
                ) : (
                  <img
                    src={media.thumbnail_url ?? media.content_url}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                )
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-muted">
                  媒体暂不可用
                </div>
              )}
            </div>
            <div className="mt-2 flex items-center justify-between gap-2">
              <span className="text-xs text-muted">#{output.output_index + 1}</span>
              {selected ? <Badge tone="success">已采用</Badge> : null}
            </div>
            <Button
              type="button"
              variant={selected ? "secondary" : "default"}
              size="sm"
              className="mt-2 w-full"
              onClick={() => onSelect(output.id)}
              disabled={busy || selected}
            >
              {selected ? (
                <>
                  <Check className="h-4 w-4" aria-hidden="true" />
                  已采用
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" aria-hidden="true" />
                  采用
                </>
              )}
            </Button>
          </article>
        );
      })}
    </div>
  );
}

function outputsForTask(
  task: KeyframeTask | null,
  runsByTask: Map<string, KeyframeRun[]>
): KeyframeOutput[] {
  if (!task) return [];
  return (runsByTask.get(task.id) ?? []).flatMap((run) => run.outputs);
}

function preferredVideoWorkflow(workflows: VideoWorkflow[]) {
  return (
    workflows.find((workflow) => workflow.available && workflow.mode === "first_last_frame_to_video") ??
    workflows.find((workflow) => workflow.available) ??
    null
  );
}

function isActiveRun(run: Pick<KeyframeRun | VideoRun, "status">) {
  return activeRunStatuses.has(run.status);
}

function getErrorText(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}
