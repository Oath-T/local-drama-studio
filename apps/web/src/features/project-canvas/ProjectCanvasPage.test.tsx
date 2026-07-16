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
      onNodeDragStop,
      onDrop,
      onDragOver
    }: {
      children: React.ReactNode;
      nodes: Array<{ id: string; data?: { canvasNode?: { title?: string } } }>;
      edges: Array<{ id: string; label?: string }>;
      onSelectionChange?: (selection: { nodes: Array<{ id: string }>; edges: Array<{ id: string }> }) => void;
      onPaneContextMenu?: (event: React.MouseEvent<HTMLDivElement>) => void;
      onConnect?: (connection: { source: string; target: string }) => void;
      onNodeDragStop?: (event: MouseEvent, node: { id: string; position: { x: number; y: number } }) => void;
      onDrop?: (event: React.DragEvent<HTMLDivElement>) => void;
      onDragOver?: (event: React.DragEvent<HTMLDivElement>) => void;
    }) =>
      React.createElement(
        "div",
        {
          "data-testid": "react-flow",
          onContextMenu: onPaneContextMenu,
          onDrop,
          onDragOver
        },
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
      setCenter: vi.fn(),
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

const characterNode = {
  id: "character-node",
  node_type: "character" as const,
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
};

const shotNode = {
  id: "shot-node",
  node_type: "shot" as const,
  title: "开场镜头",
  position_x: 380,
  position_y: 80,
  width: 240,
  height: 120,
  z_index: 1,
  entity_type: "shot",
  entity_id: "shot-1",
  data: {},
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
    if (url === `/api/projects/${projectId}` && method === "GET") return jsonResponse(project);
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
        title: string | null;
        position_x: number;
        position_y: number;
        entity_type?: string | null;
        entity_id?: string | null;
        data?: ProjectCanvas["nodes"][number]["data"];
      };
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        nodes: [
          ...canvas.nodes,
          {
            id: `node-${canvas.nodes.length + 1}`,
            node_type: payload.node_type,
            title: payload.title ?? payload.node_type,
            position_x: payload.position_x,
            position_y: payload.position_y,
            width: 240,
            height: 120,
            z_index: canvas.nodes.length,
            entity_type: payload.entity_type ?? null,
            entity_id: payload.entity_id ?? null,
            data: payload.data ?? {},
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
        data?: ProjectCanvas["nodes"][number]["data"];
      };
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        nodes: canvas.nodes.map((node) =>
          node.id === patchNodeMatch[1]
            ? {
                ...node,
                position_x: payload.position_x ?? node.position_x,
                position_y: payload.position_y ?? node.position_y,
                data: payload.data ?? node.data
              }
            : node
        )
      };
      return jsonResponse(canvas);
    }
    const deleteNodeMatch = url.match(/^\/api\/projects\/[^/]+\/canvas\/nodes\/([^/?]+)/);
    if (deleteNodeMatch && method === "DELETE") {
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        nodes: canvas.nodes.filter((node) => node.id !== deleteNodeMatch[1]),
        edges: canvas.edges.filter(
          (edge) => edge.source_node_id !== deleteNodeMatch[1] && edge.target_node_id !== deleteNodeMatch[1]
        )
      };
      return jsonResponse(canvas);
    }
    if (url === `/api/projects/${projectId}/canvas/bindings/apply` && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as {
        edge_id?: string | null;
        source_node_id: string;
        target_node_id: string;
        semantic_type: ProjectCanvas["edges"][number]["semantic_type"];
        apply_business?: boolean;
      };
      const status: ProjectCanvas["edges"][number]["data"]["status"] = payload.apply_business
        ? payload.semantic_type === "pose_reference"
          ? "failed"
          : "applied"
        : "draft";
      const edge = {
        id: payload.edge_id ?? `edge-${canvas.edges.length + 1}`,
        source_node_id: payload.source_node_id,
        target_node_id: payload.target_node_id,
        source_handle: null,
        target_handle: null,
        semantic_type: payload.semantic_type,
        data: {
          status,
          business_entity_type: status === "applied" ? "shot_character" : null,
          business_entity_id: status === "applied" ? "shot-character-1" : null,
          error_message: status === "failed" ? "普通媒体不能绑定为姿态参考。" : null
        },
        created_at: "2026-07-15T00:00:00+00:00",
        updated_at: "2026-07-15T00:00:00+00:00"
      };
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        edges: [...canvas.edges.filter((item) => item.id !== edge.id), edge]
      };
      return jsonResponse(canvas);
    }
    const deleteBindingMatch = url.match(/^\/api\/projects\/[^/]+\/canvas\/bindings\/([^/]+)/);
    if (deleteBindingMatch && method === "DELETE") {
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        edges: canvas.edges.filter((edge) => edge.id !== deleteBindingMatch[1])
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
        nodes: [characterNode, shotNode],
        edges: []
      };
      return jsonResponse(canvas);
    }
    if (url === `/api/projects/${projectId}/canvas/import-business-relations/preview` && method === "GET") {
      return jsonResponse({ character_edges: 1, scene_edges: 0, reference_edges: 0, total_edges: 1 });
    }
    if (url.startsWith(`/api/projects/${projectId}/canvas/import-business-relations`) && method === "POST") {
      canvas = {
        ...canvas,
        revision: canvas.revision + 1,
        nodes: [characterNode, shotNode],
        edges: [
          {
            id: "imported-edge",
            source_node_id: "character-node",
            target_node_id: "shot-node",
            source_handle: null,
            target_handle: null,
            semantic_type: "uses_character",
            data: {
              status: "applied",
              business_entity_type: "shot_character",
              business_entity_id: "shot-character-1"
            },
            created_at: "2026-07-15T00:00:00+00:00",
            updated_at: "2026-07-15T00:00:00+00:00"
          }
        ]
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
            default_look: {
              id: "look-1",
              character_id: "character-1",
              name: "黑西装",
              description: null,
              costume_description: null,
              hair_description: null,
              makeup_description: null,
              condition_description: null,
              prompt_appearance: null,
              is_default: true,
              reference_count: 1,
              primary_reference: null,
              created_at: "2026-07-15T00:00:00+00:00",
              updated_at: "2026-07-15T00:00:00+00:00"
            },
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
            default_state: {
              id: "scene-state-1",
              scene_id: "scene-1",
              name: "夜晚",
              description: null,
              time_of_day: "night",
              weather: "indoor",
              custom_weather: null,
              lighting: "warm_indoor",
              custom_lighting: null,
              season: "not_applicable",
              environment_condition: null,
              crowd_level: "normal",
              prompt_state: null,
              is_default: true,
              reference_count: 1,
              primary_reference: null,
              created_at: "2026-07-15T00:00:00+00:00",
              updated_at: "2026-07-15T00:00:00+00:00"
            },
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
            scene_id: "scene-1",
            scene_state_id: null,
            scene: { id: "scene-1", name: "会议室" },
            scene_state: null,
            notes: null,
            readiness_status: "asset_ready",
            missing_items: [],
            character_count: 1,
            reference_count: 1,
            characters: [],
            references: [
              {
                id: "shot-reference-1",
                shot_id: "shot-1",
                reference_type: "character",
                character_reference_id: "character-reference-1",
                scene_reference_id: null,
                shot_character_id: "shot-character-1",
                purpose: "identity",
                order_index: 1,
                notes: null,
                media_asset: {
                  id: "media-image-1",
                  project_id: projectId,
                  media_type: "image",
                  original_filename: "identity.png",
                  mime_type: "image/png",
                  extension: ".png",
                  size_bytes: 10,
                  width: 512,
                  height: 512,
                  sha256: "hash",
                  thumbnail_url: "/api/media/media-image-1/thumbnail",
                  content_url: "/api/media/media-image-1/content",
                  created_at: "2026-07-15T00:00:00+00:00"
                },
                character_reference: null,
                scene_reference: null,
                created_at: "2026-07-15T00:00:00+00:00",
                updated_at: "2026-07-15T00:00:00+00:00"
              }
            ],
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

test("资产抽屉支持拖入已有资产，重复实体会定位已有节点", async () => {
  const requests = mockCanvasApi();
  const user = userEvent.setup();

  renderCanvas();

  const characterAsset = await screen.findByRole("button", { name: /林知夏/ });
  fireEvent.dragStart(characterAsset, {
    dataTransfer: {
      setData: vi.fn(),
      effectAllowed: "copy"
    }
  });
  await user.click(characterAsset);
  expect(await screen.findByText("节点已添加。")).toBeInTheDocument();
  await user.click(characterAsset);
  expect(await screen.findByText("该素材已在画布中，已定位到已有节点。")).toBeInTheDocument();

  await waitFor(() => {
    const nodeRequests = requests.filter(
      (request) => request.method === "POST" && request.url.endsWith("/canvas/nodes")
    );
    expect(nodeRequests).toHaveLength(1);
  });
});

test("本地文件拖入不会伪装成通用上传", async () => {
  mockCanvasApi();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  const file = new File(["fake"], "local.png", { type: "image/png" });
  fireEvent.drop(screen.getByTestId("react-flow"), {
    clientX: 240,
    clientY: 180,
    dataTransfer: {
      getData: () => "",
      files: [file]
    }
  });

  expect(await screen.findByText("本地文件上传即将支持，请先从资产库添加已有素材。")).toBeInTheDocument();
});

test("关系矩阵禁止 Scene 节点直接连接 Character 节点", async () => {
  const requests = mockCanvasApi();
  const user = userEvent.setup();

  renderCanvas();

  await user.click(await screen.findByRole("button", { name: /会议室/ }));
  await user.click(await screen.findByRole("button", { name: /林知夏/ }));
  await user.click(screen.getByRole("button", { name: "模拟创建连线" }));

  expect(await screen.findByText("这两类节点目前不能直接连接。")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "确认画布关系" })).not.toBeInTheDocument();
  expect(
    requests.some(
      (request) =>
        request.method === "POST" && request.url.endsWith("/canvas/bindings/apply")
    )
  ).toBe(false);
});

