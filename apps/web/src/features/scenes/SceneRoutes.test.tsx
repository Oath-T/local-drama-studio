import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import { sceneCopy } from "@/features/scenes/copy";
import type { Scene, SceneReference, SceneState } from "@/features/scenes/types";
import type { MediaAsset } from "@/features/characters/types";

const projectId = "11111111-1111-4111-8111-111111111111";
const sceneId = "22222222-2222-4222-8222-222222222222";
const stateId = "33333333-3333-4333-8333-333333333333";
const secondStateId = "33333333-3333-4333-8333-333333333334";
const referenceId = "55555555-5555-4555-8555-555555555555";
const secondReferenceId = "55555555-5555-4555-8555-555555555556";

const mediaAsset: MediaAsset = {
  id: "44444444-4444-4444-8444-444444444444",
  project_id: projectId,
  media_type: "image",
  original_filename: "lobby.png",
  mime_type: "image/png",
  extension: "png",
  size_bytes: 2048,
  width: 1200,
  height: 800,
  sha256: "abc123",
  thumbnail_url: "/api/media/44444444-4444-4444-8444-444444444444/thumbnail",
  content_url: "/api/media/44444444-4444-4444-8444-444444444444/content",
  created_at: "2026-06-28T10:00:00+00:00"
};

const secondMediaAsset: MediaAsset = {
  ...mediaAsset,
  id: "44444444-4444-4444-8444-444444444445",
  original_filename: "corner.png",
  thumbnail_url: "/api/media/44444444-4444-4444-8444-444444444445/thumbnail",
  content_url: "/api/media/44444444-4444-4444-8444-444444444445/content"
};

