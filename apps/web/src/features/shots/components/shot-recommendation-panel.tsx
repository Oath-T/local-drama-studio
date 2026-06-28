import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Sparkles } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import {
  addShotReference,
  fetchShotRecommendations,
  shotKeys
} from "@/features/shots/api";
import { shotCopy, shotRecommendationCopy } from "@/features/shots/copy";
import type {
  CharacterRecommendationItem,
  CharacterReferencePurpose,
  SceneRecommendationItem,
  SceneReferencePurpose,
  Shot,
  ShotReferenceInput
} from "@/features/shots/types";
import { copy } from "@/locales";
import { ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

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

export function ShotRecommendationPanel({
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
  const recommendationsQuery = useQuery({
    queryKey: shot ? shotKeys.recommendations(projectId, shot.id) : ["shot-recommendations", "none"],
    queryFn: () => fetchShotRecommendations(projectId, shot?.id || ""),
    enabled: Boolean(projectId && shot?.id)
  });
  const bindMutation = useMutation({
    mutationFn: (payload: ShotReferenceInput) => addShotReference(projectId, shot?.id || "", payload),
    onSuccess: async () => {
      await Promise.all([
        invalidateShotData(shot?.id),
        shot?.id
          ? queryClient.invalidateQueries({
              queryKey: shotKeys.recommendations(projectId, shot.id)
            })
          : Promise.resolve()
      ]);
      onMessage({ tone: "success", text: "参考图已绑定" });
    },
    onError: (error) =>
      onMessage({ tone: "error", text: getErrorText(error, "参考图绑定失败") })
  });

  if (!shot) {
    return <p className="text-sm text-muted">{shotRecommendationCopy.noShot}</p>;
  }

  if (recommendationsQuery.isLoading) {
    return <Skeleton className="h-80" />;
  }

  if (recommendationsQuery.isError) {
    return (
      <div className="grid gap-3 rounded-md border border-border bg-background p-3">
        <StatusMessage tone="error">{shotRecommendationCopy.loadFailed}</StatusMessage>
        <Button type="button" variant="secondary" onClick={() => void recommendationsQuery.refetch()}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          {copy.common.retry}
        </Button>
      </div>
    );
  }

  const data = recommendationsQuery.data;
  if (!data) {
    return null;
  }
  const characterGroups = data.character_recommendations ?? [];
  const sceneRecommendations = data.scene_recommendations ?? {
    status_code: "no_references" as const,
    items: []
  };

  return (
    <div className="grid gap-4">
      <p className="rounded-md border border-border bg-background p-3 text-xs leading-5 text-muted">
        {shotRecommendationCopy.description}
      </p>
      <section className="grid gap-3">
        <RecommendationSectionTitle>人物推荐</RecommendationSectionTitle>
        {characterGroups.length === 0 && (
          <p className="text-sm text-muted">{shotRecommendationCopy.noCharacters}</p>
        )}
        {characterGroups.map((group) => (
          <div key={group.shot_character_id} className="grid gap-2">
            <div>
              <div className="text-sm font-medium text-foreground">{group.character_name}</div>
              <div className="text-xs text-muted">{shotRecommendationCopy.groupLook(group.look_name)}</div>
            </div>
            {group.items.length === 0 ? (
              <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted">
                {shotRecommendationCopy.noCharacterReferences}
              </p>
            ) : (
              <div className="grid gap-2">
                {group.items.map((item) => (
                  <RecommendationCard
                    key={`${group.shot_character_id}-${item.reference_id}`}
                    kind="character"
                    item={item}
                    disabled={bindMutation.isPending}
                    onBind={(purpose) =>
                      bindMutation.mutate({
                        reference_type: "character",
                        character_reference_id: item.reference_id,
                        shot_character_id: group.shot_character_id,
                        purpose
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </section>
      <section className="grid gap-3">
        <RecommendationSectionTitle>场景推荐</RecommendationSectionTitle>
        {sceneRecommendations.status_code === "scene_state_required" && (
          <p className="text-sm text-muted">{shotRecommendationCopy.sceneStateRequired}</p>
        )}
        {sceneRecommendations.status_code === "no_references" && (
          <p className="text-sm text-muted">{shotRecommendationCopy.noSceneReferences}</p>
        )}
        {sceneRecommendations.status_code === "ready" &&
          sceneRecommendations.items.length === 0 && (
            <p className="text-sm text-muted">{shotRecommendationCopy.noSceneReferences}</p>
          )}
        <div className="grid gap-2">
          {sceneRecommendations.items.map((item) => (
            <RecommendationCard
              key={item.reference_id}
              kind="scene"
              item={item}
              disabled={bindMutation.isPending}
              onBind={(purpose) =>
                bindMutation.mutate({
                  reference_type: "scene",
                  scene_reference_id: item.reference_id,
                  purpose
                })
              }
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function RecommendationCard({
  kind,
  item,
  disabled,
  onBind
}: {
  kind: "character";
  item: CharacterRecommendationItem;
  disabled: boolean;
  onBind: (purpose: CharacterReferencePurpose) => void;
} | {
  kind: "scene";
  item: SceneRecommendationItem;
  disabled: boolean;
  onBind: (purpose: SceneReferencePurpose) => void;
}) {
  const [purpose, setPurpose] = useState(item.suggested_purpose);
  const purposes = kind === "character" ? characterPurposes : scenePurposes;
  const isBound = item.is_already_bound_for_suggested_purpose;
  const sourceText =
    kind === "character"
      ? shotRecommendationCopy.sourceLook(item.source_look_name)
      : shotRecommendationCopy.sourceState(item.source_state_name);

  return (
    <article className="rounded-md border border-border bg-background p-2">
      <div className="grid grid-cols-[96px_minmax(0,1fr)] gap-3">
        <img
          src={item.thumbnail_url}
          alt=""
          className="aspect-video w-24 rounded object-cover"
        />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-foreground">
              {shotRecommendationCopy.score(item.score)}
            </span>
            {isBound && <SmallBadge tone="success">{shotRecommendationCopy.bound}</SmallBadge>}
            {!isBound && item.bound_purposes.length > 0 && (
              <SmallBadge>{shotRecommendationCopy.boundOtherPurpose}</SmallBadge>
            )}
            {item.is_primary && <SmallBadge>{shotRecommendationCopy.reasons.primary_reference}</SmallBadge>}
            {kind === "character" && item.is_identity_anchor && (
              <SmallBadge>{shotRecommendationCopy.reasons.identity_anchor}</SmallBadge>
            )}
            {kind === "scene" && item.is_spatial_anchor && (
              <SmallBadge>{shotRecommendationCopy.reasons.spatial_anchor}</SmallBadge>
            )}
            {kind === "scene" && item.is_empty_plate && (
              <SmallBadge>{shotRecommendationCopy.reasons.empty_plate}</SmallBadge>
            )}
          </div>
          <p className="mt-1 truncate text-xs text-muted">{sourceText}</p>
          <div className="mt-2 flex flex-wrap gap-1">
            {item.reasons.map((reason) => (
              <SmallBadge key={reason}>
                {shotRecommendationCopy.reasons[reason] ?? reason}
              </SmallBadge>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto]">
        <Select value={purpose} onValueChange={(value) => setPurpose(value as typeof purpose)}>
          <SelectTrigger aria-label={shotCopy.fields.purpose}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {purposes.map((option) => (
              <SelectItem key={option} value={option}>
                {shotCopy.purposes[option]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          type="button"
          size="sm"
          disabled={disabled || isBound}
          onClick={() => onBind(purpose as never)}
        >
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          {isBound ? shotRecommendationCopy.bound : shotRecommendationCopy.bind}
        </Button>
      </div>
    </article>
  );
}

function RecommendationSectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-foreground">{children}</h3>;
}

function SmallBadge({
  children,
  tone = "default"
}: {
  children: React.ReactNode;
  tone?: "default" | "success";
}) {
  return (
    <span
      className={cn(
        "rounded border px-1.5 py-0.5 text-[11px]",
        tone === "success"
          ? "border-success/40 bg-success/10 text-success"
          : "border-border bg-panel text-muted"
      )}
    >
      {children}
    </span>
  );
}

function getErrorText(error: unknown, fallback: string) {
  return error instanceof ApiClientError ? error.message : fallback;
}