test("generated_from 只能由系统建立，Shot 到 Video 不能手动连线", async () => {
  const requests = mockCanvasApi();
  const user = userEvent.setup();

  renderCanvas();

  fireEvent.contextMenu(await screen.findByTestId("react-flow"), { clientX: 240, clientY: 180 });
  await user.click(within(await screen.findByRole("menu")).getByRole("button", { name: "镜头" }));
  fireEvent.contextMenu(screen.getByTestId("react-flow"), { clientX: 420, clientY: 180 });
  await user.click(within(await screen.findByRole("menu")).getByRole("button", { name: "视频" }));
  await user.click(screen.getByRole("button", { name: "模拟创建连线" }));

  expect(await screen.findByText("这两类节点目前不能直接连接。")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "确认画布关系" })).not.toBeInTheDocument();
  expect(
    requests.some(
      (request) =>
        request.method === "POST" && request.url.endsWith("/canvas/bindings/apply")
    )
  ).toBe(false);
});

test("Image 到 Shot 只展示允许的中文语义用途", async () => {
  mockCanvasApi();
  const user = userEvent.setup();

  renderCanvas();

  await user.click(await screen.findByRole("button", { name: /identity.png/ }));
  await user.click((await screen.findAllByRole("button", { name: /开场镜头/ }))[0]);
  await user.click(screen.getByRole("button", { name: "模拟创建连线" }));

  const dialog = await screen.findByRole("heading", { name: "确认画布关系" });
  expect(dialog).toBeInTheDocument();
  const select = screen.getByLabelText("语义用途");
  expect(within(select).getByRole("option", { name: "身份参考" })).toBeInTheDocument();
  expect(within(select).getByRole("option", { name: "造型参考" })).toBeInTheDocument();
  expect(within(select).getByRole("option", { name: "姿态参考" })).toBeInTheDocument();
  expect(within(select).getByRole("option", { name: "场景参考" })).toBeInTheDocument();
  expect(within(select).getByRole("option", { name: "首帧" })).toBeInTheDocument();
  expect(within(select).getByRole("option", { name: "尾帧" })).toBeInTheDocument();
  expect(within(select).queryByRole("option", { name: "生成自" })).not.toBeInTheDocument();
});

