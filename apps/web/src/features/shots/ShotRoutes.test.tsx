import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import type { Character, CharacterLook, CharacterReference, MediaAsset } from "@/features/characters/types";
import type { Scene, SceneReference, SceneState } from "@/features/scenes/types";
import { shotCopy } from "./copy";
import type { Shot } from "./types";

const projectId = "11111111-1111-4111-8111-111111111111";
const shotId = "22222222-2222-4222-8222-222222222222";
const characterId = "33333333-3333-4333-8333-333333333333";
const lookId = "44444444-4444-4444-8444-444444444444";
const characterReferenceId = "55555555-5555-4555-8555-555555555555";
const sceneId = "66666666-6666-4666-8666-666666666666";
const stateId = "77777777-7777-4777-8777-777777777777";
const sceneReferenceId = "88888888-8888-4888-8888-888888888888";
const secondSceneId = "12121212-1212-4121-8121-121212121212";
const secondStateId = "13131313-1313-4131-8131-131313131313";
const secondCharacterId = "14141414-1414-4141-8141-141414141414";
const secondLookId = "15151515-1515-4151-8151-151515151515";

const mediaAsset: MediaAsset = {
  id: "99999999-9999-4999-8999-999999999999",
  project_id: projectId,
  media_type: "image",
  original_filename: "reference.png",
  mime_type: "image/png",
  extension: "png",
  size_bytes: 1200,
  width: 800,
  height: 600,
  sha256: "abc123",
  thumbnail_url: "/api/media/99999999-9999-4999-8999-999999999999/thumbnail",
  content_url: "/api/media/99999999-9999-4999-8999-999999999999/content",
  created_at: "2026-06-28T10:00:00+00:00"
};

