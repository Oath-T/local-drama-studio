import { ArrowLeft, Images, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { ConfirmDeleteDialog } from "@/features/characters/components/confirm-delete-dialog";
import { Badge } from "@/features/characters/components/status-badge";
import { deleteScene, fetchScenes, sceneKeys } from "@/features/scenes/api";
import { SceneFormDialog } from "@/features/scenes/components/scene-form-dialog";
import { sceneCopy } from "@/features/scenes/copy";
import type { Scene } from "@/features/scenes/types";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { copy } from "@/locales";
import { ApiClientError } from "@/lib/api-client";

export function SceneLibraryPage() {
  const { projectId = "" } = useParams();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(
    null
  );
  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const scenesQuery = useQuery({
    queryKey: sceneKeys.lists(projectId),
    queryFn: () => fetchScenes(projectId),
    enabled: projectId.length > 0
  });

  const deleteMutation = useMutation({
    mutationFn: (sceneId: string) => deleteScene(projectId, sceneId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: sceneKeys.lists(projectId) });
      setMessage({ tone: "success", text: sceneCopy.deleted });
    },
    onError: (error) =>
      setMessage({
        tone: "error",
        text: error instanceof ApiClientError ? error.message : sceneCopy.deleteFailed
      })
  });

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <Button asChild variant="ghost" className="mb-3 w-fit">
              <Link to={projectId ? `/projects/${projectId}` : "/projects"}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                {sceneCopy.backToProject}
              </Link>
            </Button>
            <h1 className="text-2xl font-semibold text-foreground">{sceneCopy.title}</h1>
            <p className="mt-1 text-sm text-muted">
              {projectQuery.data?.name
                ? `${projectQuery.data.name} / ${sceneCopy.description}`
                : sceneCopy.description}
            </p>
          </div>
          <SceneFormDialog
            projectId={projectId}
            onSuccess={(text) => setMessage({ tone: "success", text })}
            onError={(text) => setMessage({ tone: "error", text })}
            trigger={
              <Button type="button">
                <Plus className="h-4 w-4" aria-hidden="true" />
                {sceneCopy.newScene}
              </Button>
            }
          />
        </div>

        {message && <StatusMessage tone={message.tone}>{message.text}</StatusMessage>}

        {scenesQuery.isLoading && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label={copy.common.loading}>
            <Skeleton className="h-52" />
            <Skeleton className="h-52" />
            <Skeleton className="h-52" />
          </div>
        )}

        {scenesQuery.isError && (
          <section className="rounded-md border border-border bg-panel p-6">
            <StatusMessage tone="error">{sceneCopy.loadFailed}</StatusMessage>
            <Button
              type="button"
              variant="secondary"
              className="mt-4"
              onClick={() => void scenesQuery.refetch()}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {copy.common.retry}
            </Button>
          </section>
        )}

        {scenesQuery.isSuccess && scenesQuery.data.total === 0 && (
          <EmptyState
            title={sceneCopy.emptyTitle}
            description={sceneCopy.emptyDescription}
            action={
              <SceneFormDialog
                projectId={projectId}
                onSuccess={(text) => setMessage({ tone: "success", text })}
                onError={(text) => setMessage({ tone: "error", text })}
                trigger={
                  <Button type="button">
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    {sceneCopy.newScene}
                  </Button>
                }
              />
            }
          />
        )}

        {scenesQuery.isSuccess && scenesQuery.data.total > 0 && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {scenesQuery.data.items.map((scene) => (
              <SceneCard
                key={scene.id}
                projectId={projectId}
                scene={scene}
                onSuccess={(text) => setMessage({ tone: "success", text })}
                onError={(text) => setMessage({ tone: "error", text })}
                onDelete={() => deleteMutation.mutateAsync(scene.id)}
                disabled={deleteMutation.isPending}
              />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function SceneCard({
  projectId,
  scene,
  onSuccess,
  onError,
  onDelete,
  disabled
}: {
  projectId: string;
  scene: Scene;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  onDelete: () => Promise<void>;
  disabled: boolean;
}) {
  return (
    <article className="overflow-hidden rounded-md border border-border bg-panel">
      <div className="flex aspect-[16/9] items-center justify-center bg-background">
        {scene.cover_reference ? (
          <img
            src={scene.cover_reference.media_asset.thumbnail_url}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <Images className="h-10 w-10 text-muted" aria-hidden="true" />
        )}
      </div>
      <div className="grid gap-3 p-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="break-words text-base font-semibold text-foreground">{scene.name}</h2>
            <Badge>{sceneCopy.sceneType[scene.scene_type]}</Badge>
          </div>
          <p className="mt-1 text-xs text-muted">
            {scene.state_count} 个状态 / {scene.reference_count} 张参考图
          </p>
        </div>
        <p className="line-clamp-2 min-h-10 text-sm leading-5 text-muted">
          {scene.description || scene.fixed_environment_description || sceneCopy.noDescription}
        </p>
        <p className="text-xs text-muted">
          {scene.default_state
            ? `${sceneCopy.defaultState}: ${scene.default_state.name}`
            : sceneCopy.emptyStatesTitle}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary" className="w-fit">
            <Link to={`/projects/${projectId}/scenes/${scene.id}`}>{copy.common.open}</Link>
          </Button>
          <SceneFormDialog
            projectId={projectId}
            mode="edit"
            scene={scene}
            onSuccess={onSuccess}
            onError={onError}
            trigger={
              <Button type="button" variant="secondary">
                <Pencil className="h-4 w-4" aria-hidden="true" />
                {sceneCopy.editScene}
              </Button>
            }
          />
          <ConfirmDeleteDialog
            title={sceneCopy.deleteScene}
            description={sceneCopy.deleteSceneDescription(scene.name)}
            onConfirm={onDelete}
            trigger={
              <Button type="button" variant="danger" disabled={disabled}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {sceneCopy.deleteScene}
              </Button>
            }
          />
        </div>
      </div>
    </article>
  );
}
