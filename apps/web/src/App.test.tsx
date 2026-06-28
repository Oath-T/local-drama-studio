import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "./App";
import type {
  Character,
  CharacterLook,
  CharacterReference,
  MediaAsset
} from "./features/characters/types";
import type { Project } from "./features/projects/types";

const baseProject: Project = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "逆袭归来",
  description: "都市逆袭题材短剧",
  aspect_ratio: "9:16",
  default_style: "写实电影质感",
  default_language: "zh-CN",
  default_fps: 24,
  cover_image_path: null,
  created_at: "2026-06-27T10:00:00+00:00",
  updated_at: "2026-06-27T10:00:00+00:00"
};

const baseMediaAsset: MediaAsset = {
  id: "44444444-4444-4444-8444-444444444444",
  project_id: baseProject.id,
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

const baseReference: CharacterReference = {
  id: "33333333-3333-4333-8333-333333333333",
  look_id: "22222222-2222-4222-8222-222222222222",
  media_asset_id: baseMediaAsset.id,
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
  media_asset: baseMediaAsset,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const baseLook: CharacterLook = {
  id: baseReference.look_id,
  character_id: "11111111-2222-4333-8444-555555555555",
  name: "Base Look",
  description: null,
  costume_description: null,
  hair_description: null,
  makeup_description: null,
  condition_description: null,
  prompt_appearance: null,
  is_default: true,
  reference_count: 1,
  primary_reference: baseReference,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

const baseCharacter: Character = {
  id: baseLook.character_id,
  project_id: baseProject.id,
  name: "Lin Zhixia",
  aliases: null,
  role_type: "protagonist",
  description: "Lead character",
  appearance_description: null,
  personality_description: null,
  prompt_identity: null,
  notes: null,
  default_look: baseLook,
  look_count: 1,
  reference_count: 1,
  created_at: "2026-06-28T10:00:00+00:00",
  updated_at: "2026-06-28T10:00:00+00:00"
};

function renderApp(initialPath = "/projects") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false
      }
    }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
}

function mockProjectApi(initialProjects: Project[] = []) {
  let projects = [...initialProjects];
  let counter = 0;

  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";

    if (url === "/api/health") {
      return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    }

    if (url === "/api/projects" && method === "GET") {
      return jsonResponse({ items: projects, total: projects.length });
    }

    if (url === "/api/projects" && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as Partial<Project>;
      counter += 1;
      const project: Project = {
        ...baseProject,
        id: `11111111-1111-4111-8111-11111111111${counter}`,
        name: payload.name ?? "未命名项目",
        description: (payload.description as string | null | undefined) ?? null,
        aspect_ratio: payload.aspect_ratio ?? "9:16",
        default_style: (payload.default_style as string | null | undefined) ?? null,
        default_language: payload.default_language ?? "zh-CN",
        default_fps: payload.default_fps ?? 24,
        created_at: "2026-06-27T11:00:00+00:00",
        updated_at: "2026-06-27T11:00:00+00:00"
      };
      projects = [project, ...projects];
      return jsonResponse(project, 201);
    }

    const characterListMatch = url.match(/^\/api\/projects\/([^/]+)\/characters$/);
    if (characterListMatch && method === "GET") {
      return jsonResponse({ items: [baseCharacter], total: 1 });
    }

    const characterDetailMatch = url.match(
      /^\/api\/projects\/([^/]+)\/characters\/([^/]+)$/
    );
    if (characterDetailMatch && method === "GET") {
      return jsonResponse(baseCharacter);
    }

    const looksMatch = url.match(/^\/api\/projects\/([^/]+)\/characters\/([^/]+)\/looks$/);
    if (looksMatch && method === "GET") {
      return jsonResponse({ items: [baseLook], total: 1 });
    }

    const referencesMatch = url.match(
      /^\/api\/projects\/([^/]+)\/characters\/([^/]+)\/looks\/([^/]+)\/references$/
    );
    if (referencesMatch && method === "GET") {
      return jsonResponse({ items: [baseReference], total: 1 });
    }

    const detailMatch = url.match(/^\/api\/projects\/(.+)$/);
    if (detailMatch) {
      const projectId = detailMatch[1];
      const project = projects.find((item) => item.id === projectId);

      if (!project) {
        return jsonResponse(
          { error: { code: "PROJECT_NOT_FOUND", message: "项目不存在或已被删除。" } },
          404
        );
      }

      if (method === "GET") {
        return jsonResponse(project);
      }

      if (method === "PATCH") {
        const payload = JSON.parse(String(init?.body)) as Partial<Project>;
        const updatedProject = {
          ...project,
          ...payload,
          updated_at: "2026-06-27T12:00:00+00:00"
        };
        projects = projects.map((item) => (item.id === projectId ? updatedProject : item));
        return jsonResponse(updatedProject);
      }

      if (method === "DELETE") {
        projects = projects.filter((item) => item.id !== projectId);
        return Promise.resolve(new Response(null, { status: 204 }));
      }
    }

    return jsonResponse({ error: { code: "NOT_FOUND", message: "未找到接口。" } }, 404);
  });
}

