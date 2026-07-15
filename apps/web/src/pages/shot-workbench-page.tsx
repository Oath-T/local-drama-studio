import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Copy,
  Film,
  Images,
  Plus,
  RefreshCw,
  Save,
  Settings,
  Sparkles,
  Trash2
} from "lucide-react";
import { Component, useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Textarea } from "@/components/ui/textarea";
import { AssetPickerDialog } from "@/features/asset-picker/components/asset-picker-dialog";
import { assetPickerCopy } from "@/features/asset-picker/copy";
import type { PickerOptionItem } from "@/features/asset-picker/types";
import { assetSummaryKeys } from "@/features/asset-summaries/api";
import { ShotAssetSummaryCard } from "@/features/asset-summaries/components/asset-summary-cards";
import { characterKeys, fetchCharacters, fetchLooks, fetchReferences } from "@/features/characters/api";
import { ConfirmDeleteDialog } from "@/features/characters/components/confirm-delete-dialog";
import { Badge } from "@/features/characters/components/status-badge";
import type { Character, CharacterLook } from "@/features/characters/types";
import { generationTaskKeys } from "@/features/generation-tasks/api";
import { createKeyframeTask, updateKeyframeTask } from "@/features/keyframe-tasks/api";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchSceneReferences, fetchScenes, fetchSceneStates, sceneKeys } from "@/features/scenes/api";
import type { Scene, SceneReference, SceneState } from "@/features/scenes/types";
import { KeyframeTaskPanel } from "@/features/keyframe-tasks/components/keyframe-task-panel";
import { PromptDraftCard } from "@/features/prompt-builder/components/prompt-draft-card";
import { promptBuilderCopy } from "@/features/prompt-builder/copy";
import type { PromptDraftResponse } from "@/features/prompt-builder/types";
import {
  fetchShotProductionStatus,
  productionStatusKeys
} from "@/features/production-status/api";
import { ShotProductionPanel } from "@/features/production-status/components/shot-production-panel";
import { productionStatusCopy } from "@/features/production-status/copy";
import { normalizeShotProductionStatus } from "@/features/production-status/normalizers";
import type { ShotProductionStatus } from "@/features/production-status/types";
import { ShotRecommendationPanel } from "@/features/shots/components/shot-recommendation-panel";
import { createVideoTask, updateVideoTask } from "@/features/video-generation/api";
import type { VideoTaskInputPayload } from "@/features/video-generation/types";
import {
  addShotCharacter,
  addShotReference,
  createShot,
  deleteShot,
  deleteShotCharacter,
  deleteShotReference,
  duplicateShot,
  fetchShot,
  fetchShotCharacters,
  fetchShotReferences,
  fetchShots,
  moveShot,
  moveShotCharacter,
  moveShotReference,
  shotKeys,
  updateShot,
  updateShotCharacter
} from "@/features/shots/api";
import { shotCopy, shotRecommendationCopy } from "@/features/shots/copy";
import { shotFormSchema, type ShotFormValues } from "@/features/shots/schema";
import type {
  CharacterReferencePurpose,
  SceneReferencePurpose,
  Shot,
  ShotCharacter,
  ShotInput,
  ShotReference
} from "@/features/shots/types";
import { copy } from "@/locales";
import { ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const NONE = "__none";

type CreativeMode = "first_frame" | "end_frame" | "video";
type WorkspaceMode = "quick" | "advanced";

const creativeModeCopy: Record<CreativeMode, { label: string; action: string; empty: string }> = {
  first_frame: {
    label: "首帧",
    action: "生成首帧",
    empty: "还没有首帧候选。放入参考图并填写 Prompt 后，可以在这里查看生成结果。"
  },
  end_frame: {
    label: "尾帧",
    action: "生成尾帧",
    empty: "还没有尾帧候选。采用首帧后，可以继续生成尾帧保持连续性。"
  },
  video: {
    label: "视频",
    action: "生成视频",
    empty: "还没有视频候选。采用首帧和尾帧后，可以继续生成视频。"
  }
};

const shotScaleOptions = [
  "unknown",
  "extreme_wide",
  "wide",
  "full",
  "medium_wide",
  "medium",
  "medium_close",
  "close",
  "close_up",
  "extreme_close_up"
] as const;
const cameraHeightOptions = ["unknown", "ground", "low", "eye_level", "high", "overhead", "aerial", "custom"] as const;
const cameraAngleOptions = [
  "unknown",
  "front",
  "back",
  "left_profile",
  "right_profile",
  "left_three_quarter",
  "right_three_quarter",
  "top_down",
  "dutch_angle",
  "pov",
  "over_the_shoulder",
  "custom"
] as const;
const compositionOptions = [
  "unknown",
  "centered",
  "symmetrical",
  "rule_of_thirds",
  "leading_lines",
  "frame_within_frame",
  "layered",
  "negative_space",
  "close_blocking",
  "custom"
] as const;
const movementOptions = [
  "unknown",
  "static",
  "push_in",
  "pull_out",
  "pan_left",
  "pan_right",
  "tilt_up",
  "tilt_down",
  "tracking",
  "orbit",
  "handheld",
  "crane",
  "zoom_in",
  "zoom_out",
  "custom"
] as const;

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

export function ShotWorkbenchPage() {
  const { projectId = "", shotId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [creativeMode, setCreativeMode] = useState<CreativeMode>("first_frame");
  const [workspaceMode, setWorkspaceMode] = useState<WorkspaceMode>("quick");

  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const shotsQuery = useQuery({
    queryKey: shotKeys.lists(projectId),
    queryFn: () => fetchShots(projectId),
    enabled: projectId.length > 0
  });
  const activeShotId = shotId || shotsQuery.data?.items[0]?.id || "";
  const shotQuery = useQuery({
    queryKey: shotKeys.detail(projectId, activeShotId),
    queryFn: () => fetchShot(projectId, activeShotId),
    enabled: projectId.length > 0 && activeShotId.length > 0
  });
  const productionStatusQuery = useQuery({
    queryKey: activeShotId ? productionStatusKeys.shot(projectId, activeShotId) : ["production-status", "none"],
    queryFn: () => fetchShotProductionStatus(projectId, activeShotId),
    enabled: projectId.length > 0 && activeShotId.length > 0
  });
  const charactersQuery = useQuery({
    queryKey: characterKeys.lists(projectId),
    queryFn: () => fetchCharacters(projectId),
    enabled: projectId.length > 0
  });
  const scenesQuery = useQuery({
    queryKey: sceneKeys.lists(projectId),
    queryFn: () => fetchScenes(projectId),
    enabled: projectId.length > 0
  });

  useEffect(() => {
    if (!shotId && shotsQuery.data?.items[0]?.id) {
      navigate(`/projects/${projectId}/shots/${shotsQuery.data.items[0].id}`, { replace: true });
    }
  }, [navigate, projectId, shotId, shotsQuery.data?.items]);

  async function invalidateShotData(nextShotId = activeShotId) {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: shotKeys.lists(projectId) }),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.detail(projectId, nextShotId) })
        : Promise.resolve(),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.characters(projectId, nextShotId) })
        : Promise.resolve(),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.references(projectId, nextShotId) })
        : Promise.resolve(),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: assetSummaryKeys.shot(projectId, nextShotId) })
        : Promise.resolve(),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.recommendations(projectId, nextShotId) })
        : Promise.resolve(),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.keyframeTasks(projectId, nextShotId) })
        : Promise.resolve(),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: shotKeys.videoTasks(projectId, nextShotId) })
        : Promise.resolve(),
      nextShotId
        ? queryClient.invalidateQueries({ queryKey: productionStatusKeys.shot(projectId, nextShotId) })
        : Promise.resolve(),
      queryClient.invalidateQueries({ queryKey: productionStatusKeys.project(projectId) }),
      queryClient.invalidateQueries({ queryKey: generationTaskKeys.lists(projectId) })
    ]);
  }

  async function invalidateCreatedTaskData(shotId: string, taskId: string, taskType: "keyframe" | "video") {
    await Promise.all([
      invalidateShotData(shotId),
      queryClient.invalidateQueries({
        queryKey:
          taskType === "keyframe"
            ? shotKeys.keyframeTask(projectId, taskId)
            : shotKeys.videoTask(projectId, taskId)
      }),
      taskType === "keyframe"
        ? queryClient.invalidateQueries({
            queryKey: shotKeys.keyframeTaskReferences(projectId, taskId)
          })
        : Promise.resolve()
    ]);
  }

  const createMutation = useMutation({
    mutationFn: () => createShot(projectId, { name: `镜头 ${shotsQuery.data ? shotsQuery.data.total + 1 : 1}` }),
    onSuccess: async (shot) => {
      await invalidateShotData(shot.id);
      navigate(`/projects/${projectId}/shots/${shot.id}`);
      setMessage({ tone: "success", text: "镜头已创建" });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, shotCopy.saveFailed) })
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteShot(projectId, id),
    onSuccess: async () => {
      await invalidateShotData("");
      const next = await queryClient.fetchQuery({
        queryKey: shotKeys.lists(projectId),
        queryFn: () => fetchShots(projectId)
      });
      navigate(next.items[0] ? `/projects/${projectId}/shots/${next.items[0].id}` : `/projects/${projectId}/shots`);
      setMessage({ tone: "success", text: shotCopy.deleted });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, shotCopy.deleteFailed) })
  });
  const duplicateMutation = useMutation({
    mutationFn: (id: string) => duplicateShot(projectId, id),
    onSuccess: async (shot) => {
      await invalidateShotData(shot.id);
      navigate(`/projects/${projectId}/shots/${shot.id}`);
      setMessage({ tone: "success", text: shotCopy.duplicated });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, shotCopy.saveFailed) })
  });
  const moveMutation = useMutation({
    mutationFn: ({ id, orderIndex }: { id: string; orderIndex: number }) => moveShot(projectId, id, orderIndex),
    onSuccess: async (shot) => {
      await invalidateShotData(shot.id);
      setMessage({ tone: "success", text: shotCopy.moved });
    },
    onError: (error) => setMessage({ tone: "error", text: getErrorText(error, shotCopy.saveFailed) })
  });

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div>
            <Button asChild variant="ghost" className="mb-3 w-fit">
              <Link to={projectId ? `/projects/${projectId}` : "/projects"}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                {shotCopy.backToProject}
              </Link>
            </Button>
            <h1 className="text-2xl font-semibold text-foreground">{shotCopy.title}</h1>
            <p className="mt-1 text-sm text-muted">
              {projectQuery.data?.name ? `${projectQuery.data.name} / ${shotCopy.description}` : shotCopy.description}
            </p>
          </div>
          <Button type="button" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {createMutation.isPending ? shotCopy.creating : shotCopy.newShot}
          </Button>
        </div>

        {message && <StatusMessage tone={message.tone}>{message.text}</StatusMessage>}

        {shotsQuery.isLoading && <Skeleton className="h-[620px]" />}
        {shotsQuery.isError && (
          <section className="rounded-md border border-border bg-panel p-6">
            <StatusMessage tone="error">{shotCopy.loadFailed}</StatusMessage>
            <Button type="button" variant="secondary" className="mt-4" onClick={() => void shotsQuery.refetch()}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {copy.common.retry}
            </Button>
          </section>
        )}
        {shotsQuery.isSuccess && shotsQuery.data.total === 0 && (
          <EmptyState
            title={shotCopy.emptyTitle}
            description={shotCopy.emptyDescription}
            action={
              <Button type="button" onClick={() => createMutation.mutate()}>
                <Plus className="h-4 w-4" aria-hidden="true" />
                {shotCopy.newShot}
              </Button>
            }
          />
        )}
        {shotsQuery.isSuccess && shotsQuery.data.total > 0 && (
          <PanelErrorBoundary title="创作工作台加载失败">
            <CreativeTopBar
              shot={shotQuery.data}
              mode={creativeMode}
              workspaceMode={workspaceMode}
              productionStatus={productionStatusQuery.data}
              comfyStatus="沿用现有生成服务"
              onModeChange={setCreativeMode}
              onWorkspaceModeChange={setWorkspaceMode}
              onPrimaryAction={() => {
                setWorkspaceMode("advanced");
                setMessage({
                  tone: "success",
                  text: "快速生成编排将在 Sprint 25 接入。当前已打开专业任务详情，可继续使用现有任务链生成。"
                });
              }}
            />
            <div className="grid min-h-[680px] gap-4 2xl:grid-cols-[340px_minmax(0,1fr)_430px] xl:grid-cols-[300px_minmax(0,1fr)_400px]">
              <PanelErrorBoundary title="素材与参考加载失败">
                <aside className="grid min-h-0 gap-4">
                  <CreativeReferenceSlots
                    shot={shotQuery.data}
                    mode={creativeMode}
                    productionStatus={productionStatusQuery.data}
                    onOpenAdvanced={() => setWorkspaceMode("advanced")}
                  />
                  <ShotListPanel
                    projectId={projectId}
                    shots={shotsQuery.data.items}
                    activeShotId={activeShotId}
                    onMove={(id, orderIndex) => moveMutation.mutate({ id, orderIndex })}
                    onDuplicate={(id) => duplicateMutation.mutate(id)}
                    onDelete={(id) => deleteMutation.mutateAsync(id)}
                    disabled={moveMutation.isPending || duplicateMutation.isPending || deleteMutation.isPending}
                  />
                </aside>
              </PanelErrorBoundary>
              <PanelErrorBoundary title="当前画面加载失败">
                <CreativeResultStage
                  shot={shotQuery.data}
                  mode={creativeMode}
                  productionStatus={productionStatusQuery.data}
                  onModeChange={setCreativeMode}
                  onOpenAdvanced={() => setWorkspaceMode("advanced")}
                />
              </PanelErrorBoundary>
              <PanelErrorBoundary title="Prompt 与生成控制加载失败">
                <aside className="min-h-0 overflow-y-auto rounded-md border border-border bg-panel p-4">
                  <CreativePromptControl
                    shot={shotQuery.data}
                    mode={creativeMode}
                    workspaceMode={workspaceMode}
                    onWorkspaceModeChange={setWorkspaceMode}
                    onPrimaryAction={() => {
                      setWorkspaceMode("advanced");
                      setMessage({
                        tone: "success",
                        text: "一键生成尚未接入，已展开专业任务详情。"
                      });
                    }}
                  />
                  <div className={cn("mt-4 grid gap-4", workspaceMode === "quick" && "sr-only")}>
                    <ShotEditorPanel
                      projectId={projectId}
                      shot={shotQuery.data}
                      loading={shotQuery.isLoading}
                      scenes={scenesQuery.data?.items ?? []}
                      scenesLoading={scenesQuery.isLoading}
                      scenesError={scenesQuery.isError}
                      characters={charactersQuery.data?.items ?? []}
                      charactersLoading={charactersQuery.isLoading}
                      charactersError={charactersQuery.isError}
                      onMessage={setMessage}
                      invalidateShotData={invalidateShotData}
                    />
                    <ReferencePanel
                      projectId={projectId}
                      shot={shotQuery.data}
                      characters={charactersQuery.data?.items ?? []}
                      onMessage={setMessage}
                      invalidateShotData={invalidateShotData}
                      invalidateCreatedTaskData={invalidateCreatedTaskData}
                    />
                  </div>
                </aside>
              </PanelErrorBoundary>
            </div>
          </PanelErrorBoundary>
        )}
      </div>
    </AppShell>
  );
}

