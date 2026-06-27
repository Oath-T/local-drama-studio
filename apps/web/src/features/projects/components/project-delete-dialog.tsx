import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from "@/components/ui/alert-dialog";
import { deleteProject, projectKeys } from "@/features/projects/api";
import type { Project } from "@/features/projects/types";
import { copy } from "@/locales";

interface ProjectDeleteDialogProps {
  project: Project | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

export function ProjectDeleteDialog({
  project,
  open,
  onOpenChange,
  onSuccess,
  onError
}: ProjectDeleteDialogProps) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async () => {
      if (!project) {
        return;
      }
      await deleteProject(project.id);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      if (project) {
        queryClient.removeQueries({ queryKey: projectKeys.detail(project.id) });
      }
      onOpenChange(false);
      onSuccess(copy.projects.deleted);
    },
    onError: () => {
      onError(copy.projects.deleteFailed);
    }
  });

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{copy.projects.deleteProject}</AlertDialogTitle>
          <AlertDialogDescription>
            {project ? copy.projects.deleteDescription(project.name) : ""}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={mutation.isPending}>{copy.common.cancel}</AlertDialogCancel>
          <AlertDialogAction
            disabled={mutation.isPending}
            onClick={(event) => {
              event.preventDefault();
              mutation.mutate();
            }}
          >
            {mutation.isPending ? "正在删除" : copy.projects.deleteProject}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
