import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { AppShell } from "@/components/layout/app-shell";
import { EmptyState } from "@/components/ui/empty-state";
import { fetchProject, projectKeys } from "@/features/projects/api";

export function MediaLibraryPage() {
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
            媒体库
          </div>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">
            {projectQuery.data?.name ? `${projectQuery.data.name} / 媒体库` : "媒体库"}
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            后续会集中管理项目图片、关键帧和视频输出。本轮不实现复杂媒体管理。
          </p>
        </section>
        <EmptyState
          title="媒体库后续开放"
          description="当前媒体仍在角色、场景、关键帧和视频任务中查看，避免提前伪造全局媒体管理。"
        />
      </div>
    </AppShell>
  );
}