describe("App", () => {
  it("renders an empty project list state in Chinese", async () => {
    mockProjectApi([]);
    renderApp();

    expect(await screen.findByText("当前还没有项目")).toBeInTheDocument();
    expect(screen.getByText("创建第一个短剧项目，开始管理角色、场景和镜头。")).toBeInTheDocument();
  });

  it("shows real project cards when projects exist", async () => {
    mockProjectApi([baseProject]);
    renderApp();

    expect(await screen.findByText("逆袭归来")).toBeInTheDocument();
    expect(screen.getByText("都市逆袭题材短剧")).toBeInTheDocument();
  });

  it("shows Chinese fields in the create project form", async () => {
    const user = userEvent.setup();
    mockProjectApi([]);
    renderApp();

    await user.click((await screen.findAllByRole("button", { name: "新建项目" }))[0]);

    expect(screen.getByLabelText("项目名称")).toBeInTheDocument();
    expect(screen.getByLabelText("项目简介")).toBeInTheDocument();
    expect(screen.getByText("画面比例")).toBeInTheDocument();
    expect(screen.getByText("默认内容语言")).toBeInTheDocument();
  });

  it("validates the create project form in Chinese", async () => {
    const user = userEvent.setup();
    mockProjectApi([]);
    renderApp();

    await user.click((await screen.findAllByRole("button", { name: "新建项目" }))[0]);
    await user.click(screen.getByRole("button", { name: "创建项目" }));

    expect(await screen.findByText("请输入项目名称")).toBeInTheDocument();
  });

  it("shows the project after a successful create", async () => {
    const user = userEvent.setup();
    mockProjectApi([]);
    renderApp();

    await user.click((await screen.findAllByRole("button", { name: "新建项目" }))[0]);
    await user.type(screen.getByLabelText("项目名称"), "新的短剧项目");
    await user.click(screen.getByRole("button", { name: "创建项目" }));

    expect(await screen.findByText("新的短剧项目")).toBeInTheDocument();
    expect(screen.getByText("项目已创建")).toBeInTheDocument();
  });

  it("loads existing values when editing a project", async () => {
    const user = userEvent.setup();
    mockProjectApi([baseProject]);
    renderApp();

    await screen.findByText("逆袭归来");
    await user.click(screen.getByRole("button", { name: "更多操作" }));
    await user.click(await screen.findByText("编辑"));

    expect(screen.getByDisplayValue("逆袭归来")).toBeInTheDocument();
    expect(screen.getByDisplayValue("都市逆袭题材短剧")).toBeInTheDocument();
  });

  it("requires Chinese confirmation before deleting a project", async () => {
    const user = userEvent.setup();
    mockProjectApi([baseProject]);
    renderApp();

    await screen.findByText("逆袭归来");
    await user.click(screen.getByRole("button", { name: "更多操作" }));
    await user.click(await screen.findByText("删除"));

    expect(screen.getAllByText("删除项目").length).toBeGreaterThan(0);
    expect(screen.getByText(/确定删除项目“逆袭归来”吗？/)).toBeInTheDocument();
  });

  it("shows a loading state", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise(() => {}));

    renderApp();

    expect(screen.getByLabelText("正在加载")).toBeInTheDocument();
  });

  it("shows a Chinese API failure state without breaking the page", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));
    renderApp();

    expect(await screen.findByText("项目数据加载失败，请稍后重试。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "项目" })).toBeInTheDocument();
  });

  it("shows project detail data from the backend", async () => {
    mockProjectApi([baseProject]);
    renderApp(`/projects/${baseProject.id}`);

    expect(await screen.findByRole("heading", { name: "逆袭归来" })).toBeInTheDocument();
    expect(screen.getByText("写实电影质感")).toBeInTheDocument();
    expect(screen.getAllByText("角色库").length).toBeGreaterThan(0);
    expect(screen.getAllByText("场景库").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "打开场景库" })).toHaveAttribute(
      "href",
      `/projects/${baseProject.id}/scenes`
    );
  });

  it("shows a Chinese 404 state for a missing project", async () => {
    mockProjectApi([]);
    renderApp("/projects/00000000-0000-4000-8000-000000000000");

    expect(await screen.findByText("项目不存在或已被删除")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "返回项目列表" }).length).toBeGreaterThan(0);
  });

  it("renders zh-CN as Simplified Chinese", async () => {
    mockProjectApi([baseProject]);
    renderApp();

    const card = await screen.findByText("逆袭归来");
    const article = card.closest("article");

    expect(article).not.toBeNull();
    expect(within(article as HTMLElement).getByText("简体中文")).toBeInTheDocument();
  });
});
