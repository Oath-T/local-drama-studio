import { useState } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { AppShell } from "@/components/layout/app-shell";
import { fetchProjects, projectKeys } from "@/features/projects/api";
import { ProjectDeleteDialog } from "@/features/projects/components/project-delete-dialog";
import { ProjectFormDialog } from "@/features/projects/components/project-form-dialog";
import { ProjectList } from "@/features/projects/components/project-list";
import type { Project } from "@/features/projects/types";
import { copy } from "@/locales";

export function ProjectsPage() {
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null
  );
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const projectsQuery = useQuery({
    queryKey: projectKeys.lists(),
    queryFn: fetchProjects
  });
  const visibleProjects =
    projectsQuery.data?.items.filter(
      (project) => !project.name.startsWith("E2E_") && !project.name.startsWith("__E2E_")
    ) ?? [];

  const createButton = (
    <Button type="button">
      <Plus className="h-4 w-4" aria-hidden="true" />
      {copy.projects.newProject}
    </Button>
  );

  return (
    <AppShell>
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-5">
        <section className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-4">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">{copy.projects.title}</h1>
            <p className="mt-2 text-sm text-muted">{copy.projects.description}</p>
          </div>
          <ProjectFormDialog
            mode="create"
            trigger={createButton}
            onSuccess={(message) => setFeedback({ tone: "success", message })}
            onError={(message) => setFeedback({ tone: "error", message })}
          />
        </section>

        {feedback && <StatusMessage tone={feedback.tone}>{feedback.message}</StatusMessage>}

        {projectsQuery.isLoading && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" aria-label={copy.common.loading}>
            {[0, 1, 2].map((item) => (
              <Skeleton key={item} className="h-[320px]" />
            ))}
          </div>
        )}

        {projectsQuery.isError && (
          <section className="rounded-md border border-border bg-panel p-6">
            <StatusMessage tone="error">{copy.projects.loadFailed}</StatusMessage>
            <Button
              type="button"
              className="mt-4"
              variant="secondary"
              onClick={() => void projectsQuery.refetch()}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {copy.common.retry}
            </Button>
          </section>
        )}

        {projectsQuery.isSuccess && visibleProjects.length === 0 && (
          <EmptyState
            title={copy.projects.emptyTitle}
            description={copy.projects.emptyDescription}
            action={
              <ProjectFormDialog
                mode="create"
                trigger={createButton}
                onSuccess={(message) => setFeedback({ tone: "success", message })}
                onError={(message) => setFeedback({ tone: "error", message })}
              />
            }
          />
        )}

        {projectsQuery.isSuccess && visibleProjects.length > 0 && (
          <ProjectList
            projects={visibleProjects}
            onDelete={setProjectToDelete}
            onSuccess={(message) => setFeedback({ tone: "success", message })}
            onError={(message) => setFeedback({ tone: "error", message })}
          />
        )}

        <ProjectDeleteDialog
          project={projectToDelete}
          open={projectToDelete !== null}
          onOpenChange={(open) => {
            if (!open) {
              setProjectToDelete(null);
            }
          }}
          onSuccess={(message) => setFeedback({ tone: "success", message })}
          onError={(message) => setFeedback({ tone: "error", message })}
        />
      </div>
    </AppShell>
  );
}
