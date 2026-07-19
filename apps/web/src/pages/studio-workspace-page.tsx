import { useParams } from "react-router-dom";

import { StatusMessage } from "@/components/ui/status-message";
import { StudioWorkspacePage as StudioWorkspace } from "@/features/studio-workspace/components/studio-workspace-page";

export function StudioWorkspacePage() {
  const { projectId = "" } = useParams();

  if (!projectId) {
    return <StatusMessage tone="error">请先选择项目。</StatusMessage>;
  }

  return <StudioWorkspace projectId={projectId} />;
}
