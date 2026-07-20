import { useMutation, useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Film, Maximize2, Minus, Play, Plus, RefreshCw, Save, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/features/characters/components/status-badge";
import { fetchKeyframeRuns, selectKeyframeOutput } from "@/features/keyframe-generation/api";
import type { KeyframeOutput, KeyframeRun } from "@/features/keyframe-generation/types";
import { fetchKeyframeTasks } from "@/features/keyframe-tasks/api";
import type { KeyframeTask } from "@/features/keyframe-tasks/types";
import { buildPromptDraft } from "@/features/prompt-builder/api";
import type { PromptDraftResponse } from "@/features/prompt-builder/types";
import { projectCanvasKeys } from "@/features/project-canvas/api";
import {
  executeQuickGenerate,
  previewQuickGenerate,
  quickGenerateKeys,
  syncQuickGenerateOutput
} from "@/features/project-canvas/quick-generate-api";
import type {
  QuickGenerateMode,
  QuickGeneratePreviewResponse,
  QuickGenerateRunType,
  WorkflowRoute
} from "@/features/project-canvas/quick-generate-api";
import { shotKeys } from "@/features/shots/api";
import type { Shot } from "@/features/shots/types";
import { fetchVideoRuns, fetchVideoTasks, selectVideoOutput } from "@/features/video-generation/api";
import type { VideoOutput, VideoRun } from "@/features/video-generation/types";
import { ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

type MessageTone = "success" | "error" | "neutral";
type PanelMode = "first_frame" | "end_frame" | "video";
type CandidateOutput = KeyframeOutput | VideoOutput;
type CandidateRun = KeyframeRun | VideoRun;

interface RunCandidateGroup {
  run: CandidateRun;
  outputs: CandidateOutput[];
  prompt: string;
}

const activeRunStatuses = new Set(["queued", "running"]);

const modeLabels: Record<PanelMode, string> = {
  first_frame: "首帧",
  end_frame: "尾帧",
  video: "视频"
};

export function CanvasQuickGeneratePanel({ projectId, shot }: { projectId: string; shot: Shot }) {
  const queryClient = useQueryClient();
  const [activeMode, setActiveMode] = useState<PanelMode>("first_frame");
  const [firstPrompt, setFirstPrompt] = useState(shot.visual_description ?? "");
  const [endPrompt, setEndPrompt] = useState(shot.visual_description ?? "");
  const [videoPrompt, setVideoPrompt] = useState(shot.action_summary ?? shot.visual_description ?? "");
  const [negativePrompt, setNegativePrompt] = useState("");
  const [durationPreset, setDurationPreset] = useState<"short_test" | "standard_short">("short_test");
  const [videoFps, setVideoFps] = useState(8);
  const [videoSeed, setVideoSeed] = useState("");
  const [message, setMessage] = useState<{ tone: MessageTone; text: string } | null>(null);
  const [lightbox, setLightbox] = useState<{
    output: CandidateOutput;
    mediaType: "image" | "video";
  } | null>(null);

  const keyframeTasksQuery = useQuery({
    queryKey: shotKeys.keyframeTasks(projectId, shot.id),
    queryFn: () => fetchKeyframeTasks(projectId, shot.id)
  });
  const videoTasksQuery = useQuery({
    queryKey: shotKeys.videoTasks(projectId, shot.id),
    queryFn: () => fetchVideoTasks(projectId, shot.id)
  });

  const firstPreviewQuery = useQuickPreview(projectId, shot.id, "first_frame", firstPrompt, negativePrompt);
  const endPreviewQuery = useQuickPreview(projectId, shot.id, "end_frame", endPrompt, negativePrompt);
  const videoPreviewQuery = useQuickPreview(projectId, shot.id, "video", videoPrompt, negativePrompt, {
    duration_preset: durationPreset,
    fps: videoFps,
    seed: parseOptionalSeed(videoSeed)
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

  const firstRunGroups = buildKeyframeRunGroups(firstTask, keyframeRunsByTask);
  const endRunGroups = buildKeyframeRunGroups(endTask, keyframeRunsByTask);
  const videoRunGroups = buildVideoRunGroups(videoTask, videoRunsByTask);

  const selectedFirstOutput = findSelectedOutput(firstRunGroups) as KeyframeOutput | null;
  const selectedEndOutput = findSelectedOutput(endRunGroups) as KeyframeOutput | null;
  const selectedVideoOutput =
    (findSelectedOutput(videoRunGroups) as VideoOutput | null) ?? videoTask?.selected_output ?? null;

  const firstActive = firstRunGroups.some((group) => isActiveRun(group.run));
  const endActive = endRunGroups.some((group) => isActiveRun(group.run));
  const videoActive = videoRunGroups.some((group) => isActiveRun(group.run));

  const promptDraftMutation = useMutation({
    mutationFn: () => buildPromptDraft(projectId, shot.id, { target: "all", include_negative_prompt: true }),
    onSuccess: (draft) => {
      applyPromptDraft(draft);
      setMessage({ tone: "success", text: "已根据镜头上下文生成可编辑 Prompt。" });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "Prompt 草稿生成失败。") })
  });

  const executeMutation = useMutation({
    mutationFn: ({
      mode,
      prompt,
      duration_preset,
      fps,
      seed
    }: {
      mode: QuickGenerateMode;
      prompt: string;
      duration_preset?: "short_test" | "standard_short";
      fps?: number | null;
      seed?: number | null;
    }) =>
      executeQuickGenerate(projectId, shot.id, {
        mode,
        prompt: prompt.trim(),
        negative_prompt: negativePrompt.trim() || null,
        duration_preset: duration_preset ?? null,
        fps: fps ?? null,
        seed: seed ?? null,
        request_id: crypto.randomUUID()
      }),
    onSuccess: async (response) => {
      await invalidateAll(response.task_id);
      const submittedText =
        response.mode === "first_frame"
          ? "首帧生成已提交，请在当前候选区等待结果。"
          : response.mode === "end_frame"
            ? "尾帧生成已提交，请在当前候选区等待结果。"
            : "视频生成已提交，请在当前候选区等待结果。";
      const text = response.reused_active_run
        ? "当前已有生成正在运行，已复用现有运行记录。"
        : response.idempotent_replay
          ? "该生成请求已提交过，已返回现有运行记录。"
          : submittedText;
      setActiveMode(response.mode);
      setMessage({ tone: "success", text });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "生成提交失败。") })
  });

  const selectKeyframeMutation = useMutation({
    mutationFn: (outputId: string) => selectKeyframeOutput(projectId, outputId),
    onSuccess: async () => {
      await invalidateAll();
      setMessage({ tone: "success", text: "候选图已采用。" });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "采用候选图失败。") })
  });

  const selectVideoMutation = useMutation({
    mutationFn: (outputId: string) => selectVideoOutput(projectId, outputId),
    onSuccess: async () => {
      await invalidateAll();
      setMessage({ tone: "success", text: "视频输出已采用。" });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "采用视频失败。") })
  });

  const syncOutputMutation = useMutation({
    mutationFn: ({ runType, runId }: { runType: QuickGenerateRunType; runId: string }) =>
      syncQuickGenerateOutput(projectId, shot.id, { run_type: runType, run_id: runId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectCanvasKeys.detail(projectId) });
      setMessage({ tone: "success", text: "输出节点已同步到画布。" });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, "同步输出节点失败。") })
  });

  useEffect(() => {
    setFirstPrompt((value) => value || shot.visual_description || "");
    setEndPrompt((value) => value || shot.visual_description || "");
    setVideoPrompt((value) => value || shot.action_summary || shot.visual_description || "");
  }, [shot.action_summary, shot.visual_description]);

  async function invalidateAll(taskId?: string) {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: shotKeys.keyframeTasks(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.videoTasks(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.detail(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.references(projectId, shot.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.lists(projectId) }),
      queryClient.invalidateQueries({ queryKey: projectCanvasKeys.detail(projectId) }),
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "shots", shot.id, "quick-generate"] }),
      queryClient.invalidateQueries({ queryKey: ["projects", projectId, "generation-tasks"] }),
      ...keyframeTasks.map((task) =>
        queryClient.invalidateQueries({ queryKey: shotKeys.keyframeRuns(projectId, task.id) })
      ),
      ...videoTasks.map((task) =>
        queryClient.invalidateQueries({ queryKey: shotKeys.videoRuns(projectId, task.id) })
      ),
      taskId ? queryClient.invalidateQueries({ queryKey: shotKeys.keyframeRuns(projectId, taskId) }) : Promise.resolve(),
      taskId ? queryClient.invalidateQueries({ queryKey: shotKeys.videoRuns(projectId, taskId) }) : Promise.resolve()
    ]);
  }

  function applyPromptDraft(draft: PromptDraftResponse) {
    setFirstPrompt(draft.first_frame_prompt_en);
    setEndPrompt(draft.end_frame_prompt_en);
    setVideoPrompt(draft.motion_prompt_en);
    setNegativePrompt(draft.negative_prompt_en);
  }

  const loading = keyframeTasksQuery.isLoading || videoTasksQuery.isLoading;
  const busy =
    promptDraftMutation.isPending ||
    executeMutation.isPending ||
    selectKeyframeMutation.isPending ||
    selectVideoMutation.isPending ||
    syncOutputMutation.isPending;

  if (loading) return <Skeleton className="h-80" />;

  return (
    <div className="grid min-w-0 gap-3 overflow-hidden">
      <StatusMessage tone="neutral">
        画布快速生成由后端统一预检和编排；不会修改 ComfyUI workflow，也不会自动采用结果。
      </StatusMessage>
      {message && (
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <StatusMessage tone={message.tone}>{message.text}</StatusMessage>
          </div>
          <Button type="button" variant="ghost" size="icon" aria-label="关闭提示" onClick={() => setMessage(null)}>
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      )}

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

      <div className="grid grid-cols-3 gap-1 rounded-md border border-border bg-background p-1">
        {(["first_frame", "end_frame", "video"] as const).map((mode) => (
          <button
            key={mode}
            type="button"
            className={cn(
              "rounded px-2 py-1.5 text-xs transition-colors",
              activeMode === mode ? "bg-primarySoft text-foreground" : "text-muted hover:text-foreground"
            )}
            onClick={() => setActiveMode(mode)}
          >
            {modeLabels[mode]}
          </button>
        ))}
      </div>

      {activeMode === "first_frame" && (
        <FrameQuickSection
          title="首帧"
          promptLabel="首帧 Prompt"
          prompt={firstPrompt}
          onPromptChange={setFirstPrompt}
          route={firstPreviewQuery.data?.route}
          routeError={firstPreviewQuery.error}
          active={firstActive}
          runGroups={firstRunGroups}
          selectedOutput={selectedFirstOutput}
          busy={busy}
          onGenerate={() => executeMutation.mutate({ mode: "first_frame", prompt: firstPrompt })}
          onSelect={(outputId) => selectKeyframeMutation.mutate(outputId)}
          onSync={(runId) => syncOutputMutation.mutate({ runType: "keyframe", runId })}
          onPreview={(output) => setLightbox({ output, mediaType: "image" })}
        />
      )}

      {activeMode === "end_frame" && (
        <FrameQuickSection
          title="尾帧"
          promptLabel="尾帧 Prompt"
          prompt={endPrompt}
          onPromptChange={setEndPrompt}
          route={endPreviewQuery.data?.route}
          routeError={endPreviewQuery.error}
          active={endActive}
          runGroups={endRunGroups}
          selectedOutput={selectedEndOutput}
          busy={busy}
          onGenerate={() => executeMutation.mutate({ mode: "end_frame", prompt: endPrompt })}
          onSelect={(outputId) => selectKeyframeMutation.mutate(outputId)}
          onSync={(runId) => syncOutputMutation.mutate({ runType: "keyframe", runId })}
          onPreview={(output) => setLightbox({ output, mediaType: "image" })}
        />
      )}

      {activeMode === "video" && (
        <VideoQuickSection
          prompt={videoPrompt}
          onPromptChange={setVideoPrompt}
          negativePrompt={negativePrompt}
          onNegativePromptChange={setNegativePrompt}
          route={videoPreviewQuery.data?.route}
          preview={videoPreviewQuery.data}
          routeError={videoPreviewQuery.error}
          active={videoActive}
          runGroups={videoRunGroups}
          selectedOutput={selectedVideoOutput}
          selectedFirstOutput={selectedFirstOutput}
          selectedEndOutput={selectedEndOutput}
          busy={busy}
          durationPreset={durationPreset}
          onDurationPresetChange={setDurationPreset}
          fps={videoFps}
          onFpsChange={setVideoFps}
          seed={videoSeed}
          onSeedChange={setVideoSeed}
          onGenerate={() =>
            executeMutation.mutate({
              mode: "video",
              prompt: videoPrompt,
              duration_preset: durationPreset,
              fps: videoFps,
              seed: parseOptionalSeed(videoSeed)
            })
          }
          onSelect={(outputId) => selectVideoMutation.mutate(outputId)}
          onSync={(runId) => syncOutputMutation.mutate({ runType: "video", runId })}
          onPreview={(output) => setLightbox({ output, mediaType: "video" })}
        />
      )}

      {lightbox && (
        <OutputLightbox
          output={lightbox.output}
          mediaType={lightbox.mediaType}
          busy={busy}
          onClose={() => setLightbox(null)}
          onSelect={(outputId) =>
            lightbox.mediaType === "video" ? selectVideoMutation.mutate(outputId) : selectKeyframeMutation.mutate(outputId)
          }
        />
      )}
    </div>
  );
}

