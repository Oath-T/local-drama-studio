import { Navigate, Route, Routes } from "react-router-dom";

import { AssetLibraryPage } from "./pages/asset-library-page";
import { CharacterDetailPage } from "./pages/character-detail-page";
import { CharacterLibraryPage } from "./pages/character-library-page";
import { GenerationCenterPage } from "./pages/generation-center-page";
import { MediaLibraryPage } from "./pages/media-library-page";
import { ProjectCanvasPage } from "./pages/project-canvas-page";
import { ProjectDetailPage } from "./pages/project-detail-page";
import { ProjectProductionPage } from "./pages/project-production-page";
import { ProjectSettingsPage } from "./pages/project-settings-page";
import { ProjectsPage } from "./pages/projects-page";
import { SceneDetailPage } from "./pages/scene-detail-page";
import { SceneLibraryPage } from "./pages/scene-library-page";
import { ShotWorkbenchPage } from "./pages/shot-workbench-page";
import { StudioWorkspacePage } from "./pages/studio-workspace-page";
import { TimelineExportPage } from "./pages/timeline-export-page";
import { WorkbenchPage } from "./pages/workbench-page";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/projects" replace />} />
      <Route path="/projects" element={<ProjectsPage />} />
      <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
      <Route path="/projects/:projectId/studio" element={<StudioWorkspacePage />} />
      <Route path="/projects/:projectId/canvas" element={<ProjectCanvasPage />} />
      <Route path="/projects/:projectId/assets" element={<AssetLibraryPage />} />
      <Route path="/projects/:projectId/characters" element={<CharacterLibraryPage />} />
      <Route
        path="/projects/:projectId/characters/:characterId"
        element={<CharacterDetailPage />}
      />
      <Route path="/projects/:projectId/scenes" element={<SceneLibraryPage />} />
      <Route path="/projects/:projectId/scenes/:sceneId" element={<SceneDetailPage />} />
      <Route path="/projects/:projectId/shots" element={<ShotWorkbenchPage />} />
      <Route path="/projects/:projectId/shots/:shotId" element={<ShotWorkbenchPage />} />
      <Route path="/projects/:projectId/production" element={<ProjectProductionPage />} />
      <Route path="/projects/:projectId/timeline" element={<TimelineExportPage />} />
      <Route path="/projects/:projectId/generation" element={<GenerationCenterPage />} />
      <Route path="/projects/:projectId/media" element={<MediaLibraryPage />} />
      <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
      <Route path="/characters" element={<WorkbenchPage section="characters" />} />
      <Route path="/scenes" element={<WorkbenchPage section="scenes" />} />
      <Route path="/shots" element={<WorkbenchPage section="shots" />} />
      <Route path="/tasks" element={<WorkbenchPage section="tasks" />} />
      <Route path="/media" element={<WorkbenchPage section="media" />} />
      <Route path="/settings" element={<WorkbenchPage section="settings" />} />
      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  );
}
