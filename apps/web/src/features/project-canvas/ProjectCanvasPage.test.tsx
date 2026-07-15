import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import type { ProjectCanvas } from "@/features/project-canvas/types";
import type { Project } from "@/features/projects/types";

vi.mock("@xyflow/react", async () => {
  const React = await import("react");
  return {
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) =>
      React.createElement("div", { "data-testid": "react-flow-provider" }, children),
    ReactFlow: ({
      children,
      nodes,
      edges,
      onSelectionChange,
      onPaneContextMenu,
      onConnect,
      onNodeDragStop
    }: {
      children: React.ReactNode;
      nodes: Array<{ id: string; data?: { canvasNode?: { title?: string } } }>;
      edges: Array<{ id: string; label?: string }>;
      onSelectionChange?: (selection: { nodes: Array<{ id: string }>; edges: Array<{ id: string }> }) => void;
      onPaneContextMenu?: (event: React.MouseEvent<HTMLDivElement>) => void;
      onConnect?: (connection: { source: string; target: string }) => void;
      onNodeDragStop?: (event: MouseEvent, node: { id: string; position: { x: number; y: number } }) => void;
    }) =>
      React.createElement(
        "div",
        { "data-testid": "react-flow", onContextMenu: onPaneContextMenu },
        nodes.map((node) =>
          React.createElement(
            "button",
            {
              key: node.id,
              type: "button",
              onClick: () => onSelectionChange?.({ nodes: [{ id: node.id }], edges: [] })
            },
            node.data?.canvasNode?.title ?? node.id
          )
        ),
        nodes[0]
          ? React.createElement(
              "button",
              {
                type: "button",
                onClick: () =>
                  onNodeDragStop?.(new MouseEvent("mouseup"), {
                    id: nodes[0].id,
                    position: { x: 320, y: 240 }
                  })
              },
              "模拟移动节点"
            )
          : null,
        nodes.length >= 2
          ? React.createElement(
              "button",
              {
                type: "button",
                onClick: () => onConnect?.({ source: nodes[0].id, target: nodes[1].id })
              },
              "模拟创建连线"
            )
          : null,
        edges.map((edge) =>
          React.createElement(
            "button",
            {
              key: edge.id,
              type: "button",
              onClick: () => onSelectionChange?.({ nodes: [], edges: [{ id: edge.id }] })
            },
            edge.label ?? edge.id
          )
        ),
        children
      ),
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    Handle: () => null,
    Position: { Left: "left", Right: "right" },
    applyNodeChanges: (_changes: unknown, nodes: unknown) => nodes,
    applyEdgeChanges: (_changes: unknown, edges: unknown) => edges,
    useReactFlow: () => ({
      getViewport: () => ({ x: 0, y: 0, zoom: 1 }),
      fitView: vi.fn(),
      screenToFlowPosition: ({ x, y }: { x: number; y: number }) => ({ x, y })
    })
  };
});

const projectId = "11111111-1111-4111-8111-111111111111";

const project: Project = {
  id: projectId,
  name: "逆袭归来",
  description: "短剧项目",
  aspect_ratio: "9:16",
  default_style: null,
  default_language: "zh-CN",
  default_fps: 24,
  cover_image_path: null,
  created_at: "2026-07-15T00:00:00+00:00",
  updated_at: "2026-07-15T00:00:00+00:00"
};

const emptyCanvas: ProjectCanvas = {
  id: "canvas-1",
  project_id: projectId,
  view_mode: "workflow",
  viewport: { x: 0, y: 0, zoom: 1 },
  layout_version: 1,
  revision: 1,
  nodes: [],
  edges: [],
  created_at: "2026-07-15T00:00:00+00:00",
  updated_at: "2026-07-15T00:00:00+00:00"
};

function renderCanvas(path = `/projects/${projectId}/canvas`) {
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

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
}