function useQuickPreview(
  projectId: string,
  shotId: string,
  mode: QuickGenerateMode,
  prompt: string,
  negativePrompt: string,
  options?: { duration_preset?: "short_test" | "standard_short"; fps?: number | null; seed?: number | null }
) {
  const optionKey = `${options?.duration_preset ?? ""}:${options?.fps ?? ""}:${options?.seed ?? ""}`;
  return useQuery({
    queryKey: quickGenerateKeys.preview(projectId, shotId, mode, `${prompt}\n${negativePrompt}\n${optionKey}`),
    queryFn: () =>
      previewQuickGenerate(projectId, shotId, {
        mode,
        prompt,
        negative_prompt: negativePrompt.trim() || null,
        duration_preset: options?.duration_preset ?? null,
        fps: options?.fps ?? null,
        seed: options?.seed ?? null
      }),
    staleTime: 1000
  });
}

function FrameQuickSection({
  title,
  promptLabel,
  prompt,
  onPromptChange,
  route,
  preview,
  routeError,
  active,
  runGroups,
  selectedOutput,
  busy,
  onGenerate,
  onSelect,
  onSync,
  onPreview
}: {
  title: string;
  promptLabel: string;
  prompt: string;
  onPromptChange: (value: string) => void;
  route?: WorkflowRoute;
  preview?: QuickGeneratePreviewResponse;
  routeError: unknown;
  active: boolean;
  runGroups: RunCandidateGroup[];
  selectedOutput: KeyframeOutput | null;
  busy: boolean;
  onGenerate: () => void;
  onSelect: (outputId: string) => void;
  onSync: (runId: string) => void;
  onPreview: (output: KeyframeOutput) => void;
}) {
  return (
    <section className="grid min-w-0 gap-3 overflow-hidden rounded-md border border-border bg-background p-3">
      <SectionHeader title={title} route={route} routeError={routeError} />
      <Textarea aria-label={promptLabel} value={prompt} onChange={(event) => onPromptChange(event.target.value)} rows={4} />
      <Button type="button" onClick={onGenerate} disabled={busy || active || !route?.executable}>
        <Play className="h-4 w-4" aria-hidden="true" />
        {active ? `${title}生成中` : `生成${title}`}
      </Button>
      <CandidateRuns
        title={title}
        runGroups={runGroups}
        selectedOutput={selectedOutput}
        busy={busy}
        mediaType="image"
        onSelect={onSelect}
        onSync={onSync}
        onPreview={(output) => onPreview(output as KeyframeOutput)}
      />
    </section>
  );
}

