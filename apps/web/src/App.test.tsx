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

    const sceneListMatch = url.match(/^\/api\/projects\/([^/]+)\/scenes$/);
    if (sceneListMatch && method === "GET") {
      return jsonResponse({ items: [], total: 0 });
    }

    const shotListMatch = url.match(/^\/api\/projects\/([^/]+)\/shots$/);
    if (shotListMatch && method === "GET") {
      return jsonResponse({
        items: [
          {
            id: "77777777-7777-4777-8777-777777777777",
            project_id: shotListMatch[1],
            name: "开场镜头",
            order_index: 1,
            story_description: null,
            visual_description: "城市夜景",
            dialogue: null,
            action_summary: null,
            duration_seconds: 3,
            shot_scale: "wide",
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
            readiness_status: "basic_ready",
            missing_items: [],
            character_count: 1,
            reference_count: 2,
            characters: [],
            references: [],
            created_at: "2026-06-28T10:00:00+00:00",
            updated_at: "2026-06-28T11:00:00+00:00"
          }
        ],
        total: 1
      });
    }

    const generationTaskListMatch = url.match(/^\/api\/projects\/([^/]+)\/generation-tasks$/);
    if (generationTaskListMatch && method === "GET") {
      const projectId = generationTaskListMatch[1];
      return jsonResponse({
        items: [
          {
            task_type: "video",
            task_purpose: null,
            project_id: projectId,
            task_id: "88888888-8888-4888-8888-888888888888",
            task_name: "首尾帧视频",
            task_status: "ready",
            readiness_status: null,
            shot_id: "77777777-7777-4777-8777-777777777777",
            shot_name: "开场镜头",
            workflow_id: "video_wan22_14b_flf2v_v1",
            latest_run_id: "99999999-9999-4999-8999-999999999999",
            latest_run_number: 1,
            latest_run_status: "completed",
            run_count: 1,
            output_count: 1,
            has_outputs: true,
            has_selected_output: true,
            created_at: "2026-06-28T10:00:00+00:00",
            updated_at: "2026-06-28T12:00:00+00:00"
          }
        ],
        total: 1
      });
    }

    const productionStatusMatch = url.match(/^\/api\/projects\/([^/]+)\/production-status$/);
    if (productionStatusMatch && method === "GET") {
      const projectId = productionStatusMatch[1];
      return jsonResponse({
        project_id: projectId,
        summary: {
          total_shots: 1,
          blocked: 0,
          in_progress: 0,
          ready_for_video: 1,
          completed: 0
        },
        items: [
          {
            project_id: projectId,
            shot_id: "77777777-7777-4777-8777-777777777777",
            shot_name: "开场镜头",
            order_index: 1,
            overall_status: "ready_for_video",
            steps: {
              assets: {
                status: "complete",
                character_count: 1,
                reference_count: 2,
                has_primary_subject: true,
                has_scene: true,
                has_scene_state: true,
                scene_name: "会议室",
                scene_state_name: "夜晚",
                warnings: []
              },
              director_prompt: {
                status: "available",
                director_template_available: true,
                recommended_template_id: "enter_room_shock"
              },
              first_frame: {
                status: "adopted",
                task_id: "first-task",
                task_name: "首帧草稿",
                adopted_output_id: "first-output",
                adopted_media_asset_id: baseMediaAsset.id,
                content_url: baseMediaAsset.content_url
              },
              end_frame: {
                status: "adopted",
                task_id: "end-task",
                task_name: "尾帧草稿",
                adopted_output_id: "end-output",
                adopted_media_asset_id: baseMediaAsset.id,
                content_url: baseMediaAsset.content_url
              },
              video: {
                status: "missing_inputs",
                task_id: null,
                task_name: null,
                adopted_output_id: null,
                adopted_media_asset_id: null,
                content_url: null,
                has_start_frame: false,
                has_end_frame: false
              },
              final_adoption: {
                status: "missing_inputs",
                task_id: null,
                task_name: null,
                adopted_output_id: null,
                adopted_media_asset_id: null,
                content_url: null,
                has_start_frame: false,
                has_end_frame: false
              }
            },
            blockers: ["视频任务缺少首帧或尾帧输入"],
            next_actions: ["fill_video_inputs"],
            continuity_candidate: null,
            updated_at: "2026-06-28T12:00:00+00:00"
          }
        ],
        total: 1
      });
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

  it("hides E2E projects from the normal project list and opens the Studio route", async () => {
    const user = userEvent.setup();
    const e2eProject = {
      ...baseProject,
      id: "22222222-2222-4222-8222-222222222222",
      name: "E2E_SPRINT_27C"
    };
    mockProjectApi([baseProject, e2eProject]);
    renderApp();

    expect(await screen.findByText("逆袭归来")).toBeInTheDocument();
    expect(screen.queryByText("E2E_SPRINT_27C")).not.toBeInTheDocument();

    const openLink = within(screen.getByText("逆袭归来").closest("article") as HTMLElement).getByRole(
      "link"
    );
    expect(openLink).toHaveAttribute("href", `/projects/${baseProject.id}/studio`);
    await user.click(openLink);
    expect(await screen.findByRole("heading", { name: "故事板" })).toBeInTheDocument();
  });

  it("removes the development Studio UI route from the formal app", async () => {
    mockProjectApi([baseProject]);
    renderApp("/dev/studio-ui");

    expect(await screen.findByText("逆袭归来")).toBeInTheDocument();
    expect(screen.queryByText("故事板演示区域")).not.toBeInTheDocument();
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
    expect(screen.getAllByText("项目总览").length).toBeGreaterThan(0);
    expect(screen.getByText("关键帧任务")).toBeInTheDocument();
    expect(screen.getByText("视频任务")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "进入生成中心" })).toHaveAttribute(
      "href",
      `/projects/${baseProject.id}/generation`
    );
    expect(
      screen
        .getAllByRole("link", { name: /场景库/ })
        .some((link) => link.getAttribute("href") === `/projects/${baseProject.id}/scenes`)
    ).toBe(true);
  });

  it("renders the generation center with project task summaries", async () => {
    mockProjectApi([baseProject]);
    renderApp(`/projects/${baseProject.id}/generation`);

    expect(await screen.findByRole("heading", { name: /生成中心/ })).toBeInTheDocument();
    expect(await screen.findByText("首尾帧视频")).toBeInTheDocument();
    expect(screen.getAllByText("已完成").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "打开镜头" })).toHaveAttribute(
      "href",
      `/projects/${baseProject.id}/shots/77777777-7777-4777-8777-777777777777`
    );
  });

  it("renders the project production board", async () => {
    mockProjectApi([baseProject]);
    renderApp(`/projects/${baseProject.id}/production`);

    expect(await screen.findByRole("heading", { name: /生产看板/ })).toBeInTheDocument();
    expect(await screen.findByText(/开场镜头/)).toBeInTheDocument();
    expect(screen.getAllByText("可进入视频").length).toBeGreaterThan(0);
    expect(screen.getByText("首帧已采用")).toBeInTheDocument();
    expect(screen.getByText("尾帧已采用")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "打开镜头" })).toHaveAttribute(
      "href",
      `/projects/${baseProject.id}/shots/77777777-7777-4777-8777-777777777777`
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
