import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/ui/empty-state";
import { fetchProject, projectKeys } from "@/features/projects/api";

export function ProjectSettingsPage() {
  const { projectId = "" } = useParams();
  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-5">
        <section className="border-b border-border pb-5">
          <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
            设置
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">
            {projectQuery.data?.name ? `${projectQuery.data.name} / 设置` : "设置"}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            项目默认参数、工作流配置和本地服务连接会在后续集中到这里。
          </p>
        </section>
        <EmptyState
          title="项目设置后续开放"
          description="当前请继续在项目创建和各任务面板中维护已有设置。本页不会展示伪造配置。"
        />
      </div>
    </AppShell>
  );
}
