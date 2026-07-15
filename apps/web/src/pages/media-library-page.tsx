import { useQuery } from "@tanstack/react-query";
import { Download, RefreshCw } from "lucide-react";
import { useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Badge } from "@/features/characters/components/status-badge";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchProjectExports, timelineKeys } from "@/features/timeline/api";
import { timelineCopy } from "@/features/timeline/copy";

export function MediaLibraryPage() {
  const { projectId = "" } = useParams();
  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const exportsQuery = useQuery({
    queryKey: timelineKeys.exports(projectId),
    queryFn: () => fetchProjectExports(projectId),
    enabled: projectId.length > 0
  });
  const finalOutputs =
    exportsQuery.data?.items.filter(
      (item) => item.status === "completed" && item.output_media_asset?.content_url
    ) ?? [];

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-5">
        <section className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
              媒体库
            </div>
            <h1 className="mt-2 text-2xl font-semibold text-foreground">
              {projectQuery.data?.name ? `${projectQuery.data.name} / 媒体库` : "媒体库"}
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
              当前显示项目级最终导出视频。角色、场景、关键帧和任务素材仍在各自工作流中管理。
            </p>
          </div>
          <Button type="button" variant="secondary" onClick={() => void exportsQuery.refetch()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            刷新
          </Button>
        </section>

        {exportsQuery.isLoading && <Skeleton className="h-80" />}
        {exportsQuery.isError && (
          <StatusMessage tone="error">最终导出视频加载失败，请稍后重试。</StatusMessage>
        )}
        {exportsQuery.isSuccess && finalOutputs.length === 0 && (
          <EmptyState
            title="暂无最终导出视频"
            description="在时间线与导出页面完成最终成片后，视频会显示在这里。"
          />
        )}
        {finalOutputs.length > 0 && (
          <section className="grid gap-4 lg:grid-cols-2">
            {finalOutputs.map((item) => (
              <article key={item.id} className="rounded-md border border-border bg-panel p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="font-semibold text-foreground">{item.name}</h2>
                    <p className="mt-1 text-xs text-muted">
                      {item.target_width}×{item.target_height} / {item.target_fps} fps
                    </p>
                  </div>
                  <Badge tone="success">{timelineCopy.status.completed}</Badge>
                </div>
                <video
                  className="mt-4 aspect-video w-full rounded-md border border-border bg-black"
                  controls
                  src={item.output_media_asset?.content_url}
                />
                {item.output_media_asset?.content_url && (
                  <Button asChild className="mt-3" variant="secondary">
                    <a href={item.output_media_asset.content_url} download>
                      <Download className="h-4 w-4" aria-hidden="true" />
                      下载最终视频
                    </a>
                  </Button>
                )}
              </article>
            ))}
          </section>
        )}
      </div>
    </AppShell>
  );
}
