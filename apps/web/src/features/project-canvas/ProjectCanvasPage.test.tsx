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
      onNodeClick,
      onEdgeClick,
      onNodeDragStop,
      onMoveEnd,
      onDrop,
      onDragOver
    }: {
      children: React.ReactNode;
      nodes: Array<{ id: string; data?: { canvasNode?: { title?: string } } }>;
      edges: Array<{ id: string; label?: string }>;
      onSelectionChange?: (selection: { nodes: Array<{ id: string }>; edges: Array<{ id: string }> }) => void;
      onPaneContextMenu?: (event: React.MouseEvent<HTMLDivElement>) => void;
      onConnect?: (connection: { source: string; target: string }) => void;
      onNodeClick?: (event: React.MouseEvent<HTMLButtonElement>, node: { id: string }) => void;
      onEdgeClick?: (event: React.MouseEvent<HTMLButtonElement>, edge: { id: string }) => void;
      onNodeDragStop?: (event: MouseEvent, node: { id: string; position: { x: number; y: number } }) => void;
      onMoveEnd?: () => void;
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
              onClick: (event: React.MouseEvent<HTMLButtonElement>) => {
                onNodeClick?.(event, node);
                onSelectionChange?.({ nodes: [{ id: node.id }], edges: [] });
              }
            },
            node.data?.canvasNode?.title ?? node.id
          )
        ),
        nodes[0]
          ? React.createElement(
              "button",
              {
                "data-testid": "mock-drag-node",
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
        React.createElement(
          "button",
          {
            "data-testid": "mock-save-viewport",
            type: "button",
            onClick: () => onMoveEnd?.()
          },
          "模拟保存视口"
        ),
        nodes.length >= 2
          ? React.createElement(
              "button",
                {
                  "data-testid": "mock-connect",
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
              "data-testid": `mock-edge-${edge.id}`,
              key: edge.id,
              type: "button",
              onClick: (event: React.MouseEvent<HTMLButtonElement>) => {
                onEdgeClick?.(event, edge);
                onSelectionChange?.({ nodes: [], edges: [{ id: edge.id }] });
              }
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

test("Inspector image action keeps the returned edge during viewport save", async () => {
  const unboundImageNode = { ...imageNode, id: "unbound-image-node", entity_id: "unbound-media-1", title: "unbound.png" };
  const requests = mockCanvasApi({
    initialCanvas: {
      ...emptyCanvas,
      revision: 8,
      nodes: [unboundImageNode, shotNode]
    }
  });
  const user = userEvent.setup();

  renderCanvas();

  await user.click(await screen.findByRole("button", { name: /unbound.png/ }));
  await user.click(await screen.findByRole("button", { name: "\u8bbe\u4e3a\u955c\u5934\u53c2\u8003\u56fe" }));

  expect(await screen.findByTestId("mock-edge-edge-1")).toBeInTheDocument();

  await user.click(screen.getByTestId("mock-save-viewport"));

  await waitFor(() => {
    const saveRequest = requests.find(
      (request) => request.method === "PUT" && request.url.endsWith("/canvas")
    );
    expect(saveRequest).toBeTruthy();
    const payload = JSON.parse(saveRequest?.body ?? "{}") as ProjectCanvas;
    expect(payload.edges).toHaveLength(1);
    expect(payload.edges[0].semantic_type).toBe("shot_reference");
  });
  expect(screen.getByTestId("mock-edge-edge-1")).toBeInTheDocument();
});

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

const imageNode = {
  id: "image-node",
  node_type: "image" as const,
  title: "identity.png",
  position_x: 80,
  position_y: 260,
  width: 240,
  height: 120,
  z_index: 2,
  entity_type: "image",
  entity_id: "media-image-1",
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

function mockCanvasApi(
  options: {
    conflictOnNodeCreate?: boolean;
    failCanvas?: boolean;
    withKeyframeHistory?: boolean;
    initialCanvas?: ProjectCanvas;
  } = {}
) {
  let canvas: ProjectCanvas = options.initialCanvas ?? { ...emptyCanvas };
  let keyframeTasks: Array<Record<string, any>> = [];
  const keyframeRuns = new Map<string, Array<Record<string, any>>>();
  let videoTasks: Array<Record<string, any>> = [];
  const videoRuns = new Map<string, Array<Record<string, any>>>();
  const requests: Array<{ url: string; method: string; body?: string }> = [];

  if (options.withKeyframeHistory) {
    const task = makeKeyframeTask("quick-first-task", "first_frame");
    keyframeTasks = [task];
    keyframeRuns.set(task.id, [
      makeKeyframeRun(task.id, "quick-first-current-output", {
        runId: "quick-first-current-run",
        createdAt: "2026-07-15T00:02:00+00:00",
        prompt: "current first frame prompt"
      }),
      makeKeyframeRun(task.id, "quick-first-old-output", {
        runId: "quick-first-old-run",
        createdAt: "2026-07-15T00:01:00+00:00",
        prompt: "old first frame prompt"
      })
    ]);
  }

  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method ?? "GET";
    requests.push({ url, method, body: String(init?.body ?? "") });

    if (url === "/api/health") {
      return jsonResponse({ status: "ok", service: "local-drama-studio-api" });
    }
    if (url === "/api/system/capabilities" && method === "GET") {
      return jsonResponse({
        vision_analysis: { available: false, provider: "none" },
        keyframe_generation: { available: true, provider: "comfyui", status: "online" },
        video_generation: { available: true, provider: "comfyui", status: "online" }
      });
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
          business_entity_type:
            status === "applied"
              ? payload.semantic_type === "shot_reference"
                ? "shot_reference"
                : "shot_character"
              : null,
          business_entity_id:
            status === "applied"
              ? payload.semantic_type === "shot_reference"
                ? "shot-reference-1"
                : "shot-character-1"
              : null,
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
    if (url === `/api/projects/${projectId}/keyframe-workflows` && method === "GET") {
      return jsonResponse({
        items: [
          {
            workflow_id: "keyframe_basic_v1",
            display_name: "基础关键帧",
            version: "1.0.0",
            available: true,
            missing_requirements: [],
            uses_reference_inputs: false
          }
        ],
        total: 1
      });
    }
    if (url === `/api/projects/${projectId}/video-workflows` && method === "GET") {
      return jsonResponse({
        items: [
          {
            workflow_id: "video_wan22_14b_flf2v_v1",
            display_name: "Wan2.2 14B 首尾帧视频",
            version: "0.2.0",
            mode: "first_last_frame_to_video",
            required_input_roles: ["start_frame", "end_frame"],
            available: true,
            missing_requirements: [],
            reference_inputs_used: true
          }
        ],
        total: 1
      });
    }
    const quickPreviewMatch = url.match(
      /^\/api\/projects\/[^/]+\/shots\/shot-1\/quick-generate\/preview$/
    );
    if (quickPreviewMatch && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as { mode: string };
      const missingInputs: string[] = [];
      if (payload.mode === "video") {
        const firstSelected = Array.from(keyframeRuns.values()).some((runs) =>
          runs.some((run) =>
            run.outputs.some(
              (output: Record<string, any>) =>
                output.id === "quick-first-output" && output.is_selected
            )
          )
        );
        const endSelected = Array.from(keyframeRuns.values()).some((runs) =>
          runs.some((run) =>
            run.outputs.some(
              (output: Record<string, any>) =>
                output.id === "quick-end-output" && output.is_selected
            )
          )
        );
        if (!firstSelected) missingInputs.push("adopted_first_frame");
        if (!endSelected) missingInputs.push("adopted_end_frame");
      }
      const workflowId =
        payload.mode === "video" ? "video_wan22_14b_flf2v_v1" : "keyframe_basic_v1";
      return jsonResponse({
        mode: payload.mode,
        route: {
          selected_workflow_id: workflowId,
          executable: missingInputs.length === 0,
          reason_zh: missingInputs.length === 0 ? "已选择可执行工作流。" : "缺少必要输入，暂不能开始生成。",
          required_inputs:
            payload.mode === "video"
              ? ["prompt", "adopted_first_frame", "adopted_end_frame"]
              : ["prompt"],
          missing_inputs: missingInputs,
          missing_models: [],
          missing_nodes: [],
          warnings: [],
          fallback: null
        },
        capabilities: []
      });
    }
    const quickExecuteMatch = url.match(
      /^\/api\/projects\/[^/]+\/shots\/shot-1\/quick-generate$/
    );
    if (quickExecuteMatch && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as { mode: string; request_id: string };
      if (payload.mode === "video") {
        const task = videoTasks[0] ?? makeVideoTask("quick-video-task", {});
        videoTasks = [task];
        const run = makeVideoRun(task.id);
        videoRuns.set(task.id, [run, ...(videoRuns.get(task.id) ?? [])]);
        return jsonResponse(
          quickExecuteResponse(payload.mode, payload.request_id, "video", task.id, run.id),
          202
        );
      }
      const purpose = payload.mode;
      const task = makeKeyframeTask(
        purpose === "end_frame" ? "quick-end-task" : "quick-first-task",
        purpose
      );
      keyframeTasks = [...keyframeTasks.filter((item) => item.id !== task.id), task];
      const outputId = purpose === "end_frame" ? "quick-end-output" : "quick-first-output";
      const run = makeKeyframeRun(task.id, outputId);
      keyframeRuns.set(task.id, [run, ...(keyframeRuns.get(task.id) ?? [])]);
      return jsonResponse(
        quickExecuteResponse(payload.mode, payload.request_id, "keyframe", task.id, run.id),
        202
      );
    }
    if (url === `/api/projects/${projectId}/shots/shot-1/keyframe-tasks` && method === "GET") {
      return jsonResponse({ items: keyframeTasks, total: keyframeTasks.length });
    }
    if (url === `/api/projects/${projectId}/shots/shot-1/keyframe-tasks` && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as { purpose?: string };
      const purpose = payload.purpose ?? "concept";
      const task = makeKeyframeTask(
        purpose === "end_frame" ? "quick-end-task" : "quick-first-task",
        purpose
      );
      keyframeTasks = [...keyframeTasks.filter((item) => item.id !== task.id), task];
      return jsonResponse(task, 201);
    }
    const keyframeTaskMatch = url.match(/^\/api\/projects\/[^/]+\/keyframe-tasks\/([^/]+)$/);
    if (keyframeTaskMatch && method === "PATCH") {
      const payload = JSON.parse(String(init?.body)) as Record<string, unknown>;
      const taskId = keyframeTaskMatch[1];
      keyframeTasks = keyframeTasks.map((task) =>
        task.id === taskId ? { ...task, ...payload, status: "draft" } : task
      );
      return jsonResponse(keyframeTasks.find((task) => task.id === taskId));
    }
    const keyframeReadyMatch = url.match(/^\/api\/projects\/[^/]+\/keyframe-tasks\/([^/]+)\/mark-ready$/);
    if (keyframeReadyMatch && method === "POST") {
      const taskId = keyframeReadyMatch[1];
      keyframeTasks = keyframeTasks.map((task) =>
        task.id === taskId ? { ...task, status: "ready" } : task
      );
      return jsonResponse(keyframeTasks.find((task) => task.id === taskId));
    }
    const keyframeRunsMatch = url.match(/^\/api\/projects\/[^/]+\/keyframe-tasks\/([^/]+)\/runs$/);
    if (keyframeRunsMatch && method === "GET") {
      const runs = keyframeRuns.get(keyframeRunsMatch[1]) ?? [];
      return jsonResponse({ items: runs, total: runs.length });
    }
    if (keyframeRunsMatch && method === "POST") {
      const taskId = keyframeRunsMatch[1];
      const task = keyframeTasks.find((item) => item.id === taskId);
      const outputId = task?.purpose === "end_frame" ? "quick-end-output" : "quick-first-output";
      const run = makeKeyframeRun(taskId, outputId);
      keyframeRuns.set(taskId, [run, ...(keyframeRuns.get(taskId) ?? [])]);
      return jsonResponse({ run_id: run.id, status: "queued" }, 202);
    }
    const keyframeSelectMatch = url.match(/^\/api\/projects\/[^/]+\/keyframe-outputs\/([^/]+)\/select$/);
    if (keyframeSelectMatch && method === "POST") {
      const outputId = keyframeSelectMatch[1];
      for (const [taskId, runs] of keyframeRuns) {
        keyframeRuns.set(
          taskId,
          runs.map((run) => ({
            ...run,
            outputs: run.outputs.map((output: Record<string, any>) => ({
              ...output,
              is_selected: output.id === outputId ? true : output.is_selected
            }))
          }))
        );
      }
      return jsonResponse({ ...makeKeyframeOutput(outputId), is_selected: true });
    }
    if (url === `/api/projects/${projectId}/shots/shot-1/video-tasks` && method === "GET") {
      return jsonResponse({ items: videoTasks, total: videoTasks.length });
    }
    if (url === `/api/projects/${projectId}/shots/shot-1/video-tasks` && method === "POST") {
      const payload = JSON.parse(String(init?.body)) as Record<string, unknown>;
      const task = makeVideoTask("quick-video-task", payload);
      videoTasks = [task];
      return jsonResponse(task, 201);
    }
    const videoTaskMatch = url.match(/^\/api\/projects\/[^/]+\/video-tasks\/([^/]+)$/);
    if (videoTaskMatch && method === "PATCH") {
      const payload = JSON.parse(String(init?.body)) as Record<string, unknown>;
      const taskId = videoTaskMatch[1];
      videoTasks = videoTasks.map((task) =>
        task.id === taskId ? makeVideoTask(taskId, { ...task, ...payload }) : task
      );
      return jsonResponse(videoTasks.find((task) => task.id === taskId));
    }
    const videoReadyMatch = url.match(/^\/api\/projects\/[^/]+\/video-tasks\/([^/]+)\/mark-ready$/);
    if (videoReadyMatch && method === "POST") {
      const taskId = videoReadyMatch[1];
      videoTasks = videoTasks.map((task) =>
        task.id === taskId ? { ...task, status: "ready" } : task
      );
      return jsonResponse(videoTasks.find((task) => task.id === taskId));
    }
    const videoRunsMatch = url.match(/^\/api\/projects\/[^/]+\/video-tasks\/([^/]+)\/runs$/);
    if (videoRunsMatch && method === "GET") {
      const runs = videoRuns.get(videoRunsMatch[1]) ?? [];
      return jsonResponse({ items: runs, total: runs.length });
    }
    if (videoRunsMatch && method === "POST") {
      const taskId = videoRunsMatch[1];
      const run = makeVideoRun(taskId);
      videoRuns.set(taskId, [run, ...(videoRuns.get(taskId) ?? [])]);
      return jsonResponse({ run_id: run.id, status: "queued" }, 202);
    }
    const videoSelectMatch = url.match(/^\/api\/projects\/[^/]+\/video-outputs\/([^/]+)\/select$/);
    if (videoSelectMatch && method === "POST") {
      const outputId = videoSelectMatch[1];
      for (const [taskId, runs] of videoRuns) {
        videoRuns.set(
          taskId,
          runs.map((run) => ({
            ...run,
            outputs: run.outputs.map((output: Record<string, any>) => ({
              ...output,
              is_selected: output.id === outputId
            }))
          }))
        );
      }
      videoTasks = videoTasks.map((task) => ({
        ...task,
        selected_output: makeVideoOutput(outputId, true)
      }));
      return jsonResponse(makeVideoOutput(outputId, true));
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

function makeKeyframeTask(id: string, purpose: string) {
  return {
    id,
    project_id: projectId,
    shot_id: "shot-1",
    name: purpose === "end_frame" ? "尾帧" : "首帧",
    purpose,
    status: "draft",
    shot_snapshot: {
      schema_version: 1,
      shot_id: "shot-1",
      order_index: 1,
      title: "开场镜头",
      story_description: null,
      visual_description: "男主推门进入会议室",
      action_summary: null,
      dialogue: null,
      mood_description: null,
      duration_seconds: 3,
      shot_scale: "wide",
      camera_angle: "front",
      custom_camera_angle: null,
      camera_height: "eye_level",
      custom_camera_height: null,
      lens: null,
      composition_type: "centered",
      custom_composition: null,
      camera_movement: "static",
      custom_camera_movement: null,
      scene_id: "scene-1",
      scene_name: "会议室",
      scene_state_id: null,
      scene_state_name: null,
      characters: []
    },
    source_shot_updated_at: "2026-07-15T00:00:00+00:00",
    prompt_zh: null,
    prompt_en: null,
    negative_prompt: null,
    aspect_ratio: "9:16",
    width: 768,
    height: 1360,
    seed: null,
    steps: 28,
    guidance_scale: 6.5,
    sampler_name: null,
    scheduler_name: null,
    model_provider: null,
    model_name: null,
    model_version: null,
    output_count: 1,
    readiness: { readiness_status: "ready", blocking_issues: [], warnings: [] },
    shot_changed_since_snapshot: false,
    references: [],
    reference_count: 0,
    created_at: "2026-07-15T00:00:00+00:00",
    updated_at: "2026-07-15T00:00:00+00:00"
  };
}

function quickExecuteResponse(
  mode: string,
  requestId: string,
  runType: string,
  taskId: string,
  runId: string
) {
  const workflowId = runType === "video" ? "video_wan22_14b_flf2v_v1" : "keyframe_basic_v1";
  return {
    mode,
    run_type: runType,
    request_id: requestId,
    idempotent_replay: false,
    reused_active_run: false,
    task_id: taskId,
    run_id: runId,
    status: "queued",
    workflow_id: workflowId,
    route: {
      selected_workflow_id: workflowId,
      executable: true,
      reason_zh: "已选择可执行工作流。",
      required_inputs: mode === "video" ? ["prompt", "adopted_first_frame", "adopted_end_frame"] : ["prompt"],
      missing_inputs: [],
      missing_models: [],
      missing_nodes: [],
      warnings: [],
      fallback: null
    },
    canvas_sync: {
      attempted: false,
      synced: false,
      node_id: null,
      edge_id: null,
      error_message: null
    }
  };
}

function makeKeyframeOutput(id: string, selected = false) {
  return {
    id,
    project_id: projectId,
    run_id: id === "quick-end-output" ? "quick-end-run" : "quick-first-run",
    media_asset_id: `${id}-media`,
    output_index: 0,
    width: 768,
    height: 1360,
    seed: 12345,
    is_selected: selected,
    media_asset: {
      id: `${id}-media`,
      project_id: projectId,
      media_type: "image",
      original_filename: `${id}.png`,
      mime_type: "image/png",
      extension: ".png",
      size_bytes: 10,
      width: 768,
      height: 1360,
      sha256: `${id}-hash`,
      thumbnail_url: `/api/media/${id}-media/thumbnail`,
      content_url: `/api/media/${id}-media/content`,
      created_at: "2026-07-15T00:00:00+00:00"
    },
    created_at: "2026-07-15T00:00:00+00:00"
  };
}

function makeKeyframeRun(
  taskId: string,
  outputId: string,
  options: { runId?: string; createdAt?: string; prompt?: string } = {}
) {
  const runId =
    options.runId ?? (outputId === "quick-end-output" ? "quick-end-run" : "quick-first-run");
  const createdAt = options.createdAt ?? "2026-07-15T00:00:00+00:00";
  const prompt = options.prompt ?? "dramatic office scene";
  return {
    id: runId,
    project_id: projectId,
    keyframe_task_id: taskId,
    run_number: 1,
    provider: "comfyui",
    workflow_id: "keyframe_basic_v1",
    workflow_version: "1.0.0",
    status: "completed",
    provider_job_id: null,
    submitted_payload_snapshot: {
      schema_version: 1,
      task_id: taskId,
      task_updated_at: "2026-07-15T00:00:00+00:00",
      workflow_id: "keyframe_basic_v1",
      workflow_version: "1.0.0",
      prompt_zh: null,
      prompt_en: prompt,
      effective_prompt_language: "en",
      effective_positive_prompt: prompt,
      negative_prompt: null,
      width: 768,
      height: 1360,
      seed: 12345,
      steps: 28,
      guidance_scale: 6.5,
      sampler_name: "euler",
      scheduler_name: "normal",
      output_count: 1,
      task_reference_ids: [],
      media_asset_ids: [],
      reference_inputs_used: false
    },
    error_code: null,
    error_message_safe: null,
    queued_at: null,
    started_at: null,
    completed_at: createdAt,
    created_at: createdAt,
    updated_at: createdAt,
    outputs: [{ ...makeKeyframeOutput(outputId), run_id: runId, created_at: createdAt }]
  };
}

function makeVideoTask(id: string, payload: Record<string, any> = {}) {
  return {
    id,
    project_id: projectId,
    shot_id: "shot-1",
    name: payload.name ?? "首尾帧视频",
    status: payload.status ?? "draft",
    input_media_asset_id: null,
    source_keyframe_output_id: null,
    source_keyframe_task_id: null,
    prompt: payload.prompt ?? null,
    negative_prompt: payload.negative_prompt ?? null,
    duration_seconds: payload.duration_seconds ?? 2,
    fps: payload.fps ?? 16,
    width: payload.width ?? 640,
    height: payload.height ?? 640,
    seed: payload.seed ?? null,
    motion_strength: payload.motion_strength ?? 0.45,
    camera_motion: payload.camera_motion ?? null,
    workflow_id: payload.workflow_id ?? "video_wan22_14b_flf2v_v1",
    input_media_asset: null,
    inputs: payload.inputs ?? [],
    readiness: { readiness_status: "ready", blocking_issues: [], warnings: [] },
    latest_run_status: null,
    selected_output: payload.selected_output ?? null,
    created_at: "2026-07-15T00:00:00+00:00",
    updated_at: "2026-07-15T00:00:00+00:00"
  };
}

function makeVideoOutput(id: string, selected = false) {
  return {
    id,
    project_id: projectId,
    run_id: "quick-video-run",
    media_asset_id: `${id}-media`,
    output_index: 0,
    width: 640,
    height: 640,
    duration_seconds: 2,
    fps: 16,
    seed: 12345,
    is_selected: selected,
    media_asset: {
      id: `${id}-media`,
      project_id: projectId,
      media_type: "video",
      original_filename: `${id}.mp4`,
      mime_type: "video/mp4",
      extension: ".mp4",
      size_bytes: 10,
      width: 640,
      height: 640,
      sha256: `${id}-hash`,
      thumbnail_url: null,
      content_url: `/api/media/${id}-media/content`,
      created_at: "2026-07-15T00:00:00+00:00"
    },
    created_at: "2026-07-15T00:00:00+00:00"
  };
}

function makeVideoRun(taskId: string) {
  return {
    id: "quick-video-run",
    project_id: projectId,
    video_task_id: taskId,
    run_number: 1,
    provider: "comfyui",
    workflow_id: "video_wan22_14b_flf2v_v1",
    workflow_version: "0.2.0",
    status: "completed",
    provider_job_id: null,
    submitted_payload_snapshot: {
      schema_version: 2,
      video_task_id: taskId,
      shot_id: "shot-1",
      workflow_id: "video_wan22_14b_flf2v_v1",
      workflow_version: "0.2.0",
      workflow_mode: "first_last_frame_to_video",
      input_media_asset_id: "quick-first-output-media",
      inputs: [
        { role: "start_frame", media_asset_id: "quick-first-output-media" },
        { role: "end_frame", media_asset_id: "quick-end-output-media" }
      ],
      prompt: "motion prompt",
      negative_prompt: null,
      duration_seconds: 2,
      fps: 16,
      width: 640,
      height: 640,
      seed: 12345,
      motion_strength: 0.45,
      camera_motion: null,
      reference_inputs_used: true
    },
    error_code: null,
    error_message_safe: null,
    queued_at: null,
    started_at: null,
    completed_at: "2026-07-15T00:00:00+00:00",
    created_at: "2026-07-15T00:00:00+00:00",
    updated_at: "2026-07-15T00:00:00+00:00",
    outputs: [makeVideoOutput("quick-video-output")]
  };
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

test("manual connection is downgraded to an Inspector action hint", async () => {
  const requests = mockCanvasApi({
    initialCanvas: {
      ...emptyCanvas,
      nodes: [characterNode, shotNode]
    }
  });
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByTestId("mock-connect");
  await user.click(screen.getByTestId("mock-connect"));

  expect(await screen.findByText("\u8bf7\u5728\u53f3\u4fa7 Inspector \u4f7f\u7528\u660e\u786e\u6309\u94ae\u5b8c\u6210\u7ed1\u5b9a\u3002\u5173\u7cfb\u7ebf\u5f53\u524d\u4ec5\u4f5c\u4e3a\u8f85\u52a9\u5c55\u793a\u3002")).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "\u786e\u8ba4\u753b\u5e03\u5173\u7cfb" })).not.toBeInTheDocument();
  expect(
    requests.some(
      (request) =>
        request.method === "POST" && request.url.endsWith("/canvas/bindings/apply")
    )
  ).toBe(false);
});

test("image Inspector button binds a shot reference", async () => {
  const unboundImageNode = { ...imageNode, id: "unbound-image-node", entity_id: "unbound-media-1", title: "unbound.png" };
  const requests = mockCanvasApi({
    initialCanvas: {
      ...emptyCanvas,
      nodes: [unboundImageNode, shotNode]
    }
  });
  const user = userEvent.setup();

  renderCanvas();

  await user.click(await screen.findByRole("button", { name: /unbound.png/ }));
  expect(await screen.findByText("\u955c\u5934\u53c2\u8003\u56fe")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "\u8bbe\u4e3a\u955c\u5934\u53c2\u8003\u56fe" }));

  expect(await screen.findByText("\u753b\u5e03\u5173\u7cfb\u5df2\u5904\u7406\u3002")).toBeInTheDocument();
  expect(await screen.findByTestId("mock-edge-edge-1")).toBeInTheDocument();
  const applyRequest = requests.find(
    (request) => request.method === "POST" && request.url.endsWith("/canvas/bindings/apply")
  );
  expect(applyRequest?.body).toContain('"semantic_type":"shot_reference"');
  expect(applyRequest?.body).toContain('"apply_business":true');
  expect(applyRequest?.body).toContain('"media_asset_id":"unbound-media-1"');
});

test("bound image Inspector button removes the shot reference", async () => {
  const requests = mockCanvasApi({
    initialCanvas: {
      ...emptyCanvas,
      nodes: [imageNode, shotNode],
      edges: [
        {
          id: "shot-reference-edge",
          source_node_id: imageNode.id,
          target_node_id: shotNode.id,
          source_handle: null,
          target_handle: null,
          semantic_type: "shot_reference",
          data: {
            status: "applied",
            business_entity_type: "shot_reference",
            business_entity_id: "shot-reference-1"
          },
          created_at: "2026-07-15T00:00:00+00:00",
          updated_at: "2026-07-15T00:00:00+00:00"
        }
      ]
    }
  });
  const user = userEvent.setup();

  renderCanvas();

  const identityButtons = await screen.findAllByRole("button", { name: /identity.png/ });
  await user.click(identityButtons.at(-1)!);
  expect(await screen.findByText(/\u5df2\u662f\u955c\u5934\u53c2\u8003\u56fe/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "\u4ece\u955c\u5934\u53c2\u8003\u56fe\u79fb\u9664" }));

  await waitFor(() => {
    const deleteRequest = requests.find(
      (request) => request.method === "DELETE" && request.url.includes("/canvas/bindings/")
    );
    expect(deleteRequest?.body).toContain('"mode":"unbind_business"');
  });
});

test("relation edges are hidden by default and visible for the selected node", async () => {
  mockCanvasApi({
    initialCanvas: {
      ...emptyCanvas,
      nodes: [characterNode, shotNode],
      edges: [
        {
          id: "imported-edge",
          source_node_id: characterNode.id,
          target_node_id: shotNode.id,
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
    }
  });
  const user = userEvent.setup();

  renderCanvas();

  const characterButtons = await screen.findAllByRole("button", { name: /\u6797\u77e5\u590f/ });
  expect(screen.queryByTestId("mock-edge-imported-edge")).not.toBeInTheDocument();

  await user.click(characterButtons.at(-1)!);
  expect(await screen.findByTestId("mock-edge-imported-edge")).toBeInTheDocument();
});

test("show relations toggle reveals imported business edges", async () => {
  const requests = mockCanvasApi();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("\u4ece\u8fd9\u91cc\u5f00\u59cb\u521b\u4f5c");
  await user.click(screen.getByRole("button", { name: /\u540c\u6b65\u7ed1\u5b9a \(1\)/ }));

  expect(await screen.findByText("\u73b0\u6709\u955c\u5934\u7ed1\u5b9a\u5173\u7cfb\u5df2\u540c\u6b65\u5230\u753b\u5e03\u3002")).toBeInTheDocument();
  expect(screen.queryByTestId("mock-edge-imported-edge")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "\u663e\u793a\u5173\u7cfb" }));
  expect(await screen.findByTestId("mock-edge-imported-edge")).toBeInTheDocument();
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

test("镜头节点可以在画布 Inspector 内生成并采用首帧、尾帧和视频", async () => {
  const requests = mockCanvasApi();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /导入现有内容 \(3\)/ }));
  const shotButtons = await screen.findAllByRole("button", { name: /开场镜头/ });
  await user.click(shotButtons.at(-1)!);

  expect(await screen.findByText("画布快速生成")).toBeInTheDocument();
  await user.click(await screen.findByRole("button", { name: "生成首帧" }));
  expect(await screen.findByText("首帧生成已提交，请在当前候选区等待结果。")).toBeInTheDocument();
  await user.click((await screen.findAllByRole("button", { name: "采用" }))[0]);
  expect(await screen.findByText("候选图已采用。")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "尾帧" }));
  await user.click(screen.getByRole("button", { name: "生成尾帧" }));
  expect(await screen.findByText("尾帧生成已提交，请在当前候选区等待结果。")).toBeInTheDocument();
  await user.click(
    (await screen.findAllByRole("button", { name: "采用" })).find(
      (button) => !button.hasAttribute("disabled")
    )!
  );
  expect(await screen.findByText("候选图已采用。")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "视频" }));
  const generateVideoButton = screen.getByRole("button", { name: "生成视频" });
  await waitFor(() => expect(generateVideoButton).not.toBeDisabled());
  await user.click(generateVideoButton);
  expect(await screen.findByText("视频生成已提交，请在当前候选区等待结果。")).toBeInTheDocument();
  await user.click(
    (await screen.findAllByRole("button", { name: "采用" })).find(
      (button) => !button.hasAttribute("disabled")
    )!
  );
  expect(await screen.findByText("视频输出已采用。")).toBeInTheDocument();

  expect(
    requests.some(
      (request) =>
        request.method === "POST" &&
        request.url.endsWith("/shots/shot-1/quick-generate") &&
        request.body?.includes('"mode":"first_frame"')
    )
  ).toBe(true);
  expect(
    requests.some(
      (request) =>
        request.method === "POST" &&
        request.url.endsWith("/shots/shot-1/quick-generate") &&
        request.body?.includes('"mode":"end_frame"')
    )
  ).toBe(true);
  expect(
    requests.some(
      (request) =>
        request.method === "POST" &&
        request.url.endsWith("/shots/shot-1/quick-generate/preview") &&
        request.body?.includes('"mode":"video"')
    )
  ).toBe(true);
  expect(
    requests.some(
      (request) =>
        request.method === "POST" &&
        request.url.endsWith("/shots/shot-1/quick-generate") &&
        request.body?.includes('"mode":"video"')
    )
  ).toBe(true);
  expect(
    requests.some(
      (request) =>
        request.method === "POST" && request.url.endsWith("/video-outputs/quick-video-output/select")
    )
  ).toBe(true);
});

test("快速生成面板将最新 Run 作为当前候选并折叠历史生成", async () => {
  mockCanvasApi({ withKeyframeHistory: true });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();

  renderCanvas();

  await screen.findByText("从这里开始创作");
  await user.click(screen.getByRole("button", { name: /导入现有内容 \(3\)/ }));
  const shotButtons = await screen.findAllByRole("button", { name: /开场镜头/ });
  await user.click(shotButtons.at(-1)!);

  expect(await screen.findByText("当前候选")).toBeInTheDocument();
  expect(screen.getByText("历史生成（1 次 Run）")).toBeInTheDocument();
  expect(screen.getByText(/old first frame prompt/)).not.toBeVisible();

  await user.click(screen.getAllByRole("button", { name: "原图" })[0]);
  expect(await screen.findByRole("button", { name: "关闭" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "关闭" }));
  expect(screen.queryByRole("button", { name: "关闭" })).not.toBeInTheDocument();
});
