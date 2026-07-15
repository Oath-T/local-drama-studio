import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clapperboard, Download, Play, RefreshCw, Save } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Badge } from "@/features/characters/components/status-badge";
import { fetchProject, projectKeys } from "@/features/projects/api";
import {
  createProjectExport,
  fetchProjectExports,
  fetchProjectTimeline,
  markProjectExportReady,
  startProjectExport,
  timelineKeys
} from "@/features/timeline/api";
import { timelineCopy } from "@/features/timeline/copy";
import type {
  ProjectExport,
  ProjectTimeline,
  TimelineBlocker,
  TimelineClip
} from "@/features/timeline/types";
import { cn } from "@/lib/utils";

const defaultSettings = {
  target_width: 1080,
  target_height: 1920,
  target_fps: 24
};

export function TimelineExportPage() {
  const { projectId = "" } = useParams();
  const queryClient = useQueryClient();
  const [settings, setSettings] = useState(defaultSettings);
  const [message, setMessage] = useState<string | null>(null);

  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const timelineQuery = useQuery({
    queryKey: timelineKeys.timeline(projectId),
    queryFn: () => fetchProjectTimeline(projectId),
    enabled: projectId.length > 0
  });
  const exportsQuery = useQuery({
    queryKey: timelineKeys.exports(projectId),
    queryFn: () => fetchProjectExports(projectId),
    enabled: projectId.length > 0,
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => item.status === "queued" || item.status === "running")
        ? 3000
        : false
  });

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: timelineKeys.timeline(projectId) }),
      queryClient.invalidateQueries({ queryKey: timelineKeys.exports(projectId) })
    ]);
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createProjectExport(projectId, {
        name: `${projectQuery.data?.name ?? "项目"} 最终成片`,
        ...settings,
        video_codec: "libx264"
      }),
    onSuccess: async () => {
      setMessage("已创建导出草稿。");
      await invalidate();
    },
    onError: (error: Error) => setMessage(error.message)
  });
  const markReadyMutation = useMutation({
    mutationFn: (exportId: string) => markProjectExportReady(projectId, exportId),
    onSuccess: async () => {
      setMessage("导出任务已标记为就绪。");
      await invalidate();
    },
    onError: (error: Error) => setMessage(error.message)
  });
  const startMutation = useMutation({
    mutationFn: (exportId: string) => startProjectExport(projectId, exportId),
    onSuccess: async () => {
      setMessage("已开始最终成片导出。");
      await invalidate();
    },
    onError: (error: Error) => setMessage(error.message)
  });

  const timeline = timelineQuery.data;
  const exports = exportsQuery.data?.items ?? [];
  const ffmpegBlocked = !timeline?.ffmpeg.available || !timeline?.ffmpeg.ffprobe_available;
  const runningExport = useMemo(
    () => exports.some((item) => item.status === "queued" || item.status === "running"),
    [exports]
  );

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1480px] flex-col gap-5">
        <section className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
              {timelineCopy.title}
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-foreground">
              {projectQuery.data?.name
                ? `${projectQuery.data.name} / ${timelineCopy.title}`
                : timelineCopy.title}
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
              {timelineCopy.description}
            </p>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              void timelineQuery.refetch();
              void exportsQuery.refetch();
            }}
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            {timelineCopy.refresh}
          </Button>
        </section>

        {message && <StatusMessage tone={message.includes("失败") ? "error" : "success"}>{message}</StatusMessage>}
        {(timelineQuery.isLoading || exportsQuery.isLoading) && <Skeleton className="h-96" />}
        {(timelineQuery.isError || exportsQuery.isError) && (
          <StatusMessage tone="error">时间线或导出任务加载失败，请稍后重试。</StatusMessage>
        )}

        {timeline && (
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
            <section className="grid gap-4">
              <TimelineSummary timeline={timeline} />
              {timeline.clips.length === 0 ? (
                <EmptyState
                  title={timelineCopy.emptyTimelineTitle}
                  description={timelineCopy.emptyTimelineDescription}
                />
              ) : (
                <div className="grid gap-3">
                  {timeline.clips.map((clip) => (
                    <TimelineClipCard key={clip.shot_id} projectId={projectId} clip={clip} />
                  ))}
                </div>
              )}
            </section>

            <aside className="grid content-start gap-4">
              <PreflightPanel blockers={timeline.blockers} ffmpegBlocked={ffmpegBlocked} />
              <ExportSettingsPanel
                settings={settings}
                disabled={ffmpegBlocked || !timeline.exportable || runningExport}
                creating={createMutation.isPending}
                onChange={setSettings}
                onCreate={() => createMutation.mutate()}
              />
              <ExportHistory
                projectId={projectId}
                items={exports}
                ffmpegBlocked={ffmpegBlocked}
                pendingExportId={
                  markReadyMutation.variables ?? startMutation.variables ?? null
                }
                marking={markReadyMutation.isPending}
                starting={startMutation.isPending}
                onMarkReady={(exportId) => markReadyMutation.mutate(exportId)}
                onStart={(exportId) => startMutation.mutate(exportId)}
              />
            </aside>
          </div>
        )}
      </div>
    </AppShell>
  );
}