function VideoQuickSection({
  prompt,
  onPromptChange,
  negativePrompt,
  onNegativePromptChange,
  route,
  preview,
  routeError,
  active,
  runGroups,
  selectedOutput,
  selectedFirstOutput,
  selectedEndOutput,
  durationPreset,
  onDurationPresetChange,
  fps,
  onFpsChange,
  seed,
  onSeedChange,
  busy,
  onGenerate,
  onSelect,
  onSync,
  onPreview
}: {
  prompt: string;
  onPromptChange: (value: string) => void;
  negativePrompt: string;
  onNegativePromptChange: (value: string) => void;
  route?: WorkflowRoute;
  preview?: QuickGeneratePreviewResponse;
  routeError: unknown;
  active: boolean;
  runGroups: RunCandidateGroup[];
  selectedOutput: VideoOutput | null;
  selectedFirstOutput: KeyframeOutput | null;
  selectedEndOutput: KeyframeOutput | null;
  durationPreset: "short_test" | "standard_short";
  onDurationPresetChange: (value: "short_test" | "standard_short") => void;
  fps: number;
  onFpsChange: (value: number) => void;
  seed: string;
  onSeedChange: (value: string) => void;
  busy: boolean;
  onGenerate: () => void;
  onSelect: (outputId: string) => void;
  onSync: (runId: string) => void;
  onPreview: (output: VideoOutput) => void;
}) {
  return (
    <section className="grid min-w-0 gap-3 overflow-hidden rounded-md border border-border bg-background p-3">
      <SectionHeader title="视频" route={route} routeError={routeError} />
      <Textarea aria-label="视频 Prompt" value={prompt} onChange={(event) => onPromptChange(event.target.value)} rows={4} />
      <Textarea
        aria-label="反向 Prompt"
        value={negativePrompt}
        onChange={(event) => onNegativePromptChange(event.target.value)}
        rows={3}
      />
      <div className="grid gap-2 rounded-md border border-border bg-panel p-3">
        <div className="grid gap-2 sm:grid-cols-3">
          <label className="grid gap-1 text-xs text-muted">
            <span>时长预设</span>
            <select
              className="rounded border border-border bg-background px-2 py-2 text-sm text-foreground"
              value={durationPreset}
              onChange={(event) => onDurationPresetChange(event.target.value as "short_test" | "standard_short")}
            >
              <option value="short_test">约 2 秒</option>
              <option value="standard_short">约 4 秒</option>
            </select>
          </label>
          <label className="grid gap-1 text-xs text-muted">
            <span>FPS</span>
            <input
              className="rounded border border-border bg-background px-2 py-2 text-sm text-foreground"
              inputMode="numeric"
              min={1}
              max={60}
              value={fps}
              onChange={(event) => onFpsChange(clampFps(event.currentTarget.value))}
            />
          </label>
          <label className="grid gap-1 text-xs text-muted">
            <span>Seed</span>
            <input
              className="rounded border border-border bg-background px-2 py-2 text-sm text-foreground"
              inputMode="numeric"
              placeholder="随机"
              value={seed}
              onChange={(event) => onSeedChange(event.currentTarget.value)}
            />
          </label>
        </div>
        <ResolvedPreview route={route} preview={preview} />
      </div>
      <div className="grid gap-1 text-xs text-muted">
        <p>首帧：{selectedFirstOutput ? "已采用" : "未采用"}</p>
        <p>尾帧：{selectedEndOutput ? "已采用" : "未采用"}</p>
      </div>
      <Button type="button" onClick={onGenerate} disabled={busy || active || !route?.executable}>
        <Film className="h-4 w-4" aria-hidden="true" />
        {active ? "视频生成中" : "生成视频"}
      </Button>
      <CandidateRuns
        title="视频"
        runGroups={runGroups}
        selectedOutput={selectedOutput}
        busy={busy}
        mediaType="video"
        onSelect={onSelect}
        onSync={onSync}
        onPreview={(output) => onPreview(output as VideoOutput)}
      />
    </section>
  );
}