function mockCanvasApi(options: { conflictOnNodeCreate?: boolean; failCanvas?: boolean } = {}) {
  let canvas: ProjectCanvas = { ...emptyCanvas };
  const requests: Array<{ url: string; method: string; body?: string }> = [];

  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    requests.push({ url, method, body: String(init?.body ?? "") });

    if (url === "/api/health") {
      return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    }
    if (url === `/api/projects/${projectId}` && method === "GET") {
      return jsonResponse(project);
    }
    if (url === `/api/projects/${projectId}/canvas` && method === "GET") {
      if (options.failCanvas) {
        return jsonResponse({ error: { code: "PROJECT_CANVAS_NOT_FOUND", message: "missing" } }, 500);
      }
      return jsonResponse(canvas);
    }
    if (url === `/api/projects/${projectId}/canvas` && method === "PUT") {
      const payload = JSON.parse(String(init?.body)) as {
        view_mode: ProjectCanvas["view_mode"];
        nodes: ProjectCanvas["nodes"];
        edges: ProjectCanvas["edges"];
      };
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        view_mode: payload.view_mode,
        nodes: payload.nodes,
        edges: payload.edges
      };
      return jsonResponse(canvas);
    }
    if (url === `/api/projects/${projectId}/canvas/nodes` && method === "POST") {
      if (options.conflictOnNodeCreate) {
        return jsonResponse(
          { error: { code: "PROJECT_CANVAS_REVISION_CONFLICT", message: "conflict" } },
          409
        );
      }
      const payload = JSON.parse(String(init?.body)) as {
        node_type: ProjectCanvas["nodes"][number]["node_type"];
        title: string;
        position_x: number;
        position_y: number;
        entity_type?: string | null;
        entity_id?: string | null;
      };
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        nodes: [
          ...canvas.nodes,
          {
            id: `node-${canvas.nodes.length + 1}`,
            node_type: payload.node_type,
            title: payload.title,
            position_x: payload.position_x,
            position_y: payload.position_y,
            width: 240,
            height: 120,
            z_index: canvas.nodes.length,
            entity_type: payload.entity_type ?? null,
            entity_id: payload.entity_id ?? null,
            data: {},
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ]
      };
      return jsonResponse(canvas, 201);
    }
    const patchNodeMatch = url.match(/^\/api\/projects\/[^/]+\/canvas\/nodes\/([^/]+)$/);
    if (patchNodeMatch && method === "PATCH") {
      const payload = JSON.parse(String(init?.body)) as {
        position_x?: number;
        position_y?: number;
      };
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        nodes: canvas.nodes.map((node) =>
          node.id === patchNodeMatch[1]
            ? {
                ...node,
                position_x: payload.position_x ?? node.position_x,
                position_y: payload.position_y ?? node.position_y
              }
            : node
        )
      };
      return jsonResponse(canvas);
    }
    if (url === `/api/projects/${projectId}/canvas/edges` && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as {
        source_node_id: string;
        target_node_id: string;
        semantic_type: ProjectCanvas["edges"][number]["semantic_type"];
      };
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        edges: [
          ...canvas.edges,
          {
            id: `edge-${canvas.edges.length + 1}`,
            source_node_id: payload.source_node_id,
            target_node_id: payload.target_node_id,
            source_handle: null,
            target_handle: null,
            semantic_type: payload.semantic_type,
            data: {},
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ]
      };
      return jsonResponse(canvas, 201);
    }
    const deleteEdgeMatch = url.match(/^\/api\/projects\/[^/]+\/canvas\/edges\/([^/?]+)/);
    if (deleteEdgeMatch && method === "DELETE") {
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        edges: canvas.edges.filter((edge) => edge.id !== deleteEdgeMatch[1])
      };
      return jsonResponse(canvas);
    }
    if (url === `/api/projects/${projectId}/canvas/entity-batch-preview` && method === "GET") {
      return jsonResponse({ character_count: 1, scene_count: 1, shot_count: 1, total: 3 });
    }
    if (url === `/api/projects/${projectId}/canvas/entity-batch` && method === "POST") {
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        nodes: [
          {
            id: "character-node",
            node_type: "character",
            title: "林知夏",
            position_x: 80,
            position_y: 80,
            width: 240,
            height: 120,
            z_index: 0,
            entity_type: "character",
            entity_id: "character-1",
            data: {},
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ],
        edges: []
      };
      return jsonResponse(canvas);
    }
    if (url === `/api/projects/${projectId}/characters` && method === "GET") {
      return jsonResponse({
        items: [
          {
            id: "character-1",
            project_id: projectId,
            name: "林知夏",
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
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ],
        total: 1
      });
    }
    if (url === `/api/projects/${projectId}/scenes` && method === "GET") {
      return jsonResponse({
        items: [
          {
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
            reference_count: 1,
            cover_reference: null,
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ],
        total: 1
      });
    }
    if (url === `/api/projects/${projectId}/shots` && method === "GET") {
      return jsonResponse({
        items: [
          {
            id: "shot-1",
            project_id: projectId,
            name: "开场镜头",
            order_index: 1,
            story_description: null,
            visual_description: "男主推门进入会议室",
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
            scene: { id: "scene-1", name: "会议室" },
            scene_state: null,
            notes: null,
            readiness_status: "asset_ready",
            missing_items: [],
            character_count: 1,
            reference_count: 2,
            characters: [],
            references: [],
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ],
        total: 1
      });
    }
    if (url === `/api/projects/${projectId}/generation-tasks` && method === "GET") {
      return jsonResponse({
        items: [
          {
            task_type: "video",
            task_purpose: null,
            project_id: projectId,
            task_id: "video-task-1",
            task_name: "首尾帧视频",
            task_status: "ready",
            readiness_status: null,
            shot_id: "shot-1",
            shot_name: "开场镜头",
            workflow_id: "video_wan22_14b_flf2v_v1",
            latest_run_id: null,
            latest_run_number: null,
            latest_run_status: null,
            run_count: 0,
            output_count: 1,
            has_outputs: true,
            has_selected_output: false,
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ],
        total: 1
      });
    }
    if (url === `/api/projects/${projectId}/production-status` && method === "GET") {
      return jsonResponse({
        project_id: projectId,
        summary: { total_shots: 1, blocked: 0, in_progress: 1, ready_for_video: 0, completed: 0 },
        items: [
          {
            project_id: projectId,
            shot_id: "shot-1",
            shot_name: "开场镜头",
            order_index: 1,
            overall_status: "in_progress",
            steps: {},
            blockers: [],
            next_actions: [],
            continuity_candidate: null,
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ],
        total: 1
      });
    }

    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });

  return requests;
}

test("项目创作画布路由显示空状态并可添加七种节点", async () => {
  const requests = mockCanvasApi();
  const user = userEvent.setup();

  renderCanvas();

  expect(await screen.findByRole("heading", { name: "逆袭归来" })).toBeInTheDocument();
  expect(screen.getByText("从这里开始创作")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /添加镜头节点/ }));

  expect(await screen.findByText("节点已添加。")).toBeInTheDocument();
  await waitFor(() => {
    expect(requests.some((request) => request.url.endsWith("/canvas/nodes"))).toBe(true);
  });

  fireEvent.contextMenu(screen.getByTestId("react-flow"), { clientX: 240, clientY: 180 });
  for (const label of ["文本", "角色", "场景", "镜头", "图片", "视频", "导出"]) {
    const menu = await screen.findByRole("menu");
    await user.click(within(menu).getByRole("button", { name: label }));
    fireEvent.contextMenu(screen.getByTestId("react-flow"), { clientX: 240, clientY: 180 });
  }

  await waitFor(() => {
    const nodeRequests = requests.filter(
      (request) => request.method === "POST" && request.url.endsWith("/canvas/nodes")
    );
    expect(nodeRequests.length).toBeGreaterThanOrEqual(8);
  });
});

