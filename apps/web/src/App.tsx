import { Navigate, Route, Routes } from "react-router-dom";

import { ProjectDetailPage } from "./pages/project-detail-page";
import { ProjectsPage } from "./pages/projects-page";
import { WorkbenchPage } from "./pages/workbench-page";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/projects" replace />} />
      <Route path="/projects" element={<ProjectsPage />} />
      <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
      <Route path="/characters" element={<WorkbenchPage section="characters" />} />
      <Route path="/scenes" element={<WorkbenchPage section="scenes" />} />
      <Route path="/shots" element={<WorkbenchPage section="shots" />} />
      <Route path="/tasks" element={<WorkbenchPage section="tasks" />} />
      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  );
}
