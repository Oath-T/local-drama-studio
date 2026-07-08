import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Copy,
  Plus,
  RefreshCw,
  Save,
  Trash2
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
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
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchSceneReferences, fetchScenes, fetchSceneStates, sceneKeys } from "@/features/scenes/api";
import type { Scene, SceneReference, SceneState } from "@/features/scenes/types";
import { KeyframeTaskPanel } from "@/features/keyframe-tasks/components/keyframe-task-panel";
import { ShotRecommendationPanel } from "@/features/shots/components/shot-recommendation-panel";
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
          <div className="grid min-h-[620px] gap-4 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
            <ShotListPanel
              projectId={projectId}
              shots={shotsQuery.data.items}
              activeShotId={activeShotId}
              onMove={(id, orderIndex) => moveMutation.mutate({ id, orderIndex })}
              onDuplicate={(id) => duplicateMutation.mutate(id)}
              onDelete={(id) => deleteMutation.mutateAsync(id)}
              disabled={moveMutation.isPending || duplicateMutation.isPending || deleteMutation.isPending}
            />
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
            />
          </div>
        )}
      </div>
    </AppShell>
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
  invalidateShotData
}: {
  projectId: string;
  shot?: Shot;
  characters: Character[];
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateShotData: (shotId?: string) => Promise<void>;
}) {
  const [selectedShotCharacterId, setSelectedShotCharacterId] = useState("");
  const [characterPurpose, setCharacterPurpose] = useState<CharacterReferencePurpose>("identity");
  const [scenePurpose, setScenePurpose] = useState<SceneReferencePurpose>("environment");
  const [activeTab, setActiveTab] = useState<"smart" | "keyframes" | "character" | "scene" | "selected">("smart");
  const [referencePickerOpen, setReferencePickerOpen] = useState(false);
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
        <ShotAssetSummaryCard projectId={projectId} shotId={shot.id} />
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

function pickerMetadataString(item: PickerOptionItem, key: string): string | null {
  const value = item.metadata[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

function getErrorText(error: unknown, fallback: string) {
  return error instanceof ApiClientError ? error.message : fallback;
}
