import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  hasKeyframePromptConflict,
  hasVideoPromptConflict,
  keyframeFieldsFromPromptDraft,
  videoFieldsFromPromptDraft
} from "./apply";
import { PromptDraftCard } from "./components/prompt-draft-card";
import type { PromptDraftRequest, PromptDraftResponse } from "./types";

const projectId = "11111111-1111-4111-8111-111111111111";
const shotId = "22222222-2222-4222-8222-222222222222";

const draft: PromptDraftResponse = {
  source_shot_updated_at: "2026-07-08T00:00:00+00:00",
  applied_style: "cinematic_short_drama",
  context_summary_zh: "当前镜头包含 1 位人物：男主。场景为办公楼门口。",
  first_frame_prompt_en: "cinematic short drama first frame, male lead at entrance",
  end_frame_prompt_en: "same character, same outfit, continuity from first frame",
  motion_prompt_en: "smooth cinematic short drama motion, slow push-in",
  negative_prompt_en: "low quality, blurry, inconsistent character",
  camera_motion: "slow push-in",
  warnings: [{ code: "NO_CAMERA_MOTION", message: "缺少镜头运动描述。", severity: "info" }]
};

function renderWithClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } }
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function mockDraftApi(options: { fail?: boolean; onBody?: (body: PromptDraftRequest) => void } = {}) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url =
      typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    if (url.endsWith(`/api/projects/${projectId}/shots/${shotId}/prompt-draft`)) {
      expect(init?.method).toBe("POST");
      options.onBody?.(JSON.parse(String(init?.body)) as PromptDraftRequest);
      if (options.fail) {
        return jsonResponse({ error: { code: "PROMPT_FAILED", message: "failed" } }, 500);
      }
      return jsonResponse(draft);
    }
    return jsonResponse({ error: { code: "NOT_FOUND", message: "not found" } }, 404);
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("PromptDraftCard", () => {
  it("requests a prompt draft only after clicking and renders the result", async () => {
    const user = userEvent.setup();
    const fetchMock = mockDraftApi();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) }
    });

    renderWithClient(<PromptDraftCard projectId={projectId} shotId={shotId} />);

    expect(fetchMock).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));

    expect(await screen.findByText("镜头上下文")).toBeInTheDocument();
    expect(screen.getByDisplayValue(draft.context_summary_zh)).toBeInTheDocument();
    expect(screen.getByDisplayValue(draft.motion_prompt_en)).toBeInTheDocument();
    expect(screen.getByText(/NO_CAMERA_MOTION/)).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "复制提示词" })[0]);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(draft.context_summary_zh);
  });

  it("does not show task creation actions before a draft exists", () => {
    mockDraftApi();

    renderWithClient(
      <PromptDraftCard
        projectId={projectId}
        shotId={shotId}
        onCreateFirstFrameTask={vi.fn()}
        onCreateEndFrameTask={vi.fn()}
        onCreateVideoTask={vi.fn()}
      />
    );

    expect(screen.queryByText("从当前草稿创建任务")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "创建首帧任务" })).not.toBeInTheDocument();
  });

  it("confirms before creating tasks and keeps generation available", async () => {
    const user = userEvent.setup();
    mockDraftApi();
    const confirmMock = vi.spyOn(window, "confirm").mockReturnValue(true);
    let resolveCreate: () => void = () => undefined;
    const onCreateFirstFrameTask = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveCreate = resolve;
        })
    );
    const onCreateEndFrameTask = vi.fn().mockResolvedValue(undefined);
    const onCreateVideoTask = vi.fn().mockResolvedValue(undefined);

    renderWithClient(
      <PromptDraftCard
        projectId={projectId}
        shotId={shotId}
        onCreateFirstFrameTask={onCreateFirstFrameTask}
        onCreateEndFrameTask={onCreateEndFrameTask}
        onCreateVideoTask={onCreateVideoTask}
      />
    );

    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));
    expect(await screen.findByText("从当前草稿创建任务")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "创建首帧任务" }));

    expect(confirmMock).toHaveBeenCalledWith(expect.stringContaining("首帧关键帧任务草稿"));
    expect(confirmMock).toHaveBeenCalledWith(expect.stringContaining("当前草稿还有 1 条上下文提示"));
    expect(onCreateFirstFrameTask).toHaveBeenCalledWith(draft);
    expect(screen.getByRole("button", { name: "正在创建..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "创建尾帧任务" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "创建视频任务草稿" })).toBeDisabled();

    resolveCreate();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "创建首帧任务" })).not.toBeDisabled()
    );
    await user.click(screen.getByRole("button", { name: "创建尾帧任务" }));
    await user.click(screen.getByRole("button", { name: "创建视频任务草稿" }));
    expect(onCreateEndFrameTask).toHaveBeenCalledWith(draft);
    expect(onCreateVideoTask).toHaveBeenCalledWith(draft);
    expect(screen.getByRole("button", { name: "重新生成草稿" })).toBeEnabled();
  });

  it("does not create a task when confirmation is cancelled", async () => {
    const user = userEvent.setup();
    mockDraftApi();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const onCreateFirstFrameTask = vi.fn();

    renderWithClient(
      <PromptDraftCard
        projectId={projectId}
        shotId={shotId}
        onCreateFirstFrameTask={onCreateFirstFrameTask}
      />
    );

    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));
    await user.click(await screen.findByRole("button", { name: "创建首帧任务" }));

    expect(onCreateFirstFrameTask).not.toHaveBeenCalled();
  });

  it("sends style preset and one-time override settings", async () => {
    const user = userEvent.setup();
    const bodies: PromptDraftRequest[] = [];
    mockDraftApi({ onBody: (body) => bodies.push(body) });

    renderWithClient(<PromptDraftCard projectId={projectId} shotId={shotId} />);

    await user.click(screen.getByRole("combobox", { name: "风格预设" }));
    await user.click(await screen.findByRole("option", { name: "雨夜霓虹" }));
    await user.type(screen.getByLabelText("首帧动作补充"), "抬头看向雨夜大门");
    await user.type(screen.getByLabelText("尾帧动作补充"), "走进霓虹雨幕");
    await user.type(screen.getByLabelText("视频运动补充"), "从犹豫转为向前迈步");
    await user.type(screen.getByLabelText("镜头运动补充"), "慢速推进，轻微手持");
    await user.type(screen.getByLabelText("画面风格补充"), "冷蓝色雨夜反光");
    await user.type(screen.getByLabelText("情绪氛围补充"), "压抑转为坚定");
    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));

    expect(await screen.findByText("镜头上下文")).toBeInTheDocument();
    expect(bodies[0]).toMatchObject({
      style: "rain_night_neon",
      overrides: {
        start_action: "抬头看向雨夜大门",
        end_action: "走进霓虹雨幕",
        motion_direction: "从犹豫转为向前迈步",
        camera_motion: "慢速推进，轻微手持",
        visual_style: "冷蓝色雨夜反光",
        mood: "压抑转为坚定"
      }
    });
  });

  it("clears override settings before regenerating", async () => {
    const user = userEvent.setup();
    const bodies: PromptDraftRequest[] = [];
    mockDraftApi({ onBody: (body) => bodies.push(body) });

    renderWithClient(<PromptDraftCard projectId={projectId} shotId={shotId} />);
    await user.type(screen.getByLabelText("首帧动作补充"), "临时动作");
    await user.click(screen.getByRole("button", { name: "清空覆盖项" }));
    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));

    expect(await screen.findByText("镜头上下文")).toBeInTheDocument();
    expect(bodies[0].overrides).toBeUndefined();
  });

  it("shows a safe Chinese error without breaking the card", async () => {
    const user = userEvent.setup();
    mockDraftApi({ fail: true });

    renderWithClient(<PromptDraftCard projectId={projectId} shotId={shotId} />);
    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("提示词草稿生成失败");
    expect(screen.getByText("还没有生成提示词草稿。")).toBeInTheDocument();
  });
});

