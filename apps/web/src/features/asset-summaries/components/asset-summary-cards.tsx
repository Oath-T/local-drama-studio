import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Database, Film, Image as ImageIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Badge } from "@/features/characters/components/status-badge";
import type { KeyframeTask } from "@/features/keyframe-tasks/types";
import type { Shot } from "@/features/shots/types";
import type { VideoTask } from "@/features/video-generation/types";
import { cn } from "@/lib/utils";

import {
  assetSummaryKeys,
  fetchCharacterAssetSummary,
  fetchSceneAssetSummary,
  fetchShotAssetSummary
} from "../api";
import { assetSummaryCopy } from "../copy";
import type {
  CharacterAssetSummary,
  SceneAssetSummary,
  ShotAssetSummary,
  SummaryReference
} from "../types";

export function CharacterAssetSummaryCard({
  projectId,
  characterId
}: {
  projectId: string;
  characterId: string;
}) {
  const query = useQuery({
    queryKey: assetSummaryKeys.character(projectId, characterId),
    queryFn: () => fetchCharacterAssetSummary(projectId, characterId),
    enabled: Boolean(projectId && characterId)
  });

  if (query.isLoading) {
    return <Skeleton className="h-56" aria-label={assetSummaryCopy.loading} />;
  }
  if (query.isError) {
    return <SummaryError onRetry={() => void query.refetch()} />;
  }
  if (!query.data) {
    return null;
  }
  return <CharacterSummaryContent summary={query.data} />;
}

export function SceneAssetSummaryCard({
  projectId,
  sceneId
}: {
  projectId: string;
  sceneId: string;
}) {
  const query = useQuery({
    queryKey: assetSummaryKeys.scene(projectId, sceneId),
    queryFn: () => fetchSceneAssetSummary(projectId, sceneId),
    enabled: Boolean(projectId && sceneId)
  });

  if (query.isLoading) {
    return <Skeleton className="h-56" aria-label={assetSummaryCopy.loading} />;
  }
  if (query.isError) {
    return <SummaryError onRetry={() => void query.refetch()} />;
  }
  if (!query.data) {
    return null;
  }
  return <SceneSummaryContent summary={query.data} />;
}