function TimelineSummary({ timeline }: { timeline: ProjectTimeline }) {
  return (
    <section className="grid gap-3 sm:grid-cols-4">
      <Metric label="镜头数" value={timeline.total_shots} />
      <Metric label="可导出片段" value={timeline.ready_clip_count} />
      <Metric label="缺失片段" value={timeline.missing_clip_count} tone={timeline.missing_clip_count ? "danger" : "success"} />
      <Metric label="预计时长" value={`${timeline.estimated_duration_seconds.toFixed(1)} 秒`} />
    </section>
  );
}

function Metric({
  label,
  value,
  tone = "default"
}: {
  label: string;
  value: string | number;
  tone?: "default" | "success" | "danger";
}) {
  return (
    <div className="rounded-md border border-border bg-panel p-4">
      <div className="text-sm text-muted">{label}</div>
      <div className={cn("mt-2 text-2xl font-semibold", tone === "danger" ? "text-danger" : "text-foreground")}>
        {value}
      </div>
    </div>
  );
}

function TimelineClipCard({ projectId, clip }: { projectId: string; clip: TimelineClip }) {
  const tone = clip.status === "ready" ? "success" : clip.status === "blocked" ? "danger" : "default";
  return (
    <article className="grid gap-4 rounded-md border border-border bg-panel p-4 lg:grid-cols-[120px_minmax(0,1fr)_120px]">
      <div className="text-sm text-muted">#{clip.shot_order}</div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={tone}>{timelineCopy.clipStatus[clip.status]}</Badge>
          {clip.fps && <Badge>{`${clip.fps} fps`}</Badge>}
          {clip.width && clip.height && <Badge>{`${clip.width}×${clip.height}`}</Badge>}
        </div>
        <h2 className="mt-3 truncate text-base font-semibold text-foreground">{clip.shot_name}</h2>
        {clip.warnings.length > 0 && (
          <p className="mt-2 text-sm text-danger">{clip.warnings.join(" / ")}</p>
        )}
      </div>
      <Button asChild variant="secondary">
        <Link to={`/projects/${projectId}/shots/${clip.shot_id}`}>
          <Clapperboard className="h-4 w-4" aria-hidden="true" />
          {timelineCopy.openShot}
        </Link>
      </Button>
    </article>
  );
}

function PreflightPanel({
  blockers,
  ffmpegBlocked
}: {
  blockers: TimelineBlocker[];
  ffmpegBlocked: boolean;
}) {
  return (
    <section className="rounded-md border border-border bg-panel p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-semibold text-foreground">{timelineCopy.blockersTitle}</h2>
        <Badge tone={ffmpegBlocked ? "danger" : "success"}>
          {ffmpegBlocked ? "不可导出" : "可导出"}
        </Badge>
      </div>
      <p className={cn("mt-3 text-sm", ffmpegBlocked ? "text-danger" : "text-success")}>
        {ffmpegBlocked ? timelineCopy.ffmpegUnavailable : timelineCopy.ffmpegReady}
      </p>
      <div className="mt-4 grid gap-2">
        {blockers.length === 0 ? (
          <p className="text-sm text-muted">{timelineCopy.noBlockers}</p>
        ) : (
          blockers.map((blocker) => (
            <div key={`${blocker.code}-${blocker.shot_id ?? "project"}`} className="rounded-md border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
              {blocker.message}
            </div>
          ))
        )}
      </div>
    </section>
  );
}