function SectionHeader({
  title,
  route,
  routeError
}: {
  title: string;
  route?: WorkflowRoute;
  routeError: unknown;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="min-w-0">
        <h4 className="text-sm font-semibold text-foreground">{title}</h4>
        <RouteSummary route={route} error={routeError} />
      </div>
      <Badge tone={route?.executable ? "success" : "default"}>{route?.executable ? "可生成" : "未就绪"}</Badge>
    </div>
  );
}

function RouteSummary({ route, error }: { route?: WorkflowRoute; error: unknown }) {
  if (error) return <p className="text-xs text-danger">{getErrorText(error, "工作流预检失败。")}</p>;
  if (!route) return <p className="text-xs text-muted">正在检查工作流...</p>;
  const details = [
    route.missing_inputs.length > 0 ? `缺少输入：${route.missing_inputs.map(quickRequirementLabel).join("、")}` : null,
    route.missing_models.length > 0 ? `缺少模型：${route.missing_models.join("、")}` : null,
    route.missing_nodes.length > 0 ? `缺少节点：${route.missing_nodes.map(quickRequirementLabel).join("、")}` : null
  ].filter(Boolean);
  return (
    <div className="grid gap-1">
      <p className="text-xs text-muted">
        {route.selected_workflow_id ? "工作流：已自动选择" : "暂无可用工作流"}
      </p>
      <p className={route.executable ? "text-xs text-success" : "text-xs text-warning"}>{route.reason_zh}</p>
      {details.map((detail) => (
        <p key={detail} className="text-xs text-danger">
          {detail}
        </p>
      ))}
    </div>
  );
}