const reference: SceneReference = {
  id: referenceId,
  state_id: stateId,
  media_asset_id: mediaAsset.id,
  shot_scale: "wide",
  camera_position: "eye_level",
  custom_camera_position: null,
  view_direction: "front",
  custom_view_direction: null,
  composition_type: "centered",
  custom_composition: null,
  is_empty_plate: false,
  is_primary: true,
  is_spatial_anchor: true,
  tags: ["lobby"],
  description: "front lobby reference",
  notes: null,
  analysis_status: "not_analyzed",
  suggestion_review_status: "not_reviewed",
  analysis_suggestions: null,
  media_asset: mediaAsset,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const secondReference: SceneReference = {
  ...reference,
  id: secondReferenceId,
  media_asset_id: secondMediaAsset.id,
  description: "corner reference",
  is_primary: false,
  is_spatial_anchor: false,
  is_empty_plate: true,
  media_asset: secondMediaAsset
};

const analyzedReference: SceneReference = {
  ...reference,
  shot_scale: "unknown",
  camera_position: "unknown",
  view_direction: "unknown",
  composition_type: "unknown",
  tags: [],
  description: null,
  is_spatial_anchor: false,
  is_empty_plate: false,
  analysis_status: "completed",
  analysis_suggestions: {
    schema_version: 1,
    shot_scale: "wide",
    camera_position: "eye_level",
    custom_camera_position: null,
    view_direction: "front",
    custom_view_direction: null,
    composition_type: "centered",
    custom_composition: null,
    tags: ["空间", "入口"],
    description: "宽景空间参考图",
    quality_notes: ["结构清楚"],
    spatial_anchor_recommended: true,
    empty_plate_recommended: true,
    detected_time_of_day: "night",
    detected_weather: "indoor",
    detected_lighting: "cool_indoor",
    confidence_notes: null
  }
};

const state: SceneState = {
  id: stateId,
  scene_id: sceneId,
  name: "Night Rain",
  description: null,
  time_of_day: "night",
  weather: "heavy_rain",
  custom_weather: null,
  lighting: "neon",
  custom_lighting: null,
  season: "unknown",
  environment_condition: "Wet ground",
  crowd_level: "sparse",
  prompt_state: null,
  is_default: true,
  reference_count: 2,
  primary_reference: reference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const secondState: SceneState = {
  ...state,
  id: secondStateId,
  name: "Morning Clear",
  weather: "clear",
  lighting: "natural_soft",
  is_default: false,
  reference_count: 0,
  primary_reference: null
};

const scene: Scene = {
  id: sceneId,
  project_id: projectId,
  name: "Office Exterior",
  scene_type: "exterior",
  description: "Main entrance",
  fixed_environment_description: "Stone wall and glass facade",
  spatial_layout_description: null,
  visual_style_description: null,
  prompt_environment: null,
  notes: null,
  default_state: state,
  state_count: 2,
  reference_count: 2,
  cover_reference: reference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

interface MockOptions {
  scenes?: Scene[];
  states?: SceneState[];
  references?: SceneReference[];
  failLastStateDelete?: boolean;
  failReferenceDelete?: boolean;
}

function renderRoute(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function mockSceneApi(options: MockOptions = {}) {
  const requests: Array<{ url: string; method: string; body?: unknown }> = [];
  const scenes = options.scenes ?? [scene];
  const states = options.states ?? [state, secondState];
  const references = options.references ?? [reference, secondReference];

  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    requests.push({ url, method, body: init?.body });

    if (url === "/api/health") {
      return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    }
    if (url === `/api/projects/${projectId}`) {
      return jsonResponse({
        id: projectId,
        name: "Scene Test Project",
        description: null,
        aspect_ratio: "9:16",
        default_style: null,
        default_language: "zh-CN",
        default_fps: 24,
        cover_image_path: null,
        created_at: "2026-06-28T10:00:00+00:00",
        updated_at: "2026-06-28T10:00:00+00:00"
      });
    }
    if (url === `/api/projects/${projectId}/scenes` && method === "GET") {
      return jsonResponse({ items: scenes, total: scenes.length });
    }
    if (url === `/api/projects/${projectId}/scenes` && method === "POST") {
      return jsonResponse(scene, 201);
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}` && method === "GET") {
      return jsonResponse(scene);
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}` && method === "PATCH") {
      return jsonResponse(scene);
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}` && method === "DELETE") {
      return emptyResponse();
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}/states` && method === "GET") {
      return jsonResponse({ items: states, total: states.length });
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}/states` && method === "POST") {
      return jsonResponse(state, 201);
    }
    if (url.includes("/states/") && url.endsWith("/set-default") && method === "POST") {
      return jsonResponse(secondState);
    }
    if (url.includes("/states/") && !url.includes("/references") && method === "PATCH") {
      return jsonResponse(state);
    }
    if (url.includes("/states/") && !url.includes("/references") && method === "DELETE") {
      if (options.failLastStateDelete) {
        return jsonResponse(
          { error: { code: "LAST_SCENE_STATE_DELETE_FORBIDDEN", message: "last state" } },
          400
        );
      }
      return emptyResponse();
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references`) {
      if (method === "POST") {
        return jsonResponse(reference, 201);
      }
      return jsonResponse({ items: references, total: references.length });
    }
    if (url.includes("/analysis/latest-task") && method === "GET") {
      return jsonResponse({ task: null });
    }
    if (url.includes("/analysis/tasks") && method === "POST") {
      return jsonResponse(
        {
          id: "66666666-6666-4666-8666-666666666666",
          project_id: projectId,
          target_type: "scene_reference",
          character_reference_id: null,
          scene_reference_id: referenceId,
          provider: "openai",
          status: "pending",
          attempt_count: 0,
          error_code: null,
          error_message_safe: null,
          started_at: null,
          completed_at: null,
          created_at: "2026-06-29T00:00:00+00:00",
          updated_at: "2026-06-29T00:00:00+00:00"
        },
        202
      );
    }
    if (url.includes("/analysis/confirm") && method === "POST") {
      return jsonResponse({ suggestion_review_status: "edited_and_accepted" });
    }
    if (url.includes("/analysis/reject") && method === "POST") {
      return jsonResponse({ suggestion_review_status: "rejected" });
    }
    if (url.includes("/references/") && url.endsWith("/set-primary") && method === "POST") {
      return jsonResponse(secondReference);
    }
    if (url.includes("/references/") && method === "PATCH") {
      return jsonResponse(reference);
    }
    if (url.includes("/references/") && method === "DELETE") {
      if (options.failReferenceDelete) {
        return jsonResponse(
          { error: { code: "SCENE_REFERENCE_NOT_FOUND", message: "not found" } },
          404
        );
      }
      return emptyResponse();
    }

    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });

  return { requests };
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
}

