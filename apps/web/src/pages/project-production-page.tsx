import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { ProjectProductionBoard } from "@/features/production-status/components/project-production-board";
import {
  fetchProjectProductionStatus,
  productionStatusKeys
} from "@/features/production-status/api";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchProjectExports, fetchProjectTimeline, timelineKeys } from "@/features/timeline/api";
import { timelineCopy } from "@/features/timeline/copy";

export function ProjectProductionPage() {
  const { projectId = "" } = useParams();
  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const productionQuery = useQuery({
    queryKey: productionStatusKeys.project(projectId),
    queryFn: () => fetchProjectProductionStatus(projectId),
    enabled: projectId.length > 0
  });
  const timelineQuery = useQuery({
    queryKey: timelineKeys.timeline(projectId),
    queryFn: () => fetchProjectTimeline(projectId),
    enabled: projectId.length > 0
  });
  const exportsQuery = useQuery({
    queryKey: timelineKeys.exports(projectId),
    queryFn: () => fetchProjectExports(projectId),
    enabled: projectId.length > 0
  });

  return (
    <AppShell>
      <ProjectProductionBoard
        projectId={projectId}
        projectName={projectQuery.data?.name}
        items={productionQuery.data?.items ?? []}
        loading={productionQuery.isLoading}
        error={productionQuery.isError}
        timelineExport={
          timelineQuery.data
            ? {
                readyClips: timelineQuery.data.ready_clip_count,
                totalShots: timelineQuery.data.total_shots,
                blockers: timelineQuery.data.blockers.length,
                latestExportStatus: exportsQuery.data?.items[0]
                  ? timelineCopy.status[exportsQuery.data.items[0].status]
                  : null
              }
            : undefined
        }
        onRetry={() => {
          void productionQuery.refetch();
          void timelineQuery.refetch();
          void exportsQuery.refetch();
        }}
      />
    </AppShell>
  );
}
