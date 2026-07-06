import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

import type { KeyframeTask } from "@/features/keyframe-tasks/types";
import type { Shot } from "@/features/shots/types";
import type { VideoTask } from "@/features/video-generation/types";

import {
  CharacterAssetSummaryCard,
  KeyframeInheritedAssetSummary,
  SceneAssetSummaryCard,
  ShotAssetSummaryCard,
  VideoShotContextSummary
} from "./components/asset-summary-cards";

const projectId = "11111111-1111-4111-8111-111111111111";
const characterId = "22222222-2222-4222-8222-222222222222";
const sceneId = "33333333-3333-4333-8333-333333333333";
const shotId = "44444444-4444-4444-8444-444444444444";

const mediaAsset = {
  id: "55555555-5555-4555-8555-555555555555",
  media_type: "image",
  original_filename: "reference.png",
  mime_type: "image/png",
  width: 800,
  height: 600,
  thumbnail_url: "/api/media/55555555-5555-4555-8555-555555555555/thumbnail",
  content_url: "/api/media/55555555-5555-4555-8555-555555555555/content",
  created_at: "2026-07-06T00:00:00+00:00"
};

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

function mockAssetSummaryApi(fail = false) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    if (fail) {
      return jsonResponse({ error: { code: "SUMMARY_FAILED", message: "failed" } }, 500);
    }
    if (url.endsWith(`/characters/${characterId}/asset-summary`)) {
      return jsonResponse({
        id: characterId,
        project_id: projectId,
        name: "林知夏",
        default_look_id: "look-1",
        default_look_name: "通勤造型",
        look_count: 1,
        reference_count: 1,
        primary_reference_count: 1,
        identity_anchor_count: 1,
        face_reference_count: 1,
        full_body_reference_count: 0,
        used_shot_count: 1,
        recent_shots: [{ id: shotId, name: "开场镜头", order_index: 1, updated_at: "2026-07-06T00:00:00+00:00" }],
        featured_references: [
          {
            id: "ref-1",
            reference_type: "character",
            label: "正面身份参考",
            purpose: null,
            look_id: "look-1",
            look_name: "通勤造型",
            state_id: null,
            state_name: null,
            is_primary: true,
            is_identity_anchor: true,
            is_spatial_anchor: false,
            is_empty_plate: false,
            media_asset: mediaAsset,
            created_at: "2026-07-06T00:00:00+00:00"
          }
        ],
        completeness_warnings: ["缺少全身或大半身造型参考"]
      });
    }
    if (url.endsWith(`/scenes/${sceneId}/asset-summary`)) {
      return jsonResponse({
        id: sceneId,
        project_id: projectId,
        name: "办公楼走廊",
        default_state_id: "state-1",
        default_state_name: "夜晚暴雨",
        state_count: 1,
        reference_count: 1,
        primary_reference_count: 1,
        spatial_anchor_count: 1,
        empty_plate_count: 1,
        wide_reference_count: 1,
        used_shot_count: 1,
        recent_shots: [{ id: shotId, name: "开场镜头", order_index: 1, updated_at: "2026-07-06T00:00:00+00:00" }],
        featured_references: [
          {
            id: "scene-ref-1",
            reference_type: "scene",
            label: "走廊空间结构",
            purpose: null,
            look_id: null,
            look_name: null,
            state_id: "state-1",
            state_name: "夜晚暴雨",
            is_primary: true,
            is_identity_anchor: false,
            is_spatial_anchor: true,
            is_empty_plate: true,
            media_asset: mediaAsset,
            created_at: "2026-07-06T00:00:00+00:00"
          }
        ],
        completeness_warnings: []
      });
    }
    if (url.endsWith(`/shots/${shotId}/asset-summary`)) {
      return jsonResponse({
        id: shotId,
        project_id: projectId,
        name: "开场镜头",
        characters: [
          {
            shot_character_id: "shot-character-1",
            character_id: characterId,
            character_name: "林知夏",
            look_id: "look-1",
            look_name: "通勤造型",
            is_primary_subject: true,
            bound_reference_count: 1,
            completeness_warnings: []
          }
        ],
        scene: {
          scene_id: sceneId,
          scene_name: "办公楼走廊",
          scene_state_id: "state-1",
          scene_state_name: "夜晚暴雨",
          bound_reference_count: 1,
          completeness_warnings: []
        },
        references: [],
        generation: {
          keyframe_task_count: 1,
          video_task_count: 1,
          selected_keyframe_output_count: 0,
          selected_video_output_count: 0
        },
        completeness_warnings: []
      });
    }
    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("asset summary cards", () => {
  it("renders character, scene, and shot asset summaries", async () => {
    mockAssetSummaryApi();
    renderWithClient(
      <div>
        <CharacterAssetSummaryCard projectId={projectId} characterId={characterId} />
        <SceneAssetSummaryCard projectId={projectId} sceneId={sceneId} />
        <ShotAssetSummaryCard projectId={projectId} shotId={shotId} />
      </div>
    );

    expect(await screen.findByText("可调用人物资产")).toBeInTheDocument();
    expect(await screen.findByText(/默认造型: 通勤造型/)).toBeInTheDocument();
    expect(await screen.findByText("可调用场景资产")).toBeInTheDocument();
    expect(await screen.findByText(/默认场景状态: 夜晚暴雨/)).toBeInTheDocument();
    expect(await screen.findByText("本镜头资产")).toBeInTheDocument();
    expect((await screen.findAllByText("林知夏")).length).toBeGreaterThan(0);
    expect(screen.getByText("办公楼走廊")).toBeInTheDocument();
  });

  it("shows a safe Chinese error state without breaking the page", async () => {
    mockAssetSummaryApi(true);
    renderWithClient(<ShotAssetSummaryCard projectId={projectId} shotId={shotId} />);

    expect(await screen.findByText("资产摘要加载失败，不影响当前页面操作。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重新加载" })).toBeInTheDocument();
  });

  it("renders inherited keyframe assets and video shot context", () => {
    const task = {
      shot_snapshot: {
        title: "开场镜头",
        scene_name: "办公楼走廊",
        scene_state_name: "夜晚暴雨",
        characters: [{ character_name: "林知夏" }]
      },
      references: [
        { reference_type: "character" },
        { reference_type: "scene" }
      ]
    } as unknown as KeyframeTask;
    const shot = {
      characters: [{ character_name: "林知夏" }],
      scene: { name: "办公楼走廊" },
      scene_state: { name: "夜晚暴雨" }
    } as unknown as Shot;
    const videoTask = {
      inputs: [{ role: "start_frame", media_asset: mediaAsset }]
    } as unknown as VideoTask;

    renderWithClient(
      <div>
        <KeyframeInheritedAssetSummary task={task} />
        <VideoShotContextSummary shot={shot} task={videoTask} />
      </div>
    );

    expect(screen.getByText("继承自镜头资产")).toBeInTheDocument();
    expect(screen.getByText("本视频任务来自镜头上下文")).toBeInTheDocument();
    expect(screen.getByText(/视频 workflow 直接使用起始帧/)).toBeInTheDocument();
    expect(screen.getByText(/起始帧已选择/)).toBeInTheDocument();
  });
});

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
}
