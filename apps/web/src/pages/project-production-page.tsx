import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { ProjectProductionBoard } from "@/features/production-status/components/project-production-board";
import {
  fetchProjectProductionStatus,
  productionStatusKeys
} from "@/features/production-status/api";
import { fetchProject, projectKeys } from "@/features/projects/api";

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

  return (
    <AppShell>
      <ProjectProductionBoard
        projectId={projectId}
        projectName={projectQuery.data?.name}
        items={productionQuery.data?.items ?? []}
        loading={productionQuery.isLoading}
        error={productionQuery.isError}
        onRetry={() => void productionQuery.refetch()}
      />
    </AppShell>
  );
}
