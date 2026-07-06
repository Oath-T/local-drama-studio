import { Clapperboard, RefreshCw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Badge } from "@/features/characters/components/status-badge";
import { fetchGenerationTasks, generationTaskKeys } from "@/features/generation-tasks/api";
import { generationTaskCopy } from "@/features/generation-tasks/copy";
import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { cn } from "@/lib/utils";

type FilterKey = "all" | "keyframe" | "video" | "draft" | "ready" | "running" | "completed" | "failed";

const filters: FilterKey[] = ["all", "keyframe", "video", "draft", "ready", "running", "completed", "failed"];

export function GenerationCenterPage() {
  const { projectId = "" } = useParams();
  const [filter, setFilter] = useState<FilterKey>("all");
  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const tasksQuery = useQuery({
    queryKey: generationTaskKeys.lists(projectId),
    queryFn: () => fetchGenerationTasks(projectId),
    enabled: projectId.length > 0,
    refetchInterval: (query) =>
      query.state.data?.items.some((task) =>
        task.latest_run_status === "queued" || task.latest_run_status === "running"
      )
        ? 3000
        : false
  });
  const tasks = tasksQuery.data?.items ?? [];
  const filteredTasks = useMemo(
    () => tasks.filter((task) => matchesFilter(task, filter)),
    [filter, tasks]
  );

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5">
        <section className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
              生成中心
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-foreground">
              {projectQuery.data?.name ? `${projectQuery.data.name} / 生成中心` : generationTaskCopy.title}
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
              {generationTaskCopy.description}
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={() => void tasksQuery.refetch()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            刷新
          </Button>
        </section>

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
              {generationTaskCopy.filters[item]}
            </button>
          ))}
        </div>

        {tasksQuery.isLoading && <Skeleton className="h-96" />}

        {tasksQuery.isError && (
          <StatusMessage tone="error">{generationTaskCopy.loadFailed}</StatusMessage>
        )}

        {tasksQuery.isSuccess && tasks.length === 0 && (
          <EmptyState
            title={generationTaskCopy.emptyTitle}
            description={generationTaskCopy.emptyDescription}
          />
        )}

        {tasksQuery.isSuccess && tasks.length > 0 && filteredTasks.length === 0 && (
          <EmptyState title="当前筛选下没有任务" description="切换筛选条件可以查看其他生成任务。" />
        )}

        {filteredTasks.length > 0 && (
          <section className="grid gap-3">
            {filteredTasks.map((task) => (
              <GenerationTaskCard key={`${task.task_type}-${task.task_id}`} task={task} />
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}

function GenerationTaskCard({ task }: { task: GenerationTaskSummary }) {
  const runTone =
    task.latest_run_status === "completed"
      ? "success"
      : task.latest_run_status === "queued" || task.latest_run_status === "running"
        ? "primary"
        : "default";
  const runLabel = task.latest_run_status
    ? generationTaskCopy.runStatus[task.latest_run_status]
    : generationTaskCopy.noRun;
  return (
    <article className="grid gap-4 rounded-md border border-border bg-panel p-4 lg:grid-cols-[minmax(0,1fr)_220px]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="primary">{generationTaskCopy.taskType[task.task_type]}</Badge>
          <Badge>{taskStatusText(task.task_status)}</Badge>
          <Badge tone={runTone}>{runLabel}</Badge>
          {task.has_selected_output && <Badge tone="success">{generationTaskCopy.selected}</Badge>}
        </div>
        <h2 className="mt-3 truncate text-base font-semibold text-foreground">{task.task_name}</h2>
        <p className="mt-1 text-sm text-muted">所属镜头：{task.shot_name}</p>
        <p className="mt-2 text-xs text-muted">
          工作流：{task.workflow_id || generationTaskCopy.workflowUnset}
        </p>
      </div>
      <div className="grid content-between gap-3 text-sm">
        <div className="grid grid-cols-3 gap-2 text-center">
          <MiniMetric label="Run" value={task.run_count} />
          <MiniMetric label="输出" value={task.output_count} />
          <MiniMetric label="采用" value={task.has_selected_output ? 1 : 0} />
        </div>
        <Button asChild variant="secondary">
          <Link to={`/projects/${task.project_id}/shots/${task.shot_id}`}>
            <Clapperboard className="h-4 w-4" aria-hidden="true" />
            {generationTaskCopy.openShot}
          </Link>
        </Button>
      </div>
    </article>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border bg-background p-2">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 font-semibold text-foreground">{value}</div>
    </div>
  );
}

function matchesFilter(task: GenerationTaskSummary, filter: FilterKey) {
  if (filter === "all") return true;
  if (filter === "keyframe" || filter === "video") return task.task_type === filter;
  if (filter === "draft" || filter === "ready") return task.task_status === filter;
  if (filter === "running") {
    return task.latest_run_status === "queued" || task.latest_run_status === "running";
  }
  return task.latest_run_status === filter;
}

function taskStatusText(status: string) {
  return status === "draft" || status === "ready"
    ? generationTaskCopy.taskStatus[status]
    : status;
}
