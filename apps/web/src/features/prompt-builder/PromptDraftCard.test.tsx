import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  hasKeyframePromptConflict,
  hasVideoPromptConflict,
  keyframeFieldsFromPromptDraft,
  videoFieldsFromPromptDraft
} from "./apply";
import { PromptDraftCard } from "./components/prompt-draft-card";
import type { PromptDraftResponse } from "./types";

const projectId = "11111111-1111-4111-8111-111111111111";
const shotId = "22222222-2222-4222-8222-222222222222";

const draft: PromptDraftResponse = {
  source_shot_updated_at: "2026-07-08T00:00:00+00:00",
  context_summary_zh: "当前镜头包含 1 位人物：男主。场景为办公楼门口。",
  first_frame_prompt_en: "cinematic short drama still frame, male lead at entrance",
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

function mockDraftApi(fail = false) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url =
      typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    if (url.endsWith(`/api/projects/${projectId}/shots/${shotId}/prompt-draft`)) {
      expect(init?.method).toBe("POST");
      if (fail) {
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

  it("shows a safe Chinese error without breaking the card", async () => {
    const user = userEvent.setup();
    mockDraftApi(true);

    renderWithClient(<PromptDraftCard projectId={projectId} shotId={shotId} />);
    await user.click(screen.getByRole("button", { name: "生成提示词草稿" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("提示词草稿生成失败");
    expect(screen.getByText("还没有生成提示词草稿。")).toBeInTheDocument();
  });
});

describe("prompt draft field mapping", () => {
  it("maps keyframe fields and detects overwrite conflicts", () => {
    expect(keyframeFieldsFromPromptDraft(draft)).toEqual({
      prompt_en: draft.first_frame_prompt_en,
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