function ExportSettingsPanel({
  settings,
  disabled,
  creating,
  onChange,
  onCreate
}: {
  settings: typeof defaultSettings;
  disabled: boolean;
  creating: boolean;
  onChange: (settings: typeof defaultSettings) => void;
  onCreate: () => void;
}) {
  return (
    <section className="rounded-md border border-border bg-panel p-4">
      <h2 className="font-semibold text-foreground">导出设置</h2>
      <div className="mt-4 grid grid-cols-3 gap-3">
        <NumberField label="宽度" value={settings.target_width} onChange={(value) => onChange({ ...settings, target_width: value })} />
        <NumberField label="高度" value={settings.target_height} onChange={(value) => onChange({ ...settings, target_height: value })} />
        <NumberField label="帧率" value={settings.target_fps} onChange={(value) => onChange({ ...settings, target_fps: value })} />
      </div>
      <Button className="mt-4 w-full" disabled={disabled || creating} onClick={onCreate}>
        <Save className="h-4 w-4" aria-hidden="true" />
        {creating ? "创建中" : timelineCopy.createExport}
      </Button>
      {disabled && (
        <p className="mt-3 text-xs leading-5 text-muted">
          需要所有镜头都有已采用视频，且本机可用 FFmpeg / FFprobe 后才能创建导出。
        </p>
      )}
    </section>
  );
}

function NumberField({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="grid gap-1 text-sm text-muted">
      {label}
      <input
        className="h-9 rounded-md border border-border bg-background px-3 text-sm text-foreground outline-none focus:border-primary"
        type="number"
        value={value}
        min={label === "帧率" ? 1 : 256}
        max={label === "帧率" ? 60 : 3840}
        step={label === "帧率" ? 1 : 2}
        onChange={(event) => onChange(Number(event.currentTarget.value))}
      />
    </label>
  );
}

function ExportHistory({
  projectId,
  items,
  ffmpegBlocked,
  pendingExportId,
  marking,
  starting,
  onMarkReady,
  onStart
}: {
  projectId: string;
  items: ProjectExport[];
  ffmpegBlocked: boolean;
  pendingExportId: string | null;
  marking: boolean;
  starting: boolean;
  onMarkReady: (exportId: string) => void;
  onStart: (exportId: string) => void;
}) {
  return (
    <section className="rounded-md border border-border bg-panel p-4">
      <h2 className="font-semibold text-foreground">{timelineCopy.exportHistory}</h2>
      {items.length === 0 ? (
        <EmptyState title={timelineCopy.noExportsTitle} description={timelineCopy.noExportsDescription} />
      ) : (
        <div className="mt-4 grid gap-3">
          {items.map((item) => (
            <ExportCard
              key={item.id}
              item={item}
              ffmpegBlocked={ffmpegBlocked}
              pending={pendingExportId === item.id}
              marking={marking}
              starting={starting}
              onMarkReady={onMarkReady}
              onStart={onStart}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ExportCard({
  item,
  ffmpegBlocked,
  pending,
  marking,
  starting,
  onMarkReady,
  onStart
}: {
  item: ProjectExport;
  ffmpegBlocked: boolean;
  pending: boolean;
  marking: boolean;
  starting: boolean;
  onMarkReady: (exportId: string) => void;
  onStart: (exportId: string) => void;
}) {
  const active = item.status === "queued" || item.status === "running";
  return (
    <article className="rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold text-foreground">{item.name}</h3>
          <p className="mt-1 text-xs text-muted">
            {item.clip_count} 段 / {item.target_width}×{item.target_height} / {item.target_fps} fps
          </p>
        </div>
        <Badge tone={item.status === "completed" ? "success" : item.status === "failed" ? "danger" : "primary"}>
          {timelineCopy.status[item.status]}
        </Badge>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-panelRaised">
        <div className="h-full bg-primary" style={{ width: `${item.progress_percent}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted">{item.current_stage}</p>
      {item.error_message && <p className="mt-2 text-sm text-danger">{item.error_message}</p>}
      {item.output_media_asset?.content_url ? (
        <div className="mt-3 grid gap-2">
          <video className="w-full rounded-md border border-border bg-black" controls src={item.output_media_asset.content_url} />
          <Button asChild variant="secondary">
            <a href={item.output_media_asset.content_url} download>
              <Download className="h-4 w-4" aria-hidden="true" />
              {timelineCopy.download}
            </a>
          </Button>
        </div>
      ) : (
        <p className="mt-3 rounded-md border border-dashed border-border p-3 text-sm text-muted">
          {timelineCopy.noOutput}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {(item.status === "draft" || item.status === "failed") && (
          <Button
            variant="secondary"
            disabled={ffmpegBlocked || (pending && marking)}
            onClick={() => onMarkReady(item.id)}
          >
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            {timelineCopy.markReady}
          </Button>
        )}
        {item.status === "ready" && (
          <Button disabled={ffmpegBlocked || active || (pending && starting)} onClick={() => onStart(item.id)}>
            <Play className="h-4 w-4" aria-hidden="true" />
            {timelineCopy.startExport}
          </Button>
        )}
      </div>
    </article>
  );
}
