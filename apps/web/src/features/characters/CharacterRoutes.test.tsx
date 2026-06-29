import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import type { Character, CharacterLook, CharacterReference, MediaAsset } from "./types";

const projectId = "11111111-1111-4111-8111-111111111111";
const characterId = "22222222-2222-4222-8222-222222222222";
const lookId = "33333333-3333-4333-8333-333333333333";
const secondLookId = "33333333-3333-4333-8333-333333333334";
const referenceId = "55555555-5555-4555-8555-555555555555";
const secondReferenceId = "55555555-5555-4555-8555-555555555556";

const mediaAsset: MediaAsset = {
  id: "44444444-4444-4444-8444-444444444444",
  project_id: projectId,
  media_type: "image",
  original_filename: "reference.png",
  mime_type: "image/png",
  extension: "png",
  size_bytes: 1200,
  width: 800,
  height: 600,
  sha256: "abc123",
  thumbnail_url: "/api/media/44444444-4444-4444-8444-444444444444/thumbnail",
  content_url: "/api/media/44444444-4444-4444-8444-444444444444/content",
  created_at: "2026-06-28T10:00:00+00:00"
};

const secondMediaAsset: MediaAsset = {
  ...mediaAsset,
  id: "44444444-4444-4444-8444-444444444445",
  original_filename: "side.png",
  thumbnail_url: "/api/media/44444444-4444-4444-8444-444444444445/thumbnail",
  content_url: "/api/media/44444444-4444-4444-8444-444444444445/content"
};

