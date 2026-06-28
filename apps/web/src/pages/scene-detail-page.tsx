import {
  ArrowLeft,
  Eye,
  ImagePlus,
  Landmark,
  Pencil,
  Plus,
  RefreshCw,
  Star,
  Trash2
} from "lucide-react";
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { ConfirmDeleteDialog } from "@/features/characters/components/confirm-delete-dialog";
import { Badge } from "@/features/characters/components/status-badge";
import {
  deleteScene,
  deleteSceneReference,
  deleteSceneState,
  fetchScene,
  fetchSceneReferences,
  fetchSceneStates,
  sceneKeys,
  setDefaultSceneState,
  setPrimarySceneReference,
  updateSceneReference
} from "@/features/scenes/api";
import { SceneFormDialog } from "@/features/scenes/components/scene-form-dialog";
import { SceneReferenceFormDialog } from "@/features/scenes/components/scene-reference-form-dialog";
import { SceneReferencePreviewDialog } from "@/features/scenes/components/scene-reference-preview-dialog";
import { SceneStateFormDialog } from "@/features/scenes/components/scene-state-form-dialog";
import { sceneCopy } from "@/features/scenes/copy";
import type { SceneReference, SceneState } from "@/features/scenes/types";
import { copy } from "@/locales";
import { ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function SceneDetailPage() {
  const { projectId = "", sceneId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(
    null
  );
  const [selectedStateId, setSelectedStateId] = useState<string | null>(null);

  const sceneQuery = useQuery({
    queryKey: sceneKeys.detail(projectId, sceneId),
    queryFn: () => fetchScene(projectId, sceneId),
    enabled: projectId.length > 0 && sceneId.length > 0
  });
  const statesQuery = useQuery({
    queryKey: sceneKeys.states(projectId, sceneId),
    queryFn: () => fetchSceneStates(projectId, sceneId),
    enabled: projectId.length > 0 && sceneId.length > 0
  });
  const activeState = useMemo(() => {
    if (!statesQuery.data?.items.length) {
      return null;
    }
    return (
      statesQuery.data.items.find((state) => state.id === selectedStateId) ??
      statesQuery.data.items.find((state) => state.is_default) ??
      statesQuery.data.items[0]
    );
  }, [selectedStateId, statesQuery.data?.items]);
  const referencesQuery = useQuery({
    queryKey: sceneKeys.references(projectId, sceneId, activeState?.id ?? ""),
    queryFn: () => fetchSceneReferences(projectId, sceneId, activeState?.id ?? ""),
    enabled: projectId.length > 0 && sceneId.length > 0 && Boolean(activeState?.id)
  });

  const deleteSceneMutation = useMutation({
    mutationFn: () => deleteScene(projectId, sceneId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: sceneKeys.lists(projectId) });
      setMessage({ tone: "success", text: sceneCopy.deleted });
      navigate(`/projects/${projectId}/scenes`);
    },
    onError: (error) => setErrorMessage(error, sceneCopy.deleteFailed, setMessage)
  });

  const setDefaultStateMutation = useMutation({
    mutationFn: (stateId: string) => setDefaultSceneState(projectId, sceneId, stateId),
    onSuccess: async () => {
      await invalidateSceneScope(queryClient, projectId, sceneId);
      setMessage({ tone: "success", text: sceneCopy.defaultStateUpdated });
    },
    onError: (error) => setErrorMessage(error, sceneCopy.stateSaveFailed, setMessage)
  });

  const deleteStateMutation = useMutation({
    mutationFn: (stateId: string) => deleteSceneState(projectId, sceneId, stateId),
    onSuccess: async (_, stateId) => {
      setSelectedStateId(null);
      await invalidateSceneScope(queryClient, projectId, sceneId, stateId);
      setMessage({ tone: "success", text: sceneCopy.stateDeleted });
    },
    onError: (error) => setErrorMessage(error, sceneCopy.stateDeleteFailed, setMessage)
  });

  const setPrimaryMutation = useMutation({
    mutationFn: (reference: SceneReference) =>
      setPrimarySceneReference(projectId, sceneId, reference.state_id, reference.id),
    onSuccess: async (_, reference) => {
      await invalidateSceneScope(queryClient, projectId, sceneId, reference.state_id);
      setMessage({ tone: "success", text: sceneCopy.primaryReferenceUpdated });
    },
    onError: (error) => setErrorMessage(error, sceneCopy.referenceActionFailed, setMessage)
  });

  const toggleSpatialMutation = useMutation({
    mutationFn: (reference: SceneReference) =>
      updateSceneReference(projectId, sceneId, reference.state_id, reference.id, {
        is_spatial_anchor: !reference.is_spatial_anchor
      }),
    onSuccess: async (_, reference) => {
      await invalidateSceneScope(queryClient, projectId, sceneId, reference.state_id);
      setMessage({ tone: "success", text: sceneCopy.spatialAnchorUpdated });
    },
    onError: (error) => setErrorMessage(error, sceneCopy.referenceActionFailed, setMessage)
  });

  const toggleEmptyPlateMutation = useMutation({
    mutationFn: (reference: SceneReference) =>
      updateSceneReference(projectId, sceneId, reference.state_id, reference.id, {
        is_empty_plate: !reference.is_empty_plate
      }),
    onSuccess: async (_, reference) => {
      await invalidateSceneScope(queryClient, projectId, sceneId, reference.state_id);
      setMessage({ tone: "success", text: sceneCopy.emptyPlateUpdated });
    },
    onError: (error) => setErrorMessage(error, sceneCopy.referenceActionFailed, setMessage)
  });

  const deleteReferenceMutation = useMutation({
    mutationFn: (reference: SceneReference) =>
      deleteSceneReference(projectId, sceneId, reference.state_id, reference.id),
    onSuccess: async (_, reference) => {
      await invalidateSceneScope(queryClient, projectId, sceneId, reference.state_id);
      setMessage({ tone: "success", text: sceneCopy.referenceDeleted });
    },
    onError: (error) => setErrorMessage(error, sceneCopy.referenceDeleteFailed, setMessage)
  });

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-5">
        <Button asChild variant="ghost" className="w-fit">
          <Link to={`/projects/${projectId}/scenes`}>
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            {sceneCopy.backToScenes}
          </Link>
        </Button>

        {message && <StatusMessage tone={message.tone}>{message.text}</StatusMessage>}

        {sceneQuery.isLoading && (
          <div className="grid gap-4" aria-label={copy.common.loading}>
            <Skeleton className="h-10 w-1/3" />
            <Skeleton className="h-32" />
            <Skeleton className="h-72" />
          </div>
        )}

        {sceneQuery.isError && (
          <section className="rounded-md border border-border bg-panel p-6">
            <h1 className="text-xl font-semibold text-foreground">{sceneCopy.notFoundTitle}</h1>
            <Button
              type="button"
              variant="secondary"
              className="mt-4"
              onClick={() => void sceneQuery.refetch()}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {copy.common.retry}
            </Button>
          </section>
        )}

        {sceneQuery.isSuccess && (
          <>
            <section className="grid gap-4 border-b border-border pb-5 lg:grid-cols-[1fr_280px]">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="break-words text-2xl font-semibold text-foreground">
                    {sceneQuery.data.name}
                  </h1>
                  <Badge>{sceneCopy.sceneType[sceneQuery.data.scene_type]}</Badge>
                  <SceneFormDialog
                    projectId={projectId}
                    mode="edit"
                    scene={sceneQuery.data}
                    onSuccess={(text) => setMessage({ tone: "success", text })}
                    onError={(text) => setMessage({ tone: "error", text })}
                    trigger={
                      <Button type="button" size="sm" variant="secondary">
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                        {sceneCopy.editScene}
                      </Button>
                    }
                  />
                  <ConfirmDeleteDialog
                    title={sceneCopy.deleteScene}
                    description={sceneCopy.deleteSceneDescription(sceneQuery.data.name)}
                    onConfirm={() => deleteSceneMutation.mutateAsync()}
                    trigger={
                      <Button type="button" size="sm" variant="danger" disabled={deleteSceneMutation.isPending}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        {sceneCopy.deleteScene}
                      </Button>
                    }
                  />
                </div>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-muted">
                  {sceneQuery.data.description ||
                    sceneQuery.data.fixed_environment_description ||
                    sceneCopy.noDescription}
                </p>
              </div>
              <div className="grid grid-cols-3 gap-2 rounded-md border border-border bg-panel p-3 text-center">
                <Metric label="状态" value={sceneQuery.data.state_count} />
                <Metric label="参考图" value={sceneQuery.data.reference_count} />
                <Metric label="类型" value={sceneCopy.sceneType[sceneQuery.data.scene_type]} />
              </div>
            </section>

            <section className="grid min-h-[520px] gap-4 lg:grid-cols-[300px_1fr]">
              <aside className="rounded-md border border-border bg-panel p-3">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <h2 className="text-sm font-semibold text-foreground">场景状态</h2>
                  <SceneStateFormDialog
                    projectId={projectId}
                    sceneId={sceneId}
                    onSuccess={(text) => setMessage({ tone: "success", text })}
                    onError={(text) => setMessage({ tone: "error", text })}
                    trigger={
                      <Button type="button" size="sm" variant="secondary">
                        <Plus className="h-4 w-4" aria-hidden="true" />
                        {sceneCopy.newState}
                      </Button>
                    }
                  />
                </div>
                {statesQuery.data?.items.map((state) => (
                  <StateButton
                    key={state.id}
                    state={state}
                    active={state.id === activeState?.id}
                    canDelete={(statesQuery.data?.total ?? 0) > 1}
                    onClick={() => setSelectedStateId(state.id)}
                    onSetDefault={() => setDefaultStateMutation.mutate(state.id)}
                    onDelete={() => deleteStateMutation.mutateAsync(state.id)}
                    projectId={projectId}
                    sceneId={sceneId}
                    onSuccess={(text) => setMessage({ tone: "success", text })}
                    onError={(text) => setMessage({ tone: "error", text })}
                  />
                ))}
              </aside>

              <section className="rounded-md border border-border bg-panel p-4">
                {activeState ? (
                  <div className="flex h-full flex-col gap-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="text-lg font-semibold text-foreground">{activeState.name}</h2>
                          {activeState.is_default && <Badge tone="primary">{sceneCopy.defaultState}</Badge>}
                        </div>
                        <p className="mt-1 text-sm text-muted">
                          {stateSummary(activeState)}
                        </p>
                      </div>
                      <SceneReferenceFormDialog
                        projectId={projectId}
                        sceneId={sceneId}
                        stateId={activeState.id}
                        onSuccess={(text) => setMessage({ tone: "success", text })}
                        onError={(text) => setMessage({ tone: "error", text })}
                        trigger={
                          <Button type="button">
                            <ImagePlus className="h-4 w-4" aria-hidden="true" />
                            {sceneCopy.uploadReference}
                          </Button>
                        }
                      />
                    </div>

                    {referencesQuery.isLoading && (
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        <Skeleton className="h-64" />
                        <Skeleton className="h-64" />
                      </div>
                    )}

                    {referencesQuery.isSuccess && referencesQuery.data.total === 0 && (
                      <EmptyState
                        title={sceneCopy.emptyReferencesTitle}
                        description={sceneCopy.emptyReferencesDescription}
                      />
                    )}

                    {referencesQuery.isSuccess && referencesQuery.data.total > 0 && (
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {referencesQuery.data.items.map((reference) => (
                          <ReferenceCard
                            key={reference.id}
                            projectId={projectId}
                            sceneId={sceneId}
                            reference={reference}
                            onSuccess={(text) => setMessage({ tone: "success", text })}
                            onError={(text) => setMessage({ tone: "error", text })}
                            onSetPrimary={() => setPrimaryMutation.mutate(reference)}
                            onToggleSpatialAnchor={() => toggleSpatialMutation.mutate(reference)}
                            onToggleEmptyPlate={() => toggleEmptyPlateMutation.mutate(reference)}
                            onDelete={() => deleteReferenceMutation.mutateAsync(reference)}
                            disabled={
                              setPrimaryMutation.isPending ||
                              toggleSpatialMutation.isPending ||
                              toggleEmptyPlateMutation.isPending ||
                              deleteReferenceMutation.isPending
                            }
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <EmptyState
                    title={sceneCopy.emptyStatesTitle}
                    description={sceneCopy.emptyStatesDescription}
                    action={
                      <SceneStateFormDialog
                        projectId={projectId}
                        sceneId={sceneId}
                        onSuccess={(text) => setMessage({ tone: "success", text })}
                        onError={(text) => setMessage({ tone: "error", text })}
                        trigger={
                          <Button type="button">
                            <Plus className="h-4 w-4" aria-hidden="true" />
                            {sceneCopy.newFirstState}
                          </Button>
                        }
                      />
                    }
                  />
                )}
              </section>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <div className="text-base font-semibold text-foreground">{value}</div>
      <div className="mt-1 text-xs text-muted">{label}</div>
    </div>
  );
}

function StateButton({
  state,
  active,
  canDelete,
  onClick,
  onSetDefault,
  onDelete,
  projectId,
  sceneId,
  onSuccess,
  onError
}: {
  state: SceneState;
  active: boolean;
  canDelete: boolean;
  onClick: () => void;
  onSetDefault: () => void;
  onDelete: () => Promise<void>;
  projectId: string;
  sceneId: string;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}) {
  return (
    <div
      className={cn(
        "mb-2 rounded-md border",
        active ? "border-primary bg-primarySoft" : "border-border bg-background"
      )}
    >
      <button
        type="button"
        aria-current={active ? "true" : undefined}
        className="flex w-full items-start justify-between gap-2 px-3 py-2 text-left text-sm"
        onClick={onClick}
      >
        <span className="min-w-0">
          <span className="block truncate font-medium text-foreground">{state.name}</span>
          <span className="mt-1 block text-xs text-muted">{state.reference_count} 张参考图</span>
        </span>
        {state.is_default && <Star className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />}
      </button>
      {state.is_default && (
        <div className="px-3 pb-2">
          <Badge tone="primary">{sceneCopy.defaultState}</Badge>
        </div>
      )}
      <div className="flex flex-wrap gap-2 border-t border-border px-3 py-2">
        <SceneStateFormDialog
          projectId={projectId}
          sceneId={sceneId}
          mode="edit"
          state={state}
          onSuccess={onSuccess}
          onError={onError}
          trigger={
            <Button type="button" size="sm" variant="secondary">
              <Pencil className="h-4 w-4" aria-hidden="true" />
              {sceneCopy.editState}
            </Button>
          }
        />
        {!state.is_default && (
          <Button type="button" size="sm" variant="secondary" onClick={onSetDefault}>
            <Star className="h-4 w-4" aria-hidden="true" />
            {sceneCopy.setDefaultState}
          </Button>
        )}
        <ConfirmDeleteDialog
          title={sceneCopy.deleteState}
          description={
            canDelete
              ? sceneCopy.deleteStateDescription(state.name)
              : sceneCopy.lastStateDeleteForbidden
          }
          onConfirm={onDelete}
          trigger={
            <Button type="button" size="sm" variant="danger">
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {sceneCopy.deleteState}
            </Button>
          }
        />
      </div>
    </div>
  );
}

function ReferenceCard({
  projectId,
  sceneId,
  reference,
  onSuccess,
  onError,
  onSetPrimary,
  onToggleSpatialAnchor,
  onToggleEmptyPlate,
  onDelete,
  disabled
}: {
  projectId: string;
  sceneId: string;
  reference: SceneReference;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  onSetPrimary: () => void;
  onToggleSpatialAnchor: () => void;
  onToggleEmptyPlate: () => void;
  onDelete: () => Promise<void>;
  disabled: boolean;
}) {
  return (
    <article className="overflow-hidden rounded-md border border-border bg-background">
      <img src={reference.media_asset.thumbnail_url} alt="" className="aspect-[4/3] w-full object-cover" />
      <div className="grid gap-3 p-3">
        <div className="flex flex-wrap gap-2">
          {reference.is_primary && <Badge tone="primary">{sceneCopy.primaryReference}</Badge>}
          {reference.is_spatial_anchor && <Badge tone="success">{sceneCopy.spatialAnchor}</Badge>}
          {reference.is_empty_plate && <Badge>{sceneCopy.emptyPlate}</Badge>}
          <Badge>{sceneCopy.analysisStatus[reference.analysis_status]}</Badge>
        </div>
        <p className="text-sm text-foreground">
          {reference.description || sceneCopy.noDescription}
        </p>
        <div className="grid gap-1 text-xs text-muted">
          <span>
            {sceneCopy.shotScale[reference.shot_scale]} /{" "}
            {sceneCopy.cameraPosition[reference.camera_position]}
          </span>
          <span>
            {sceneCopy.viewDirection[reference.view_direction]} /{" "}
            {sceneCopy.compositionType[reference.composition_type]}
          </span>
          {reference.tags.length > 0 && <span>{reference.tags.join(" / ")}</span>}
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          <SceneReferencePreviewDialog
            reference={reference}
            trigger={
              <Button type="button" size="sm" variant="secondary">
                <Eye className="h-4 w-4" aria-hidden="true" />
                {sceneCopy.previewOriginal}
              </Button>
            }
          />
          <SceneReferenceFormDialog
            projectId={projectId}
            sceneId={sceneId}
            stateId={reference.state_id}
            mode="edit"
            reference={reference}
            onSuccess={onSuccess}
            onError={onError}
            trigger={
              <Button type="button" size="sm" variant="secondary">
                <Pencil className="h-4 w-4" aria-hidden="true" />
                {sceneCopy.editReference}
              </Button>
            }
          />
          {!reference.is_primary && (
            <Button type="button" size="sm" variant="secondary" disabled={disabled} onClick={onSetPrimary}>
              <Star className="h-4 w-4" aria-hidden="true" />
              {sceneCopy.setPrimaryReference}
            </Button>
          )}
          <Button type="button" size="sm" variant="secondary" disabled={disabled} onClick={onToggleSpatialAnchor}>
            <Landmark className="h-4 w-4" aria-hidden="true" />
            {reference.is_spatial_anchor ? sceneCopy.unsetSpatialAnchor : sceneCopy.setSpatialAnchor}
          </Button>
          <Button type="button" size="sm" variant="secondary" disabled={disabled} onClick={onToggleEmptyPlate}>
            {reference.is_empty_plate ? sceneCopy.unmarkEmptyPlate : sceneCopy.markEmptyPlate}
          </Button>
          <ConfirmDeleteDialog
            title={sceneCopy.deleteReference}
            description={sceneCopy.deleteReferenceDescription(reference.media_asset.original_filename)}
            onConfirm={onDelete}
            trigger={
              <Button type="button" size="sm" variant="danger" disabled={disabled}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {sceneCopy.deleteReference}
              </Button>
            }
          />
        </div>
      </div>
    </article>
  );
}

function stateSummary(state: SceneState): string {
  const weather =
    state.weather === "custom" && state.custom_weather
      ? state.custom_weather
      : sceneCopy.weather[state.weather];
  const lighting =
    state.lighting === "custom" && state.custom_lighting
      ? state.custom_lighting
      : sceneCopy.lighting[state.lighting];
  return `${sceneCopy.timeOfDay[state.time_of_day]} / ${weather} / ${lighting} / ${sceneCopy.crowdLevel[state.crowd_level]}`;
}

async function invalidateSceneScope(
  queryClient: QueryClient,
  projectId: string,
  sceneId: string,
  stateId?: string
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: sceneKeys.lists(projectId) }),
    queryClient.invalidateQueries({ queryKey: sceneKeys.detail(projectId, sceneId) }),
    queryClient.invalidateQueries({ queryKey: sceneKeys.states(projectId, sceneId) }),
    stateId
      ? queryClient.invalidateQueries({ queryKey: sceneKeys.references(projectId, sceneId, stateId) })
      : Promise.resolve()
  ]);
}

function setErrorMessage(
  error: unknown,
  fallback: string,
  setMessage: (message: { tone: "success" | "error"; text: string }) => void
) {
  setMessage({
    tone: "error",
    text: error instanceof ApiClientError ? error.message : fallback
  });
}
