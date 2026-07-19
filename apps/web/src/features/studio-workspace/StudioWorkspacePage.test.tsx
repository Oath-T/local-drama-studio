import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { StudioWorkspacePage } from "@/features/studio-workspace/components/studio-workspace-page";
import { createDefaultStudioSession, getStudioSessionStorageKey } from "@/features/studio-workspace/session";
import type { Character } from "@/features/characters/types";
import type { Project } from "@/features/projects/types";
import type { Scene } from "@/features/scenes/types";
import type { Shot } from "@/features/shots/types";

const projectId = "8c6200f3-23b0-4af5-a4db-6a2bd9cd6702";

const project: Project = {
  id: projectId,
  name: "复仇赘婿",
  description: "本地短剧项目",
  aspect_ratio: "9:16",
  default_style: "写实电影感",
  default_language: "zh-CN",
  default_fps: 24,
  cover_image_path: null,
  created_at: "2026-07-18T00:00:00+00:00",
  updated_at: "2026-07-18T00:00:00+00:00"
};

const character: Character = {
  id: "character-1",
  project_id: projectId,
  name: "男主",
  aliases: null,
  role_type: "protagonist",
  description: null,
  appearance_description: null,
  personality_description: null,
  prompt_identity: null,
  notes: null,
  default_look: null,
  look_count: 1,
  reference_count: 2,
  created_at: "2026-07-18T00:00:00+00:00",
  updated_at: "2026-07-18T01:00:00+00:00"
};

const scene: Scene = {
  id: "scene-1",
  project_id: projectId,
  name: "会议室",
  scene_type: "interior",
  description: null,
  fixed_environment_description: null,
  spatial_layout_description: null,
  visual_style_description: null,
  prompt_environment: null,
  notes: null,
  default_state: null,
  state_count: 1,
  reference_count: 3,
  cover_reference: null,
  created_at: "2026-07-18T00:00:00+00:00",
  updated_at: "2026-07-18T01:10:00+00:00"
};

const shot: Shot = {
  id: "shot-1",
  project_id: projectId,
  name: "镜头1",
  order_index: 1,
  story_description: "男主推门进入会议室",
  visual_description: "会议室内所有人震惊回头",
  dialogue: null,
  action_summary: null,
  duration_seconds: 2,
  shot_scale: "medium",
  camera_height: "eye_level",
  custom_camera_height: null,
  camera_angle: "front",
  custom_camera_angle: null,
  composition_type: "centered",
  custom_composition: null,
  camera_movement: "static",
  custom_camera_movement: null,
  focal_subject: null,
  mood_description: null,
  scene_id: scene.id,
  scene_state_id: null,
  scene: { id: scene.id, name: scene.name },
  scene_state: null,
  notes: null,
  readiness_status: "asset_ready",
  missing_items: [],
  character_count: 1,
  reference_count: 1,
  characters: [],
  references: [],
  created_at: "2026-07-18T00:00:00+00:00",
  updated_at: "2026-07-18T01:20:00+00:00"
};

function LocationView() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
}

function mockStudioApi(options: { empty?: boolean; healthDown?: boolean; partialFailure?: boolean } = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    if (url === "/api/health") {
      if (options.healthDown) {
        return Promise.reject(new Error("offline"));
      }
      return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    }
    if (url === `/api/projects/${projectId}`) return jsonResponse(project);
    if (url === `/api/projects/${projectId}/characters`) {
      if (options.partialFailure) return jsonResponse({ error: { code: "FAILED" } }, 500);
      return jsonResponse({ items: options.empty ? [] : [character], total: options.empty ? 0 : 1 });
    }
    if (url === `/api/projects/${projectId}/scenes`) return jsonResponse({ items: options.empty ? [] : [scene], total: options.empty ? 0 : 1 });
    if (url === `/api/projects/${projectId}/shots`) return jsonResponse({ items: options.empty ? [] : [shot], total: options.empty ? 0 : 1 });
    if (url === `/api/projects/${projectId}/production-status`) {
      return jsonResponse({
        project_id: projectId,
        summary: { total_shots: options.empty ? 0 : 1, blocked: 0, in_progress: 1, ready_for_video: 0, completed: 0 },
        items: options.empty
          ? []
          : [
              {
                project_id: projectId,
                shot_id: shot.id,
                shot_name: shot.name,
                order_index: 1,
                overall_status: "in_progress",
                steps: {
                  assets: { status: "complete", character_count: 1, reference_count: 1, has_scene: true },
                  first_frame: {
                    status: "adopted",
                    task_id: "first-task",
                    adopted_output_id: "first-output",
                    adopted_media_asset_id: "media-1",
                    content_url: "/media/first"
                  },
                  end_frame: {
                    status: "not_created",
                    task_id: null,
                    adopted_output_id: null,
                    adopted_media_asset_id: null,
                    content_url: null
                  },
                  video: {
                    status: "not_created",
                    task_id: null,
                    adopted_output_id: null,
                    adopted_media_asset_id: null,
                    content_url: null,
                    has_start_frame: true,
                    has_end_frame: false
                  }
                },
                blockers: [],
                next_actions: [],
                continuity_candidate: null,
                updated_at: "2026-07-18T01:20:00+00:00"
              }
            ],
        total: options.empty ? 0 : 1
      });
    }
    if (url === `/api/projects/${projectId}/generation-tasks`) return jsonResponse({ items: [], total: 0 });
    if (url === `/api/projects/${projectId}/timeline`) {
      return jsonResponse({
        project_id: projectId,
        exportable: false,
        total_shots: options.empty ? 0 : 1,
        ready_clip_count: 0,
        missing_clip_count: options.empty ? 0 : 1,
        estimated_duration_seconds: 0,
        project_spec: { aspect_ratio: "9:16", default_fps: 24 },
        ffmpeg: { available: true, ffprobe_available: true, message: null },
        clips: [],
        blockers: []
      });
    }
    if (url === "/api/system/capabilities") {
      return jsonResponse({
        vision_analysis: { available: false, provider: "none" },
        keyframe_generation: { available: true, provider: "comfyui", status: "online" },
        video_generation: { available: false, provider: "comfyui", status: "unconfigured" }
      });
    }
    if (url === `/api/projects/${projectId}/video-workflows`) return jsonResponse({ items: [], total: 0 });
    return jsonResponse({ error: { code: "NOT_FOUND" } }, 404);
  });
}