test("连线后可以仅保留 draft edge，也可以确认真实绑定为 applied", async () => {
  const requests = mockCanvasApi();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /导入现有内容 \(3\)/ }));
  expect(await screen.findByText("现有角色、场景和镜头已导入画布。")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "模拟创建连线" }));
  expect(await screen.findByRole("heading", { name: "确认画布关系" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "仅保留画布关系" }));

  expect(await screen.findByText("画布关系已处理。")).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: /使用角色 · 草稿/ })).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: /使用角色 · 草稿/ }));
  await user.click(screen.getByRole("button", { name: "应用 / 编辑绑定" }));
  await user.click(screen.getByRole("button", { name: "确认真实绑定" }));

  expect(await screen.findByRole("button", { name: /使用角色 · 已绑定/ })).toBeInTheDocument();
  const applyRequests = requests.filter(
    (request) => request.method === "POST" && request.url.endsWith("/canvas/bindings/apply")
  );
  expect(applyRequests[0]?.body).toContain('"apply_business":false');
  expect(applyRequests[1]?.body).toContain('"apply_business":true');
});

test("失败连线在 Inspector 显示错误并可重试", async () => {
  mockCanvasApi();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(await screen.findByRole("button", { name: /identity.png/ }));
  await user.click((await screen.findAllByRole("button", { name: /开场镜头/ }))[0]);
  await user.click(screen.getByRole("button", { name: "模拟创建连线" }));
  await user.selectOptions(screen.getByLabelText("语义用途"), "pose_reference");
  await user.click(screen.getByRole("button", { name: "确认真实绑定" }));

  expect(await screen.findByText("真实绑定失败，已保留为失败连线，可在 Inspector 重试。")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /姿态参考 · 失败/ }));
  expect(screen.getByText("普通媒体不能绑定为姿态参考。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重试应用" })).toBeInTheDocument();
});