class PanelErrorBoundary extends Component<
  { children: React.ReactNode; title: string },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="rounded-md border border-danger/40 bg-danger/10 p-4">
          <StatusMessage tone="error">{this.props.title}，请刷新或重试。</StatusMessage>
          <Button type="button" variant="secondary" className="mt-3" onClick={() => this.setState({ hasError: false })}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            重试
          </Button>
        </section>
      );
    }
    return this.props.children;
  }
}

function CreativeTopBar({
  shot,
  mode,
  workspaceMode,
  productionStatus,
  comfyStatus,
  onModeChange,
  onWorkspaceModeChange,
  onPrimaryAction
}: {
  shot?: Shot;
  mode: CreativeMode;
  workspaceMode: WorkspaceMode;
  productionStatus?: ShotProductionStatus;
  comfyStatus: string;
  onModeChange: (mode: CreativeMode) => void;
  onWorkspaceModeChange: (mode: WorkspaceMode) => void;
  onPrimaryAction: () => void;
}) {
  const safeStatus = productionStatus ? normalizeShotProductionStatus(productionStatus) : null;
  const characterSummary =
    shot?.characters.length
      ? shot.characters.map((item) => `${item.character_name}${item.look_name ? ` · ${item.look_name}` : ""}`).join(" / ")
      : "缺少人物参考";
  const sceneSummary = shot?.scene?.name
    ? `${shot.scene.name}${shot.scene_state?.name ? ` · ${shot.scene_state.name}` : ""}`
    : "缺少场景参考";
  const workflowLabel =
    mode === "video"
      ? safeStatus?.steps.video.status === "not_created"
        ? "等待首尾帧"
        : "沿用视频任务"
      : "将自动选择";

  return (
    <section className="sticky top-0 z-10 rounded-md border border-border bg-panel/95 p-3 shadow-sm backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="primary">{`模式：${creativeModeCopy[mode].label}`}</Badge>
            <Badge>{workspaceMode === "quick" ? "快速创作模式" : "高级模式"}</Badge>
            <Badge>{`工作流：${workflowLabel}`}</Badge>
            <Badge>{`ComfyUI：${comfyStatus}`}</Badge>
          </div>
          <h2 className="mt-2 truncate text-base font-semibold text-foreground">
            {shot ? `镜头 ${shot.order_index}：${shot.name}` : "请选择镜头"}
          </h2>
          <p className="mt-1 line-clamp-1 text-xs text-muted">
            人物：{characterSummary} / 场景：{sceneSummary}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ModeTabs mode={mode} onModeChange={onModeChange} />
          <Button type="button" variant="secondary" onClick={() => onWorkspaceModeChange(workspaceMode === "quick" ? "advanced" : "quick")}>
            <Settings className="h-4 w-4" aria-hidden="true" />
            {workspaceMode === "quick" ? "高级设置" : "返回快速模式"}
          </Button>
          <Button type="button" onClick={onPrimaryAction}>
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {creativeModeCopy[mode].action}
          </Button>
        </div>
      </div>
      {(!shot?.characters.length || !shot.scene_id) && (
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted">
          {!shot?.characters.length && <Badge tone="danger">缺少人物参考</Badge>}
          {!shot?.scene_id && <Badge tone="danger">缺少场景参考</Badge>}
          <span>补齐后再生成，结果会更稳定。</span>
        </div>
      )}
    </section>
  );
}

