import { ArrowLeft, Clapperboard, ExternalLink, ImageOff, MoreHorizontal, Settings } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { fetchHealth } from "@/features/health/api";
import { fetchSystemCapabilities } from "@/features/keyframe-generation/api";
import { productionStatusKeys, fetchProjectProductionStatus } from "@/features/production-status/api";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchShots, shotKeys } from "@/features/shots/api";
import { cn } from "@/lib/utils";

import {
  buildStoryboardShotItems,
  type StoryboardMediaPreview,
  type StoryboardShotItem
} from "../storyboard";
import {
  createDefaultStudioSession,
  loadStudioSession,
  parseStudioUrlContext,
  sanitizeStudioSessionSelection,
  saveStudioSession,
  type StudioSessionState
} from "../session";

export function StudioWorkspacePage({ projectId }: { projectId: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [session, setSession] = useState<StudioSessionState>(() => loadStudioSession(projectId));
  const [notice, setNotice] = useState<string | null>(null);

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
  const productionQuery = useQuery({
    queryKey: productionStatusKeys.project(projectId),
    queryFn: () => fetchProjectProductionStatus(projectId),
    enabled: projectId.length > 0,
    refetchInterval: (query) =>
      (query.state.data?.items ?? []).some((shot) =>
        [shot.steps.first_frame?.status, shot.steps.end_frame?.status, shot.steps.video?.status].some(
          (status) => status === "running"
        )
      )
        ? 4000
        : false
  });
  const capabilitiesQuery = useQuery({
    queryKey: shotKeys.systemCapabilities(),
    queryFn: fetchSystemCapabilities,
    enabled: projectId.length > 0,
    staleTime: 30_000
  });
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    retry: false,
    refetchInterval: 30_000
  });

  const shots = shotsQuery.data?.items ?? [];
  const videoAvailable = Boolean(capabilitiesQuery.data?.video_generation?.available);
  const storyboardItems = useMemo(
    () =>
      buildStoryboardShotItems({
        shots,
        productionStatus: productionQuery.data ?? null,
        videoAvailable
      }),
    [productionQuery.data, shots, videoAvailable]
  );
  const selectedShot =
    storyboardItems.find((item) => item.shot.id === session.selectedShotId) ?? storyboardItems[0] ?? null;
  const hasPartialError = shotsQuery.isError || productionQuery.isError || capabilitiesQuery.isError;

  useEffect(() => {
    const context = parseStudioUrlContext(location.search);
    if (context.ignored) {
      setNotice("已忽略不适用于简化 Studio 的上下文参数。");
    }
    if (context.selectedShotId) {
      updateSession((current) => ({ ...current, selectedShotId: context.selectedShotId }));
    }
  }, [location.search]);

  useEffect(() => {
    if (!shotsQuery.isSuccess) return;
    updateSession((current) =>
      sanitizeStudioSessionSelection(current, new Set(shots.map((shot) => shot.id)))
    );
  }, [shots, shotsQuery.isSuccess]);

  useEffect(() => {
    if (!scrollRef.current || session.scrollPosition <= 0) return;
    scrollRef.current.scrollTop = session.scrollPosition;
  }, []);

  function updateSession(updater: (current: StudioSessionState) => StudioSessionState) {
    setSession((current) => {
      const next = updater(current);
      try {
        saveStudioSession(next);
      } catch {
        setNotice("Studio 现场保存失败，本次页面仍可继续使用。");
      }
      return next;
    });
  }

  function selectShot(shotId: string) {
    updateSession((current) => ({ ...current, selectedShotId: shotId }));
  }

  function openGeneration(shotId: string) {
    navigate(`/projects/${projectId}/shots/${shotId}?intent=generate&returnTo=studio`);
  }

  function saveScrollPosition() {
    updateSession((current) => ({
      ...current,
      scrollPosition: scrollRef.current?.scrollTop ?? 0
    }));
  }

  if (projectQuery.isError) {
    return (
      <AppShell>
        <StatusMessage tone="error">项目不存在或无法访问。</StatusMessage>
        <Button asChild className="mt-4" variant="secondary">
          <Link to="/projects">返回项目列表</Link>
        </Button>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto flex h-full max-w-[1680px] flex-col overflow-hidden">
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
              <Link to="/projects" className="inline-flex items-center gap-1 hover:text-foreground">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                项目
              </Link>
              <span>/</span>
              <span className="truncate">{projectQuery.data?.name ?? "加载项目中"}</span>
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-foreground">故事板</h1>
            <p className="mt-1 text-sm text-muted">
              选择真实镜头进入生成工作台，完成首帧、尾帧、视频候选和手动采用。
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill tone={healthQuery.isSuccess ? "success" : "danger"}>
              {healthQuery.isSuccess ? "后端已连接" : "后端不可用"}
            </StatusPill>
            <StatusPill tone={videoAvailable ? "success" : "warning"}>
              {videoAvailable ? "视频能力可用" : "视频能力不可用"}
            </StatusPill>
            <Button asChild variant="secondary" size="sm">
              <Link to={`/projects/${projectId}/characters`}>角色库</Link>
            </Button>
            <Button asChild variant="secondary" size="sm">
              <Link to={`/projects/${projectId}/scenes`}>场景库</Link>
            </Button>
            <details className="relative">
              <summary className="flex h-9 cursor-pointer list-none items-center gap-2 rounded-md border border-border bg-panel px-3 text-sm text-muted hover:bg-panelRaised hover:text-foreground">
                <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                更多
              </summary>
              <div className="absolute right-0 z-20 mt-2 grid w-44 gap-1 rounded-md border border-border bg-panel p-2 shadow-workbench">
                <MenuLink to={`/projects/${projectId}/canvas`}>旧画布</MenuLink>
                <MenuLink to={`/projects/${projectId}/generation`}>生成中心</MenuLink>
                <MenuLink to={`/projects/${projectId}/timeline`}>时间线 / 导出</MenuLink>
                <MenuLink to={`/projects/${projectId}/media`}>媒体库</MenuLink>
                <MenuLink to={`/projects/${projectId}/settings`}>项目设置</MenuLink>
              </div>
            </details>
          </div>
        </header>

        {notice && (
          <div className="mt-4">
            <StatusMessage tone="neutral">{notice}</StatusMessage>
          </div>
        )}
        {hasPartialError && (
          <div className="mt-4">
            <StatusMessage tone="neutral">部分状态加载失败，已显示可用的真实镜头数据。</StatusMessage>
          </div>
        )}

        <section className="mt-4 grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div
            ref={scrollRef}
            className="min-w-0 overflow-y-auto overflow-x-hidden pr-1"
            onScroll={saveScrollPosition}
          >
            {projectQuery.isLoading || shotsQuery.isLoading ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {[0, 1, 2].map((item) => (
                  <Skeleton key={item} className="h-[360px]" />
                ))}
              </div>
            ) : null}

            {shotsQuery.isSuccess && storyboardItems.length === 0 ? (
              <EmptyState
                title="暂无镜头"
                description="先创建第一个镜头，再进入生成工作台制作首帧、尾帧和视频。"
                action={
                  <Button asChild>
                    <Link to={`/projects/${projectId}/shots`}>打开镜头工作台</Link>
                  </Button>
                }
              />
            ) : null}

            {storyboardItems.length > 0 ? (
              <div className="grid min-w-0 gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {storyboardItems.map((item) => (
                  <ShotCard
                    key={item.shot.id}
                    item={item}
                    selected={selectedShot?.shot.id === item.shot.id}
                    onSelect={() => selectShot(item.shot.id)}
                    onOpenGeneration={() => openGeneration(item.shot.id)}
                  />
                ))}
              </div>
            ) : null}
          </div>

          <aside className="min-w-0 rounded-md border border-border bg-panel p-4">
            <div className="flex items-center gap-2">
              <Clapperboard className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-sm font-semibold">当前镜头</h2>
            </div>
            {selectedShot ? (
              <div className="mt-4 space-y-4">
                <div>
                  <div className="text-xs text-muted">镜头 {selectedShot.shot.order_index}</div>
                  <h3 className="mt-1 text-lg font-semibold">{selectedShot.shot.name}</h3>
                </div>
                <dl className="space-y-3 text-sm">
                  <InfoRow label="首帧" value={selectedShot.firstFramePreview.label} />
                  <InfoRow label="尾帧" value={selectedShot.endFramePreview.label} />
                  <InfoRow label="视频" value={selectedShot.videoPreview.label} />
                </dl>
                <Button type="button" className="w-full" onClick={() => openGeneration(selectedShot.shot.id)}>
                  打开生成
                </Button>
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted">请选择一个镜头。</p>
            )}
            <div className="mt-6 border-t border-border pt-4">
              <h3 className="text-xs font-semibold text-muted">次级入口</h3>
              <div className="mt-3 grid gap-2">
                <MenuLink to={`/projects/${projectId}/canvas`}>旧 Canvas</MenuLink>
                <MenuLink to={`/projects/${projectId}/production`}>生产看板</MenuLink>
                <MenuLink to={`/projects/${projectId}/generation`}>生成中心</MenuLink>
                <MenuLink to={`/projects/${projectId}/settings`}>
                  <Settings className="mr-2 inline h-3.5 w-3.5" aria-hidden="true" />
                  设置
                </MenuLink>
              </div>
            </div>
          </aside>
        </section>
      </div>
    </AppShell>
  );
}

