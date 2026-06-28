import { Navigate, Route, Routes } from "react-router-dom";

import { CharacterDetailPage } from "./pages/character-detail-page";
import { CharacterLibraryPage } from "./pages/character-library-page";
import { ProjectDetailPage } from "./pages/project-detail-page";
import { ProjectsPage } from "./pages/projects-page";
import { SceneDetailPage } from "./pages/scene-detail-page";
import { SceneLibraryPage } from "./pages/scene-library-page";
import { WorkbenchPage } from "./pages/workbench-page";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/projects" replace />} />
      <Route path="/projects" element={<ProjectsPage />} />
      <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
      <Route path="/projects/:projectId/characters" element={<CharacterLibraryPage />} />
      <Route
        path="/projects/:projectId/characters/:characterId"
        element={<CharacterDetailPage />}
      />
      <Route path="/projects/:projectId/scenes" element={<SceneLibraryPage />} />
      <Route path="/projects/:projectId/scenes/:sceneId" element={<SceneDetailPage />} />
      <Route path="/characters" element={<WorkbenchPage section="characters" />} />
      <Route path="/scenes" element={<WorkbenchPage section="scenes" />} />
      <Route path="/shots" element={<WorkbenchPage section="shots" />} />
      <Route path="/tasks" element={<WorkbenchPage section="tasks" />} />
      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  );
}