const characterReference: CharacterReference = {
  id: characterReferenceId,
  look_id: lookId,
  media_asset_id: mediaAsset.id,
  shot_type: "closeup",
  view_angle: "front",
  expression: "neutral",
  pose_type: "standing",
  custom_expression: null,
  custom_pose: null,
  tags: ["identity"],
  description: "front identity",
  notes: null,
  is_primary: true,
  is_identity_anchor: true,
  analysis_status: "not_analyzed",
  suggestion_review_status: "not_reviewed",
  analysis_suggestions: null,
  media_asset: mediaAsset,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const look: CharacterLook = {
  id: lookId,
  character_id: characterId,
  name: "基础造型",
  description: null,
  costume_description: null,
  hair_description: null,
  makeup_description: null,
  condition_description: null,
  prompt_appearance: null,
  is_default: true,
  reference_count: 1,
  primary_reference: characterReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const character: Character = {
  id: characterId,
  project_id: projectId,
  name: "林知夏",
  aliases: null,
  role_type: "protagonist",
  description: null,
  appearance_description: null,
  personality_description: null,
  prompt_identity: null,
  notes: null,
  default_look: look,
  look_count: 1,
  reference_count: 1,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const sceneReference: SceneReference = {
  id: sceneReferenceId,
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
  description: "lobby",
  notes: null,
  analysis_status: "not_analyzed",
  suggestion_review_status: "not_reviewed",
  analysis_suggestions: null,
  media_asset: mediaAsset,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const state: SceneState = {
  id: stateId,
  scene_id: sceneId,
  name: "夜雨",
  description: null,
  time_of_day: "night",
  weather: "heavy_rain",
  custom_weather: null,
  lighting: "neon",
  custom_lighting: null,
  season: "unknown",
  environment_condition: null,
  crowd_level: "sparse",
  prompt_state: null,
  is_default: true,
  reference_count: 1,
  primary_reference: sceneReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const scene: Scene = {
  id: sceneId,
  project_id: projectId,
  name: "办公楼外",
  scene_type: "exterior",
  description: null,
  fixed_environment_description: null,
  spatial_layout_description: null,
  visual_style_description: null,
  prompt_environment: null,
  notes: null,
  default_state: state,
  state_count: 1,
  reference_count: 1,
  cover_reference: sceneReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const secondState: SceneState = {
  ...state,
  id: secondStateId,
  scene_id: secondSceneId,
  name: "Second State",
  primary_reference: null,
  reference_count: 0
};

const secondScene: Scene = {
  ...scene,
  id: secondSceneId,
  name: "Warehouse",
  default_state: secondState,
  cover_reference: null,
  reference_count: 0
};

const secondLook: CharacterLook = {
  ...look,
  id: secondLookId,
  character_id: secondCharacterId,
  name: "Noir Look",
  primary_reference: null,
  reference_count: 0
};

const secondCharacter: Character = {
  ...character,
  id: secondCharacterId,
  name: "Second Character",
  default_look: secondLook,
  look_count: 1,
  reference_count: 0
};

const shot: Shot = {
  id: shotId,
  project_id: projectId,
  name: "镜头一",
  order_index: 1,
  story_description: null,
  visual_description: "林知夏走进雨夜。",
  dialogue: null,
  action_summary: null,
  duration_seconds: 3,
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
  scene_id: sceneId,
  scene_state_id: stateId,
  scene: { id: sceneId, name: scene.name },
  scene_state: { id: stateId, name: state.name },
  notes: null,
  readiness_status: "basic_ready",
  missing_items: ["character_references", "scene_references"],
  character_count: 1,
  reference_count: 0,
  characters: [
    {
      id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      shot_id: shotId,
      character_id: characterId,
      character_name: character.name,
      look_id: lookId,
      look_name: look.name,
      action_description: null,
      expression_description: null,
      position_description: null,
      is_primary_subject: true,
      order_index: 1,
      notes: null,
      created_at: "2026-06-28T10:00:00+00:00",
      updated_at: "2026-06-28T10:00:00+00:00"
    }
  ],
  references: [],
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

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

function mockShotApi(
  options: {
    shots?: Shot[];
    scenes?: Scene[];
    characters?: Character[];
    statesByScene?: Record<string, SceneState[]>;
    failReference?: boolean;
    failScenes?: boolean;
    failCharacters?: boolean;
    failShotUpdate?: boolean;
  } = {}
) {
  const requests: Array<{ url: string; method: string; body?: string }> = [];
  let shots = options.shots ?? [shot];
  const scenes = options.scenes ?? [scene];
  const characters = options.characters ?? [character];
  const statesByScene = options.statesByScene ?? { [sceneId]: [state] };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? init.body : undefined;
    requests.push({ url, method, body });

    if (url === "/api/health") return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    if (url === `/api/projects/${projectId}`) {
      return jsonResponse({
        id: projectId,
        name: "测试项目",
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
    if (url === `/api/projects/${projectId}/shots` && method === "GET") {
      return jsonResponse({ items: shots, total: shots.length });
    }
    if (url === `/api/projects/${projectId}/shots` && method === "POST") {
      const created = { ...shot, id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", name: "镜头 1" };
      shots = [created];
      return jsonResponse(created, 201);
    }
    if (url.startsWith(`/api/projects/${projectId}/shots/`) && method === "GET" && !url.includes("/characters") && !url.includes("/references")) {
      const id = url.split("/shots/")[1];
      return jsonResponse(shots.find((item) => item.id === id) ?? shot);
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}` && method === "PATCH") {
      if (options.failShotUpdate) {
        return jsonResponse(
          { error: { code: "SHOT_DURATION_SECONDS_POSITIVE", message: "invalid duration" } },
          422
        );
      }
      return jsonResponse({ ...shot, ...(body ? JSON.parse(body) : {}) });
    }
    if (url === `/api/projects/${projectId}/shots/${shotId}` && method === "DELETE") return emptyResponse();
    if (url.endsWith("/move") && method === "POST") return jsonResponse(shot);
    if (url.endsWith("/duplicate") && method === "POST") return jsonResponse({ ...shot, id: "copy", name: "镜头一 - 副本" });
    if (url === `/api/projects/${projectId}/shots/${shotId}/characters` && method === "GET") return jsonResponse({ items: shot.characters, total: 1 });
    if (url === `/api/projects/${projectId}/shots/${shotId}/characters` && method === "POST") return jsonResponse(shot.characters[0], 201);
    if (url.includes("/characters/") && method === "PATCH") return jsonResponse(shot.characters[0]);
    if (url.includes("/characters/") && method === "DELETE") return emptyResponse();
    if (url === `/api/projects/${projectId}/shots/${shotId}/references` && method === "GET") return jsonResponse({ items: shot.references, total: 0 });
    if (url === `/api/projects/${projectId}/shots/${shotId}/references` && method === "POST") {
      if (options.failReference) return jsonResponse({ error: { code: "SHOT_REFERENCE_ALREADY_BOUND", message: "duplicate" } }, 409);
      return jsonResponse({ ...shot.references[0], id: "new-ref" }, 201);
    }
    if (url.includes("/references/") && method === "DELETE") return emptyResponse();
    if (url.includes("/references/") && method === "PATCH") return jsonResponse(shot.references[0]);
    if (url === `/api/projects/${projectId}/characters`) {
      if (options.failCharacters) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      return jsonResponse({ items: characters, total: characters.length });
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}/looks`) return jsonResponse({ items: [look], total: 1 });
    if (url === `/api/projects/${projectId}/characters/${secondCharacterId}/looks`) return jsonResponse({ items: [secondLook], total: 1 });
    if (url === `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references`) return jsonResponse({ items: [characterReference], total: 1 });
    if (url === `/api/projects/${projectId}/scenes`) {
      if (options.failScenes) return jsonResponse({ error: { code: "TEST_ERROR", message: "failed" } }, 500);
      return jsonResponse({ items: scenes, total: scenes.length });
    }
    if (url.startsWith(`/api/projects/${projectId}/scenes/`) && url.endsWith("/states")) {
      const id = url.split("/scenes/")[1].split("/states")[0];
      const items = statesByScene[id] ?? [];
      return jsonResponse({ items, total: items.length });
    }
    if (url === `/api/projects/${projectId}/scenes/${sceneId}/states/${stateId}/references`) return jsonResponse({ items: [sceneReference], total: 1 });
    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });
  return { requests };
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

function emptyResponse() {
  return Promise.resolve(new Response(null, { status: 204 }));
}

describe("shot workbench routes", () => {
  it("renders a global project guide without guessing project", async () => {
    mockShotApi();
    renderRoute("/shots");

    expect(await screen.findByText("请先选择一个项目")).toBeInTheDocument();
  });

  it("renders empty state and creates the first shot", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ shots: [] });
    renderRoute(`/projects/${projectId}/shots`);

    expect(await screen.findByText("当前项目还没有镜头")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "新建镜头" })[0]);

    expect(requests.some((request) => request.method === "POST" && request.url.endsWith("/shots"))).toBe(true);
  });

  it("renders the three-panel workbench and saves shot edits", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByRole("heading", { name: "镜头工作台" })).toBeInTheDocument();
    expect(await screen.findByText("镜头列表")).toBeInTheDocument();
    expect(await screen.findByText("镜头信息")).toBeInTheDocument();
    expect(await screen.findByText("人物参考")).toBeInTheDocument();
    await user.clear(screen.getByLabelText("镜头名称"));
    await user.type(screen.getByLabelText("镜头名称"), "雨夜入场");
    await user.click(screen.getByRole("button", { name: "保存镜头" }));

    expect(requests.some((request) => request.method === "PATCH" && request.body?.includes("雨夜入场"))).toBe(true);
  });

  it("submits empty duration as null and allows positive duration", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const durationInput = await screen.findByLabelText(shotCopy.fields.duration);
    await user.clear(durationInput);
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" && request.body?.includes('"duration_seconds":null')
        )
      ).toBe(true);
    });

    await user.clear(durationInput);
    await user.type(durationInput, "4.5");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" && request.body?.includes('"duration_seconds":4.5')
        )
      ).toBe(true);
    });
  });

  it("rejects zero and negative duration before sending a save request", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi();
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const durationInput = await screen.findByLabelText(shotCopy.fields.duration);
    await user.clear(durationInput);
    await user.type(durationInput, "0");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    expect(await screen.findByText("预计时长必须大于 0 秒")).toBeInTheDocument();
    expect(requests.some((request) => request.method === "PATCH")).toBe(false);

    await user.clear(durationInput);
    await user.type(durationInput, "-1");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    expect(await screen.findByText("预计时长必须大于 0 秒")).toBeInTheDocument();
    expect(requests.some((request) => request.method === "PATCH")).toBe(false);
  });

  it("keeps form input and does not show success when duration validation fails from the API", async () => {
    const user = userEvent.setup();
    mockShotApi({ failShotUpdate: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    const nameInput = await screen.findByLabelText(shotCopy.fields.name);
    const durationInput = screen.getByLabelText(shotCopy.fields.duration);
    await user.clear(nameInput);
    await user.type(nameInput, "保留输入");
    await user.clear(durationInput);
    await user.type(durationInput, "5");
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    expect(await screen.findByText("预计时长必须大于 0 秒。")).toBeInTheDocument();
    expect(nameInput).toHaveValue("保留输入");
    expect(durationInput).toHaveValue(5);
    expect(screen.queryByText("镜头已保存")).not.toBeInTheDocument();
  });

  it("opens scene select, filters states by selected scene, and submits scene ids", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({
      scenes: [scene, secondScene],
      statesByScene: { [sceneId]: [state], [secondSceneId]: [secondState] }
    });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.sections.scene)).toBeInTheDocument();
    const sceneSelect = screen.getByRole("combobox", { name: shotCopy.fields.scene });
    await user.click(sceneSelect);
    await user.click(await screen.findByRole("option", { name: "Warehouse" }));

    const stateSelect = screen.getByRole("combobox", { name: shotCopy.fields.sceneState });
    await waitFor(() => expect(stateSelect).not.toBeDisabled());
    await user.click(stateSelect);
    expect(await screen.findByRole("option", { name: "Second State" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: state.name })).not.toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: "Second State" }));
    await user.click(screen.getByRole("button", { name: shotCopy.saveShot }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "PATCH" &&
            request.body?.includes(secondSceneId) &&
            request.body?.includes(secondStateId)
        )
      ).toBe(true);
    });
  });

  it("opens character select, filters looks by selected character, and adds the shot character", async () => {
    const user = userEvent.setup();
    const { requests } = mockShotApi({ characters: [character, secondCharacter] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.sections.characters)).toBeInTheDocument();
    const characterSelect = screen.getAllByRole("combobox", { name: shotCopy.fields.character })[0];
    await user.click(characterSelect);
    await user.click(await screen.findByRole("option", { name: "Second Character" }));

    const lookSelect = screen.getByRole("combobox", { name: shotCopy.fields.look });
    await user.click(lookSelect);
    expect(await screen.findByRole("option", { name: "Noir Look" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: look.name })).not.toBeInTheDocument();
    await user.click(screen.getByRole("option", { name: "Noir Look" }));
    await user.click(screen.getByRole("button", { name: "添加" }));

    await waitFor(() => {
      expect(
        requests.some(
          (request) =>
            request.method === "POST" &&
            request.url.endsWith(`/shots/${shotId}/characters`) &&
            request.body?.includes(secondCharacterId) &&
            request.body?.includes(secondLookId)
        )
      ).toBe(true);
    });
  });

  it("shows clear empty and error states for scene and character option requests", async () => {
    mockShotApi({ scenes: [], characters: [] });
    const { unmount } = renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.noScenes)).toBeInTheDocument();
    expect(await screen.findByText(shotCopy.noCharacters)).toBeInTheDocument();

    unmount();
    vi.restoreAllMocks();
    mockShotApi({ failScenes: true, failCharacters: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText(shotCopy.scenesLoadFailed)).toBeInTheDocument();
    expect(await screen.findByText(shotCopy.charactersLoadFailed)).toBeInTheDocument();
  });

  it("supports duplicate, move, and delete confirmation", async () => {
    const user = userEvent.setup();
    const secondShot = { ...shot, id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", name: "镜头二", order_index: 2 };
    const { requests } = mockShotApi({ shots: [shot, secondShot] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    await screen.findByText("镜头一");
    await user.click(screen.getAllByTitle("复制")[0]);
    await user.click(screen.getAllByTitle("下移")[0]);
    await user.click(screen.getAllByTitle("删除镜头")[0]);
    expect(screen.getByText(/确定删除镜头/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "确认删除" }));

    expect(requests.some((request) => request.url.endsWith("/duplicate"))).toBe(true);
    expect(requests.some((request) => request.url.endsWith("/move"))).toBe(true);
    expect(requests.some((request) => request.method === "DELETE" && request.url.includes(`/shots/${shotId}`))).toBe(true);
  });

  it("binds character and scene references and keeps page structure after API error", async () => {
    const user = userEvent.setup();
    mockShotApi({ failReference: true });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText("人物参考")).toBeInTheDocument();
    const referenceButtons = await screen.findAllByRole("button", { name: /身份/ });
    await user.click(referenceButtons[0]);

    expect(await screen.findByText("相同用途的参考图已经绑定。")).toBeInTheDocument();
    expect(screen.getByText("镜头列表")).toBeInTheDocument();
    expect(screen.getByText("镜头信息")).toBeInTheDocument();
  });

  it("keeps scene reference warning copy available for clearing incompatible bindings", async () => {
    const shotWithSceneRef = {
      ...shot,
      references: [
        {
          id: "scene-bound",
          shot_id: shot.id,
          reference_type: "scene" as const,
          character_reference_id: null,
          scene_reference_id: sceneReferenceId,
          shot_character_id: null,
          purpose: "environment",
          order_index: 1,
          notes: null,
          media_asset: mediaAsset,
          character_reference: null,
          scene_reference: sceneReference,
          created_at: "2026-06-28T10:00:00+00:00",
          updated_at: "2026-06-28T10:00:00+00:00"
        }
      ],
      reference_count: 1
    };
    mockShotApi({ shots: [shotWithSceneRef] });
    renderRoute(`/projects/${projectId}/shots/${shotId}`);

    expect(await screen.findByText("场景绑定")).toBeInTheDocument();
    expect(shotWithSceneRef.references[0].reference_type).toBe("scene");
  });
});