test("删除 applied edge 可选择仅隐藏或同时解除业务绑定", async () => {
  const requests = mockCanvasApi();
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /导入现有内容 \(3\)/ }));
  await user.click(await screen.findByRole("button", { name: "模拟创建连线" }));
  await user.click(screen.getByRole("button", { name: "确认真实绑定" }));
  await screen.findByRole("button", { name: /使用角色 · 已绑定/ });

  confirmSpy.mockReturnValueOnce(false);
  await user.click(screen.getByRole("button", { name: /使用角色 · 已绑定/ }));
  await user.click(screen.getByRole("button", { name: "删除所选" }));
  await waitFor(() => {
    const deleteRequest = requests.find(
      (request) => request.method === "DELETE" && request.url.includes("/canvas/bindings/")
    );
    expect(deleteRequest?.body).toContain('"mode":"hide_only"');
  });

  await user.click(screen.getByRole("button", { name: /同步绑定/ }));
  await screen.findByRole("button", { name: /使用角色 · 已绑定/ });
  confirmSpy.mockReturnValueOnce(true);
  await user.click(screen.getByRole("button", { name: /使用角色 · 已绑定/ }));
  await user.click(screen.getByRole("button", { name: "删除所选" }));
  await waitFor(() => {
    const deleteRequests = requests.filter(
      (request) => request.method === "DELETE" && request.url.includes("/canvas/bindings/")
    );
    expect(deleteRequests.at(-1)?.body).toContain('"mode":"unbind_business"');
  });
});

test("同步现有业务关系先预览再确认导入", async () => {
  const requests = mockCanvasApi();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /同步绑定 \(1\)/ }));

  expect(await screen.findByText("现有镜头绑定关系已同步到画布。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /使用角色 · 已绑定/ })).toBeInTheDocument();
  expect(
    requests.some(
      (request) =>
        request.method === "POST" && request.url.includes("/canvas/import-business-relations")
    )
  ).toBe(true);
});

test("revision 冲突时显示中文提示且页面不黑屏", async () => {
  mockCanvasApi({ conflictOnNodeCreate: true });
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /添加镜头节点/ }));

  expect(await screen.findByText("画布数据已在其他页面更新，请重新加载后再试。")).toBeInTheDocument();
  expect(screen.getByText("逆袭归来")).toBeInTheDocument();
});

test("canvas API 失败时只显示画布错误，不影响外层导航", async () => {
  mockCanvasApi({ failCanvas: true });

  renderCanvas();

  expect(await screen.findByText("创作画布加载失败，请重试。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument();
});
