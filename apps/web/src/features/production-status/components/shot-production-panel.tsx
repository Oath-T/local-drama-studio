import { Clapperboard, Film, Images, ListChecks, RefreshCw, Wand2 } from "lucide-react";
import type React from "react";
import { Component } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Badge } from "@/features/characters/components/status-badge";

import { productionStatusCopy } from "../copy";
import { normalizeShotProductionStatus } from "../normalizers";
import type { ProductionAction, ProductionFrameStep, ShotProductionStatus } from "../types";

export function ShotProductionPanel({
  onRetry,
  ...props
}: {
  status?: ShotProductionStatus;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  onOpenPrompt: () => void;
  onOpenTasks: () => void;
  onCreateVideoTask: () => void;
}) {
  return (
    <ShotProductionPanelErrorBoundary onRetry={onRetry}>
      <ShotProductionPanelContent {...props} onRetry={onRetry} />
    </ShotProductionPanelErrorBoundary>
  );
}

function ShotProductionPanelContent({
  status,
  loading,
  error,
  onRetry,
  onOpenPrompt,
  onOpenTasks,
  onCreateVideoTask
}: {
  status?: ShotProductionStatus;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  onOpenPrompt: () => void;
  onOpenTasks: () => void;
  onCreateVideoTask: () => void;
}) {
  if (loading) {
    return <Skeleton className="h-80" />;
  }

  if (error) {
    return (
      <section className="grid gap-3 rounded-md border border-border bg-background p-3">
        <StatusMessage tone="error">{productionStatusCopy.loadFailed}</StatusMessage>
        <Button type="button" variant="secondary" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          重试
        </Button>
      </section>
    );
  }

  if (!status) {
    return (
      <section className="grid gap-3 rounded-md border border-border bg-background p-3">
        <StatusMessage tone="error">生产流程加载失败，请重试。</StatusMessage>
        <Button type="button" variant="secondary" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          重试
        </Button>
      </section>
    );
  }

  const safeStatus = normalizeShotProductionStatus(status);

  return (
    <section className="grid gap-3 rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground">{productionStatusCopy.title}</h3>
          <p className="mt-1 text-xs text-muted">{safeStatus.shotName}</p>
        </div>
        <Badge tone={safeStatus.overallStatus === "completed" ? "success" : safeStatus.overallStatus === "blocked" ? "danger" : "primary"}>
          {productionStatusCopy.overall[safeStatus.overallStatus]}
        </Badge>
      </div>

      <div className="grid gap-2">
        <ProductionStep
          icon={<Images className="h-4 w-4" aria-hidden="true" />}
          title={productionStatusCopy.steps.assets}
          status={productionStatusCopy.assetStatus[safeStatus.steps.assets.status]}
          tone={safeStatus.steps.assets.status === "complete" ? "success" : safeStatus.steps.assets.status === "missing" ? "danger" : "default"}
          description={`${safeStatus.steps.assets.character_count} 个角色 / ${safeStatus.steps.assets.reference_count} 张镜头参考`}
        />
        <ProductionStep
          icon={<Wand2 className="h-4 w-4" aria-hidden="true" />}
          title={productionStatusCopy.steps.director_prompt}
          status={productionStatusCopy.directorStatus[safeStatus.steps.director_prompt.status]}
          tone="primary"
          description={
            safeStatus.steps.director_prompt.recommended_template_id
              ? `推荐模板：${safeStatus.steps.director_prompt.recommended_template_id}`
              : "可从镜头上下文生成可编辑草稿"
          }
          action={
            <Button type="button" variant="secondary" size="sm" onClick={onOpenPrompt}>
              {productionStatusCopy.action.create_director_prompt}
            </Button>
          }
        />
        <FrameStepCard
          title={productionStatusCopy.steps.first_frame}
          step={safeStatus.steps.first_frame}
          onOpenTasks={onOpenTasks}
        />
        <FrameStepCard
          title={productionStatusCopy.steps.end_frame}
          step={safeStatus.steps.end_frame}
          onOpenTasks={onOpenTasks}
        />
        <ProductionStep
          icon={<Film className="h-4 w-4" aria-hidden="true" />}
          title={productionStatusCopy.steps.video}
          status={productionStatusCopy.videoStatus[safeStatus.steps.video.status]}
          tone={safeStatus.steps.video.status === "adopted" ? "success" : safeStatus.steps.video.status === "missing_inputs" ? "danger" : "primary"}
          description={`${safeStatus.steps.video.has_start_frame ? productionStatusCopy.startFrameSelected : productionStatusCopy.startFrameMissing} / ${safeStatus.steps.video.has_end_frame ? productionStatusCopy.endFrameSelected : productionStatusCopy.endFrameMissing}`}
          action={
            <Button type="button" variant="secondary" size="sm" onClick={onCreateVideoTask}>
              {productionStatusCopy.createVideoTask}
            </Button>
          }
        />
        <ProductionStep
          icon={<ListChecks className="h-4 w-4" aria-hidden="true" />}
          title={productionStatusCopy.steps.final_adoption}
          status={productionStatusCopy.videoStatus[safeStatus.steps.final_adoption.status]}
          tone={safeStatus.steps.final_adoption.status === "adopted" ? "success" : "default"}
          description={
            safeStatus.steps.final_adoption.adopted_output_id
              ? "已有采用的视频输出"
              : "等待最终视频输出采用"
          }
        />
      </div>

      <div className="rounded-md border border-border bg-panel p-2 text-xs leading-5 text-muted">
        <div className="font-medium text-foreground">阻断项</div>
        {safeStatus.blockers.length > 0 ? safeStatus.blockers.join(" / ") : productionStatusCopy.noBlockers}
      </div>

      {safeStatus.nextActions.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {safeStatus.nextActions.map((action) => (
            <Badge key={action}>{actionLabel(action)}</Badge>
          ))}
        </div>
      )}

      {safeStatus.continuityCandidate && (
        <div className="rounded-md border border-border bg-panel p-2 text-xs leading-5 text-muted">
          <div className="font-medium text-foreground">{productionStatusCopy.continuityTitle}</div>
          {productionStatusCopy.continuityDescription}
          <div className="mt-1 text-foreground">
            {safeStatus.continuityCandidate.source_shot_name} /{" "}
            {safeStatus.continuityCandidate.source_type === "video" ? "视频" : "尾帧"}
          </div>
        </div>
      )}
    </section>
  );
}

