import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { StudioWorkspacePage } from "@/features/studio-workspace/components/studio-workspace-page";
import { createDefaultStudioSession, getStudioSessionStorageKey } from "@/features/studio-workspace/session";
import type { Project } from "@/features/projects/types";
import type { Shot } from "@/features/shots/types";

const projectId = "8c6200f3-23b0-4af5-a4db-6a2bd9cd6702";

const project: Project = {
  id: projectId,
  name: "复仇归来",
  description: "本地短剧项目",
  aspect_ratio: "9:16",
  default_style: "写实电影感",
  default_language: "zh-CN",
  default_fps: 24,
  cover_image_path: null,
  created_at: "2026-07-18T00:00:00+00:00",
  updated_at: "2026-07-18T00:00:00+00:00"
};

const shot: Shot = {
  id: "shot-1",
  project_id: projectId,
  name: "镜头 1",
  order_index: 1,
  story_description: "男主推门进入会议室",
  visual_description: "所有人震惊回头",
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
  scene_id: null,
  scene_state_id: null,
  scene: null,
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

function mockStudioApi(
  options: {
    empty?: boolean;
    healthDown?: boolean;
    productionFails?: boolean;
    videoStatus?: "not_created" | "missing_inputs" | "draft" | "ready" | "running" | "completed" | "adopted";
    videoAvailable?: boolean;
  } = {}
) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

    if (url === "/api/health") {
      if (options.healthDown) return Promise.reject(new Error("offline"));
      return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    }
    if (url === `/api/projects/${projectId}`) return jsonResponse(project);
    if (url === `/api/projects/${projectId}/shots`) {
      return jsonResponse({ items: options.empty ? [] : [shot], total: options.empty ? 0 : 1 });
    }
    if (url === `/api/projects/${projectId}/production-status`) {
      if (options.productionFails) return jsonResponse({ error: { code: "FAILED" } }, 500);
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
                    content_url: "/api/media/first"
                  },
                  end_frame: {
                    status: "completed",
                    task_id: "end-task",
                    adopted_output_id: null,
                    adopted_media_asset_id: null,
                    content_url: "/api/media/end"
                  },
                  video: {
                    status: options.videoStatus ?? "not_created",
                    task_id: null,
                    adopted_output_id: null,
                    adopted_media_asset_id: null,
                    content_url: null,
                    has_start_frame: true,
                    has_end_frame: false
                  }
                },
                blockers: options.videoStatus === "running" ? [] : [],
                next_actions: [],
                continuity_candidate: null,
                updated_at: "2026-07-18T01:20:00+00:00"
              }
            ],
        total: options.empty ? 0 : 1
      });
    }
    if (url === "/api/system/capabilities") {
      return jsonResponse({
        vision_analysis: { available: false, provider: "none" },
        keyframe_generation: { available: true, provider: "comfyui", status: "online" },
        video_generation: {
          available: options.videoAvailable ?? false,
          provider: "comfyui",
          status: options.videoAvailable ? "online" : "unconfigured"
        }
      });
    }

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
  window.localStorage.clear();
});

describe("StudioWorkspacePage", () => {
  it("renders a real storyboard without Demo shell copy", async () => {
    mockStudioApi();
    renderStudio();

    expect(await screen.findByRole("heading", { name: "故事板" })).toBeInTheDocument();
    expect((await screen.findAllByText("镜头 1")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("首帧已采用")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("尾帧待采用")).length).toBeGreaterThan(0);
    expect((await screen.findAllByText("视频能力不可用")).length).toBeGreaterThan(0);
    expect(screen.queryByText("故事板演示区域")).not.toBeInTheDocument();
    expect(screen.queryByText("开场 establishing shot")).not.toBeInTheDocument();
  });

  it("opens the existing shot generation workbench with Studio return context", async () => {
    const user = userEvent.setup();
    mockStudioApi({ videoAvailable: true });
    renderStudio();

    const card = await screen.findByTestId("studio-storyboard-card");
    await user.click(within(card).getByRole("button", { name: "打开生成" }));

    expect(screen.getByTestId("location")).toHaveTextContent(
      `/projects/${projectId}/shots/${shot.id}?intent=generate&returnTo=studio`
    );
  });

  it("restores the selected shot from simplified session and cleans missing ids", async () => {
    window.localStorage.setItem(
      getStudioSessionStorageKey(projectId),
      JSON.stringify({ ...createDefaultStudioSession(projectId), selectedShotId: "missing-shot" })
    );
    mockStudioApi();
    renderStudio();

    expect((await screen.findAllByText("镜头 1")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(window.localStorage.getItem(getStudioSessionStorageKey(projectId))).toContain('"selectedShotId":null');
    });
  });

  it("keeps the page useful when production status or health is unavailable", async () => {
    mockStudioApi({ healthDown: true, productionFails: true });
    renderStudio();

    expect((await screen.findAllByText("镜头 1")).length).toBeGreaterThan(0);
    expect(screen.getByText("后端不可用")).toBeInTheDocument();
    expect(screen.getByText("部分状态加载失败，已显示可用的真实镜头数据。")).toBeInTheDocument();
  });

  it("does not load timeline, full generation task, character, scene, or media records on first screen", async () => {
    const fetchSpy = mockStudioApi();
    renderStudio();

    await screen.findAllByText("镜头 1");
    const urls = fetchSpy.mock.calls.map(([input]) =>
      typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url
    );

    expect(urls).toContain(`/api/projects/${projectId}`);
    expect(urls).toContain(`/api/projects/${projectId}/shots`);
    expect(urls).toContain(`/api/projects/${projectId}/production-status`);
    expect(urls).toContain("/api/system/capabilities");
    expect(urls).toContain("/api/health");
    expect(urls.some((url) => url.includes("/timeline"))).toBe(false);
    expect(urls.some((url) => url.includes("/generation-tasks"))).toBe(false);
    expect(urls.some((url) => url.includes("/characters"))).toBe(false);
    expect(urls.some((url) => url.includes("/scenes"))).toBe(false);
    expect(urls.some((url) => url.includes("/media"))).toBe(false);
  });

  it("shows an empty state for projects without shots", async () => {
    mockStudioApi({ empty: true });
    renderStudio();

    expect(await screen.findByText("暂无镜头")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开镜头工作台" })).toHaveAttribute(
      "href",
      `/projects/${projectId}/shots`
    );
  });

  it("keeps real active and failed video states distinct", async () => {
    mockStudioApi({ videoStatus: "running", videoAvailable: false });
    renderStudio();

    expect((await screen.findAllByText("视频生成中")).length).toBeGreaterThan(0);
  });
});