const reference: CharacterReference = {
  id: referenceId,
  look_id: lookId,
  media_asset_id: mediaAsset.id,
  shot_type: "closeup",
  view_angle: "front",
  expression: "neutral",
  pose_type: "standing",
  custom_expression: null,
  custom_pose: null,
  tags: ["identity"],
  description: "front identity reference",
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

const secondReference: CharacterReference = {
  ...reference,
  id: secondReferenceId,
  media_asset_id: secondMediaAsset.id,
  description: "side reference",
  is_primary: false,
  is_identity_anchor: false,
  media_asset: secondMediaAsset
};

const analyzedReference: CharacterReference = {
  ...reference,
  shot_type: "unknown",
  view_angle: "unknown",
  expression: "unknown",
  pose_type: "unknown",
  tags: [],
  description: null,
  is_identity_anchor: false,
  analysis_status: "completed",
  analysis_suggestions: {
    schema_version: 1,
    shot_type: "closeup",
    view_angle: "front",
    expression: "neutral",
    custom_expression: null,
    pose_type: "standing",
    custom_pose: null,
    tags: ["正脸", "清晰"],
    description: "正面近景参考图",
    quality_notes: ["画面清晰"],
    identity_anchor_recommended: true,
    appearance_summary: "可见面部特征",
    costume_summary: "深色服装",
    hair_summary: "短发",
    confidence_notes: "基于可见画面判断"
  }
};

const look: CharacterLook = {
  id: lookId,
  character_id: characterId,
  name: "Base Look",
  description: null,
  costume_description: null,
  hair_description: null,
  makeup_description: null,
  condition_description: null,
  prompt_appearance: null,
  is_default: true,
  reference_count: 2,
  primary_reference: reference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const secondLook: CharacterLook = {
  ...look,
  id: secondLookId,
  name: "Night Look",
  is_default: false,
  reference_count: 0,
  primary_reference: null
};

const character: Character = {
  id: characterId,
  project_id: projectId,
  name: "Lin Zhixia",
  aliases: null,
  role_type: "protagonist",
  description: "Lead character",
  appearance_description: null,
  personality_description: null,
  prompt_identity: null,
  notes: null,
  default_look: look,
  look_count: 2,
  reference_count: 2,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

interface MockOptions {
  characters?: Character[];
  character?: Character;
  looks?: CharacterLook[];
  references?: CharacterReference[];
  failLastLookDelete?: boolean;
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

function mockCharacterApi(options: MockOptions = {}) {
  const requests: Array<{ url: string; method: string; body?: string }> = [];
  const characters = options.characters ?? [options.character ?? character];
  const currentCharacter = options.character ?? character;
  const looks = options.looks ?? [look, secondLook];
  const references = options.references ?? [reference, secondReference];

  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    const body = typeof init?.body === "string" ? init.body : undefined;
    requests.push({ url, method, body });

    if (url === "/api/health") {
      return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    }
    if (url === `/api/projects/${projectId}`) {
      return jsonResponse({
        id: projectId,
        name: "Character Test Project",
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
    if (url === `/api/projects/${projectId}/characters` && method === "GET") {
      return jsonResponse({ items: characters, total: characters.length });
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}` && method === "GET") {
      return jsonResponse(currentCharacter);
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}` && method === "PATCH") {
      return jsonResponse(currentCharacter);
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}` && method === "DELETE") {
      return emptyResponse();
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}/looks` && method === "GET") {
      return jsonResponse({ items: looks, total: looks.length });
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}/looks` && method === "POST") {
      return jsonResponse(look);
    }
    if (url.includes(`/looks/${lookId}`) && url.endsWith("/set-default") && method === "POST") {
      return jsonResponse(look);
    }
    if (url.includes(`/looks/${secondLookId}`) && url.endsWith("/set-default") && method === "POST") {
      return jsonResponse(secondLook);
    }
    if (url.includes("/looks/") && !url.includes("/references") && method === "PATCH") {
      return jsonResponse(look);
    }
    if (url.includes("/looks/") && !url.includes("/references") && method === "DELETE") {
      if (options.failLastLookDelete) {
        return jsonResponse(
          {
            error: {
              code: "LAST_LOOK_DELETE_FORBIDDEN",
              message: "不能删除角色的最后一套造型。"
            }
          },
          400
        );
      }
      return emptyResponse();
    }
    if (url === `/api/projects/${projectId}/characters/${characterId}/looks/${lookId}/references`) {
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
          target_type: "character_reference",
          character_reference_id: referenceId,
          scene_reference_id: null,
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
        return jsonResponse({ error: { code: "CHARACTER_REFERENCE_NOT_FOUND", message: "not found" } }, 404);
      }
      return emptyResponse();
    }

    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });

  return { fetchMock, requests };
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

afterEach(() => {
  vi.restoreAllMocks();
});

describe("character routes", () => {
  it("renders the project character library route", async () => {
    mockCharacterApi();
    renderRoute(`/projects/${projectId}/characters`);

    expect(await screen.findByRole("heading", { name: "角色库" })).toBeInTheDocument();
    expect(await screen.findByText("Lin Zhixia")).toBeInTheDocument();
    expect(screen.getByText("Lead character")).toBeInTheDocument();
  });

  it("renders an empty character library state", async () => {
    mockCharacterApi({ characters: [] });
    renderRoute(`/projects/${projectId}/characters`);

    expect(await screen.findByText("当前项目还没有角色")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "新建角色" }).length).toBeGreaterThan(0);
  });

  it("shows the no-look empty state for a character without looks", async () => {
    mockCharacterApi({
      character: { ...character, default_look: null, look_count: 0, reference_count: 0 },
      looks: [],
      references: []
    });
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    expect(await screen.findByText("当前角色还没有造型")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "新建第一套造型" })).toBeInTheDocument();
  });

  it("edits a character and keeps the dialog form wired to PATCH", async () => {
    const user = userEvent.setup();
    const { requests } = mockCharacterApi();
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    await user.click(await screen.findByRole("button", { name: "编辑角色" }));
    const input = screen.getByLabelText("角色名称");
    await user.clear(input);
    await user.type(input, "林知夏");
    await user.click(screen.getByRole("button", { name: "编辑角色" }));

    expect(requests).toContainEqual(
      expect.objectContaining({
        url: `/api/projects/${projectId}/characters/${characterId}`,
        method: "PATCH",
        body: expect.stringContaining("林知夏")
      })
    );
  });

  it("deletes a character after Chinese confirmation", async () => {
    const user = userEvent.setup();
    const { requests } = mockCharacterApi();
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    await user.click(await screen.findByRole("button", { name: "删除角色" }));
    expect(screen.getByText(/确定删除角色“Lin Zhixia”吗/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "确认删除" }));

    expect(requests).toContainEqual(
      expect.objectContaining({
        url: `/api/projects/${projectId}/characters/${characterId}`,
        method: "DELETE"
      })
    );
  });

  it("supports look edit, default setting, delete confirmation, and last-look error copy", async () => {
    const user = userEvent.setup();
    const { requests } = mockCharacterApi({ looks: [look], failLastLookDelete: true });
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    expect((await screen.findAllByText("Base Look")).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "编辑造型" }));
    const lookNameInput = screen.getByLabelText("造型名称");
    await user.clear(lookNameInput);
    await user.type(lookNameInput, "通勤造型");
    await user.click(screen.getByRole("button", { name: "编辑造型" }));
    expect(requests.some((request) => request.method === "PATCH" && request.body?.includes("通勤造型"))).toBe(true);

    await user.click(screen.getByRole("button", { name: "删除造型" }));
    expect(screen.getAllByText("不能删除角色的最后一套造型。").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "确认删除" }));
    expect((await screen.findAllByText("不能删除角色的最后一套造型。")).length).toBeGreaterThan(0);
  });

  it("sets a non-default look as default", async () => {
    const user = userEvent.setup();
    const { requests } = mockCharacterApi();
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    await screen.findByText("Night Look");
    await user.click(screen.getByRole("button", { name: "设为默认造型" }));

    expect(requests).toContainEqual(
      expect.objectContaining({
        url: `/api/projects/${projectId}/characters/${characterId}/looks/${secondLookId}/set-default`,
        method: "POST"
      })
    );
  });

  it("edits reference metadata and handles primary, identity, delete, and preview actions", async () => {
    const user = userEvent.setup();
    const { requests } = mockCharacterApi();
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    expect((await screen.findAllByText("尚未分析")).length).toBeGreaterThan(0);
    expect(screen.queryByText("AI 建议")).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "查看原图" })[0]);
    expect((await screen.findAllByText("reference.png")).length).toBeGreaterThan(0);
    expect(screen.getByText("800 × 600")).toBeInTheDocument();
    expect(screen.queryByText(/projects\\|file:|relative_path|F:/i)).not.toBeInTheDocument();

    await user.keyboard("{Escape}");
    await user.click(screen.getAllByRole("button", { name: "编辑元数据" })[0]);
    const tagsInput = screen.getByLabelText("标签");
    await user.clear(tagsInput);
    await user.type(tagsInput, "正面, 身份");
    await user.click(screen.getByRole("button", { name: "编辑元数据" }));
    expect(requests.some((request) => request.method === "PATCH" && request.body?.includes("正面"))).toBe(true);

    await user.click(screen.getByRole("button", { name: "设为主图" }));
    expect(requests.some((request) => request.url.endsWith(`/${secondReferenceId}/set-primary`))).toBe(true);

    await user.click(screen.getAllByRole("button", { name: "取消身份基准" })[0]);
    expect(requests.some((request) => request.method === "PATCH" && request.body?.includes("is_identity_anchor"))).toBe(true);

    await user.click(screen.getAllByRole("button", { name: "删除参考图" })[0]);
    expect(screen.getByText(/确定删除参考图“reference.png”吗/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "确认删除" }));
    expect(requests.some((request) => request.method === "DELETE" && request.url.includes(referenceId))).toBe(true);
  });

  it("keeps the page structure after an API error", async () => {
    const user = userEvent.setup();
    mockCharacterApi({ failReferenceDelete: true });
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    expect(await screen.findByRole("heading", { name: "Lin Zhixia" })).toBeInTheDocument();
    expect(await screen.findByText("front identity reference")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "删除参考图" })[0]);
    await user.click(screen.getByRole("button", { name: "确认删除" }));

    expect(await screen.findByText("参考图不存在或已被删除。")).toBeInTheDocument();
    expect(screen.getByText("Lin Zhixia")).toBeInTheDocument();
    expect(screen.getAllByText("Base Look").length).toBeGreaterThan(0);
  });

  it("reviews completed vision suggestions without auto-accepting boolean fields", async () => {
    const user = userEvent.setup();
    const { requests } = mockCharacterApi({ references: [analyzedReference] });
    renderRoute(`/projects/${projectId}/characters/${characterId}`);

    await user.click(await screen.findByRole("button", { name: "查看建议" }));

    expect(await screen.findByRole("heading", { name: "视觉分析建议" })).toBeInTheDocument();
    expect(screen.getByText("正面近景参考图")).toBeInTheDocument();
    expect(screen.getByText("身份基准图")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "采纳选中字段" }));

    const confirmRequest = requests.find((request) => request.url.includes("/analysis/confirm"));
    expect(confirmRequest?.method).toBe("POST");
    expect(confirmRequest?.body).toContain("description");
    expect(confirmRequest?.body).not.toContain("is_identity_anchor");
  });
});
