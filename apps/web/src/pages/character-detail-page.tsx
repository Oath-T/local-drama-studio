import {
  ArrowLeft,
  Eye,
  ImagePlus,
  Pencil,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
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
import { assetSummaryKeys } from "@/features/asset-summaries/api";
import { CharacterAssetSummaryCard } from "@/features/asset-summaries/components/asset-summary-cards";
import {
  characterKeys,
  deleteCharacter,
  deleteLook,
  deleteReference,
  fetchCharacter,
  fetchLooks,
  fetchReferences,
  setDefaultLook,
  setPrimaryReference,
  updateReference
} from "@/features/characters/api";
import { CharacterFormDialog } from "@/features/characters/components/character-form-dialog";
import { ConfirmDeleteDialog } from "@/features/characters/components/confirm-delete-dialog";
import { LookFormDialog } from "@/features/characters/components/look-form-dialog";
import { ReferenceMetadataDialog } from "@/features/characters/components/reference-metadata-dialog";
import { ReferencePreviewDialog } from "@/features/characters/components/reference-preview-dialog";
import { ReferenceUploadDialog } from "@/features/characters/components/reference-upload-dialog";
import { Badge } from "@/features/characters/components/status-badge";
import { characterCopy } from "@/features/characters/copy";
import type { CharacterLook, CharacterReference } from "@/features/characters/types";
import { CharacterReferenceAnalysisDialog } from "@/features/vision-analysis/components/reference-analysis-dialog";
import { copy } from "@/locales";
import { ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function CharacterDetailPage() {
  const { projectId = "", characterId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(
    null
  );
  const [selectedLookId, setSelectedLookId] = useState<string | null>(null);

  const characterQuery = useQuery({
    queryKey: characterKeys.detail(projectId, characterId),
    queryFn: () => fetchCharacter(projectId, characterId),
    enabled: projectId.length > 0 && characterId.length > 0
  });
  const looksQuery = useQuery({
    queryKey: characterKeys.looks(projectId, characterId),
    queryFn: () => fetchLooks(projectId, characterId),
    enabled: projectId.length > 0 && characterId.length > 0
  });
  const activeLook = useMemo(() => {
    if (!looksQuery.data?.items.length) {
      return null;
    }
    return (
      looksQuery.data.items.find((look) => look.id === selectedLookId) ??
      looksQuery.data.items.find((look) => look.is_default) ??
      looksQuery.data.items[0]
    );
  }, [looksQuery.data?.items, selectedLookId]);
  const referencesQuery = useQuery({
    queryKey: characterKeys.references(projectId, characterId, activeLook?.id ?? ""),
    queryFn: () => fetchReferences(projectId, characterId, activeLook?.id ?? ""),
    enabled: projectId.length > 0 && characterId.length > 0 && Boolean(activeLook?.id)
  });

  const deleteCharacterMutation = useMutation({
    mutationFn: () => deleteCharacter(projectId, characterId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: characterKeys.lists(projectId) });
      setMessage({ tone: "success", text: characterCopy.deleted });
      navigate(`/projects/${projectId}/characters`);
    },
    onError: (error) => setErrorMessage(error, characterCopy.deleteFailed, setMessage)
  });

  const setDefaultLookMutation = useMutation({
    mutationFn: (lookId: string) => setDefaultLook(projectId, characterId, lookId),
    onSuccess: async () => {
      await invalidateCharacterScope(queryClient, projectId, characterId);
      setMessage({ tone: "success", text: characterCopy.defaultLookUpdated });
    },
    onError: (error) => setErrorMessage(error, characterCopy.lookSaveFailed, setMessage)
  });

  const deleteLookMutation = useMutation({
    mutationFn: (lookId: string) => deleteLook(projectId, characterId, lookId),
    onSuccess: async (_, lookId) => {
      setSelectedLookId(null);
      await invalidateCharacterScope(queryClient, projectId, characterId, lookId);
      setMessage({ tone: "success", text: characterCopy.lookDeleted });
    },
    onError: (error) => setErrorMessage(error, characterCopy.lookDeleteFailed, setMessage)
  });

  const setPrimaryReferenceMutation = useMutation({
    mutationFn: (reference: CharacterReference) =>
      setPrimaryReference(projectId, characterId, reference.look_id, reference.id),
    onSuccess: async (_, reference) => {
      await invalidateCharacterScope(queryClient, projectId, characterId, reference.look_id);
      setMessage({ tone: "success", text: characterCopy.primaryReferenceUpdated });
    },
    onError: (error) => setErrorMessage(error, characterCopy.referenceActionFailed, setMessage)
  });

  const toggleIdentityMutation = useMutation({
    mutationFn: (reference: CharacterReference) =>
      updateReference(projectId, characterId, reference.look_id, reference.id, {
        is_identity_anchor: !reference.is_identity_anchor
      }),
    onSuccess: async (_, reference) => {
      await invalidateCharacterScope(queryClient, projectId, characterId, reference.look_id);
      setMessage({ tone: "success", text: characterCopy.identityAnchorUpdated });
    },
    onError: (error) => setErrorMessage(error, characterCopy.referenceActionFailed, setMessage)
  });

  const deleteReferenceMutation = useMutation({
    mutationFn: (reference: CharacterReference) =>
      deleteReference(projectId, characterId, reference.look_id, reference.id),
    onSuccess: async (_, reference) => {
      await invalidateCharacterScope(queryClient, projectId, characterId, reference.look_id);
      setMessage({ tone: "success", text: characterCopy.referenceDeleted });
    },
    onError: (error) => setErrorMessage(error, characterCopy.referenceDeleteFailed, setMessage)
  });

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-5">
        <Button asChild variant="ghost" className="w-fit">
          <Link to={`/projects/${projectId}/characters`}>
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            {characterCopy.backToCharacters}
          </Link>
        </Button>

        {message && <StatusMessage tone={message.tone}>{message.text}</StatusMessage>}

        {characterQuery.isLoading && (
          <div className="grid gap-4" aria-label={copy.common.loading}>
            <Skeleton className="h-10 w-1/3" />
            <Skeleton className="h-32" />
            <Skeleton className="h-72" />
          </div>
        )}

        {characterQuery.isError && (
          <section className="rounded-md border border-border bg-panel p-6">
            <h1 className="text-xl font-semibold text-foreground">
              {characterCopy.notFoundTitle}
            </h1>
            <Button
              type="button"
              variant="secondary"
              className="mt-4"
              onClick={() => void characterQuery.refetch()}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {copy.common.retry}
            </Button>
          </section>
        )}

        {characterQuery.isSuccess && (
          <>
            <section className="grid gap-4 border-b border-border pb-5 lg:grid-cols-[1fr_280px]">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="break-words text-2xl font-semibold text-foreground">
                    {characterQuery.data.name}
                  </h1>
                  <CharacterFormDialog
                    projectId={projectId}
                    mode="edit"
                    character={characterQuery.data}
                    onSuccess={(text) => setMessage({ tone: "success", text })}
                    onError={(text) => setMessage({ tone: "error", text })}
                    trigger={
                      <Button type="button" size="sm" variant="secondary">
                        <Pencil className="h-4 w-4" aria-hidden="true" />
                        {characterCopy.editCharacter}
                      </Button>
                    }
                  />
                  <ConfirmDeleteDialog
                    title={characterCopy.deleteCharacter}
                    description={characterCopy.deleteCharacterDescription(characterQuery.data.name)}
                    onConfirm={() => deleteCharacterMutation.mutateAsync()}
                    trigger={
                      <Button
                        type="button"
                        size="sm"
                        variant="danger"
                        disabled={deleteCharacterMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        {characterCopy.deleteCharacter}
                      </Button>
                    }
                  />
                </div>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-muted">
                  {characterQuery.data.description || characterCopy.noDescription}
                </p>
              </div>
              <div className="grid grid-cols-3 gap-2 rounded-md border border-border bg-panel p-3 text-center">
                <Metric label="造型" value={characterQuery.data.look_count} />
                <Metric label="参考图" value={characterQuery.data.reference_count} />
                <Metric
                  label="类型"
                  value={characterCopy.role[characterQuery.data.role_type]}
                />
              </div>
            </section>

            <CharacterAssetSummaryCard projectId={projectId} characterId={characterId} />

            <section className="grid min-h-[520px] gap-4 lg:grid-cols-[280px_1fr]">
              <aside className="rounded-md border border-border bg-panel p-3">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <h2 className="text-sm font-semibold text-foreground">造型</h2>
                  <LookFormDialog
                    projectId={projectId}
                    characterId={characterId}
                    onSuccess={(text) => setMessage({ tone: "success", text })}
                    onError={(text) => setMessage({ tone: "error", text })}
                    trigger={
                      <Button type="button" size="sm" variant="secondary">
                        <Plus className="h-4 w-4" aria-hidden="true" />
                        {characterCopy.newLook}
                      </Button>
                    }
                  />
                </div>
                {looksQuery.data?.items.map((look) => (
                  <LookButton
                    key={look.id}
                    look={look}
                    active={look.id === activeLook?.id}
                    canDelete={(looksQuery.data?.total ?? 0) > 1}
                    onClick={() => setSelectedLookId(look.id)}
                    onSetDefault={() => setDefaultLookMutation.mutate(look.id)}
                    onDelete={() => deleteLookMutation.mutateAsync(look.id)}
                    projectId={projectId}
                    characterId={characterId}
                    onSuccess={(text) => setMessage({ tone: "success", text })}
                    onError={(text) => setMessage({ tone: "error", text })}
                  />
                ))}
              </aside>

              <section className="rounded-md border border-border bg-panel p-4">
                {activeLook ? (
                  <div className="flex h-full flex-col gap-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h2 className="text-lg font-semibold text-foreground">{activeLook.name}</h2>
                          {activeLook.is_default && <Badge tone="primary">{characterCopy.defaultLook}</Badge>}
                        </div>
                        <p className="mt-1 text-sm text-muted">
                          {activeLook.description || characterCopy.noDescription}
                        </p>
                      </div>
                      <ReferenceUploadDialog
                        projectId={projectId}
                        characterId={characterId}
                        lookId={activeLook.id}
                        onSuccess={(text) => setMessage({ tone: "success", text })}
                        onError={(text) => setMessage({ tone: "error", text })}
                        trigger={
                          <Button type="button">
                            <ImagePlus className="h-4 w-4" aria-hidden="true" />
                            {characterCopy.uploadReference}
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
                        title={characterCopy.emptyReferencesTitle}
                        description={characterCopy.emptyReferencesDescription}
                      />
                    )}

                    {referencesQuery.isSuccess && referencesQuery.data.total > 0 && (
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                        {referencesQuery.data.items.map((reference) => (
                          <ReferenceCard
                            key={reference.id}
                            projectId={projectId}
                            characterId={characterId}
                            reference={reference}
                            onSuccess={(text) => setMessage({ tone: "success", text })}
                            onError={(text) => setMessage({ tone: "error", text })}
                            onSetPrimary={() => setPrimaryReferenceMutation.mutate(reference)}
                            onToggleIdentity={() => toggleIdentityMutation.mutate(reference)}
                            onDelete={() => deleteReferenceMutation.mutateAsync(reference)}
                            onAnalysisUpdated={() =>
                              invalidateCharacterScope(
                                queryClient,
                                projectId,
                                characterId,
                                reference.look_id
                              )
                            }
                            disabled={
                              setPrimaryReferenceMutation.isPending ||
                              toggleIdentityMutation.isPending ||
                              deleteReferenceMutation.isPending
                            }
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <EmptyState
                    title={characterCopy.emptyLooksTitle}
                    description={characterCopy.emptyLooksDescription}
                    action={
                      <LookFormDialog
                        projectId={projectId}
                        characterId={characterId}
                        onSuccess={(text) => setMessage({ tone: "success", text })}
                        onError={(text) => setMessage({ tone: "error", text })}
                        trigger={
                          <Button type="button">
                            <Plus className="h-4 w-4" aria-hidden="true" />
                            {characterCopy.newFirstLook}
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

function LookButton({
  look,
  active,
  canDelete,
  onClick,
  onSetDefault,
  onDelete,
  projectId,
  characterId,
  onSuccess,
  onError
}: {
  look: CharacterLook;
  active: boolean;
  canDelete: boolean;
  onClick: () => void;
  onSetDefault: () => void;
  onDelete: () => Promise<void>;
  projectId: string;
  characterId: string;
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
          <span className="block truncate font-medium text-foreground">{look.name}</span>
          <span className="mt-1 block text-xs text-muted">{look.reference_count} 张参考图</span>
        </span>
        {look.is_default && <Star className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />}
      </button>
      {look.is_default && (
        <div className="px-3 pb-2">
          <Badge tone="primary">{characterCopy.defaultLook}</Badge>
        </div>
      )}
      <div className="flex flex-wrap gap-2 border-t border-border px-3 py-2">
        <LookFormDialog
          projectId={projectId}
          characterId={characterId}
          mode="edit"
          look={look}
          onSuccess={onSuccess}
          onError={onError}
          trigger={
            <Button type="button" size="sm" variant="secondary">
              <Pencil className="h-4 w-4" aria-hidden="true" />
              {characterCopy.editLook}
            </Button>
          }
        />
        {!look.is_default && (
          <Button type="button" size="sm" variant="secondary" onClick={onSetDefault}>
            <Star className="h-4 w-4" aria-hidden="true" />
            {characterCopy.setDefaultLook}
          </Button>
        )}
        <ConfirmDeleteDialog
          title={characterCopy.deleteLook}
          description={
            canDelete
              ? characterCopy.deleteLookDescription(look.name)
              : characterCopy.lastLookDeleteForbidden
          }
          onConfirm={onDelete}
          trigger={
            <Button type="button" size="sm" variant="danger">
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {characterCopy.deleteLook}
            </Button>
          }
        />
      </div>
    </div>
  );
}

function ReferenceCard({
  projectId,
  characterId,
  reference,
  onSuccess,
  onError,
  onSetPrimary,
  onToggleIdentity,
  onDelete,
  onAnalysisUpdated,
  disabled
}: {
  projectId: string;
  characterId: string;
  reference: CharacterReference;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  onSetPrimary: () => void;
  onToggleIdentity: () => void;
  onDelete: () => Promise<void>;
  onAnalysisUpdated: () => Promise<void>;
  disabled: boolean;
}) {
  return (
    <article className="overflow-hidden rounded-md border border-border bg-background">
      <img
        src={reference.media_asset.thumbnail_url ?? reference.media_asset.content_url}
        alt=""
        className="aspect-[4/3] w-full object-cover"
      />
      <div className="grid gap-3 p-3">
        <div className="flex flex-wrap gap-2">
          {reference.is_primary && <Badge tone="primary">{characterCopy.primaryReference}</Badge>}
          {reference.is_identity_anchor && <Badge tone="success">{characterCopy.identityAnchor}</Badge>}
          <Badge>{characterCopy.analysisStatus[reference.analysis_status]}</Badge>
        </div>
        <p className="text-sm text-foreground">
          {reference.description || characterCopy.noDescription}
        </p>
        <div className="grid gap-1 text-xs text-muted">
          <span>
            {characterCopy.shotType[reference.shot_type]} /{" "}
            {characterCopy.viewAngle[reference.view_angle]}
          </span>
          <span>
            {characterCopy.expression[reference.expression]} /{" "}
            {characterCopy.poseType[reference.pose_type]}
          </span>
          {reference.tags.length > 0 && <span>{reference.tags.join(" / ")}</span>}
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          <CharacterReferenceAnalysisDialog
            projectId={projectId}
            characterId={characterId}
            reference={reference}
            onUpdated={onAnalysisUpdated}
            onSuccess={onSuccess}
            onError={onError}
          />
          <ReferencePreviewDialog
            reference={reference}
            trigger={
              <Button type="button" size="sm" variant="secondary">
                <Eye className="h-4 w-4" aria-hidden="true" />
                {characterCopy.previewOriginal}
              </Button>
            }
          />
          <ReferenceMetadataDialog
            projectId={projectId}
            characterId={characterId}
            reference={reference}
            onSuccess={onSuccess}
            onError={onError}
            trigger={
              <Button type="button" size="sm" variant="secondary">
                <Pencil className="h-4 w-4" aria-hidden="true" />
                {characterCopy.editReference}
              </Button>
            }
          />
          {!reference.is_primary && (
            <Button type="button" size="sm" variant="secondary" disabled={disabled} onClick={onSetPrimary}>
              <Star className="h-4 w-4" aria-hidden="true" />
              {characterCopy.setPrimaryReference}
            </Button>
          )}
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={disabled}
            onClick={onToggleIdentity}
          >
            {reference.is_identity_anchor ? (
              <ShieldOff className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            )}
            {reference.is_identity_anchor
              ? characterCopy.unsetIdentityAnchor
              : characterCopy.setIdentityAnchor}
          </Button>
          <ConfirmDeleteDialog
            title={characterCopy.deleteReference}
            description={characterCopy.deleteReferenceDescription(reference.media_asset.original_filename)}
            onConfirm={onDelete}
            trigger={
              <Button type="button" size="sm" variant="danger" disabled={disabled}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {characterCopy.deleteReference}
              </Button>
            }
          />
        </div>
      </div>
    </article>
  );
}

async function invalidateCharacterScope(
  queryClient: QueryClient,
  projectId: string,
  characterId: string,
  lookId?: string
) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: characterKeys.lists(projectId) }),
    queryClient.invalidateQueries({ queryKey: characterKeys.detail(projectId, characterId) }),
    queryClient.invalidateQueries({ queryKey: characterKeys.looks(projectId, characterId) }),
    queryClient.invalidateQueries({
      queryKey: assetSummaryKeys.character(projectId, characterId)
    }),
    lookId
      ? queryClient.invalidateQueries({
          queryKey: characterKeys.references(projectId, characterId, lookId)
        })
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
