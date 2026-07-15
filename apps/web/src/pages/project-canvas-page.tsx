import { useParams } from "react-router-dom";

import { AppShell } from "@/components/layout/app-shell";
import { StatusMessage } from "@/components/ui/status-message";
import { ProjectCanvasWorkspace } from "@/features/project-canvas/components/project-canvas-workspace";

export function ProjectCanvasPage() {
  const { projectId = "" } = useParams();

  return (
    <AppShell>
      {projectId ? (
        <ProjectCanvasWorkspace projectId={projectId} />
      ) : (
        <StatusMessage tone="error">请先选择项目。</StatusMessage>
      )}
    </AppShell>
  );
}