describe("prompt draft field mapping", () => {
  it("maps first and end keyframe fields and detects overwrite conflicts", () => {
    expect(keyframeFieldsFromPromptDraft(draft)).toEqual({
      prompt_en: draft.first_frame_prompt_en,
      negative_prompt: draft.negative_prompt_en
    });
    expect(keyframeFieldsFromPromptDraft(draft, "end")).toEqual({
      prompt_en: draft.end_frame_prompt_en,
      negative_prompt: draft.negative_prompt_en
    });
    expect(hasKeyframePromptConflict({ prompt_en: "", negative_prompt: "" })).toBe(false);
    expect(hasKeyframePromptConflict({ prompt_en: "existing", negative_prompt: "" })).toBe(true);
  });

  it("maps video fields and detects overwrite conflicts", () => {
    expect(videoFieldsFromPromptDraft(draft)).toEqual({
      prompt: draft.motion_prompt_en,
      negative_prompt: draft.negative_prompt_en,
      camera_motion: "slow push-in"
    });
    expect(hasVideoPromptConflict({ prompt: "", negative_prompt: "", camera_motion: "" })).toBe(
      false
    );
    expect(hasVideoPromptConflict({ prompt: "", negative_prompt: "", camera_motion: "push" })).toBe(
      true
    );
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
