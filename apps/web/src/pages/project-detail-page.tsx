import { ArrowLeft, RefreshCw, UserRound } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { copy } from "@/locales";

function formatLocalDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1120px] flex-col gap-5">
        <Button asChild variant="ghost" className="w-fit">
          <Link to="/projects">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            {copy.common.backToProjects}
          </Link>
        </Button>

        {projectQuery.isLoading && (
          <div className="grid gap-4" aria-label={copy.common.loading}>
            <Skeleton className="h-10 w-1/2" />
            <Skeleton className="h-28" />
            <Skeleton className="h-48" />
          </div>
        )}

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
            <section className="border-b border-border pb-4">
              <h1 className="break-words text-2xl font-semibold text-foreground">
                {projectQuery.data.name}
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
                {projectQuery.data.description || copy.projects.noDescription}
              </p>
            </section>

            <section className="grid gap-4 rounded-md border border-border bg-panel p-5 md:grid-cols-2">
              <InfoItem label={copy.projects.aspectRatio} value={projectQuery.data.aspect_ratio} />
              <InfoItem
                label={copy.projects.defaultLanguage}
                value={copy.options.language[projectQuery.data.default_language]}
              />
              <InfoItem
                label={copy.projects.defaultFps}
                value={copy.options.fps[projectQuery.data.default_fps]}
              />
              <InfoItem
                label={copy.projects.defaultStyle}
                value={projectQuery.data.default_style || copy.projects.noDescription}
              />
              <InfoItem
                label={copy.projects.createdAt}
                value={formatLocalDate(projectQuery.data.created_at)}
              />
              <InfoItem
                label={copy.projects.updatedAt}
                value={formatLocalDate(projectQuery.data.updated_at)}
              />
            </section>

            <section className="rounded-md border border-border bg-panel p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-semibold text-foreground">角色库</h2>
                  <p className="mt-1 text-sm text-muted">{copy.projects.detailPlaceholder}</p>
                </div>
                <Button asChild>
                  <Link to={`/projects/${projectQuery.data.id}/characters`}>
                    <UserRound className="h-4 w-4" aria-hidden="true" />
                    打开角色库
                  </Link>
                </Button>
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 break-words text-sm text-foreground">{value}</div>
    </div>
  );
}