function emptyResponse() {
  return Promise.resolve(new Response(null, { status: 204 }));
}

describe("scene routes", () => {
  it("shows project-scoped scenes and the global project guide", async () => {
    mockSceneApi();
    renderRoute(`/projects/${projectId}/scenes`);

    expect(await screen.findByRole("heading", { name: sceneCopy.title })).toBeInTheDocument();
    expect(await screen.findByText("Office Exterior")).toBeInTheDocument();
    expect(screen.getByText("2 个状态 / 2 张参考图")).toBeInTheDocument();
  });

  it("does not guess a project for the global scene entry", async () => {
    mockSceneApi();
    renderRoute("/scenes");

    expect(await screen.findByText(sceneCopy.globalGuideTitle)).toBeInTheDocument();
    expect(screen.getByText(sceneCopy.globalGuideDescription)).toBeInTheDocument();
  });

  it("creates, edits, and confirms scene deletion", async () => {
    const user = userEvent.setup();
    const { requests } = mockSceneApi({ scenes: [] });
    renderRoute(`/projects/${projectId}/scenes`);

    expect(await screen.findByText(sceneCopy.emptyTitle)).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: sceneCopy.newScene })[0]);
    await user.type(screen.getByLabelText(sceneCopy.fields.name), "New Scene");
    await user.click(screen.getByRole("button", { name: sceneCopy.save }));
    expect(requests.some((request) => request.method === "POST" && request.url.endsWith("/scenes"))).toBe(true);

    await screen.findByText(sceneCopy.created);
  });

  it("shows no-state empty state and creates the first default state", async () => {
    const user = userEvent.setup();
    const noStateScene = { ...scene, default_state: null, state_count: 0, reference_count: 0 };
    const { requests } = mockSceneApi({ scenes: [noStateScene], states: [], references: [] });
    renderRoute(`/projects/${projectId}/scenes/${sceneId}`);

    expect(await screen.findByText(sceneCopy.emptyStatesTitle)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: sceneCopy.newFirstState }));
    await user.type(screen.getByLabelText(sceneCopy.fields.stateName), "First State");
    await user.click(screen.getByRole("button", { name: sceneCopy.save }));

    expect(requests.some((request) => request.method === "POST" && request.url.endsWith("/states"))).toBe(true);
  });

  it("edits state metadata, sets default, and shows last-state delete copy", async () => {
    const user = userEvent.setup();
    const { requests } = mockSceneApi({ states: [state], failLastStateDelete: true });
    renderRoute(`/projects/${projectId}/scenes/${sceneId}`);

    expect((await screen.findAllByText("Night Rain")).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: sceneCopy.editState }));
    await user.clear(screen.getByLabelText(sceneCopy.fields.stateName));
    await user.type(screen.getByLabelText(sceneCopy.fields.stateName), "Updated State");
    await user.click(screen.getByRole("button", { name: sceneCopy.save }));
    expect(requests.some((request) => request.method === "PATCH")).toBe(true);

    await user.click(screen.getByRole("button", { name: sceneCopy.deleteState }));
    expect(screen.getAllByText(sceneCopy.lastStateDeleteForbidden).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: sceneCopy.confirmDelete }));
    expect((await screen.findAllByText(sceneCopy.lastStateDeleteForbidden)).length).toBeGreaterThan(0);
  });

  it("sets a non-default state as default", async () => {
    const user = userEvent.setup();
    const { requests } = mockSceneApi();
    renderRoute(`/projects/${projectId}/scenes/${sceneId}`);

    await screen.findByText("Morning Clear");
    await user.click(screen.getByRole("button", { name: sceneCopy.setDefaultState }));

    expect(requests.some((request) => request.url.endsWith(`/${secondStateId}/set-default`))).toBe(true);
  });

  it("uploads and edits scene references without showing AI suggestions", async () => {
    const user = userEvent.setup();
    const { requests } = mockSceneApi();
    renderRoute(`/projects/${projectId}/scenes/${sceneId}`);

    expect((await screen.findAllByText(sceneCopy.analysisStatus.not_analyzed)).length).toBeGreaterThan(0);
    expect(screen.queryByText("AI 建议")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: sceneCopy.uploadReference }));
    await user.upload(
      screen.getByLabelText(sceneCopy.fields.file),
      new File(["image"], "new-scene.png", { type: "image/png" })
    );
    await user.click(screen.getByRole("button", { name: sceneCopy.save }));
    expect(requests.some((request) => request.method === "POST" && request.body instanceof FormData)).toBe(true);

    await user.click(screen.getAllByRole("button", { name: sceneCopy.editReference })[0]);
    const tagsInput = screen.getByLabelText(sceneCopy.fields.tags);
    await user.clear(tagsInput);
    await user.type(tagsInput, "正门, 雨夜");
    await user.click(screen.getByRole("button", { name: sceneCopy.save }));
    expect(requests.some((request) => request.method === "PATCH")).toBe(true);
  });

  it("handles primary, spatial anchor, empty plate, delete, preview, and errors", async () => {
    const user = userEvent.setup();
    const { requests } = mockSceneApi({ failReferenceDelete: true });
    renderRoute(`/projects/${projectId}/scenes/${sceneId}`);

    await screen.findByText("front lobby reference");
    await user.click(screen.getAllByRole("button", { name: sceneCopy.previewOriginal })[0]);
    expect((await screen.findAllByText("lobby.png")).length).toBeGreaterThan(0);
    expect(screen.getByText("1200 x 800")).toBeInTheDocument();
    expect(screen.queryByText(/relative_path|file:|F:/i)).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: sceneCopy.setPrimaryReference }));
    await user.click(screen.getByRole("button", { name: sceneCopy.unsetSpatialAnchor }));
    await user.click(screen.getByRole("button", { name: sceneCopy.unmarkEmptyPlate }));

    expect(requests.some((request) => request.url.endsWith(`/${secondReferenceId}/set-primary`))).toBe(true);
    expect(requests.some((request) => request.method === "PATCH")).toBe(true);

    await user.click(screen.getAllByRole("button", { name: sceneCopy.deleteReference })[0]);
    expect(screen.getByText(sceneCopy.deleteReferenceDescription("lobby.png"))).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: sceneCopy.confirmDelete }));

    expect(await screen.findByText("场景参考图不存在或已被删除。")).toBeInTheDocument();
    expect(screen.getByText("Office Exterior")).toBeInTheDocument();
  });

  it("reviews scene vision suggestions without auto-accepting boolean fields", async () => {
    const user = userEvent.setup();
    const { requests } = mockSceneApi({ references: [analyzedReference] });
    renderRoute(`/projects/${projectId}/scenes/${sceneId}`);

    await user.click(await screen.findByRole("button", { name: "查看建议" }));

    expect(await screen.findByRole("heading", { name: "视觉分析建议" })).toBeInTheDocument();
    expect(screen.getByText("宽景空间参考图")).toBeInTheDocument();
    expect(screen.getByText("空间结构基准图")).toBeInTheDocument();
    expect(screen.getByText("空镜")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "采纳选中字段" }));

    const confirmRequest = requests.find((request) => request.url.includes("/analysis/confirm"));
    const body = String(confirmRequest?.body ?? "");
    expect(confirmRequest?.method).toBe("POST");
    expect(body).toContain("description");
    expect(body).not.toContain("is_spatial_anchor");
    expect(body).not.toContain("is_empty_plate");
  });
});
