import { Clapperboard, Images, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchCharacters, characterKeys } from "@/features/characters/api";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchScenes, sceneKeys } from "@/features/scenes/api";

export function AssetLibraryPage() {
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

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-5">
        <section className="border-b border-border pb-5">
          <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
            资产库
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">
            {projectQuery.data?.name ? `${projectQuery.data.name} / 资产库` : "资产库"}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            角色库和场景库是镜头工作台调用资产的基础。本轮先统一入口，不改变既有资产结构。
          </p>
        </section>

        {projectQuery.isLoading ? (
          <Skeleton className="h-64" />
        ) : (
          <section className="grid gap-4 lg:grid-cols-3">
            <AssetCard
              title="角色库"
              description="管理人物设定、造型、定妆照和身份参考。"
              metric={`${charactersQuery.data?.total ?? 0} 个角色`}
              href={`/projects/${projectId}/characters`}
              icon={<UserRound className="h-5 w-5" aria-hidden="true" />}
            />
            <AssetCard
              title="场景库"
              description="管理地点、场景状态、空间基准图和空镜。"
              metric={`${scenesQuery.data?.total ?? 0} 个场景`}
              href={`/projects/${projectId}/scenes`}
              icon={<Images className="h-5 w-5" aria-hidden="true" />}
            />
            <AssetCard
              title="镜头可用资产"
              description="后续会统一角色、场景和媒体选择器；当前请在对应资产库维护。"
              metric="后续开放"
              href={`/projects/${projectId}/shots`}
              icon={<Clapperboard className="h-5 w-5" aria-hidden="true" />}
              secondary
            />
          </section>
        )}
      </div>
    </AppShell>
  );
}

function AssetCard({
  title,
  description,
  metric,
  href,
  icon,
  secondary = false
}: {
  title: string;
  description: string;
  metric: string;
  href: string;
  icon: ReactNode;
  secondary?: boolean;
}) {
  return (
    <article className="rounded-md border border-border bg-panel p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-panelRaised text-primary">
          {icon}
        </div>
        <span className="rounded-sm border border-border bg-background px-2 py-1 text-xs text-muted">
          {metric}
        </span>
      </div>
      <h2 className="mt-4 text-base font-semibold text-foreground">{title}</h2>
      <p className="mt-2 min-h-[48px] text-sm leading-6 text-muted">{description}</p>
      <Button asChild variant={secondary ? "secondary" : "default"} className="mt-4">
        <Link to={href}>{secondary ? "查看镜头工作台" : `打开${title}`}</Link>
      </Button>
    </article>
  );
}
