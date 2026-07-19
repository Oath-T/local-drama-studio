import { MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { ProjectFormDialog } from "@/features/projects/components/project-form-dialog";
import type { Project } from "@/features/projects/types";
import { copy } from "@/locales";

interface ProjectCardProps {
  project: Project;
  onDelete: (project: Project) => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

function formatLocalDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function ProjectCard({ project, onDelete, onSuccess, onError }: ProjectCardProps) {
  const [editOpen, setEditOpen] = useState(false);

  return (
    <>
      <article className="grid min-h-[320px] overflow-hidden rounded-md border border-border bg-panel shadow-workbench">
        <div className="flex h-28 items-center justify-center border-b border-border bg-panelRaised text-sm text-muted">
          {copy.projects.coverPlaceholder}
        </div>
        <div className="flex min-h-0 flex-col gap-4 p-4">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-foreground">{project.name}</h2>
            <p className="mt-2 line-clamp-2 min-h-[40px] text-sm leading-5 text-muted">
              {project.description || copy.projects.noDescription}
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
            <div>
              <dt className="text-muted">{copy.projects.aspectRatio}</dt>
              <dd className="mt-1 text-foreground">{project.aspect_ratio}</dd>
            </div>
            <div>
              <dt className="text-muted">{copy.projects.defaultLanguage}</dt>
              <dd className="mt-1 text-foreground">
                {copy.options.language[project.default_language]}
              </dd>
            </div>
            <div>
              <dt className="text-muted">{copy.projects.defaultFps}</dt>
              <dd className="mt-1 text-foreground">{copy.options.fps[project.default_fps]}</dd>
            </div>
            <div>
              <dt className="text-muted">{copy.projects.updatedAt}</dt>
              <dd className="mt-1 text-foreground">{formatLocalDate(project.updated_at)}</dd>
            </div>
          </dl>

          <div className="mt-auto flex items-center justify-between gap-2">
            <Button asChild variant="secondary">
              <Link to={`/projects/${project.id}/studio`}>{copy.projects.openProject}</Link>
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button type="button" variant="ghost" size="icon" aria-label={copy.common.actions}>
                  <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => setEditOpen(true)}>
                  <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
                  {copy.common.edit}
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-danger focus:text-danger"
                  onSelect={() => onDelete(project)}
                >
                  <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
                  {copy.common.delete}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </article>

      <ProjectFormDialog
        mode="edit"
        project={project}
        open={editOpen}
        onOpenChange={setEditOpen}
        onSuccess={onSuccess}
        onError={onError}
      />
    </>
  );
}