class ShotProductionPanelErrorBoundary extends Component<
  { children: React.ReactNode; onRetry: () => void },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidUpdate(previousProps: { children: React.ReactNode; onRetry: () => void }) {
    if (previousProps.children !== this.props.children && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="grid gap-3 rounded-md border border-border bg-background p-3">
          <StatusMessage tone="error">生产流程加载失败，请重试。</StatusMessage>
          <Button type="button" variant="secondary" onClick={this.props.onRetry}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            重试
          </Button>
        </section>
      );
    }
    return this.props.children;
  }
}

function actionLabel(action: string) {
  return productionStatusCopy.action[action as ProductionAction] ?? action;
}

function FrameStepCard({
  title,
  step,
  onOpenTasks
}: {
  title: string;
  step: ProductionFrameStep;
  onOpenTasks: () => void;
}) {
  return (
    <ProductionStep
      icon={<Clapperboard className="h-4 w-4" aria-hidden="true" />}
      title={title}
      status={productionStatusCopy.frameStatus[step.status]}
      tone={step.status === "adopted" ? "success" : step.status === "not_created" ? "default" : "primary"}
      description={step.task_name ?? "还没有结构化关键帧任务"}
      previewUrl={step.content_url}
      action={
        <Button type="button" variant="secondary" size="sm" onClick={onOpenTasks}>
          {productionStatusCopy.openTasks}
        </Button>
      }
    />
  );
}

function ProductionStep({
  icon,
  title,
  status,
  tone,
  description,
  previewUrl,
  action
}: {
  icon: React.ReactNode;
  title: string;
  status: string;
  tone: "default" | "primary" | "success" | "danger";
  description: string;
  previewUrl?: string | null;
  action?: React.ReactNode;
}) {
  return (
    <article className="grid gap-3 rounded-md border border-border bg-background p-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 gap-2">
          <div className="mt-0.5 text-muted">{icon}</div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-foreground">{title}</div>
            <p className="mt-1 line-clamp-2 text-xs text-muted">{description}</p>
          </div>
        </div>
        <Badge tone={tone}>{status}</Badge>
      </div>
      {previewUrl && (
        <img
          src={previewUrl}
          alt=""
          className="aspect-video w-full rounded border border-border object-cover"
        />
      )}
      {action && <div className="flex justify-end">{action}</div>}
    </article>
  );
}
