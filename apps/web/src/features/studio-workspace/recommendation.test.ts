import { describe, expect, it } from "vitest";

import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import type { ProjectProductionStatus, ShotProductionStatus } from "@/features/production-status/types";
import type { Shot } from "@/features/shots/types";

import { buildStudioRecommendation, countAdoptedSteps } from "./recommendation";

const projectId = "project-1";

function shot(id: string, order = 1): Shot {
  return {
    id,
    project_id: projectId,
    name: `镜头 ${order}`,
    order_index: order,
    story_description: null,
    visual_description: "画面",
    dialogue: null,
    action_summary: null,
    duration_seconds: 2,
    shot_scale: "medium",
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
    reference_count: 0,
    characters: [],
    references: [],
    created_at: "2026-07-18T00:00:00+00:00",
    updated_at: "2026-07-18T00:00:00+00:00"
  };
}

function productionShot(
  id: string,
  first: string,
  end: string,
  video: string,
  order = 1,
  overall: ShotProductionStatus["overall_status"] = "in_progress"
): ShotProductionStatus {
  return {
    project_id: projectId,
    shot_id: id,
    shot_name: `镜头 ${order}`,
    order_index: order,
    overall_status: overall,
    steps: {
      assets: { status: "complete" },
      first_frame: {
        status: first as never,
        task_id: null,
        adopted_output_id: first === "adopted" ? "first" : null,
        adopted_media_asset_id: null,
        content_url: null
      },
      end_frame: {
        status: end as never,
        task_id: null,
        adopted_output_id: end === "adopted" ? "end" : null,
        adopted_media_asset_id: null,
        content_url: null
      },
      video: {
        status: video as never,
        task_id: null,
        adopted_output_id: video === "adopted" ? "video" : null,
        adopted_media_asset_id: null,
        content_url: null,
        has_start_frame: first === "adopted",
        has_end_frame: end === "adopted"
      }
    },
    blockers: [],
    next_actions: [],
    continuity_candidate: null,
    updated_at: "2026-07-18T00:00:00+00:00"
  };
}

function production(items: ShotProductionStatus[], blocked = 0): ProjectProductionStatus {
  return {
    project_id: projectId,
    summary: { total_shots: items.length, blocked, in_progress: 0, ready_for_video: 0, completed: 0 },
    items,
    total: items.length
  };
}

function task(status: GenerationTaskSummary["latest_run_status"]): GenerationTaskSummary {
  return {
    task_type: "keyframe",
    task_purpose: "first_frame",
    project_id: projectId,
    task_id: "task-1",
    task_name: "失败任务",
    task_status: "ready",
    readiness_status: "ready",
    shot_id: "shot-1",
    shot_name: "镜头 1",
    workflow_id: "keyframe_basic_v1",
    latest_run_id: "run-1",
    latest_run_number: 1,
    latest_run_status: status,
    run_count: 1,
    output_count: 0,
    has_outputs: false,
    has_selected_output: false,
    created_at: "2026-07-18T00:00:00+00:00",
    updated_at: "2026-07-18T00:00:00+00:00"
  };
}

function recommend(overrides: Partial<Parameters<typeof buildStudioRecommendation>[0]> = {}) {
  return buildStudioRecommendation({
    projectId,
    characterCount: 1,
    sceneCount: 1,
    shots: [shot("shot-1")],
    productionStatus: production([productionShot("shot-1", "adopted", "adopted", "adopted", 1, "completed")]),
    generationTasks: [],
    videoGenerationAvailable: true,
    ...overrides
  });
}

describe("buildStudioRecommendation", () => {
  it("covers all deterministic recommendation branches", () => {
    expect(recommend({ characterCount: 0 }).kind).toBe("create_character");
    expect(recommend({ sceneCount: 0 }).kind).toBe("create_scene");
    expect(recommend({ shots: [] }).kind).toBe("create_shot");
    expect(
      recommend({ productionStatus: production([productionShot("shot-1", "not_created", "not_created", "not_created")]) }).kind
    ).toBe("generate_first_frame");
    expect(
      recommend({ productionStatus: production([productionShot("shot-1", "adopted", "not_created", "not_created")]) }).kind
    ).toBe("generate_end_frame");
    expect(
      recommend({ productionStatus: production([productionShot("shot-1", "adopted", "adopted", "not_created")]), videoGenerationAvailable: true }).kind
    ).toBe("generate_video");
    expect(
      recommend({ productionStatus: production([productionShot("shot-1", "adopted", "adopted", "not_created")]), videoGenerationAvailable: false }).kind
    ).toBe("check_video_config");
    expect(recommend({ generationTasks: [task("failed")] }).kind).toBe("review_failed_tasks");
    expect(
      recommend({
        shots: [shot("shot-1"), shot("shot-2", 2)],
        productionStatus: production([
          productionShot("shot-1", "adopted", "adopted", "adopted", 1, "completed"),
          productionShot("shot-2", "adopted", "adopted", "adopted", 2, "in_progress")
        ])
      }).kind
    ).toBe("continue_next_shot");
    expect(recommend().kind).toBe("preview_final");
  });

  it("counts adopted first frame, end frame and video steps", () => {
    expect(
      countAdoptedSteps(
        production([
          productionShot("shot-1", "adopted", "adopted", "not_created"),
          productionShot("shot-2", "adopted", "not_created", "adopted")
        ])
      )
    ).toEqual({ firstFrame: 2, endFrame: 1, video: 1 });
  });
});