function ShotCard({
  item,
  selected,
  onSelect,
  onOpenGeneration
}: {
  item: StoryboardShotItem;
  selected: boolean;
  onSelect: () => void;
  onOpenGeneration: () => void;
}) {
  return (
    <article
      data-testid="studio-storyboard-card"
      className={cn(
        "min-w-0 rounded-md border bg-panel p-3 shadow-workbench transition",
        selected ? "border-primary" : "border-border hover:border-borderStrong"
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-xs text-muted">镜头 {item.shot.order_index}</div>
          <h2 className="mt-1 truncate text-base font-semibold">{item.shot.name}</h2>
        </div>
        <StatusPill tone={statusTone(item.videoPreview.status)}>{item.videoPreview.label}</StatusPill>
      </div>

      <div className="mt-3 grid gap-3">
        <PreviewFrame preview={item.firstFramePreview} title="首帧" />
        <PreviewFrame preview={item.endFramePreview} title="尾帧" />
      </div>

      <Button
        type="button"
        className="mt-4 w-full"
        onClick={(event) => {
          event.stopPropagation();
          onOpenGeneration();
        }}
      >
        打开生成
      </Button>
    </article>
  );
}

function PreviewFrame({ preview, title }: { preview: StoryboardMediaPreview; title: string }) {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-background">
      <div className="flex items-center justify-between px-3 py-2 text-xs">
        <span className="font-medium">{title}</span>
        <span className="text-muted">{preview.label}</span>
      </div>
      <div className="grid aspect-video place-items-center border-t border-border bg-black/20">
        {preview.contentUrl ? (
          <img
            src={preview.contentUrl}
            alt={`${title}预览`}
            className="h-full w-full object-contain"
            loading="lazy"
            onError={(event) => {
              event.currentTarget.replaceWith(document.createTextNode("图片加载失败"));
            }}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-xs text-muted">
            <ImageOff className="h-5 w-5" aria-hidden="true" />
            暂无画面
          </div>
        )}
      </div>
    </div>
  );
}

function StatusPill({ children, tone }: { children: string; tone: "success" | "warning" | "danger" | "neutral" }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center rounded-full border px-2 py-1 text-xs",
        tone === "success" && "border-success/40 bg-success/10 text-success",
        tone === "warning" && "border-warning/40 bg-warning/10 text-warning",
        tone === "danger" && "border-danger/40 bg-danger/10 text-danger",
        tone === "neutral" && "border-border bg-panelRaised text-muted"
      )}
    >
      {children}
    </span>
  );
}

function statusTone(status: StoryboardMediaPreview["status"]) {
  if (status === "adopted") return "success";
  if (status === "running" || status === "completed") return "warning";
  if (status === "failed" || status === "unavailable") return "danger";
  return "neutral";
}

function MenuLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      className="rounded-md px-3 py-2 text-sm text-muted transition hover:bg-panelRaised hover:text-foreground"
    >
      <ExternalLink className="mr-2 inline h-3.5 w-3.5" aria-hidden="true" />
      {children}
    </Link>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right text-foreground">{value}</dd>
    </div>
  );
}
