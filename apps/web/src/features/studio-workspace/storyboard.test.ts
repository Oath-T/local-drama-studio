import { describe, expect, it } from "vitest";

import type { ProjectProductionStatus, ShotProductionStatus } from "@/features/production-status/types";
import type { Shot } from "@/features/shots/types";

import { buildStoryboardShotItems, getStoryboardProductionItems } from "./storyboard";

const baseShot: Shot = {
  id: "shot-1",
  project_id: "project-1",
  name: "镜头 1",
  order_index: 1,
  story_description: null,
  visual_description: null,
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
  character_count: 0,
  reference_count: 0,
  characters: [],
  references: [],
  created_at: "2026-07-18T00:00:00+00:00",
  updated_at: "2026-07-18T00:00:00+00:00"
};

function production(overrides: Partial<ShotProductionStatus> = {}): ShotProductionStatus {
  return {
    shot_id: baseShot.id,
    shot_name: baseShot.name,
    order_index: 1,
    overall_status: "in_progress",
    steps: {
      assets: { status: "complete" },
      first_frame: {
        status: "adopted",
        task_id: "first-task",
        adopted_output_id: "first-output",
        adopted_media_asset_id: "media-first",
        content_url: "/api/media/first/content"
      },
      end_frame: {
        status: "completed",
        task_id: "end-task",
        adopted_output_id: null,
        adopted_media_asset_id: null,
        content_url: "/api/media/end/content"
      },
      video: {
        status: "not_created",
        task_id: null,
        adopted_output_id: null,
        adopted_media_asset_id: null,
        content_url: null,
        has_start_frame: true,
        has_end_frame: true
      }
    },
    blockers: [],
    next_actions: [],
    continuity_candidate: null,
    ...overrides
  };
}

describe("storyboard mapping", () => {
  it("normalizes project production items from both response shapes", () => {
    const status: ProjectProductionStatus = {
      summary: { total_shots: 1, blocked: 0, in_progress: 1, ready_for_video: 0, completed: 0 },
      shots: [production()]
    };

    expect(getStoryboardProductionItems(status)).toHaveLength(1);
  });

  it("shows adopted and latest completed frame previews", () => {
    const [item] = buildStoryboardShotItems({
      shots: [baseShot],
      productionStatus: {
        summary: { total_shots: 1, blocked: 0, in_progress: 1, ready_for_video: 0, completed: 0 },
        items: [production()]
      },
      videoAvailable: true
    });

    expect(item.firstFramePreview).toMatchObject({
      label: "首帧已采用",
      contentUrl: "/api/media/first/content"
    });
    expect(item.endFramePreview).toMatchObject({
      label: "尾帧待采用",
      contentUrl: "/api/media/end/content"
    });
  });

  it("marks video unavailable only when no real active or completed state exists", () => {
    const [item] = buildStoryboardShotItems({
      shots: [baseShot],
      productionStatus: {
        summary: { total_shots: 1, blocked: 0, in_progress: 1, ready_for_video: 0, completed: 0 },
        items: [production()]
      },
      videoAvailable: false
    });

    expect(item.videoPreview.label).toBe("视频能力不可用");
  });

  it("keeps a true active video run visible as generating", () => {
    const [item] = buildStoryboardShotItems({
      shots: [baseShot],
      productionStatus: {
        summary: { total_shots: 1, blocked: 0, in_progress: 1, ready_for_video: 0, completed: 0 },
        items: [
          production({
            steps: {
              ...production().steps,
              video: {
                status: "running",
                task_id: "video-task",
                adopted_output_id: null,
                adopted_media_asset_id: null,
                content_url: null,
                has_start_frame: true,
                has_end_frame: true
              }
            }
          })
        ]
      },
      videoAvailable: false
    });

    expect(item.videoPreview.label).toBe("视频生成中");
  });

  it("does not leave failed history looking like active generation", () => {
    const [item] = buildStoryboardShotItems({
      shots: [baseShot],
      productionStatus: {
        summary: { total_shots: 1, blocked: 1, in_progress: 0, ready_for_video: 0, completed: 0 },
        items: [production({ blockers: ["视频生成失败，请重试。"] })]
      },
      videoAvailable: true
    });

    expect(item.videoPreview.label).toBe("视频生成失败");
    expect(item.videoPreview.status).toBe("failed");
  });
});