function ResolvedPreview({ route, preview }: { route?: WorkflowRoute; preview?: QuickGeneratePreviewResponse }) {
  if (!route) return <p className="text-xs text-muted">正在预检视频参数...</p>;
  if (!route.executable) return <p className="text-xs text-warning">预检通过前不会提交视频任务。</p>;
  const output = preview?.estimated_output;
  const details =
    output?.width && output.height && output.frame_count && output.fps
      ? `${output.width}×${output.height} / ${output.frame_count} 帧 / ${output.fps} FPS / 约 ${output.duration_seconds}s`
      : "参数已通过预检";
  return (
    <div className="grid gap-1 text-xs">
      <p className="text-success">预检通过后将使用已采用首尾帧生成视频候选，不会自动采用结果。</p>
      <p className="text-muted">{details}</p>
    </div>
  );
}

function CandidateRuns({
  title,
  runGroups,
  selectedOutput,
  busy,
  mediaType,
  onSelect,
  onSync,
  onPreview
}: {
  title: string;
  runGroups: RunCandidateGroup[];
  selectedOutput: CandidateOutput | null;
  busy: boolean;
  mediaType: "image" | "video";
  onSelect: (outputId: string) => void;
  onSync: (runId: string) => void;
  onPreview: (output: CandidateOutput) => void;
}) {
  const currentRun = runGroups[0] ?? null;
  const historyRuns = currentRun ? runGroups.slice(1) : [];
  const currentOutputs = currentRun?.outputs.filter((output) => output.id !== selectedOutput?.id) ?? [];

  return (
    <div className="grid min-w-0 gap-3 overflow-hidden">
      {selectedOutput && (
        <div className="grid gap-2 rounded-md border border-success/40 bg-success/5 p-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-success">已采用{title}</span>
            <Badge tone="success">已采用</Badge>
          </div>
          <OutputCard
            output={selectedOutput}
            selectedOutputId={selectedOutput.id}
            busy={busy}
            mediaType={mediaType}
            onSelect={onSelect}
            onSync={onSync}
            onPreview={onPreview}
          />
        </div>
      )}

      <div className="grid gap-2">
        <div className="flex items-center justify-between gap-2">
          <h5 className="text-xs font-semibold text-foreground">当前候选</h5>
          {currentRun && <Badge tone={isActiveRun(currentRun.run) ? "primary" : "default"}>{runStatusLabel(currentRun.run.status)}</Badge>}
        </div>
        {!currentRun ? (
          <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted">暂无{title}候选</div>
        ) : currentOutputs.length === 0 ? (
          <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted">
            最新 Run 的候选已在顶部采用区显示，或该 Run 尚未产生输出。
          </div>
        ) : (
          <OutputGrid
            outputs={currentOutputs}
            selectedOutputId={selectedOutput?.id ?? null}
            busy={busy}
            mediaType={mediaType}
            onSelect={onSelect}
            onSync={onSync}
            onPreview={onPreview}
          />
        )}
      </div>

      {historyRuns.length > 0 && (
        <details className="rounded-md border border-border bg-panel p-2">
          <summary className="cursor-pointer text-xs font-medium text-muted">历史生成（{historyRuns.length} 次 Run）</summary>
          <div className="mt-3 grid gap-3">
            {historyRuns.map((group) => (
              <div key={group.run.id} className="grid gap-2 rounded-md border border-border bg-background p-2">
                <div className="grid gap-1 text-xs text-muted">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span>{formatDateTime(group.run.created_at)}</span>
                    <Badge tone={isActiveRun(group.run) ? "primary" : "default"}>{runStatusLabel(group.run.status)}</Badge>
                  </div>
                  <span>Prompt：{summarize(group.prompt || "未记录", 64)}</span>
                  <span>候选数量：{group.outputs.length}</span>
                </div>
                {group.outputs.length > 0 && (
                  <OutputGrid
                    outputs={group.outputs}
                    selectedOutputId={selectedOutput?.id ?? null}
                    busy={busy}
                    mediaType={mediaType}
                    onSelect={onSelect}
                    onSync={onSync}
                    onPreview={onPreview}
                  />
                )}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

function OutputGrid({
  outputs,
  selectedOutputId,
  busy,
  onSelect,
  onSync,
  onPreview,
  mediaType
}: {
  outputs: CandidateOutput[];
  selectedOutputId: string | null;
  busy: boolean;
  onSelect: (outputId: string) => void;
  onSync: (runId: string) => void;
  onPreview: (output: CandidateOutput) => void;
  mediaType: "image" | "video";
}) {
  return (
    <div className="grid min-w-0 grid-cols-1 gap-3 2xl:grid-cols-2">
      {outputs.map((output) => (
        <OutputCard
          key={output.id}
          output={output}
          selectedOutputId={selectedOutputId}
          busy={busy}
          mediaType={mediaType}
          onSelect={onSelect}
          onSync={onSync}
          onPreview={onPreview}
        />
      ))}
    </div>
  );
}

function OutputCard({
  output,
  selectedOutputId,
  busy,
  mediaType,
  onSelect,
  onSync,
  onPreview
}: {
  output: CandidateOutput;
  selectedOutputId: string | null;
  busy: boolean;
  mediaType: "image" | "video";
  onSelect: (outputId: string) => void;
  onSync: (runId: string) => void;
  onPreview: (output: CandidateOutput) => void;
}) {
  const media = output.media_asset;
  const selected = output.id === selectedOutputId || output.is_selected;

  return (
    <article className="min-w-0 rounded-md border border-border bg-panel p-2">
      <button
        type="button"
        className="block w-full overflow-hidden rounded border border-border bg-background"
        onClick={() => media && onPreview(output)}
        disabled={!media}
      >
        {media ? (
          mediaType === "video" ? (
            <video src={media.content_url} className="max-h-[320px] w-full object-contain" muted controls />
          ) : (
            <img
              src={media.thumbnail_url ?? media.content_url}
              alt=""
              className="max-h-[360px] w-full object-contain"
            />
          )
        ) : (
          <div className="flex h-44 items-center justify-center text-xs text-muted">媒体暂不可用</div>
        )}
      </button>
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-xs text-muted">候选 #{output.output_index}</span>
        {selected ? <Badge tone="success">已采用</Badge> : <Badge>未采用</Badge>}
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2">
        <Button type="button" variant={selected ? "secondary" : "default"} size="sm" onClick={() => onSelect(output.id)} disabled={busy || selected}>
          {selected ? <Check className="h-4 w-4" aria-hidden="true" /> : <Save className="h-4 w-4" aria-hidden="true" />}
          {selected ? "已采用" : "采用"}
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={() => onPreview(output)} disabled={!media}>
          <Maximize2 className="h-4 w-4" aria-hidden="true" />
          原图
        </Button>
        <Button type="button" variant="secondary" size="sm" onClick={() => onSync(output.run_id)} disabled={busy}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          同步
        </Button>
      </div>
    </article>
  );
}

function OutputLightbox({
  output,
  mediaType,
  busy,
  onClose,
  onSelect
}: {
  output: CandidateOutput;
  mediaType: "image" | "video";
  busy: boolean;
  onClose: () => void;
  onSelect: (outputId: string) => void;
}) {
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragStart, setDragStart] = useState<{ x: number; y: number; ox: number; oy: number } | null>(null);
  const media = output.media_asset;

  return (
    <div className="fixed inset-0 z-[80] grid bg-black/85 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-sm text-white">候选 #{output.output_index}</div>
        <div className="flex items-center gap-2">
          {mediaType === "image" && (
            <>
              <Button type="button" variant="secondary" size="icon" onClick={() => setScale((value) => Math.max(0.5, value - 0.25))}>
                <Minus className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button type="button" variant="secondary" size="icon" onClick={() => setScale((value) => Math.min(3, value + 0.25))}>
                <Plus className="h-4 w-4" aria-hidden="true" />
              </Button>
            </>
          )}
          <Button type="button" onClick={() => onSelect(output.id)} disabled={busy || output.is_selected}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {output.is_selected ? "已采用" : "采用"}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            关闭
          </Button>
        </div>
      </div>
      <div
        className="min-h-0 overflow-hidden rounded-md border border-border bg-black"
        onMouseMove={(event) => {
          if (!dragStart) return;
          setOffset({
            x: dragStart.ox + event.clientX - dragStart.x,
            y: dragStart.oy + event.clientY - dragStart.y
          });
        }}
        onMouseUp={() => setDragStart(null)}
        onMouseLeave={() => setDragStart(null)}
      >
        {media ? (
          mediaType === "video" ? (
            <video src={media.content_url} className="h-full max-h-[calc(100vh-96px)] w-full object-contain" controls />
          ) : (
            <img
              src={media.content_url}
              alt=""
              className="h-full max-h-[calc(100vh-96px)] w-full cursor-grab object-contain active:cursor-grabbing"
              style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }}
              onMouseDown={(event) =>
                setDragStart({ x: event.clientX, y: event.clientY, ox: offset.x, oy: offset.y })
              }
              draggable={false}
            />
          )
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-white">媒体暂不可用</div>
        )}
      </div>
    </div>
  );
}

function buildKeyframeRunGroups(
  task: KeyframeTask | null,
  runsByTask: Map<string, KeyframeRun[]>
): RunCandidateGroup[] {
  if (!task) return [];
  return sortRuns(runsByTask.get(task.id) ?? []).map((run) => ({
    run,
    outputs: run.outputs,
    prompt: run.submitted_payload_snapshot.effective_positive_prompt
  }));
}

function buildVideoRunGroups(
  task: { id: string } | null,
  runsByTask: Map<string, VideoRun[]>
): RunCandidateGroup[] {
  if (!task) return [];
  return sortRuns(runsByTask.get(task.id) ?? []).map((run) => ({
    run,
    outputs: run.outputs,
    prompt: run.submitted_payload_snapshot.prompt
  }));
}

function sortRuns<T extends CandidateRun>(runs: T[]): T[] {
  return [...runs].sort((left, right) => {
    const activeDelta = Number(isActiveRun(right)) - Number(isActiveRun(left));
    if (activeDelta !== 0) return activeDelta;
    return Date.parse(right.created_at) - Date.parse(left.created_at);
  });
}

function findSelectedOutput(groups: RunCandidateGroup[]): CandidateOutput | null {
  for (const group of groups) {
    const output = group.outputs.find((item) => item.is_selected);
    if (output) return output;
  }
  return null;
}

function isActiveRun(run: Pick<KeyframeRun | VideoRun, "status">) {
  return activeRunStatuses.has(run.status);
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function summarize(value: string, maxLength: number) {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) return normalized;
  return `${normalized.slice(0, maxLength)}...`;
}

function runStatusLabel(status: string) {
  const labels: Record<string, string> = {
    queued: "排队中",
    running: "生成中",
    completed: "已完成",
    failed: "失败",
    cancelled: "已取消",
    interrupted: "已中断"
  };
  return labels[status] ?? status;
}

function quickRequirementLabel(value: string) {
  const labels: Record<string, string> = {
    prompt: "视频提示词",
    adopted_first_frame: "已采用首帧",
    adopted_end_frame: "已采用尾帧",
    adopted_first_frame_media_missing: "首帧媒体记录",
    adopted_end_frame_media_missing: "尾帧媒体记录",
    adopted_first_frame_file_missing: "首帧文件",
    adopted_end_frame_file_missing: "尾帧文件",
    adopted_first_frame_not_image: "首帧图片",
    adopted_end_frame_not_image: "尾帧图片",
    multiple_adopted_first_frame: "唯一首帧采用结果",
    multiple_adopted_end_frame: "唯一尾帧采用结果"
  };
  return labels[value] ?? value;
}

function parseOptionalSeed(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

function clampFps(value: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 8;
  return Math.min(60, Math.max(1, Math.round(parsed)));
}

function getErrorText(error: unknown, fallback: string) {
  if (error instanceof ApiClientError) return error.message;
  if (error instanceof Error) return error.message;
  return fallback;
}
