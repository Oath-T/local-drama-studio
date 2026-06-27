import type { Project } from "@/features/projects/types";
import { ProjectCard } from "./project-card";

interface ProjectListProps {
  projects: Project[];
  onDelete: (project: Project) => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

export function ProjectList({ projects, onDelete, onSuccess, onError }: ProjectListProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard
          key={project.id}
          project={project}
          onDelete={onDelete}
          onSuccess={onSuccess}
          onError={onError}
        />
      ))}
    </div>
  );
}
