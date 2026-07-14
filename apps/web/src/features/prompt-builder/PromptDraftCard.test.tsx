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
  recommended_template_id: "enter_room_shock",
  applied_template_id: "enter_room_shock",
  workflow_hint: "pose_control",
  director_context: {
    shot_id: shotId,
    template_id: "enter_room_shock",
    subjects: [
      {
        shot_character_id: "33333333-3333-4333-8333-333333333333",
        character_id: "44444444-4444-4444-8444-444444444444",
        role: "primary",
        identity: "男主",
        look: "黑西装",
        position: "doorway foreground",
        start_action: "pushes the door open",
        end_action: "stands inside the room",
        expression_start: "urgent",
        expression_end: "determined"
      }
    ],
    scene: {
      scene_id: "55555555-5555-4555-8555-555555555555",
      state_id: "66666666-6666-4666-8666-666666666666",
      name: "董事会议室",
      state: "夜晚",
      layout: "long meeting table, doorway visible",
      lighting: "cold corporate lighting",
      environment_motion: "tense stillness"
    },
    reaction: {
      crowd_action: "everyone turns toward the entrance",
      crowd_emotion: "shock"
    },
    camera: {
      shot_scale: "medium wide shot",
      angle: "eye-level camera angle",
      height: "eye-level camera height",
      lens: "28mm",
      composition: "subject at doorway, crowd around table",
      movement: "slow push-in"
    },
    style: {
      preset: "cinematic_short_drama",
      aspect_ratio: "9:16"
    }
  },
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

  it("sends selected template and temporary director overrides", async () => {
    const user = userEvent.setup();
    const bodies: PromptDraftRequest[] = [];
    mockDraftApi({ onBody: (body) => bodies.push(body) });

    renderWithClient(<PromptDraftCard projectId={projectId} shotId={shotId} />);

    await user.click(screen.getByRole("combobox", { name: "镜头模板" }));
    await user.click(await screen.findByRole("option", { name: "闯入震惊" }));
    await user.type(screen.getByLabelText("人物位置"), "门口前景");
    await user.type(screen.getByLabelText("导演首帧动作"), "推门冲进会议室");
    await user.type(screen.getByLabelText("导演尾帧动作"), "站在会议室内对峙众人");
    await user.type(screen.getByLabelText("群众动作"), "所有人转头看向门口");
    await user.type(screen.getByLabelText("群众情绪"), "震惊");
    await user.type(screen.getByLabelText("构图"), "主角在门口，会议桌和众人可见");
    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));

    expect(await screen.findByText("导演结构预览")).toBeInTheDocument();
    expect(screen.getByText(/Workflow hint/)).toBeInTheDocument();
    expect(bodies[0]).toMatchObject({
      template_id: "enter_room_shock",
      director_overrides: {
        subject_position: "门口前景",
        start_action: "推门冲进会议室",
        end_action: "站在会议室内对峙众人",
        crowd_action: "所有人转头看向门口",
        crowd_emotion: "震惊",
        composition: "主角在门口，会议桌和众人可见"
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

  it("clears temporary director settings before regenerating", async () => {
    const user = userEvent.setup();
    const bodies: PromptDraftRequest[] = [];
    mockDraftApi({ onBody: (body) => bodies.push(body) });

    renderWithClient(<PromptDraftCard projectId={projectId} shotId={shotId} />);
    await user.type(screen.getByLabelText("人物位置"), "门口");
    await user.click(screen.getByRole("button", { name: "清空导演设置" }));
    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));

    expect(await screen.findByText("导演结构预览")).toBeInTheDocument();
    expect(bodies[0].director_overrides).toBeUndefined();
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
