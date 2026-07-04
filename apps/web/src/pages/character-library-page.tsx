import { ArrowLeft, Plus, RefreshCw, UserRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { characterKeys, fetchCharacters } from "@/features/characters/api";
import { CharacterFormDialog } from "@/features/characters/components/character-form-dialog";
import { characterCopy } from "@/features/characters/copy";
import type { Character } from "@/features/characters/types";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { copy } from "@/locales";

export function CharacterLibraryPage() {
  const { projectId = "" } = useParams();
  const [message, setMessage] = useState<{ tone: "success" | "error"; text: string } | null>(
    null
  );
  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const charactersQuery = useQuery({
    queryKey: characterKeys.lists(projectId),
    queryFn: () => fetchCharacters(projectId),
    enabled: projectId.length > 0
  });

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <Button asChild variant="ghost" className="mb-3 w-fit">
              <Link to={projectId ? `/projects/${projectId}` : "/projects"}>
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                {characterCopy.backToProject}
              </Link>
            </Button>
            <h1 className="text-2xl font-semibold text-foreground">{characterCopy.title}</h1>
            <p className="mt-1 text-sm text-muted">
              {projectQuery.data?.name
                ? `${projectQuery.data.name} / ${characterCopy.description}`
                : characterCopy.description}
            </p>
          </div>
          <CharacterFormDialog
            projectId={projectId}
            onSuccess={(text) => setMessage({ tone: "success", text })}
            onError={(text) => setMessage({ tone: "error", text })}
            trigger={
              <Button type="button">
                <Plus className="h-4 w-4" aria-hidden="true" />
                {characterCopy.newCharacter}
              </Button>
            }
          />
        </div>

        {message && <StatusMessage tone={message.tone}>{message.text}</StatusMessage>}

        {charactersQuery.isLoading && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label={copy.common.loading}>
            <Skeleton className="h-44" />
            <Skeleton className="h-44" />
            <Skeleton className="h-44" />
          </div>
        )}

        {charactersQuery.isError && (
          <section className="rounded-md border border-border bg-panel p-6">
            <StatusMessage tone="error">{characterCopy.loadFailed}</StatusMessage>
            <Button
              type="button"
              variant="secondary"
              className="mt-4"
              onClick={() => void charactersQuery.refetch()}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {copy.common.retry}
            </Button>
          </section>
        )}

        {charactersQuery.isSuccess && charactersQuery.data.total === 0 && (
          <EmptyState
            title={characterCopy.emptyTitle}
            description={characterCopy.emptyDescription}
            action={
              <CharacterFormDialog
                projectId={projectId}
                onSuccess={(text) => setMessage({ tone: "success", text })}
                onError={(text) => setMessage({ tone: "error", text })}
                trigger={
                  <Button type="button">
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    {characterCopy.newCharacter}
                  </Button>
                }
              />
            }
          />
        )}

        {charactersQuery.isSuccess && charactersQuery.data.total > 0 && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {charactersQuery.data.items.map((character) => (
              <CharacterCard key={character.id} projectId={projectId} character={character} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function CharacterCard({ projectId, character }: { projectId: string; character: Character }) {
  const primaryReference = character.default_look?.primary_reference;

  return (
    <article className="overflow-hidden rounded-md border border-border bg-panel">
      <div className="flex aspect-[16/9] items-center justify-center bg-background">
        {primaryReference ? (
          <img
            src={primaryReference.media_asset.thumbnail_url ?? primaryReference.media_asset.content_url}
            alt=""
            className="h-full w-full object-cover"
          />
        ) : (
          <UserRound className="h-10 w-10 text-muted" aria-hidden="true" />
        )}
      </div>
      <div className="grid gap-3 p-4">
        <div>
          <h2 className="break-words text-base font-semibold text-foreground">
            {character.name}
          </h2>
          <p className="mt-1 text-xs text-muted">
            {characterCopy.role[character.role_type]} / {character.look_count} 套造型 /{" "}
            {character.reference_count} 张参考图
          </p>
        </div>
        <p className="line-clamp-2 min-h-10 text-sm leading-5 text-muted">
          {character.description || characterCopy.noDescription}
        </p>
        <Button asChild variant="secondary" className="w-fit">
          <Link to={`/projects/${projectId}/characters/${character.id}`}>打开角色</Link>
        </Button>
      </div>
    </article>
  );
}