function CreativeReferenceSlots({
  shot,
  mode,
  productionStatus,
  onOpenAdvanced
}: {
  shot?: Shot;
  mode: CreativeMode;
  productionStatus?: ShotProductionStatus;
  onOpenAdvanced: () => void;
}) {
  const safeStatus = productionStatus ? normalizeShotProductionStatus(productionStatus) : null;
  const slots =
    mode === "video"
      ? [
          {
            id: "start_frame",
            title: "视频首帧",
            purpose: "首帧",
            mediaUrl: safeStatus?.steps.first_frame.content_url,
            filled: Boolean(safeStatus?.steps.first_frame.adopted_media_asset_id)
          },
          {
            id: "end_frame",
            title: "视频尾帧",
            purpose: "尾帧",
            mediaUrl: safeStatus?.steps.end_frame.content_url,
            filled: Boolean(safeStatus?.steps.end_frame.adopted_media_asset_id)
          },
          ...referenceSlotsFromShot(shot, ["identity", "environment", "pose", "general"])
        ]
      : referenceSlotsFromShot(shot, ["identity", "appearance", "environment", "pose", "composition", "general"]);

  return (
    <section className="rounded-md border border-border bg-panel p-4">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-foreground">素材与参考</h2>
          <p className="mt-1 text-xs text-muted">把参考图按用途放入槽位，后续将用于自动装配工作流。</p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={onOpenAdvanced}>
          从资产选择
        </Button>
      </div>
      <div className="mt-4 grid gap-2">
        {slots.map((slot) => (
          <ReferenceSlotCard key={slot.id} {...slot} onOpenAdvanced={onOpenAdvanced} />
        ))}
      </div>
    </section>
  );
}

function ReferenceSlotCard({
  title,
  purpose,
  mediaUrl,
  filled,
  onOpenAdvanced
}: {
  title: string;
  purpose: string;
  mediaUrl?: string | null;
  filled: boolean;
  onOpenAdvanced: () => void;
}) {
  return (
    <article className="grid grid-cols-[72px_minmax(0,1fr)] gap-3 rounded-md border border-border bg-background p-2">
      <div className="flex aspect-square items-center justify-center overflow-hidden rounded border border-border bg-panel">
        {mediaUrl ? (
          <img src={mediaUrl} alt="" className="h-full w-full object-cover" loading="lazy" />
        ) : (
          <Images className="h-5 w-5 text-muted" aria-hidden="true" />
        )}
      </div>
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="truncate text-sm font-medium text-foreground">{title}</h3>
          <Badge tone={filled ? "success" : "default"}>{filled ? "已放入" : "空"}</Badge>
        </div>
        <p className="mt-1 text-xs text-muted">用途：{purpose}</p>
        <button type="button" className="mt-2 text-xs text-primary hover:text-foreground" onClick={onOpenAdvanced}>
          选择 / 替换
        </button>
      </div>
    </article>
  );
}