function renderStudio(path = `/projects/${projectId}/studio`) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/projects/:projectId/studio" element={<StudioWorkspacePage projectId={projectId} />} />
          <Route path="*" element={<LocationView />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
  window.localStorage.clear();
  Object.defineProperty(window, "innerWidth", { configurable: true, value: 1440 });
  window.dispatchEvent(new Event("resize"));
});

describe("StudioWorkspacePage", () => {
  it("renders the formal Studio route and default start page", async () => {
    mockStudioApi();
    renderStudio();

    expect(await screen.findByRole("heading", { name: "复仇赘婿" })).toBeInTheDocument();
    expect(screen.getAllByText("生成尾帧").length).toBeGreaterThan(0);
    expect(screen.getByText("角色与造型")).toBeInTheDocument();
    expect(screen.getByText("打开现有工作流画布")).toHaveAttribute("href", `/projects/${projectId}/canvas?view=workflow`);
  });

  it("restores the last view from a valid project session", async () => {
    window.localStorage.setItem(
      getStudioSessionStorageKey(projectId),
      JSON.stringify({ ...createDefaultStudioSession(projectId), currentMode: "storyboard", currentView: "storyboard" })
    );
    mockStudioApi();
    renderStudio();

    expect(await screen.findByRole("heading", { name: "故事板" })).toBeInTheDocument();
  });

  it("falls back from a corrupted session and keeps project sessions isolated", async () => {
    window.localStorage.setItem(getStudioSessionStorageKey(projectId), "{bad json");
    window.localStorage.setItem(
      getStudioSessionStorageKey("other-project"),
      JSON.stringify({ ...createDefaultStudioSession("other-project"), currentView: "storyboard" })
    );
    mockStudioApi();
    renderStudio();

    expect(await screen.findByText("续作起点")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "故事板" })).not.toBeInTheDocument();
  });

  it("uses shotId URL context and ignores invalid params safely", async () => {
    mockStudioApi();
    const firstRender = renderStudio(`/projects/${projectId}/studio?shotId=${shot.id}&intent=inspect`);

    expect(await screen.findByText("镜头摘要")).toBeInTheDocument();
    expect(screen.getAllByText("镜头1").length).toBeGreaterThan(0);

    firstRender.unmount();
    window.localStorage.clear();
    vi.restoreAllMocks();
    mockStudioApi();
    renderStudio(`/projects/${projectId}/studio?entityType=prop&entityId=bad`);
    expect(await screen.findByText("已忽略无效的 Studio 上下文参数。")).toBeInTheDocument();
  });

  it("navigates from the primary recommendation and quick entries", async () => {
    const user = userEvent.setup();
    mockStudioApi({ empty: true });
    renderStudio();

    await user.click(await screen.findByRole("button", { name: "创建第一个角色" }));
    expect(screen.getByTestId("location")).toHaveTextContent(`/projects/${projectId}/characters`);
  });

  it("keeps the page usable during partial API failure and backend disconnection", async () => {
    mockStudioApi({ partialFailure: true, healthDown: true });
    renderStudio();

    expect((await screen.findAllByText("后端不可用")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("复仇赘婿")).length).toBeGreaterThan(0);
    expect(await screen.findByText("部分数据加载失败，已加载区域仍可继续使用。")).toBeInTheDocument();
    expect(screen.getByText("上下文面板")).toBeInTheDocument();
  });

  it("supports layout persistence, drawer closing and clearing workspace session", async () => {
    const user = userEvent.setup();
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 1024 });
    window.dispatchEvent(new Event("resize"));
    mockStudioApi();
    renderStudio();

    await user.click(await screen.findByRole("button", { name: "上下文" }));
    expect(screen.getByTestId("studio-formal-compact-drawer")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "关闭抽屉" }));
    expect(screen.queryByTestId("studio-formal-compact-drawer")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "清除工作现场" }));
    expect(screen.getByText("工作现场已清除。")).toBeInTheDocument();
  });
});