export function ShotAssetSummaryCard({
  projectId,
  shotId
}: {
  projectId: string;
  shotId: string;
}) {
  const query = useQuery({
    queryKey: assetSummaryKeys.shot(projectId, shotId),
    queryFn: () => fetchShotAssetSummary(projectId, shotId),
    enabled: Boolean(projectId && shotId)
  });

  if (query.isLoading) {
    return <Skeleton className="h-48" aria-label={assetSummaryCopy.loading} />;
  }
  if (query.isError) {
    return <SummaryError onRetry={() => void query.refetch()} compact />;
  }
  if (!query.data) {
    return null;
  }
  const summary = query.data;
  if (!isShotAssetSummary(summary)) {
    return <SummaryError onRetry={() => void query.refetch()} compact />;
  }
  return (
    <SummarySection title={assetSummaryCopy.shotTitle} icon={<Database className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2">
        <Metric label={assetSummaryCopy.metrics.characters} value={summary.characters.length} />
        <Metric
          label={assetSummaryCopy.metrics.references}
          value={summary.references.length}
        />
        <Metric
          label={assetSummaryCopy.metrics.keyframeTasks}
          value={summary.generation.keyframe_task_count}
        />
        <Metric label={assetSummaryCopy.metrics.videoTasks} value={summary.generation.video_task_count} />
      </div>
      <div className="grid gap-2">
        {summary.characters.length === 0 ? (
          <Hint>暂无参与人物</Hint>
        ) : (
          summary.characters.map((character) => (
            <div key={character.shot_character_id} className="rounded-md border border-border bg-panel p-2">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium text-foreground">
                  {character.character_name}
                </span>
                {character.is_primary_subject && <Badge tone="primary">主角</Badge>}
              </div>
              <p className="mt-1 text-xs text-muted">
                {character.look_name ?? "未指定造型"} / {character.bound_reference_count} 张参考图
              </p>
            </div>
          ))
        )}
      </div>
      <div className="rounded-md border border-border bg-panel p-2 text-xs text-muted">
        <div className="font-medium text-foreground">
          {summary.scene.scene_name ?? "未选择场景"}
        </div>
        <div className="mt-1">
          {summary.scene.scene_state_name ?? "未选择场景状态"} /{" "}
          {summary.scene.bound_reference_count} 张场景参考图
        </div>
      </div>
      <WarningList items={summary.completeness_warnings} />
    </SummarySection>
  );
}

function isShotAssetSummary(value: ShotAssetSummary): boolean {
  return Boolean(
    value.generation &&
      value.scene &&
      Array.isArray(value.characters) &&
      Array.isArray(value.references) &&
      Array.isArray(value.completeness_warnings)
  );
}

export function KeyframeInheritedAssetSummary({ task }: { task: KeyframeTask }) {
  const characters = task.shot_snapshot.characters;
  const characterRefs = task.references.filter((reference) => reference.reference_type === "character");
  const sceneRefs = task.references.filter((reference) => reference.reference_type === "scene");
  return (
    <SummarySection
      title={assetSummaryCopy.inheritedTitle}
      icon={<Database className="h-4 w-4" />}
      compact
    >
      <div className="grid gap-2 text-xs text-muted">
        <span>镜头：{task.shot_snapshot.title}</span>
        <span>
          人物：{characters.length > 0 ? characters.map((item) => item.character_name).join(" / ") : "暂无"}
        </span>
        <span>
          场景：{task.shot_snapshot.scene_name ?? "未选择"} /{" "}
          {task.shot_snapshot.scene_state_name ?? "未选择状态"}
        </span>
        <span>
          参考图：人物 {characterRefs.length} 张 / 场景 {sceneRefs.length} 张
        </span>
      </div>
    </SummarySection>
  );
}

export function VideoShotContextSummary({
  shot,
  task
}: {
  shot: Shot;
  task: VideoTask;
}) {
  const startFrame = task.inputs.find((input) => input.role === "start_frame");
  const endFrame = task.inputs.find((input) => input.role === "end_frame");
  return (
    <SummarySection
      title={assetSummaryCopy.videoContextTitle}
      icon={<Film className="h-4 w-4" />}
      compact
    >
      <div className="grid gap-2 text-xs text-muted">
        <span>
          人物：{shot.characters.length > 0 ? shot.characters.map((item) => item.character_name).join(" / ") : "暂无"}
        </span>
        <span>
          场景：{shot.scene?.name ?? "未选择"} / {shot.scene_state?.name ?? "未选择状态"}
        </span>
        <span>
          {startFrame?.media_asset
            ? assetSummaryCopy.startFrameSelected
            : assetSummaryCopy.startFrameMissing}
          {" / "}
          {endFrame?.media_asset
            ? assetSummaryCopy.endFrameSelected
            : assetSummaryCopy.endFrameMissing}
        </span>
      </div>
      <p className="text-xs leading-5 text-muted">
        这里展示的是镜头上下文。视频 workflow 直接使用起始帧、结束帧、提示词和参数。
      </p>
    </SummarySection>
  );
}

function CharacterSummaryContent({ summary }: { summary: CharacterAssetSummary }) {
  return (
    <SummarySection title={assetSummaryCopy.characterTitle} icon={<Database className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Metric label={assetSummaryCopy.metrics.looks} value={summary.look_count} />
        <Metric label={assetSummaryCopy.metrics.references} value={summary.reference_count} />
        <Metric label={assetSummaryCopy.metrics.identity} value={summary.identity_anchor_count} />
        <Metric label={assetSummaryCopy.metrics.usedShots} value={summary.used_shot_count} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge tone={summary.default_look_name ? "primary" : "default"}>
          {`${assetSummaryCopy.defaultLook}: ${summary.default_look_name ?? "暂无"}`}
        </Badge>
        <Badge>{`${assetSummaryCopy.metrics.face}: ${summary.face_reference_count}`}</Badge>
        <Badge>{`${assetSummaryCopy.metrics.fullBody}: ${summary.full_body_reference_count}`}</Badge>
      </div>
      <ReferenceStrip references={summary.featured_references} />
      <RecentShotLinks projectId={summary.project_id} shots={summary.recent_shots} />
      <WarningList items={summary.completeness_warnings} />
    </SummarySection>
  );
}

function SceneSummaryContent({ summary }: { summary: SceneAssetSummary }) {
  return (
    <SummarySection title={assetSummaryCopy.sceneTitle} icon={<Database className="h-4 w-4" />}>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Metric label={assetSummaryCopy.metrics.states} value={summary.state_count} />
        <Metric label={assetSummaryCopy.metrics.references} value={summary.reference_count} />
        <Metric label={assetSummaryCopy.metrics.spatial} value={summary.spatial_anchor_count} />
        <Metric label={assetSummaryCopy.metrics.usedShots} value={summary.used_shot_count} />
      </div>
      <div className="flex flex-wrap gap-2">
        <Badge tone={summary.default_state_name ? "primary" : "default"}>
          {`${assetSummaryCopy.defaultState}: ${summary.default_state_name ?? "暂无"}`}
        </Badge>
        <Badge>{`${assetSummaryCopy.metrics.emptyPlate}: ${summary.empty_plate_count}`}</Badge>
        <Badge>{`${assetSummaryCopy.metrics.wide}: ${summary.wide_reference_count}`}</Badge>
      </div>
      <ReferenceStrip references={summary.featured_references} />
      <RecentShotLinks projectId={summary.project_id} shots={summary.recent_shots} />
      <WarningList items={summary.completeness_warnings} />
    </SummarySection>
  );
}

function SummarySection({
  title,
  icon,
  children,
  compact = false
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  compact?: boolean;
}) {
  return (
    <section
      className={cn(
        "grid gap-3 rounded-md border border-border bg-panel",
        compact ? "p-3" : "p-4"
      )}
    >
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        {icon}
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-md border border-border bg-background p-2">
      <div className="text-base font-semibold text-foreground">{value}</div>
      <div className="mt-1 text-xs text-muted">{label}</div>
    </div>
  );
}

function ReferenceStrip({ references }: { references: SummaryReference[] }) {
  if (references.length === 0) {
    return <Hint>{assetSummaryCopy.noReferences}</Hint>;
  }
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
      {references.map((reference) => (
        <article key={reference.id} className="overflow-hidden rounded-md border border-border bg-background">
          {reference.media_asset ? (
            <img
              src={reference.media_asset.thumbnail_url ?? reference.media_asset.content_url}
              alt=""
              className="aspect-video w-full object-cover"
            />
          ) : (
            <div className="flex aspect-video items-center justify-center border-b border-border">
              <ImageIcon className="h-5 w-5 text-muted" aria-hidden="true" />
            </div>
          )}
          <div className="grid gap-1 p-2">
            <div className="truncate text-xs font-medium text-foreground">{reference.label}</div>
            <div className="flex flex-wrap gap-1">
              {reference.is_primary && <Badge tone="primary">{assetSummaryCopy.primaryReference}</Badge>}
              {reference.is_identity_anchor && <Badge tone="success">{assetSummaryCopy.identityAnchor}</Badge>}
              {reference.is_spatial_anchor && <Badge tone="success">{assetSummaryCopy.spatialAnchor}</Badge>}
              {reference.is_empty_plate && <Badge>{assetSummaryCopy.emptyPlate}</Badge>}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function RecentShotLinks({ projectId, shots }: { projectId: string; shots: Array<{ id: string; name: string; order_index: number }> }) {
  if (shots.length === 0) {
    return <Hint>{assetSummaryCopy.noRecentShots}</Hint>;
  }
  return (
    <div className="flex flex-wrap gap-2 text-xs">
      {shots.map((shot) => (
        <Link
          key={shot.id}
          to={`/projects/${projectId}/shots/${shot.id}`}
          className="rounded border border-border bg-background px-2 py-1 text-muted hover:border-primary hover:text-foreground"
        >
          #{shot.order_index} {shot.name}
        </Link>
      ))}
    </div>
  );
}

function WarningList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-success/30 bg-success/10 p-2 text-xs text-success">
        <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
        {assetSummaryCopy.noWarnings}
      </div>
    );
  }
  return (
    <div className="grid gap-1 rounded-md border border-border bg-background p-2 text-xs text-muted">
      {items.map((item) => (
        <div key={item} className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-300" aria-hidden="true" />
          {item}
        </div>
      ))}
    </div>
  );
}

function Hint({ children }: { children: ReactNode }) {
  return <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted">{children}</div>;
}

function SummaryError({
  onRetry,
  compact = false
}: {
  onRetry: () => void;
  compact?: boolean;
}) {
  return (
    <div className={cn("rounded-md border border-border bg-panel", compact ? "p-3" : "p-4")}>
      <StatusMessage tone="error">{assetSummaryCopy.loadFailed}</StatusMessage>
      <Button type="button" variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
        重新加载
      </Button>
    </div>
  );
}