function CreativeResultStage({
  shot,
  mode,
  productionStatus,
  onModeChange,
  onOpenAdvanced
}: {
  shot?: Shot;
  mode: CreativeMode;
  productionStatus?: ShotProductionStatus;
  onModeChange: (mode: CreativeMode) => void;
  onOpenAdvanced: () => void;
}) {
  const safeStatus = productionStatus ? normalizeShotProductionStatus(productionStatus) : null;
  const currentStep =
    mode === "first_frame"
      ? safeStatus?.steps.first_frame
      : mode === "end_frame"
        ? safeStatus?.steps.end_frame
        : safeStatus?.steps.video;
  const contentUrl = currentStep?.content_url;
  const adopted = Boolean(currentStep?.adopted_output_id);

  return (
    <main className="min-h-0 overflow-y-auto rounded-md border border-border bg-panel p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">当前画面与生成结果</h2>
          <p className="mt-1 text-xs text-muted">围绕当前镜头查看候选、采用结果和下一步。</p>
        </div>
        <ModeTabs mode={mode} onModeChange={onModeChange} />
      </div>
      <section className="mt-4 overflow-hidden rounded-md border border-border bg-background">
        <div className="flex aspect-[9/16] min-h-[420px] items-center justify-center bg-black/20">
          {contentUrl ? (
            mode === "video" ? (
              <video src={contentUrl} controls className="h-full max-h-[720px] w-full object-contain" />
            ) : (
              <img src={contentUrl} alt="" className="h-full max-h-[720px] w-full object-contain" />
            )
          ) : (
            <div className="max-w-sm px-6 text-center">
              <Film className="mx-auto h-10 w-10 text-muted" aria-hidden="true" />
              <h3 className="mt-3 text-sm font-semibold text-foreground">{creativeModeCopy[mode].label}结果区</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{creativeModeCopy[mode].empty}</p>
              <Button type="button" variant="secondary" className="mt-4" onClick={onOpenAdvanced}>
                查看专业任务详情
              </Button>
            </div>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border p-3">
          <Badge tone={adopted ? "success" : "default"}>{adopted ? "已采用" : "未采用"}</Badge>
          <div className="text-xs text-muted">
            未采用候选不会进入时间线。
          </div>
        </div>
      </section>
      <section className="mt-4 grid gap-3 rounded-md border border-border bg-background p-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-foreground">候选结果</h3>
          <Button type="button" variant="secondary" size="sm" onClick={onOpenAdvanced}>
            打开任务详情
          </Button>
        </div>
        <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted">
          当前模式下的候选会在这里集中展示。Sprint 23 保留现有任务链，不自动启动生成。
        </div>
      </section>
      {shot && (
        <section className="mt-4 rounded-md border border-border bg-background p-3 text-sm text-muted">
          下一步建议：{nextActionHint(shot, safeStatus, mode)}
        </section>
      )}
    </main>
  );
}

function CreativePromptControl({
  shot,
  mode,
  workspaceMode,
  onWorkspaceModeChange,
  onPrimaryAction
}: {
  shot?: Shot;
  mode: CreativeMode;
  workspaceMode: WorkspaceMode;
  onWorkspaceModeChange: (mode: WorkspaceMode) => void;
  onPrimaryAction: () => void;
}) {
  const promptSeed = [
    shot?.visual_description,
    shot?.action_summary,
    shot?.mood_description
  ].filter(Boolean).join("\n");

  return (
    <section className="grid gap-4">
      <div>
        <h2 className="text-base font-semibold text-foreground">Prompt 与生成控制</h2>
        <p className="mt-1 text-xs text-muted">快速模式只保留创作必需项，底层任务参数放在高级设置。</p>
      </div>
      <div className="grid gap-3">
        <Field label="镜头意图">
          <Input defaultValue={shot?.action_summary ?? ""} placeholder="例如：男主推门闯入会议室" />
        </Field>
        <Field label="Prompt">
          <Textarea defaultValue={promptSeed} placeholder="描述画面主体、场景、动作和氛围" />
        </Field>
        <details className="rounded-md border border-border bg-background p-3">
          <summary className="cursor-pointer text-sm font-medium text-foreground">负面 Prompt</summary>
          <Textarea className="mt-3" placeholder="低质量、变形、模糊等" />
        </details>
        <div className="grid gap-3 md:grid-cols-2">
          <SelectField label="快速景别" value={shot?.shot_scale ?? "unknown"} onChange={() => undefined} options={shotScaleOptions} />
          <SelectField label="快速镜头运动" value={shot?.camera_movement ?? "unknown"} onChange={() => undefined} options={movementOptions} />
        </div>
        {mode === "video" && (
          <Field label="时长（秒）">
            <Input type="number" min="0.1" step="0.1" defaultValue={shot?.duration_seconds ?? ""} />
          </Field>
        )}
        <Field label="候选数量">
          <Input type="number" min="1" max="4" defaultValue={1} />
        </Field>
        <Button type="button" onClick={onPrimaryAction}>
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          {creativeModeCopy[mode].action}
        </Button>
        <StatusMessage tone="success">
          Sprint 23 只重构创作入口；一键创建、ready 和 start 将在 Sprint 25 接入。当前可通过高级任务详情继续使用原生成链路。
        </StatusMessage>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant={workspaceMode === "quick" ? "secondary" : "default"}
          onClick={() => onWorkspaceModeChange(workspaceMode === "quick" ? "advanced" : "quick")}
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          {workspaceMode === "quick" ? "查看高级设置" : "收起高级设置"}
        </Button>
      </div>
    </section>
  );
}

function ModeTabs({
  mode,
  onModeChange
}: {
  mode: CreativeMode;
  onModeChange: (mode: CreativeMode) => void;
}) {
  return (
    <div className="grid grid-cols-3 gap-1 rounded-md border border-border bg-background p-1 text-xs">
      {(Object.keys(creativeModeCopy) as CreativeMode[]).map((item) => (
        <button
          key={item}
          type="button"
          className={cn(
            "rounded px-3 py-2 text-muted transition-colors",
            mode === item && "bg-primarySoft text-foreground"
          )}
          onClick={() => onModeChange(item)}
        >
          {`${creativeModeCopy[item].label}模式`}
        </button>
      ))}
    </div>
  );
}

function ShotListPanel({
  projectId,
  shots,
  activeShotId,
  onMove,
  onDuplicate,
  onDelete,
  disabled
}: {
  projectId: string;
  shots: Shot[];
  activeShotId: string;
  onMove: (id: string, orderIndex: number) => void;
  onDuplicate: (id: string) => void;
  onDelete: (id: string) => Promise<void>;
  disabled: boolean;
}) {
  return (
    <aside className="min-h-0 overflow-hidden rounded-md border border-border bg-panel">
      <div className="border-b border-border px-4 py-3 text-sm font-semibold">{shotCopy.sections.list}</div>
      <div className="max-h-[560px] space-y-2 overflow-y-auto p-3">
        {shots.map((shot) => (
          <article
            key={shot.id}
            className={cn(
              "rounded-md border p-3",
              shot.id === activeShotId ? "border-primary bg-primarySoft" : "border-border bg-background"
            )}
          >
            <Link to={`/projects/${projectId}/shots/${shot.id}`} className="block">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-muted">#{shot.order_index}</span>
                <ReadinessBadge status={shot.readiness_status} />
              </div>
              <h2 className="mt-2 break-words text-sm font-semibold text-foreground">{shot.name}</h2>
              <p className="mt-1 line-clamp-2 text-xs text-muted">
                {shot.missing_items.length > 0
                  ? shot.missing_items.map((item) => shotCopy.missing[item]).join(" / ")
                  : `${shot.character_count} 个角色 / ${shot.reference_count} 条参考`}
              </p>
            </Link>
            <div className="mt-3 flex flex-wrap gap-1">
              <Button type="button" variant="secondary" size="icon" title="上移" disabled={disabled || shot.order_index <= 1} onClick={() => onMove(shot.id, shot.order_index - 1)}>
                <ArrowUp className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button type="button" variant="secondary" size="icon" title="下移" disabled={disabled || shot.order_index >= shots.length} onClick={() => onMove(shot.id, shot.order_index + 1)}>
                <ArrowDown className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button type="button" variant="secondary" size="icon" title="复制" disabled={disabled} onClick={() => onDuplicate(shot.id)}>
                <Copy className="h-4 w-4" aria-hidden="true" />
              </Button>
              <ConfirmDeleteDialog
                title={shotCopy.deleteShot}
                description={shotCopy.deleteShotDescription(shot.name)}
                onConfirm={() => onDelete(shot.id)}
                trigger={
                  <Button type="button" variant="danger" size="icon" title={shotCopy.deleteShot} disabled={disabled}>
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </Button>
                }
              />
            </div>
          </article>
        ))}
      </div>
    </aside>
  );
}

function ShotEditorPanel({
  projectId,
  shot,
  loading,
  scenes,
  scenesLoading,
  scenesError,
  characters,
  charactersLoading,
  charactersError,
  onMessage,
  invalidateShotData
}: {
  projectId: string;
  shot?: Shot;
  loading: boolean;
  scenes: Scene[];
  scenesLoading: boolean;
  scenesError: boolean;
  characters: Character[];
  charactersLoading: boolean;
  charactersError: boolean;
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateShotData: (shotId?: string) => Promise<void>;
}) {
  const queryClient = useQueryClient();
  const form = useForm<ShotFormValues>({
    resolver: zodResolver(shotFormSchema),
    defaultValues: defaultShotFormValues()
  });
  const selectedSceneId = form.watch("scene_id");
  const [scenePickerOpen, setScenePickerOpen] = useState(false);
  const [sceneStatePickerOpen, setSceneStatePickerOpen] = useState(false);
  const cameraHeight = form.watch("camera_height");
  const cameraAngle = form.watch("camera_angle");
  const composition = form.watch("composition_type");
  const movement = form.watch("camera_movement");
  const statesQuery = useQuery({
    queryKey: sceneKeys.states(projectId, selectedSceneId || ""),
    queryFn: () => fetchSceneStates(projectId, selectedSceneId || ""),
    enabled: Boolean(selectedSceneId)
  });
  const shotReferencesQuery = useQuery({
    queryKey: shot ? shotKeys.references(projectId, shot.id) : ["shots", "none"],
    queryFn: () => fetchShotReferences(projectId, shot?.id || ""),
    enabled: Boolean(shot?.id)
  });

  useEffect(() => {
    if (shot) {
      form.reset(shotToFormValues(shot));
    }
  }, [form, shot]);

  const updateMutation = useMutation({
    mutationFn: (payload: ShotInput) => updateShot(projectId, shot?.id || "", payload),
    onSuccess: async (updated) => {
      await invalidateShotData(updated.id);
      onMessage({ tone: "success", text: "镜头已保存" });
    },
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, shotCopy.saveFailed) })
  });
  const addCharacterMutation = useMutation({
    mutationFn: (payload: { characterId: string; lookId: string | null }) =>
      addShotCharacter(projectId, shot?.id || "", {
        character_id: payload.characterId,
        look_id: payload.lookId,
        is_primary_subject: (shot?.characters.length ?? 0) === 0
      }),
    onSuccess: async () => {
      await invalidateShotData(shot?.id);
      onMessage({ tone: "success", text: "镜头角色已添加" });
    },
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "镜头角色保存失败") })
  });

  function handleSceneChange(nextSceneId: string) {
    const actual = nextSceneId === NONE ? "" : nextSceneId;
    const willClearRefs = hasSceneRefs(shotReferencesQuery.data?.items ?? []) && actual !== shot?.scene_id;
    if (willClearRefs && !window.confirm(shotCopy.sceneReferenceClearWarning)) {
      return;
    }
    form.setValue("scene_id", actual);
    form.setValue("scene_state_id", "");
    void queryClient.invalidateQueries({ queryKey: shot ? shotKeys.references(projectId, shot.id) : undefined });
  }

  function handleStateChange(nextStateId: string) {
    const actual = nextStateId === NONE ? "" : nextStateId;
    const willClearRefs = hasSceneRefs(shotReferencesQuery.data?.items ?? []) && actual !== shot?.scene_state_id;
    if (willClearRefs && !window.confirm(shotCopy.sceneReferenceClearWarning)) {
      return;
    }
    form.setValue("scene_state_id", actual);
  }

  function handleScenePickerConfirm(item: PickerOptionItem) {
    const nextSceneId = item.id;
    const willClearRefs = hasSceneRefs(shotReferencesQuery.data?.items ?? []) && nextSceneId !== shot?.scene_id;
    if (willClearRefs && !window.confirm(shotCopy.sceneReferenceClearWarning)) {
      return;
    }
    form.setValue("scene_id", nextSceneId);
    form.setValue("scene_state_id", "");
    updateMutation.mutate(
      formValuesToPayload({
        ...form.getValues(),
        scene_id: nextSceneId,
        scene_state_id: ""
      })
    );
  }

  function handleSceneStatePickerConfirm(item: PickerOptionItem) {
    if (!shot?.scene_id) {
      onMessage({ tone: "error", text: "请先选择场景，再选择场景状态" });
      return;
    }
    const nextStateId = item.id;
    const willClearRefs =
      hasSceneRefs(shotReferencesQuery.data?.items ?? []) && nextStateId !== shot.scene_state_id;
    if (willClearRefs && !window.confirm(shotCopy.sceneReferenceClearWarning)) {
      return;
    }
    form.setValue("scene_state_id", nextStateId);
    updateMutation.mutate(
      formValuesToPayload({
        ...form.getValues(),
        scene_state_id: nextStateId
      })
    );
  }

  if (loading) {
    return <Skeleton className="min-h-[620px]" />;
  }
  if (!shot) {
    return <section className="rounded-md border border-border bg-panel p-5">{shotCopy.emptyTitle}</section>;
  }

  const selectedStateId = form.watch("scene_state_id");
  const stateOptions = statesQuery.data?.items ?? [];
  const stateSelectDisabled = !selectedSceneId || statesQuery.isLoading || statesQuery.isError;

  return (
    <section className="min-h-0 overflow-y-auto rounded-md border border-border bg-panel p-4">
      <form
        className="grid gap-4"
        onSubmit={form.handleSubmit((values) => updateMutation.mutate(formValuesToPayload(values)))}
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">{shotCopy.sections.basic}</h2>
            <p className="mt-1 text-xs text-muted">{shotCopy.readiness[shot.readiness_status]}</p>
          </div>
          <Button type="submit" disabled={updateMutation.isPending}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {updateMutation.isPending ? shotCopy.saving : shotCopy.saveShot}
          </Button>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <Field label={shotCopy.fields.name}>
            <Input {...form.register("name")} />
          </Field>
          <Field label={shotCopy.fields.duration}>
            <Input type="number" step="0.1" {...form.register("duration_seconds")} />
            {form.formState.errors.duration_seconds?.message && (
              <FieldHint tone="error">{form.formState.errors.duration_seconds.message}</FieldHint>
            )}
          </Field>
        </div>
        <Field label={shotCopy.fields.visualDescription}>
          <Textarea {...form.register("visual_description")} />
        </Field>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label={shotCopy.fields.storyDescription}>
            <Textarea {...form.register("story_description")} />
          </Field>
          <Field label={shotCopy.fields.actionSummary}>
            <Textarea {...form.register("action_summary")} />
          </Field>
        </div>
        <Field label={shotCopy.fields.dialogue}>
          <Textarea {...form.register("dialogue")} />
        </Field>

        <SectionTitle>{shotCopy.sections.scene}</SectionTitle>
        <div className="grid gap-3 md:grid-cols-2">
          <Field label={shotCopy.fields.scene}>
            <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
            <Select value={selectedSceneId || NONE} onValueChange={handleSceneChange}>
              <SelectTrigger aria-label={shotCopy.fields.scene}><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>未选择</SelectItem>
                {scenes.map((scene) => <SelectItem key={scene.id} value={scene.id}>{scene.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button type="button" variant="secondary" onClick={() => setScenePickerOpen(true)}>
              {assetPickerCopy.chooseScene}
            </Button>
            </div>
            {scenesLoading && <FieldHint>{shotCopy.loadingOptions}</FieldHint>}
            {scenesError && <FieldHint tone="error">{shotCopy.scenesLoadFailed}</FieldHint>}
            {!scenesLoading && !scenesError && scenes.length === 0 && <FieldHint>{shotCopy.noScenes}</FieldHint>}
            <AssetPickerDialog
              open={scenePickerOpen}
              onOpenChange={setScenePickerOpen}
              projectId={projectId}
              scope="shot"
              assetType="scene"
              shotId={shot.id}
              title={assetPickerCopy.chooseScene}
              onConfirm={handleScenePickerConfirm}
            />
          </Field>
          <Field label={shotCopy.fields.sceneState}>
            <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
              <Select value={selectedStateId || NONE} onValueChange={handleStateChange} disabled={stateSelectDisabled}>
                <SelectTrigger aria-label={shotCopy.fields.sceneState}><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE}>未选择</SelectItem>
                  {stateOptions.map((state) => <SelectItem key={state.id} value={state.id}>{state.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  if (!selectedSceneId) {
                    onMessage({ tone: "error", text: "请先选择场景，再选择场景状态" });
                    return;
                  }
                  setSceneStatePickerOpen(true);
                }}
              >
                {assetPickerCopy.chooseSceneState}
              </Button>
            </div>
            {selectedSceneId && statesQuery.isLoading && <FieldHint>{shotCopy.loadingOptions}</FieldHint>}
            {selectedSceneId && statesQuery.isError && <FieldHint tone="error">{shotCopy.statesLoadFailed}</FieldHint>}
            {selectedSceneId && statesQuery.isSuccess && stateOptions.length === 0 && <FieldHint>{shotCopy.noSceneStates}</FieldHint>}
            {selectedSceneId && (
              <AssetPickerDialog
                open={sceneStatePickerOpen}
                onOpenChange={setSceneStatePickerOpen}
                projectId={projectId}
                scope="shot"
                assetType="scene_state"
                shotId={shot.id}
                sceneId={selectedSceneId}
                title={assetPickerCopy.chooseSceneState}
                onConfirm={handleSceneStatePickerConfirm}
              />
            )}
          </Field>
        </div>

        <SectionTitle>{shotCopy.sections.camera}</SectionTitle>
        <div className="grid gap-3 md:grid-cols-2">
          <SelectField label={shotCopy.fields.shotScale} value={form.watch("shot_scale")} onChange={(value) => form.setValue("shot_scale", value)} options={shotScaleOptions} />
          <SelectField label={shotCopy.fields.cameraHeight} value={cameraHeight} onChange={(value) => form.setValue("camera_height", value)} options={cameraHeightOptions} />
          {cameraHeight === "custom" && <Field label="自定义机位高度"><Input {...form.register("custom_camera_height")} /></Field>}
          <SelectField label={shotCopy.fields.cameraAngle} value={cameraAngle} onChange={(value) => form.setValue("camera_angle", value)} options={cameraAngleOptions} />
          {cameraAngle === "custom" && <Field label="自定义拍摄角度"><Input {...form.register("custom_camera_angle")} /></Field>}
          <SelectField label={shotCopy.fields.composition} value={composition} onChange={(value) => form.setValue("composition_type", value)} options={compositionOptions} />
          {composition === "custom" && <Field label="自定义构图"><Input {...form.register("custom_composition")} /></Field>}
          <SelectField label={shotCopy.fields.cameraMovement} value={movement} onChange={(value) => form.setValue("camera_movement", value)} options={movementOptions} />
          {movement === "custom" && <Field label="自定义镜头运动"><Input {...form.register("custom_camera_movement")} /></Field>}
          <Field label={shotCopy.fields.focalSubject}><Input {...form.register("focal_subject")} /></Field>
          <Field label={shotCopy.fields.mood}><Input {...form.register("mood_description")} /></Field>
        </div>
        <Field label={shotCopy.fields.notes}><Textarea {...form.register("notes")} /></Field>
      </form>

      <ShotCharactersEditor
        projectId={projectId}
        shot={shot}
        characters={characters}
        charactersLoading={charactersLoading}
        charactersError={charactersError}
        onAdd={(characterId, lookId) => addCharacterMutation.mutate({ characterId, lookId })}
        onMessage={onMessage}
        invalidateShotData={invalidateShotData}
      />
    </section>
  );
}

function ShotCharactersEditor({
  projectId,
  shot,
  characters,
  charactersLoading,
  charactersError,
  onAdd,
  onMessage,
  invalidateShotData
}: {
  projectId: string;
  shot: Shot;
  characters: Character[];
  charactersLoading: boolean;
  charactersError: boolean;
  onAdd: (characterId: string, lookId: string | null) => void;
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateShotData: (shotId?: string) => Promise<void>;
}) {
  const [characterId, setCharacterId] = useState("");
  const [lookId, setLookId] = useState("");
  const [characterPickerOpen, setCharacterPickerOpen] = useState(false);
  const [lookPickerShotCharacter, setLookPickerShotCharacter] = useState<ShotCharacter | null>(null);
  const looksQuery = useQuery({
    queryKey: characterId ? characterKeys.looks(projectId, characterId) : ["looks", "none"],
    queryFn: () => fetchLooks(projectId, characterId),
    enabled: characterId.length > 0
  });
  const updateMutation = useMutation({
    mutationFn: ({ item, patch }: { item: ShotCharacter; patch: Record<string, unknown> }) =>
      updateShotCharacter(projectId, shot.id, item.id, patch),
    onSuccess: async () => invalidateShotData(shot.id),
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "镜头角色保存失败") })
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteShotCharacter(projectId, shot.id, id),
    onSuccess: async () => invalidateShotData(shot.id),
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "镜头角色删除失败") })
  });
  const moveMutation = useMutation({
    mutationFn: ({ id, orderIndex }: { id: string; orderIndex: number }) =>
      moveShotCharacter(projectId, shot.id, id, orderIndex),
    onSuccess: async () => invalidateShotData(shot.id)
  });

  function handleCharacterPickerConfirm(item: PickerOptionItem) {
    const defaultLookId =
      typeof item.metadata.default_look_id === "string" ? item.metadata.default_look_id : null;
    onAdd(item.id, defaultLookId);
  }

  function handleLookPickerConfirm(item: PickerOptionItem) {
    if (!lookPickerShotCharacter) {
      return;
    }
    updateMutation.mutate({
      item: lookPickerShotCharacter,
      patch: { look_id: item.id }
    });
  }

  return (
    <div className="mt-6 grid gap-3 border-t border-border pt-4">
      <SectionTitle>{shotCopy.sections.characters}</SectionTitle>
      <div className="grid gap-2 md:grid-cols-[1fr_1fr_auto_auto]">
        <Select value={characterId || NONE} onValueChange={(value) => { setCharacterId(value === NONE ? "" : value); setLookId(""); }}>
          <SelectTrigger aria-label={shotCopy.fields.character}><SelectValue placeholder={shotCopy.fields.character} /></SelectTrigger>
          <SelectContent>
            <SelectItem value={NONE}>选择角色</SelectItem>
            {characters.map((character) => <SelectItem key={character.id} value={character.id}>{character.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={lookId || NONE} onValueChange={(value) => setLookId(value === NONE ? "" : value)} disabled={!characterId}>
          <SelectTrigger aria-label={shotCopy.fields.look}><SelectValue placeholder={shotCopy.fields.look} /></SelectTrigger>
          <SelectContent>
            <SelectItem value={NONE}>不指定造型</SelectItem>
            {(looksQuery.data?.items ?? []).map((look) => <SelectItem key={look.id} value={look.id}>{look.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Button type="button" onClick={() => characterId && onAdd(characterId, lookId || null)} disabled={!characterId}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          添加
        </Button>
        <Button type="button" variant="secondary" onClick={() => setCharacterPickerOpen(true)}>
          {assetPickerCopy.chooseCharacter}
        </Button>
      </div>
      <AssetPickerDialog
        open={characterPickerOpen}
        onOpenChange={setCharacterPickerOpen}
        projectId={projectId}
        scope="shot"
        assetType="character"
        shotId={shot.id}
        title={assetPickerCopy.chooseCharacter}
        onConfirm={handleCharacterPickerConfirm}
      />
      {charactersLoading && <FieldHint>{shotCopy.loadingOptions}</FieldHint>}
      {charactersError && <FieldHint tone="error">{shotCopy.charactersLoadFailed}</FieldHint>}
      {!charactersLoading && !charactersError && characters.length === 0 && <FieldHint>{shotCopy.noCharacters}</FieldHint>}
      {characterId && looksQuery.isSuccess && (looksQuery.data?.items ?? []).length === 0 && (
        <FieldHint>该角色还没有造型。</FieldHint>
      )}
      {shot.characters.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted">当前镜头还没有角色。</div>
      ) : (
        <div className="grid gap-2">
          {shot.characters.map((item) => (
            <article key={item.id} className="rounded-md border border-border bg-background p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium">{item.character_name}</div>
                  <div className="text-xs text-muted">{item.look_name || "未指定造型"}</div>
                </div>
                <div className="flex gap-1">
                  <Button
                    type="button"
                    variant="secondary"
                    title={assetPickerCopy.chooseCharacterLook}
                    onClick={() => setLookPickerShotCharacter(item)}
                  >
                    {assetPickerCopy.chooseCharacterLook}
                  </Button>
                  <Button type="button" variant="secondary" size="icon" title="上移" disabled={item.order_index <= 1} onClick={() => moveMutation.mutate({ id: item.id, orderIndex: item.order_index - 1 })}><ArrowUp className="h-4 w-4" aria-hidden="true" /></Button>
                  <Button type="button" variant="secondary" size="icon" title="下移" disabled={item.order_index >= shot.characters.length} onClick={() => moveMutation.mutate({ id: item.id, orderIndex: item.order_index + 1 })}><ArrowDown className="h-4 w-4" aria-hidden="true" /></Button>
                  <ConfirmDeleteDialog
                    title={shotCopy.deleteShotCharacter}
                    description={shotCopy.deleteShotCharacterDescription(item.character_name)}
                    onConfirm={() => deleteMutation.mutateAsync(item.id)}
                    trigger={<Button type="button" variant="danger" size="icon" title={shotCopy.deleteShotCharacter}><Trash2 className="h-4 w-4" aria-hidden="true" /></Button>}
                  />
                </div>
              </div>
              <div className="mt-3 grid gap-2 md:grid-cols-3">
                <Input placeholder={shotCopy.fields.action} defaultValue={item.action_description ?? ""} onBlur={(event) => updateMutation.mutate({ item, patch: { action_description: event.currentTarget.value } })} />
                <Input placeholder={shotCopy.fields.expression} defaultValue={item.expression_description ?? ""} onBlur={(event) => updateMutation.mutate({ item, patch: { expression_description: event.currentTarget.value } })} />
                <Input placeholder={shotCopy.fields.position} defaultValue={item.position_description ?? ""} onBlur={(event) => updateMutation.mutate({ item, patch: { position_description: event.currentTarget.value } })} />
              </div>
              <label className="mt-3 flex items-center gap-2 text-sm">
                <input type="checkbox" defaultChecked={item.is_primary_subject} onChange={(event) => updateMutation.mutate({ item, patch: { is_primary_subject: event.currentTarget.checked } })} />
                {shotCopy.fields.primarySubject}
              </label>
            </article>
          ))}
          {lookPickerShotCharacter && (
            <AssetPickerDialog
              open={Boolean(lookPickerShotCharacter)}
              onOpenChange={(open) => {
                if (!open) {
                  setLookPickerShotCharacter(null);
                }
              }}
              projectId={projectId}
              scope="shot"
              assetType="character_look"
              shotId={shot.id}
              characterId={lookPickerShotCharacter.character_id}
              shotCharacterId={lookPickerShotCharacter.id}
              title={assetPickerCopy.chooseCharacterLook}
              onConfirm={handleLookPickerConfirm}
            />
          )}
        </div>
      )}
    </div>
  );
}

function ReferencePanel({
  projectId,
  shot,
  characters,
  onMessage,
  invalidateShotData,
  invalidateCreatedTaskData
}: {
  projectId: string;
  shot?: Shot;
  characters: Character[];
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateShotData: (shotId?: string) => Promise<void>;
  invalidateCreatedTaskData: (
    shotId: string,
    taskId: string,
    taskType: "keyframe" | "video"
  ) => Promise<void>;
}) {
  const [selectedShotCharacterId, setSelectedShotCharacterId] = useState("");
  const [characterPurpose, setCharacterPurpose] = useState<CharacterReferencePurpose>("identity");
  const [scenePurpose, setScenePurpose] = useState<SceneReferencePurpose>("environment");
  const [activeTab, setActiveTab] = useState<"smart" | "keyframes" | "character" | "scene" | "selected">("smart");
  const [referencePickerOpen, setReferencePickerOpen] = useState(false);
  const productionStatusQuery = useQuery({
    queryKey: shot ? productionStatusKeys.shot(projectId, shot.id) : ["production-status", "none"],
    queryFn: () => fetchShotProductionStatus(projectId, shot?.id || ""),
    enabled: Boolean(projectId && shot?.id)
  });
  const selectedShotCharacter = shot?.characters.find((item) => item.id === selectedShotCharacterId) ?? shot?.characters[0];
  const selectedCharacter = characters.find((item) => item.id === selectedShotCharacter?.character_id);
  const looksQuery = useQuery({
    queryKey: selectedCharacter ? characterKeys.looks(projectId, selectedCharacter.id) : ["looks", "none"],
    queryFn: () => fetchLooks(projectId, selectedCharacter?.id || ""),
    enabled: Boolean(selectedCharacter?.id)
  });
  const activeLook = useMemo(() => {
    const looks = looksQuery.data?.items ?? [];
    return looks.find((look) => look.id === selectedShotCharacter?.look_id) ?? looks[0];
  }, [looksQuery.data?.items, selectedShotCharacter?.look_id]);
  const characterRefsQuery = useQuery({
    queryKey: activeLook && selectedCharacter ? characterKeys.references(projectId, selectedCharacter.id, activeLook.id) : ["refs", "none"],
    queryFn: () => fetchReferences(projectId, selectedCharacter?.id || "", activeLook?.id || ""),
    enabled: Boolean(selectedCharacter?.id && activeLook?.id)
  });
  const sceneRefsQuery = useQuery({
    queryKey: shot?.scene_id && shot.scene_state_id ? sceneKeys.references(projectId, shot.scene_id, shot.scene_state_id) : ["scene-refs", "none"],
    queryFn: () => fetchSceneReferences(projectId, shot?.scene_id || "", shot?.scene_state_id || ""),
    enabled: Boolean(shot?.scene_id && shot.scene_state_id)
  });
  const addRefMutation = useMutation({
    mutationFn: (payload: Parameters<typeof addShotReference>[2]) => addShotReference(projectId, shot?.id || "", payload),
    onSuccess: async () => invalidateShotData(shot?.id),
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "参考图绑定失败") })
  });
  const deleteRefMutation = useMutation({
    mutationFn: (id: string) => deleteShotReference(projectId, shot?.id || "", id),
    onSuccess: async () => invalidateShotData(shot?.id),
    onError: (error) => onMessage({ tone: "error", text: getErrorText(error, "参考图解绑失败") })
  });
  const moveRefMutation = useMutation({
    mutationFn: ({ id, orderIndex }: { id: string; orderIndex: number }) => moveShotReference(projectId, shot?.id || "", id, orderIndex),
    onSuccess: async () => invalidateShotData(shot?.id)
  });

  async function createKeyframeTaskFromDraft(
    draft: PromptDraftResponse,
    frame: "first" | "end"
  ) {
    if (!shot) {
      return;
    }
    let taskId = "";
    try {
      const created = await createKeyframeTask(projectId, shot.id, {
        name: `${frame === "first" ? "首帧草稿" : "尾帧草稿"} - ${shotTaskLabel(shot)}`,
        purpose: frame === "first" ? "first_frame" : "end_frame",
        copy_current_references: true
      });
      taskId = created.id;
    } catch (error) {
      onMessage({
        tone: "error",
        text: getErrorText(error, promptBuilderCopy.taskCreateFailed)
      });
      return;
    }

    try {
      const updated = await updateKeyframeTask(projectId, taskId, {
        prompt_zh: draft.context_summary_zh,
        prompt_en:
          frame === "first" ? draft.first_frame_prompt_en : draft.end_frame_prompt_en,
        negative_prompt: draft.negative_prompt_en
      });
      await invalidateCreatedTaskData(shot.id, updated.id, "keyframe");
      setActiveTab("keyframes");
      onMessage({
        tone: "success",
        text:
          frame === "first"
            ? promptBuilderCopy.firstFrameTaskCreated
            : promptBuilderCopy.endFrameTaskCreated
      });
    } catch {
      await invalidateCreatedTaskData(shot.id, taskId, "keyframe");
      setActiveTab("keyframes");
      onMessage({ tone: "error", text: promptBuilderCopy.taskPatchFailed });
    }
  }

  async function createVideoTaskFromDraft(draft: PromptDraftResponse) {
    await createVideoTaskWithOptionalAdoptedFrames(draft);
  }

  async function createVideoTaskFromProductionPanel() {
    await createVideoTaskWithOptionalAdoptedFrames();
  }

  async function createVideoTaskWithOptionalAdoptedFrames(draft?: PromptDraftResponse) {
    if (!shot) {
      return;
    }
    const adoptedInputs = confirmedAdoptedVideoInputs(productionStatusQuery.data);
    let taskId = "";
    try {
      const created = await createVideoTask(projectId, shot.id, {});
      taskId = created.id;
    } catch (error) {
      onMessage({
        tone: "error",
        text: getErrorText(error, promptBuilderCopy.taskCreateFailed)
      });
      return;
    }

    try {
      const updated = await updateVideoTask(projectId, taskId, {
        name: `视频草稿 - ${shotTaskLabel(shot)}`,
        inputs: adoptedInputs.length > 0 ? adoptedInputs : undefined,
        prompt: draft?.motion_prompt_en,
        negative_prompt: draft?.negative_prompt_en,
        camera_motion: draft?.camera_motion,
        duration_seconds:
          typeof shot.duration_seconds === "number" && shot.duration_seconds > 0
            ? shot.duration_seconds
            : undefined
      });
      await invalidateCreatedTaskData(shot.id, updated.id, "video");
      setActiveTab("keyframes");
      onMessage({
        tone: "success",
        text:
          adoptedInputs.length > 0
            ? productionStatusCopy.videoTaskCreatedWithFrames
            : promptBuilderCopy.videoTaskCreated
      });
    } catch {
      await invalidateCreatedTaskData(shot.id, taskId, "video");
      setActiveTab("keyframes");
      onMessage({
        tone: "error",
        text:
          adoptedInputs.length > 0
            ? productionStatusCopy.videoTaskFrameFillFailed
            : promptBuilderCopy.taskPatchFailed
      });
    }
  }

  function handleReferencePickerConfirm(item: PickerOptionItem) {
    const referenceType = pickerMetadataString(item, "reference_type");
    const suggestedPurpose = pickerMetadataString(item, "suggested_purpose");
    if (referenceType === "character") {
      const characterReferenceId = pickerMetadataString(item, "character_reference_id");
      const shotCharacterId = pickerMetadataString(item, "shot_character_id");
      if (!characterReferenceId) {
        onMessage({ tone: "error", text: "人物参考图信息不完整，无法绑定。" });
        return;
      }
      addRefMutation.mutate({
        reference_type: "character",
        character_reference_id: characterReferenceId,
        shot_character_id: shotCharacterId || undefined,
        purpose: (suggestedPurpose || "identity") as CharacterReferencePurpose
      });
      return;
    }
    if (referenceType === "scene") {
      const sceneReferenceId = pickerMetadataString(item, "scene_reference_id");
      if (!sceneReferenceId) {
        onMessage({ tone: "error", text: "场景参考图信息不完整，无法绑定。" });
        return;
      }
      addRefMutation.mutate({
        reference_type: "scene",
        scene_reference_id: sceneReferenceId,
        purpose: (suggestedPurpose || "environment") as SceneReferencePurpose
      });
      return;
    }
    onMessage({ tone: "error", text: "当前参考图类型暂不支持绑定。" });
  }

  if (!shot) {
    return <aside className="rounded-md border border-border bg-panel p-4 text-sm text-muted">请选择镜头。</aside>;
  }

  return (
    <aside className="min-h-0 overflow-y-auto rounded-md border border-border bg-panel p-4">
      <div className="grid gap-4">
        <ShotProductionPanel
          status={productionStatusQuery.data}
          loading={productionStatusQuery.isLoading}
          error={productionStatusQuery.isError}
          onRetry={() => void productionStatusQuery.refetch()}
          onOpenPrompt={() =>
            document.getElementById("shot-prompt-draft")?.scrollIntoView({
              behavior: "smooth",
              block: "start"
            })
          }
          onOpenTasks={() => setActiveTab("keyframes")}
          onCreateVideoTask={createVideoTaskFromProductionPanel}
        />
        <ShotAssetSummaryCard projectId={projectId} shotId={shot.id} />
        <div id="shot-prompt-draft">
          <PromptDraftCard
            projectId={projectId}
            shotId={shot.id}
            onCreateFirstFrameTask={(draft) => createKeyframeTaskFromDraft(draft, "first")}
            onCreateEndFrameTask={(draft) => createKeyframeTaskFromDraft(draft, "end")}
            onCreateVideoTask={createVideoTaskFromDraft}
          />
        </div>
        <Button type="button" variant="secondary" onClick={() => setReferencePickerOpen(true)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {assetPickerCopy.chooseReferenceImage}
        </Button>
        <AssetPickerDialog
          open={referencePickerOpen}
          onOpenChange={setReferencePickerOpen}
          projectId={projectId}
          scope="shot"
          assetType="reference_image"
          shotId={shot.id}
          source="shot_context"
          title={assetPickerCopy.chooseReferenceImage}
          description={assetPickerCopy.referenceDescription}
          onConfirm={handleReferencePickerConfirm}
        />
        <div className="grid grid-cols-2 gap-1 rounded-md border border-border bg-background p-1 text-xs">
          {(["smart", "keyframes", "character", "scene", "selected"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              className={cn(
                "rounded px-2 py-1.5 text-muted",
                activeTab === tab && "bg-primarySoft text-foreground"
              )}
              onClick={() => setActiveTab(tab)}
            >
              {shotRecommendationCopy.tabs[tab]}
            </button>
          ))}
        </div>
        {activeTab === "smart" && (
          <ShotRecommendationPanel
            projectId={projectId}
            shot={shot}
            onMessage={onMessage}
            invalidateShotData={invalidateShotData}
          />
        )}
        {activeTab === "keyframes" && (
          <KeyframeTaskPanel
            projectId={projectId}
            shot={shot}
            onMessage={onMessage}
            invalidateShotData={invalidateShotData}
          />
        )}
        {activeTab === "character" && (
        <section className="grid gap-3">
          <SectionTitle>{shotCopy.sections.characterRefs}</SectionTitle>
          {shot.characters.length === 0 ? (
            <p className="text-sm text-muted">请先添加镜头角色。</p>
          ) : (
            <>
              <Select value={selectedShotCharacter?.id || NONE} onValueChange={(value) => setSelectedShotCharacterId(value === NONE ? "" : value)}>
                <SelectTrigger aria-label={shotCopy.fields.character}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {shot.characters.map((item) => <SelectItem key={item.id} value={item.id}>{item.character_name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={characterPurpose} onValueChange={(value) => setCharacterPurpose(value as CharacterReferencePurpose)}>
                <SelectTrigger aria-label={shotCopy.fields.purpose}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {characterPurposes.map((purpose) => <SelectItem key={purpose} value={purpose}>{shotCopy.purposes[purpose]}</SelectItem>)}
                </SelectContent>
              </Select>
              <div className="grid grid-cols-2 gap-2">
                {(characterRefsQuery.data?.items ?? []).map((reference) => {
                  const mismatched = Boolean(selectedShotCharacter?.look_id && reference.look_id !== selectedShotCharacter.look_id);
                  return (
                    <button
                      key={reference.id}
                      type="button"
                      className="rounded-md border border-border bg-background p-2 text-left hover:border-primary"
                      onClick={() => addRefMutation.mutate({
                        reference_type: "character",
                        character_reference_id: reference.id,
                        shot_character_id: selectedShotCharacter?.id,
                        purpose: characterPurpose
                      })}
                    >
                      <img
                        src={reference.media_asset.thumbnail_url ?? reference.media_asset.content_url}
                        alt=""
                        className="aspect-video w-full rounded object-cover"
                      />
                      <div className="mt-1 text-xs text-foreground">{shotCopy.purposes[characterPurpose]}</div>
                      {mismatched && <div className="mt-1 text-xs text-amber-300">{shotCopy.lookMismatchWarning}</div>}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </section>
        )}

        {activeTab === "scene" && (
        <section className="grid gap-3">
          <SectionTitle>{shotCopy.sections.sceneRefs}</SectionTitle>
          {!shot.scene_state_id ? (
            <p className="text-sm text-muted">{shotCopy.noSceneReferenceWarning}</p>
          ) : (
            <>
              <Select value={scenePurpose} onValueChange={(value) => setScenePurpose(value as SceneReferencePurpose)}>
                <SelectTrigger aria-label={shotCopy.fields.purpose}><SelectValue /></SelectTrigger>
                <SelectContent>
                  {scenePurposes.map((purpose) => <SelectItem key={purpose} value={purpose}>{shotCopy.purposes[purpose]}</SelectItem>)}
                </SelectContent>
              </Select>
              <div className="grid grid-cols-2 gap-2">
                {(sceneRefsQuery.data?.items ?? []).map((reference: SceneReference) => (
                  <button
                    key={reference.id}
                    type="button"
                    className="rounded-md border border-border bg-background p-2 text-left hover:border-primary"
                    onClick={() => addRefMutation.mutate({
                      reference_type: "scene",
                      scene_reference_id: reference.id,
                      purpose: scenePurpose
                    })}
                  >
                    <img
                      src={reference.media_asset.thumbnail_url ?? reference.media_asset.content_url}
                      alt=""
                      className="aspect-video w-full rounded object-cover"
                    />
                    <div className="mt-1 text-xs text-foreground">{shotCopy.purposes[scenePurpose]}</div>
                  </button>
                ))}
              </div>
            </>
          )}
        </section>
        )}

        {activeTab === "selected" && (
        <section className="grid gap-3">
          <SectionTitle>{shotCopy.sections.selectedRefs}</SectionTitle>
          {shot.references.length === 0 ? (
            <p className="text-sm text-muted">当前镜头还没有绑定参考图。</p>
          ) : (
            shot.references.map((reference: ShotReference) => (
              <article key={reference.id} className="rounded-md border border-border bg-background p-2">
                {reference.media_asset && (
                  <img
                    src={reference.media_asset.thumbnail_url ?? reference.media_asset.content_url}
                    alt=""
                    className="aspect-video w-full rounded object-cover"
                  />
                )}
                <div className="mt-2 flex items-center justify-between gap-2">
                  <div className="text-sm">{shotCopy.purposes[reference.purpose as keyof typeof shotCopy.purposes] ?? reference.purpose}</div>
                  <Badge>{reference.reference_type === "character" ? "人物" : "场景"}</Badge>
                </div>
                <div className="mt-2 flex gap-1">
                  <Button type="button" variant="secondary" size="icon" title="上移" disabled={reference.order_index <= 1} onClick={() => moveRefMutation.mutate({ id: reference.id, orderIndex: reference.order_index - 1 })}><ArrowUp className="h-4 w-4" aria-hidden="true" /></Button>
                  <Button type="button" variant="secondary" size="icon" title="下移" disabled={reference.order_index >= shot.references.length} onClick={() => moveRefMutation.mutate({ id: reference.id, orderIndex: reference.order_index + 1 })}><ArrowDown className="h-4 w-4" aria-hidden="true" /></Button>
                  <ConfirmDeleteDialog
                    title={shotCopy.deleteShotReference}
                    description={shotCopy.deleteShotReferenceDescription}
                    onConfirm={() => deleteRefMutation.mutateAsync(reference.id)}
                    trigger={<Button type="button" variant="danger" size="icon" title={shotCopy.deleteShotReference}><Trash2 className="h-4 w-4" aria-hidden="true" /></Button>}
                  />
                </div>
              </article>
            ))
          )}
        </section>
        )}
      </div>
    </aside>
  );
}

function ReadinessBadge({ status }: { status: Shot["readiness_status"] }) {
  const tone = status === "asset_ready" ? "success" : status === "basic_ready" ? "primary" : "default";
  return <Badge tone={tone}>{shotCopy.readiness[status]}</Badge>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm">
      <span className="text-xs text-muted">{label}</span>
      {children}
    </label>
  );
}

function FieldHint({
  children,
  tone = "muted"
}: {
  children: React.ReactNode;
  tone?: "muted" | "error";
}) {
  return (
    <span className={cn("text-xs", tone === "error" ? "text-danger" : "text-muted")}>
      {children}
    </span>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-foreground">{children}</h3>;
}

function SelectField({
  label,
  value,
  onChange,
  options
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
}) {
  return (
    <Field label={label}>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger aria-label={label}><SelectValue /></SelectTrigger>
        <SelectContent>
          {options.map((option) => <SelectItem key={option} value={option}>{shotCopy.options[option as keyof typeof shotCopy.options] ?? option}</SelectItem>)}
        </SelectContent>
      </Select>
    </Field>
  );
}

function defaultShotFormValues(): ShotFormValues {
  return {
    name: "",
    story_description: "",
    visual_description: "",
    dialogue: "",
    action_summary: "",
    duration_seconds: "",
    shot_scale: "unknown",
    camera_height: "unknown",
    custom_camera_height: "",
    camera_angle: "unknown",
    custom_camera_angle: "",
    composition_type: "unknown",
    custom_composition: "",
    camera_movement: "unknown",
    custom_camera_movement: "",
    focal_subject: "",
    mood_description: "",
    scene_id: "",
    scene_state_id: "",
    notes: ""
  };
}

function shotToFormValues(shot: Shot): ShotFormValues {
  return {
    name: shot.name,
    story_description: shot.story_description ?? "",
    visual_description: shot.visual_description ?? "",
    dialogue: shot.dialogue ?? "",
    action_summary: shot.action_summary ?? "",
    duration_seconds: shot.duration_seconds ?? "",
    shot_scale: shot.shot_scale,
    camera_height: shot.camera_height,
    custom_camera_height: shot.custom_camera_height ?? "",
    camera_angle: shot.camera_angle,
    custom_camera_angle: shot.custom_camera_angle ?? "",
    composition_type: shot.composition_type,
    custom_composition: shot.custom_composition ?? "",
    camera_movement: shot.camera_movement,
    custom_camera_movement: shot.custom_camera_movement ?? "",
    focal_subject: shot.focal_subject ?? "",
    mood_description: shot.mood_description ?? "",
    scene_id: shot.scene_id ?? "",
    scene_state_id: shot.scene_state_id ?? "",
    notes: shot.notes ?? ""
  };
}

function formValuesToPayload(values: ShotFormValues): ShotInput {
  const duration = values.duration_seconds === "" ? null : Number(values.duration_seconds);
  return {
    ...values,
    duration_seconds: Number.isFinite(duration) ? duration : null,
    scene_id: values.scene_id || null,
    scene_state_id: values.scene_state_id || null
  } as ShotInput;
}

function hasSceneRefs(references: ShotReference[]) {
  return references.some((reference) => reference.reference_type === "scene");
}

function shotTaskLabel(shot: Shot) {
  return shot.name.trim() || `镜头 ${shot.order_index}`;
}

function confirmedAdoptedVideoInputs(
  status?: ShotProductionStatus
): VideoTaskInputPayload[] {
  const inputs = adoptedVideoInputs(status);
  if (inputs.length === 0) {
    return [];
  }
  const confirmed = window.confirm(
    inputs.length === 2
      ? productionStatusCopy.inheritedFramesConfirm
      : productionStatusCopy.partialInheritedFramesConfirm
  );
  return confirmed ? inputs : [];
}

function adoptedVideoInputs(status?: ShotProductionStatus): VideoTaskInputPayload[] {
  if (!status) {
    return [];
  }
  const safeStatus = normalizeShotProductionStatus(status);
  const items: VideoTaskInputPayload[] = [];
  if (
    safeStatus.steps.first_frame.adopted_media_asset_id &&
    safeStatus.steps.first_frame.adopted_output_id &&
    safeStatus.steps.first_frame.task_id
  ) {
    items.push({
      role: "start_frame",
      media_asset_id: safeStatus.steps.first_frame.adopted_media_asset_id,
      source_keyframe_output_id: safeStatus.steps.first_frame.adopted_output_id,
      source_keyframe_task_id: safeStatus.steps.first_frame.task_id
    });
  }
  if (
    safeStatus.steps.end_frame.adopted_media_asset_id &&
    safeStatus.steps.end_frame.adopted_output_id &&
    safeStatus.steps.end_frame.task_id
  ) {
    items.push({
      role: "end_frame",
      media_asset_id: safeStatus.steps.end_frame.adopted_media_asset_id,
      source_keyframe_output_id: safeStatus.steps.end_frame.adopted_output_id,
      source_keyframe_task_id: safeStatus.steps.end_frame.task_id
    });
  }
  return items;
}

function referenceSlotsFromShot(
  shot: Shot | undefined,
  purposes: string[]
) {
  const titleByPurpose: Record<string, string> = {
    identity: "人物身份参考",
    appearance: "人物造型参考",
    environment: "场景参考",
    pose: "姿态参考",
    composition: "构图参考",
    general: "连续性参考"
  };
  return purposes.map((purpose) => {
    const reference = shot?.references.find((item) => item.purpose === purpose);
    return {
      id: purpose,
      title: titleByPurpose[purpose] ?? purpose,
      purpose: shotCopy.purposes[purpose as keyof typeof shotCopy.purposes] ?? purpose,
      mediaUrl: reference?.media_asset?.thumbnail_url ?? reference?.media_asset?.content_url,
      filled: Boolean(reference)
    };
  });
}

function nextActionHint(
  shot: Shot,
  status: ReturnType<typeof normalizeShotProductionStatus> | null,
  mode: CreativeMode
) {
  if (shot.characters.length === 0) {
    return "请先添加人物，并放入人物身份或造型参考图。";
  }
  if (!shot.scene_id) {
    return "请先选择场景，并放入场景参考图。";
  }
  if (!status) {
    return "正在读取生产状态，请稍后继续。";
  }
  if (mode === "first_frame") {
    if (status.steps.first_frame.status === "adopted") {
      return "首帧已采用，可以切换到尾帧模式继续生成。";
    }
    return "建议先生成并采用首帧。";
  }
  if (mode === "end_frame") {
    if (status.steps.first_frame.status !== "adopted") {
      return "请先采用首帧，再生成尾帧以保证连续性。";
    }
    if (status.steps.end_frame.status === "adopted") {
      return "尾帧已采用，可以切换到视频模式。";
    }
    return "可以生成尾帧，并检查与首帧的人物、造型和场景连续性。";
  }
  if (status.steps.video.status === "adopted") {
    return "视频已采用，可以进入时间线与导出。";
  }
  if (status.steps.first_frame.status === "adopted" && status.steps.end_frame.status === "adopted") {
    return "首尾帧已采用，可以生成视频。";
  }
  return "请先补齐并采用首帧和尾帧。";
}

function pickerMetadataString(item: PickerOptionItem, key: string): string | null {
  const value = item.metadata[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function getErrorText(error: unknown, fallback: string) {
  return error instanceof ApiClientError ? error.message : fallback;
}
