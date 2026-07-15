import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import App from "@/App";
import type { Project } from "@/features/projects/types";
import type { ProjectExport, ProjectTimeline } from "@/features/timeline/types";

const projectId = "11111111-1111-4111-8111-111111111111";

const project: Project = {
  id: projectId,
  name: "逆袭归来",
  description: null,
  aspect_ratio: "9:16",
  default_style: null,
  default_language: "zh-CN",
  default_fps: 24,
  cover_image_path: null,
  created_at: "2026-07-15T00:00:00+00:00",
  updated_at: "2026-07-15T00:00:00+00:00"
};

const timelineReady: ProjectTimeline = {
  project_id: projectId,
  exportable: true,
  total_shots: 2,
  ready_clip_count: 2,
  missing_clip_count: 0,
  estimated_duration_seconds: 4,
  project_spec: { aspect_ratio: "9:16", default_fps: 24 },
  ffmpeg: { available: true, ffprobe_available: true, message: null },
  clips: [
    {
      shot_id: "shot-1",
      shot_order: 1,
      shot_name: "男主推门",
      status: "ready",
      adopted_video_output_id: "out-1",
      media_asset_id: "media-1",
      content_url: "/api/media/media-1/content",
      duration_seconds: 2,
      width: 640,
      height: 640,
      fps: 16,
      warnings: []
    },
    {
      shot_id: "shot-2",
      shot_order: 2,
      shot_name: "众人震惊",
      status: "ready",
      adopted_video_output_id: "out-2",
      media_asset_id: "media-2",
      content_url: "/api/media/media-2/content",
      duration_seconds: 2,
      width: 640,
      height: 640,
      fps: 16,
      warnings: []
    }
  ],
  blockers: []
};

const completedExport: ProjectExport = {
  id: "export-1",
  project_id: projectId,
  name: "最终成片",
  status: "completed",
  progress_percent: 100,
  current_stage: "已完成",
  clip_count: 2,
  duration_seconds: 4,
  target_width: 1080,
  target_height: 1920,
  target_fps: 24,
  video_codec: "libx264",
  output_format: "mp4",
  error_message: null,
  output_media_asset_id: "media-final",
  output_media_asset: {
    id: "media-final",
    project_id: projectId,
    media_type: "video",
    original_filename: "project-export-export-1.mp4",
    mime_type: "video/mp4",
    extension: "mp4",
    size_bytes: 2048,
    width: 1080,
    height: 1920,
    sha256: "abc",
    thumbnail_url: null,
    content_url: "/api/media/media-final/content",
    created_at: "2026-07-15T00:00:00+00:00"
  },
  created_at: "2026-07-15T00:00:00+00:00",
  updated_at: "2026-07-15T00:00:00+00:00",
  started_at: "2026-07-15T00:00:00+00:00",
  completed_at: "2026-07-15T00:01:00+00:00"
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

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" }
    })
  );
}

function mockTimelineApi({
  timeline = timelineReady,
  exports = []
}: {
  timeline?: ProjectTimeline;
  exports?: ProjectExport[];
}) {
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
    if (url === `/api/projects/${projectId}/timeline` && method === "GET") {
      return jsonResponse(timeline);
    }
    if (url === `/api/projects/${projectId}/exports` && method === "GET") {
      return jsonResponse({ items: exports, total: exports.length });
    }
    if (url === `/api/projects/${projectId}/production-status` && method === "GET") {
      return jsonResponse({
        project_id: projectId,
        summary: { total_shots: 2, blocked: 0, in_progress: 0, ready_for_video: 0, completed: 2 },
        items: [],
        total: 0
      });
    }
    if (url === `/api/projects/${projectId}/exports` && method === "POST") {
      return jsonResponse({ ...completedExport, status: "draft", output_media_asset: null }, 201);
    }
    if (url === `/api/projects/${projectId}/exports/export-1/mark-ready` && method === "POST") {
      return jsonResponse({ ...completedExport, status: "ready", output_media_asset: null });
    }
    if (url === `/api/projects/${projectId}/exports/export-1/start` && method === "POST") {
      return jsonResponse({ id: "export-1", status: "queued", progress_percent: 0, current_stage: "排队中" });
    }
    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });
  return requests;
}

test("时间线按镜头顺序显示并展示最终视频播放下载入口", async () => {
  mockTimelineApi({ exports: [completedExport] });

  renderRoute(`/projects/${projectId}/timeline`);

  expect(await screen.findByText("男主推门")).toBeInTheDocument();
  const first = screen.getByText("男主推门");
  const second = screen.getByText("众人震惊");
  expect(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByText("FFmpeg / FFprobe 已可用")).toBeInTheDocument();
  expect(screen.getByText("最终成片")).toBeInTheDocument();
  expect(screen.getByText("下载最终视频")).toBeInTheDocument();
});

test("FFmpeg 不可用时显示阻断并禁用创建导出", async () => {
  const blockedTimeline: ProjectTimeline = {
    ...timelineReady,
    exportable: false,
    ffmpeg: {
      available: false,
      ffprobe_available: false,
      message: "未检测到 FFmpeg"
    },
    blockers: [
      { code: "FFMPEG_UNAVAILABLE", shot_id: null, message: "未检测到 FFmpeg，无法开始成片导出。" }
    ]
  };
  mockTimelineApi({ timeline: blockedTimeline });

  renderRoute(`/projects/${projectId}/timeline`);

  expect(await screen.findByText("未检测到 FFmpeg / FFprobe，暂不能导出最终成片。")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /创建导出草稿/ })).toBeDisabled();
});

test("创建、标记就绪和开始导出使用只读时间线结果", async () => {
  const requests = mockTimelineApi({
    exports: [{ ...completedExport, status: "draft", output_media_asset: null }]
  });
  const user = userEvent.setup();

  renderRoute(`/projects/${projectId}/timeline`);
  await screen.findByText("男主推门");

  await user.click(screen.getByRole("button", { name: /创建导出草稿/ }));
  await user.click(screen.getByRole("button", { name: /标记可导出/ }));

  await waitFor(() => {
    expect(requests.some((request) => request.method === "POST" && request.url.endsWith("/exports"))).toBe(true);
    expect(requests.some((request) => request.url.endsWith("/exports/export-1/mark-ready"))).toBe(true);
  });
});

test("就绪导出可以开始并显示排队状态请求", async () => {
  const requests = mockTimelineApi({
    exports: [{ ...completedExport, status: "ready", output_media_asset: null }]
  });
  const user = userEvent.setup();

  renderRoute(`/projects/${projectId}/timeline`);
  await screen.findByText("男主推门");

  await user.click(screen.getByRole("button", { name: /开始导出/ }));

  await waitFor(() => {
    expect(requests.some((request) => request.url.endsWith("/exports/export-1/start"))).toBe(true);
  });
});

test("媒体库显示已完成最终导出视频", async () => {
  mockTimelineApi({ exports: [completedExport] });

  renderRoute(`/projects/${projectId}/media`);

  expect(await screen.findByText("最终成片")).toBeInTheDocument();
  expect(screen.queryByText("暂无最终导出视频")).not.toBeInTheDocument();
  expect(screen.getByText("下载最终视频")).toBeInTheDocument();
});

test("生产看板显示最终成片准备摘要", async () => {
  mockTimelineApi({ exports: [completedExport] });

  renderRoute(`/projects/${projectId}/production`);

  expect(await screen.findByText("最终成片准备")).toBeInTheDocument();
  expect(screen.getByText("已采用视频 2/2，阻断项 0。")).toBeInTheDocument();
});
