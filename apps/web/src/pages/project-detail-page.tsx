import {
  Clapperboard,
  Film,
  Images,
  ListChecks,
  Plus,
  RefreshCw,
  UserRound,
  Workflow
} from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { fetchCharacters, characterKeys } from "@/features/characters/api";
import { fetchGenerationTasks, generationTaskKeys } from "@/features/generation-tasks/api";
import { generationTaskCopy } from "@/features/generation-tasks/copy";
import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchScenes, sceneKeys } from "@/features/scenes/api";
import { fetchShots, shotKeys } from "@/features/shots/api";
import type { Shot } from "@/features/shots/types";
import { copy } from "@/locales";

const activeRunStatuses = new Set(["queued", "running"]);

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
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
  const scenesQuery = useQuery({
    queryKey: sceneKeys.lists(projectId),
    queryFn: () => fetchScenes(projectId),
    enabled: projectId.length > 0
  });
  const shotsQuery = useQuery({
    queryKey: shotKeys.lists(projectId),
    queryFn: () => fetchShots(projectId),
    enabled: projectId.length > 0
  });
  const generationTasksQuery = useQuery({
    queryKey: generationTaskKeys.lists(projectId),
    queryFn: () => fetchGenerationTasks(projectId),
    enabled: projectId.length > 0
  });

  const generationTasks = generationTasksQuery.data?.items ?? [];
  const recentShots = [...(shotsQuery.data?.items ?? [])]
    .sort((left, right) => Date.parse(right.updated_at) - Date.parse(left.updated_at))
    .slice(0, 4);
  const recentTasks = generationTasks.slice(0, 4);
  const recentOutputs = generationTasks.filter((task) => task.has_outputs).slice(0, 4);

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5">
        {projectQuery.isLoading && <ProjectOverviewSkeleton />}

        {projectQuery.isError && (
          <section className="rounded-md border border-border bg-panel p-6">
            <h1 className="text-xl font-semibold text-foreground">{copy.projects.notFoundTitle}</h1>
            <p className="mt-2 text-sm text-muted">{copy.projects.notFoundDescription}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button asChild variant="secondary">
                <Link to="/projects">{copy.common.backToProjects}</Link>
              </Button>
              <Button type="button" variant="secondary" onClick={() => void projectQuery.refetch()}>
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                {copy.common.retry}
              </Button>
            </div>
          </section>
        )}

        {projectQuery.isSuccess && (
          <>
            <section className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
              <div className="min-w-0">
                <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
                  项目总览
                </div>
                <h1 className="mt-2 break-words text-2xl font-semibold text-foreground">
                  {projectQuery.data.name}
                </h1>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
                  {projectQuery.data.description || "暂无项目简介。"}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button asChild>
                  <Link to={`/projects/${projectQuery.data.id}/canvas`}>
                    <Workflow className="h-4 w-4" aria-hidden="true" />
                    进入创作画布
                  </Link>
                </Button>
                <Button asChild variant="secondary">
                  <Link to={`/projects/${projectQuery.data.id}/generation`}>
                  <ListChecks className="h-4 w-4" aria-hidden="true" />
                  进入生成中心
                  </Link>
                </Button>
              </div>
            </section>

            <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-7">
              <MetricCard label="角色" value={charactersQuery.data?.total} loading={charactersQuery.isLoading} />
              <MetricCard label="场景" value={scenesQuery.data?.total} loading={scenesQuery.isLoading} />
              <MetricCard label="镜头" value={shotsQuery.data?.total} loading={shotsQuery.isLoading} />
              <MetricCard
                label="关键帧任务"
                value={generationTasks.filter((task) => task.task_type === "keyframe").length}
                loading={generationTasksQuery.isLoading}
              />
              <MetricCard
                label="视频任务"
                value={generationTasks.filter((task) => task.task_type === "video").length}
                loading={generationTasksQuery.isLoading}
              />
              <MetricCard
                label="运行中"
                value={
                  generationTasks.filter(
                    (task) => task.latest_run_status && activeRunStatuses.has(task.latest_run_status)
                  ).length
                }
                loading={generationTasksQuery.isLoading}
              />
              <MetricCard
                label="已采用输出"
                value={generationTasks.filter((task) => task.has_selected_output).length}
                loading={generationTasksQuery.isLoading}
              />
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
              <DashboardPanel title="快捷入口">
                <div className="grid gap-2 sm:grid-cols-2">
                  <QuickLink
                    icon={<Workflow className="h-4 w-4" aria-hidden="true" />}
                    title="打开创作画布"
                    description="在项目级画布中组织角色、场景、镜头、输出和导出关系。"
                    href={`/projects/${projectQuery.data.id}/canvas`}
                  />
                  <QuickLink
                    icon={<UserRound className="h-4 w-4" aria-hidden="true" />}
                    title="新建角色"
                    description="进入角色库管理人物、造型和参考图。"
                    href={`/projects/${projectQuery.data.id}/characters`}
                  />
                  <QuickLink
                    icon={<Images className="h-4 w-4" aria-hidden="true" />}
                    title="新建场景"
                    description="进入场景库管理地点、状态和空间参考。"
                    href={`/projects/${projectQuery.data.id}/scenes`}
                  />
                  <QuickLink
                    icon={<Clapperboard className="h-4 w-4" aria-hidden="true" />}
                    title="新建镜头"
                    description="进入镜头工作台组织镜头和绑定资产。"
                    href={`/projects/${projectQuery.data.id}/shots`}
                  />
                  <QuickLink
                    icon={<Film className="h-4 w-4" aria-hidden="true" />}
                    title="查看生成任务"
                    description="集中查看关键帧与视频任务状态。"
                    href={`/projects/${projectQuery.data.id}/generation`}
                  />
                </div>
              </DashboardPanel>

              <DashboardPanel title="资产库">
                <div className="grid gap-3">
                  <AssetArea
                    title="角色库"
                    description="人物、造型、定妆参考图。"
                    href={`/projects/${projectQuery.data.id}/characters`}
                  />
                  <AssetArea
                    title="场景库"
                    description="地点、场景状态、空间参考图。"
                    href={`/projects/${projectQuery.data.id}/scenes`}
                  />
                </div>
              </DashboardPanel>
            </section>

            {generationTasksQuery.isError && (
              <StatusMessage tone="error">{generationTaskCopy.loadFailed}</StatusMessage>
            )}

            <section className="grid gap-4 xl:grid-cols-3">
              <DashboardPanel title="最近镜头">
                <RecentShotList projectId={projectQuery.data.id} shots={recentShots} loading={shotsQuery.isLoading} />
              </DashboardPanel>
              <DashboardPanel title="最近生成任务">
                <GenerationTaskList tasks={recentTasks} loading={generationTasksQuery.isLoading} />
              </DashboardPanel>
              <DashboardPanel title="最近输出">
                <GenerationTaskList
                  tasks={recentOutputs}
                  loading={generationTasksQuery.isLoading}
                  emptyTitle="暂无输出"
                  emptyDescription="完成生成并保存输出后，会在这里出现。"
                />
              </DashboardPanel>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}

function ProjectOverviewSkeleton() {
  return (
    <div className="grid gap-4" aria-label={copy.common.loading}>
      <Skeleton className="h-24" />
      <div className="grid gap-3 md:grid-cols-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

function MetricCard({
  label,
  value,
  loading
}: {
  label: string;
  value: number | undefined;
  loading: boolean;
}) {
  return (
    <div className="rounded-md border border-border bg-panel p-4">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-3 text-2xl font-semibold text-foreground">
        {loading ? "..." : (value ?? 0)}
      </div>
    </div>
  );
}

function DashboardPanel({
  title,
  children
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-md border border-border bg-panel p-4">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function QuickLink({
  icon,
  title,
  description,
  href
}: {
  icon: ReactNode;
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      to={href}
      className="rounded-md border border-border bg-background p-3 transition-colors hover:border-primary hover:bg-panelRaised"
    >
      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
        {icon}
        {title}
      </div>
      <p className="mt-2 text-xs leading-5 text-muted">{description}</p>
    </Link>
  );
}

function AssetArea({
  title,
  description,
  href
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      to={href}
      className="flex items-center justify-between gap-3 rounded-md border border-border bg-background p-3 hover:border-primary"
    >
      <span>
        <span className="block text-sm font-semibold text-foreground">{title}</span>
        <span className="mt-1 block text-xs text-muted">{description}</span>
      </span>
      <Plus className="h-4 w-4 text-primary" aria-hidden="true" />
    </Link>
  );
}

function RecentShotList({
  projectId,
  shots,
  loading
}: {
  projectId: string;
  shots: Shot[];
  loading: boolean;
}) {
  if (loading) {
    return <Skeleton className="h-32" />;
  }
  if (shots.length === 0) {
    return (
      <EmptyState
        title="暂无镜头"
        description="创建第一条镜头后，项目总览会显示最近更新的镜头。"
        action={
          <Button asChild>
            <Link to={`/projects/${projectId}/shots`}>新建镜头</Link>
          </Button>
        }
      />
    );
  }
  return (
    <div className="grid gap-2">
      {shots.map((shot) => (
        <Link
          key={shot.id}
          to={`/projects/${projectId}/shots/${shot.id}`}
          className="rounded-md border border-border bg-background p-3 hover:border-primary"
        >
          <div className="flex items-center justify-between gap-3 text-xs text-muted">
            <span>#{shot.order_index}</span>
            <span>{shot.character_count} 人物 / {shot.reference_count} 参考</span>
          </div>
          <div className="mt-2 truncate text-sm font-semibold text-foreground">{shot.name}</div>
        </Link>
      ))}
    </div>
  );
}

function GenerationTaskList({
  tasks,
  loading,
  emptyTitle = "暂无生成任务",
  emptyDescription = "创建关键帧或视频任务后，会在这里显示。"
}: {
  tasks: GenerationTaskSummary[];
  loading: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  if (loading) {
    return <Skeleton className="h-32" />;
  }
  if (tasks.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }
  return (
    <div className="grid gap-2">
      {tasks.map((task) => (
        <TaskSummaryRow key={`${task.task_type}-${task.task_id}`} task={task} />
      ))}
    </div>
  );
}

function TaskSummaryRow({ task }: { task: GenerationTaskSummary }) {
  const runLabel = task.latest_run_status
    ? generationTaskCopy.runStatus[task.latest_run_status]
    : generationTaskCopy.noRun;
  return (
    <Link
      to={`/projects/${task.project_id}/shots/${task.shot_id}`}
      className="block rounded-md border border-border bg-background p-3 hover:border-primary"
    >
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        <span className="rounded-sm border border-border bg-panel px-2 py-1">
          {generationTaskCopy.taskType[task.task_type]}
        </span>
        <span>{taskStatusText(task.task_status)}</span>
        <span>{runLabel}</span>
      </div>
      <div className="mt-2 truncate text-sm font-semibold text-foreground">{task.task_name}</div>
      <div className="mt-1 truncate text-xs text-muted">{task.shot_name}</div>
      <div className="mt-2 text-xs text-muted">
        {task.has_outputs ? generationTaskCopy.hasOutput : generationTaskCopy.noOutput}
        {" / "}
        {task.has_selected_output ? generationTaskCopy.selected : generationTaskCopy.unselected}
      </div>
    </Link>
  );
}

function taskStatusText(status: string) {
  return status === "draft" || status === "ready"
    ? generationTaskCopy.taskStatus[status]
    : status;
}