test("资产抽屉可以把现有角色加入画布", async () => {
  const requests = mockCanvasApi();
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("资产抽屉");
  await user.click(await screen.findByRole("button", { name: /林知夏/ }));

  await waitFor(() => {
    const request = requests.find((item) => item.method === "POST" && item.url.endsWith("/canvas/nodes"));
    expect(request?.body).toContain("character-1");
  });
});

test("节点移动、创建边和删除边会保存到后端", async () => {
  const requests = mockCanvasApi();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  fireEvent.contextMenu(screen.getByTestId("react-flow"), { clientX: 240, clientY: 180 });
  await user.click(within(await screen.findByRole("menu")).getByRole("button", { name: "角色" }));
  fireEvent.contextMenu(screen.getByTestId("react-flow"), { clientX: 420, clientY: 180 });
  await user.click(within(await screen.findByRole("menu")).getByRole("button", { name: "镜头" }));

  await user.click(await screen.findByRole("button", { name: "模拟移动节点" }));
  await waitFor(() => {
    expect(requests.some((request) => request.method === "PATCH" && request.url.includes("/canvas/nodes/"))).toBe(
      true
    );
  });

  await user.click(screen.getByRole("button", { name: "模拟创建连线" }));
  expect(await screen.findByRole("button", { name: "使用角色" })).toBeInTheDocument();
  expect(requests.some((request) => request.method === "POST" && request.url.endsWith("/canvas/edges"))).toBe(true);

  await user.click(screen.getByRole("button", { name: "使用角色" }));
  await user.click(screen.getByRole("button", { name: "删除所选" }));
  await waitFor(() => {
    expect(requests.some((request) => request.method === "DELETE" && request.url.includes("/canvas/edges/"))).toBe(
      true
    );
  });
});

test("可以批量导入现有项目内容并进入故事板视图", async () => {
  mockCanvasApi();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /将项目现有内容添加到画布/ }));

  expect(await screen.findByText("已将现有角色、场景和镜头加入画布。")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "故事板" }));
  expect((await screen.findAllByText("开场镜头")).length).toBeGreaterThan(0);
  expect(screen.getByText(/3s/)).toBeInTheDocument();
});

test("revision 冲突时显示中文提示且页面不黑屏", async () => {
  mockCanvasApi({ conflictOnNodeCreate: true });
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /添加镜头节点/ }));

  expect(await screen.findByText("数据已在其他页面更新，请重新加载或覆盖。")).toBeInTheDocument();
  expect(screen.getByText("创作画布")).toBeInTheDocument();
});

test("canvas API 失败时只显示画布错误，不影响外层导航", async () => {
  mockCanvasApi({ failCanvas: true });

  renderCanvas();

  expect(await screen.findByText("创作画布加载失败。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
});
