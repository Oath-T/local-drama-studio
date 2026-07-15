import { Clapperboard, Film, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Badge } from "@/features/characters/components/status-badge";
import { cn } from "@/lib/utils";

import { productionStatusCopy } from "../copy";
import type { ProductionOverallStatus, ShotProductionStatus } from "../types";

type FilterKey = "all" | ProductionOverallStatus;

const filters: FilterKey[] = ["all", "blocked", "in_progress", "ready_for_video", "completed"];

export function ProjectProductionBoard({
  projectId,
  projectName,
  items,
  loading,
  error,
  timelineExport,
  onRetry
}: {
  projectId: string;
  projectName?: string;
  items: ShotProductionStatus[];
  loading: boolean;
  error: boolean;
  timelineExport?: {
    readyClips: number;
    totalShots: number;
    blockers: number;
    latestExportStatus: string | null;
  };
  onRetry: () => void;
}) {
  const [filter, setFilter] = useState<FilterKey>("all");
  const filteredItems = useMemo(
    () => items.filter((item) => filter === "all" || item.overall_status === filter),
    [filter, items]
  );
  const counts = useMemo(() => {
    return items.reduce(
      (acc, item) => {
        acc[item.overall_status] += 1;
        return acc;
      },
      { blocked: 0, in_progress: 0, ready_for_video: 0, completed: 0 } satisfies Record<ProductionOverallStatus, number>
    );
  }, [items]);

  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5">
      <section className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
            {productionStatusCopy.boardTitle}
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">
            {projectName ? `${projectName} / ${productionStatusCopy.boardTitle}` : productionStatusCopy.boardTitle}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            {productionStatusCopy.boardDescription}
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          刷新
        </Button>
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label={productionStatusCopy.overall.blocked} value={counts.blocked} tone="danger" />
        <Metric label={productionStatusCopy.overall.in_progress} value={counts.in_progress} tone="primary" />
        <Metric label={productionStatusCopy.overall.ready_for_video} value={counts.ready_for_video} tone="primary" />
        <Metric label={productionStatusCopy.overall.completed} value={counts.completed} tone="success" />
      </section>

      {timelineExport && (
        <section className="rounded-md border border-border bg-panel p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-foreground">最终成片准备</h2>
              <p className="mt-1 text-sm text-muted">
                已采用视频 {timelineExport.readyClips}/{timelineExport.totalShots}，阻断项 {timelineExport.blockers}。
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={timelineExport.blockers > 0 ? "danger" : "success"}>
                {timelineExport.blockers > 0 ? "仍有阻断" : "时间线就绪"}
              </Badge>
              {timelineExport.latestExportStatus && (
                <Badge>{`最近导出：${timelineExport.latestExportStatus}`}</Badge>
              )}
              <Button asChild variant="secondary">
                <Link to={`/projects/${projectId}/timeline`}>进入时间线与导出</Link>
              </Button>
            </div>
          </div>
        </section>
      )}

      <div className="flex flex-wrap gap-2">
        {filters.map((item) => (
          <button
            key={item}
            type="button"
            className={cn(
              "rounded-md border px-3 py-2 text-sm transition-colors",
              filter === item
                ? "border-primary bg-primarySoft text-foreground"
                : "border-border bg-panel text-muted hover:border-primary hover:text-foreground"
            )}
            onClick={() => setFilter(item)}
          >
            {productionStatusCopy.filters[item]}
          </button>
        ))}
      </div>

      {loading && <Skeleton className="h-96" />}
      {error && <StatusMessage tone="error">{productionStatusCopy.loadFailed}</StatusMessage>}
      {!loading && !error && items.length === 0 && (
        <EmptyState
          title={productionStatusCopy.emptyTitle}
          description={productionStatusCopy.emptyDescription}
        />
      )}
      {!loading && !error && items.length > 0 && filteredItems.length === 0 && (
        <EmptyState title="当前筛选下没有镜头" description="切换筛选条件可以查看其他生产状态。" />
      )}

      {filteredItems.length > 0 && (
        <section className="grid gap-3">
          {filteredItems.map((item) => (
            <ProductionShotCard key={item.shot_id} projectId={projectId} item={item} />
          ))}
        </section>
      )}
    </div>
  );
}

function ProductionShotCard({
  projectId,
  item
}: {
  projectId: string;
  item: ShotProductionStatus;
}) {
  const firstReady = item.steps.first_frame.status === "adopted";
  const endReady = item.steps.end_frame.status === "adopted";
  return (
    <article className="grid gap-4 rounded-md border border-border bg-panel p-4 lg:grid-cols-[minmax(0,1fr)_220px]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={item.overall_status === "completed" ? "success" : item.overall_status === "blocked" ? "danger" : "primary"}>
            {productionStatusCopy.overall[item.overall_status]}
          </Badge>
          <Badge>{productionStatusCopy.assetStatus[item.steps.assets.status]}</Badge>
          {firstReady && <Badge tone="success">{productionStatusCopy.startFrameSelected}</Badge>}
          {endReady && <Badge tone="success">{productionStatusCopy.endFrameSelected}</Badge>}
        </div>
        <h2 className="mt-3 truncate text-base font-semibold text-foreground">
          #{item.order_index} {item.shot_name}
        </h2>
        <p className="mt-2 text-sm text-muted">
          {item.steps.assets.scene_name ?? "未选择场景"} / {item.steps.assets.scene_state_name ?? "未选择状态"}
        </p>
        <p className="mt-2 text-xs text-muted">
          {item.blockers.length > 0 ? item.blockers.join(" / ") : productionStatusCopy.noBlockers}
        </p>
      </div>
      <div className="grid content-between gap-3 text-sm">
        <div className="grid grid-cols-2 gap-2 text-center">
          <MiniMetric label="首帧" value={productionStatusCopy.frameStatus[item.steps.first_frame.status]} />
          <MiniMetric label="尾帧" value={productionStatusCopy.frameStatus[item.steps.end_frame.status]} />
          <MiniMetric label="视频" value={productionStatusCopy.videoStatus[item.steps.video.status]} />
          <MiniMetric label="采用" value={item.steps.final_adoption.adopted_output_id ? "已采用" : "未采用"} />
        </div>
        <Button asChild variant="secondary">
          <Link to={`/projects/${projectId}/shots/${item.shot_id}`}>
            <Clapperboard className="h-4 w-4" aria-hidden="true" />
            {productionStatusCopy.openShot}
          </Link>
        </Button>
      </div>
    </article>
  );
}

function Metric({
  label,
  value,
  tone
}: {
  label: string;
  value: number;
  tone: "default" | "primary" | "success" | "danger";
}) {
  return (
    <div className="rounded-md border border-border bg-panel p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm text-muted">{label}</span>
        <Badge tone={tone}>{String(value)}</Badge>
      </div>
      <div className="mt-3 text-2xl font-semibold text-foreground">{value}</div>
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-background p-2">
      <div className="flex items-center justify-center gap-1 text-xs text-muted">
        <Film className="h-3 w-3" aria-hidden="true" />
        {label}
      </div>
      <div className="mt-1 truncate font-semibold text-foreground">{value}</div>
    </div>
  );
}
