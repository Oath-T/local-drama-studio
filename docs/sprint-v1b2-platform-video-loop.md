# Sprint V1-B2: Platform Wan2.2 Video Loop

## Adjusted Acceptance Boundary

The V1-B2 acceptance boundary was narrowed after the initial implementation work:

- Codex must not trigger real Wan2.2 video execution.
- Codex must not call ComfyUI `/prompt`.
- Codex must not create a real project VideoRun, VideoOutput, poster, or adopted video.
- Codex must not wait for long-running real model sampling.
- Codex is responsible for code implementation, automated tests, Mock Provider coverage, read-only Preview checks, UI implementation, documentation, and Git diff review.
- Product-manager manual validation owns real video generation, playback, adoption, Timeline verification, and Final Export verification.

Manual validation instructions are in:

- `docs/sprint-v1b2-manual-video-validation.md`

## Phase Status

This document was started in Phase 2 of Sprint V1-B2. Phase 2 is investigation and documentation only. No business logic, frontend code, backend code, database schema, workflow JSON, manifest, runner, provider, project data, VideoTask, VideoRun, VideoOutput, or MediaAsset was modified in this phase.

## Phase 0: V1-B1 Report Baseline

- Branch: `main`
- V1-B1 report commit: `28ad3f2eb60cd202e4163625858641baaadd8ab0`
- V1-B1 commit message: `docs: record Wan2.2 native video smoke test`
- `HEAD == origin/main`: yes before Phase 1
- Working tree after Phase 0: clean

V1-B1 confirmed:

- Four Wan2.2 FP8 model files passed size and SHA-256 checks.
- ComfyUI Loader recognized the high-noise UNET, low-noise UNET, UMT5 text encoder, and Wan VAE.
- Native ComfyUI FLF2V smoke succeeded.
- Output MP4 was H.264, 320x576, 8 FPS, 17 frames, about 2.125 seconds.
- No OOM and no retry were observed.
- Peak observed VRAM was about 12.9 GB.
- No platform VideoTask, VideoRun, or VideoOutput was created.
- Known issue: the temporary PowerShell prompt injection path corrupted Chinese prompt text into question marks.
- Known issue: the adopted keyframe media database size/hash values differ from the actual disk files.

## Phase 1: Environment State

| Item | Status |
| --- | --- |
| API | `http://127.0.0.1:8000/api/health` returns `{"status":"ok","service":"local-drama-studio-api"}` |
| Web | `http://127.0.0.1:5173` returns HTTP 200 |
| ComfyUI | `http://127.0.0.1:8188/system_stats`, `/object_info`, `/queue`, `/history` reachable |
| ComfyUI queue | empty: `queue_running=[]`, `queue_pending=[]` |
| ComfyUI PID | `238012` |
| ComfyUI command line | `"F:\AI\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe" main.py --listen 127.0.0.1 --port 8188` |
| ComfyUI process executable reported by Windows | `F:\AI\ComfyUI\ComfyUI\standalone-env\python.exe` |
| Web PID | `247832`, `node.exe`, Vite on port 5173 |
| API PID during Phase 1 | API was restarted from the project `.venv`; Windows process metadata may still show the venv base interpreter, while `.venv\Scripts\python.exe -c` reports `sys.executable=F:\LocalDramaStudio\apps\api\.venv\Scripts\python.exe` |
| FFmpeg | `ffmpeg version 8.1.1-essentials_build-www.gyan.dev` |
| FFprobe | `ffprobe version 8.1.1-essentials_build-www.gyan.dev` |
| GPU | NVIDIA GeForce RTX 5060 Ti, 16311 MiB |
| GPU state during check | 12554 MiB used, 3499 MiB free because ComfyUI had models loaded |
| System memory | about 32.6 GB total, about 11 GB free |
| F drive free space | about 516.6 GB |
| Git | clean before Phase 2 documentation |

Loader checks from ComfyUI `/object_info`:

| Loader | Required model | Recognized |
| --- | --- | --- |
| `UNETLoader` | `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | yes |
| `UNETLoader` | `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | yes |
| `CLIPLoader` | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | yes |
| `VAELoader` | `wan_2.1_vae.safetensors` | yes |

## Phase 2: Existing Video Chain Code Map

| Link | Current file(s) | Current implementation | Reuse | Minimum V1-B2 concern |
| --- | --- | --- | --- | --- |
| VideoTask data model | `apps/api/app/infrastructure/models/video_generation.py`, `apps/api/app/domain/video_generation.py` | `VideoGenerationTaskRecord` stores shot/project, prompt, negative prompt, duration, fps, width, height, seed, workflow, status. `VideoGenerationTaskInputRecord` stores `start_frame` and `end_frame` role inputs. | yes | Reuse existing model; no migration unless a later phase proves necessary. |
| VideoRun data model | `apps/api/app/infrastructure/models/video_generation.py` | `VideoGenerationRunRecord` stores provider, workflow id/version, queued/running/completed/failed/interrupted, provider job id, payload snapshot, safe error fields. | yes | Use existing run state; do not add second run model. |
| VideoOutput data model | `apps/api/app/infrastructure/models/video_generation.py` | `VideoGenerationOutputRecord` links run to `MediaAssetRecord`, stores output index, provider file info, dimensions, duration, fps, seed, `is_selected`. | yes | Reuse for candidates and adoption. |
| MediaAsset model | `apps/api/app/infrastructure/models/character.py`, `apps/api/app/domain/media_asset.py` | Shared media table supports image/video records and safe content URLs. | yes | Preserve safe path behavior and avoid absolute paths. |
| VideoOutput -> MediaAsset | `apps/api/app/service/video_generation_runner.py`, `apps/api/app/repository/video_generation_repository.py` | Runner stores generated video through `MediaStorageService.store_generated_video`, creates `MediaAssetRecord`, then creates `VideoGenerationOutputRecord`. | yes | Verify FFprobe/poster metadata in later phases if required. |
| Adopted video field | `apps/api/app/infrastructure/models/video_generation.py`, `apps/api/app/service/video_generation_service.py` | `VideoGenerationOutputRecord.is_selected` marks adopted video output. `select_output` and `unselect_output` exist. | yes | Must not auto-adopt real project output. |
| Quick Generate preview | `apps/api/app/api/quick_generate.py`, `apps/api/app/service/quick_generate_service.py` | `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/preview`; calls `WorkflowCapabilityRegistry`, then deterministic route. | yes | Extend existing request/response if needed; do not add parallel endpoint. |
| Quick Generate execute | `apps/api/app/api/quick_generate.py`, `apps/api/app/service/quick_generate_service.py` | `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate`; creates/reuses keyframe/video task, marks ready, creates run, background starts runner. | yes | Video branch currently hard-codes 2s/16fps/640x640 and reads selected keyframes. Later phases must align with V1-B2 preset. |
| Quick Generate sync output | `apps/api/app/api/quick_generate.py`, `apps/api/app/service/quick_generate_service.py`, `apps/api/app/service/canvas_output_sync_service.py` | `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/sync-output`; syncs generated outputs into canvas nodes/edges. | yes | Reuse; canvas sync failure must not fail real output. |
| Video task CRUD/run APIs | `apps/api/app/api/video_generation.py`, `apps/api/app/service/video_generation_service.py` | Existing endpoints for workflows, tasks, mark-ready/draft, runs, output select/unselect, input upload. | yes | Keep as professional path. |
| Video candidates API | `apps/api/app/api/video_generation.py`, `apps/api/app/service/video_generation_service.py` | Run list and task detail include outputs; output responses include media assets and selection state. | yes | Ensure ShotWorkbench displays latest candidates without auto-adoption. |
| Video adoption API | `apps/api/app/api/video_generation.py`, `apps/api/app/service/video_generation_service.py` | `POST /api/projects/{project_id}/video-tasks/{task_id}/outputs/{output_id}/select`; `DELETE .../select` unselects. | yes | Product manager must manually adopt real project output. |
| Production Status | `apps/api/app/api/production_status.py`, `apps/api/app/service/production_status_service.py`, `apps/api/app/repository/production_status_repository.py` | Read-only project/shot production status. Video step uses selected video output, active/completed video tasks, and task inputs. | yes | V1-A found possible misleading video status from old tasks; later phase must fix selector if confirmed. |
| Workflow Capability Registry | `apps/api/app/service/workflow_capability_registry.py` | Lists keyframe and video capabilities using existing services. | yes | Must report Wan available now that models are installed and ComfyUI is online. |
| Deterministic Router | `apps/api/app/service/quick_generate_service.py` | `_route` chooses matching capability and blocks missing prompt/adopted first/end frame. | yes | Must preserve stable routing and video blockers. |
| ComfyUI video provider | `apps/api/app/infrastructure/generation/comfyui_video_provider.py` | Handles health, object_info, upload input images, submit prompt, poll queue/history, fetch video outputs. | yes | Must ensure UTF-8 JSON bytes and no shell prompt construction. |
| Video workflow registry/mapper | `apps/api/app/infrastructure/generation/video_workflow.py` | Loads manifest/workflow, validates safety, applies image and parameter bindings, computed `duration_seconds_times_fps_plus_one`. | yes | Central place for workflow node contract and prompt injection. |
| Video runner | `apps/api/app/service/video_generation_runner.py` | Loads run snapshot, uploads input images to ComfyUI, builds workflow payload, submits, polls, saves outputs, syncs canvas. | yes | Must verify provider history/output discovery with real Wan run. |
| Output discovery | `apps/api/app/infrastructure/generation/comfyui_video_provider.py` | `fetch_video_outputs` reads history outputs by manifest `output_node_ids` and output file keys, filters video extensions. | yes | Confirm with real platform run. |
| Media sync | `apps/api/app/service/media_storage_service.py`, `apps/api/app/service/video_generation_runner.py` | Stores generated video into project storage as `MediaAsset(video)`. | yes | Avoid absolute path leaks; include poster only if already supported or minimally needed later. |
| Timeline | `apps/api/app/api/project_timeline.py`, `apps/api/app/service/project_timeline_service.py`, `apps/api/app/repository/project_timeline_repository.py` | Reads adopted video outputs in shot order. | yes | Real project shot 2 currently has no adopted video, so final export should clearly block. |
| Final Export | `apps/api/app/api/project_exports.py`, `apps/api/app/service/project_export_service.py`, `apps/api/app/service/export/export_runner.py` | Reads timeline snapshot and FFmpeg service; exports adopted video outputs. | yes | Full export should be validated on E2E project, not by mutating real project shot 2. |
| ShotWorkbench video UI | `apps/web/src/features/video-generation/components/video-generation-panel.tsx`, `apps/web/src/pages/shot-workbench-page.tsx` | Existing professional video generation panel and route. | yes | Must support real candidate display, manual adoption, refresh, playback. |
| Canvas quick generate UI | `apps/web/src/features/project-canvas/components/canvas-quick-generate-panel.tsx`, `apps/web/src/features/project-canvas/quick-generate-api.ts` | Calls unified Quick Generate preview/execute/sync APIs. | yes | V1-B2 should not re-expand complex canvas UI. |
| Minimal storyboard video status | `apps/web/src/features/studio-workspace/storyboard.ts`, `apps/web/src/features/studio-workspace/components/studio-workspace-page.tsx` | Studio storyboard shows real shot cards and generation status. | yes | Must show adopted video after manual adoption and avoid false "video generating". |
| Media content playback/download | `apps/api/app/api/media.py`, `apps/api/app/service/media_storage_service.py` | Safe media content endpoints exist. | yes | Add minimal Range only if browser video playback requires it. |

## Existing API Surface To Reuse

- `GET /api/projects/{project_id}/shots/{shot_id}/video-tasks`
- `POST /api/projects/{project_id}/shots/{shot_id}/video-tasks`
- `GET /api/projects/{project_id}/video-tasks/{task_id}`
- `PATCH /api/projects/{project_id}/video-tasks/{task_id}`
- `DELETE /api/projects/{project_id}/video-tasks/{task_id}`
- `POST /api/projects/{project_id}/video-tasks/{task_id}/mark-ready`
- `POST /api/projects/{project_id}/video-tasks/{task_id}/mark-draft`
- `POST /api/projects/{project_id}/video-tasks/{task_id}/runs`
- `GET /api/projects/{project_id}/video-tasks/{task_id}/runs`
- `GET /api/projects/{project_id}/video-tasks/{task_id}/runs/{run_id}`
- `POST /api/projects/{project_id}/video-tasks/{task_id}/outputs/{output_id}/select`
- `DELETE /api/projects/{project_id}/video-tasks/{task_id}/outputs/{output_id}/select`
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/preview`
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate`
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/sync-output`
- `GET /api/projects/{project_id}/shots/{shot_id}/production-status`

## Final Read-Only Acceptance After Product-Manager Generation

Date: 2026-07-20

This final closeout was performed after the product manager manually generated and manually adopted one real Wan2.2 video candidate. Codex did not call ComfyUI `/prompt`, did not create another `VideoRun`, did not create another `VideoOutput`, did not create another `MediaAsset`, and did not change adoption state.

Fixed validation target:

- Project: `8c6200f3-23b0-4af5-a4db-6a2bd9cd6702`
- Shot: `8b56399b-3d2a-4150-bdf9-4c840058a357`
- Workflow: `video_wan22_14b_flf2v_v1`
- Latest real `VideoRun`: `293dcae3-a97f-4f82-ae4b-9d65c1c2470a`
- Request ID: `f5bf01d1-9609-499b-8271-78ced649bb77`
- ComfyUI prompt ID / provider job ID: `9cf93e3b-2b1a-4b12-9a97-73a08b04c476`
- `VideoOutput`: `459e9063-0abb-44fe-9ae8-dd4af15dd2f5`
- Video `MediaAsset`: `b8a618c6-0e63-426b-adf1-cd1ee68437f9`
- Poster: stored as `thumbnail_relative_path` on the same video `MediaAsset`; there is no separate poster `MediaAsset` record.
- Adopted state: `is_selected=true`
- Adopted video outputs for the same shot: exactly `1`
- Completed video candidates for the same shot: `2`
- Active video runs for the same shot: `0`

The adopted media file exists under project storage:

- Relative path: `projects/8c6200f3-23b0-4af5-a4db-6a2bd9cd6702/media/generated-videos/9ba08954-f32d-4e76-bcbb-961e993d5474.mp4`
- Size: `957994` bytes
- SHA-256: `dba82e0c3dd3fa7c1b6cef606b4d8a6794b895ac688caca122ef33bf88753da6`
- Poster relative path: `projects/8c6200f3-23b0-4af5-a4db-6a2bd9cd6702/media/generated-video-posters/459e9063-0abb-44fe-9ae8-dd4af15dd2f5.png`
- Poster exists: yes

FFprobe read-only inspection:

- Codec: `h264`
- Pixel format: `yuv420p`
- Width: `320`
- Height: `576`
- FPS: `8`
- Frames: `33`
- Duration: `4.125` seconds

Prompt integrity:

- Positive prompt remained complete Chinese text: `镜头固定，人物缓慢抬头并自然呼吸，衣摆和发丝轻微摆动，环境光保持稳定，动作连续平滑，从首帧自然过渡到尾帧，不切换镜头。`
- Negative prompt remained complete Chinese text: `切镜，镜头跳动，快速摇镜，人物变形，面部变化，多余肢体，闪烁，光线突变，画面撕裂，严重模糊，文字，水印。`

Production status:

- Shot 1 video step is `adopted`.
- Shot 1 first frame remains `adopted`.
- Shot 1 end frame remains `adopted`.
- There is one historical failed video run (`video_comfyui_timeout`), but no active video run. The adopted video takes precedence over historical failed runs.
- The generated video content endpoint supports partial video reads with HTTP `206 Partial Content`, `content-type: video/mp4`, and `accept-ranges: bytes`.

Timeline read-only verification:

- Timeline reads adopted video outputs only.
- Shot 1 appears as a ready clip with `duration_seconds=4.125`, `width=320`, `height=576`, and `fps=8`.
- Shot order is still based on `order_index`.
- Shot 2 still exists with no adopted video.
- Timeline is not exportable because Shot 2 has no adopted video.
- Final Export preflight blocker: `SHOT_ADOPTED_VIDEO_MISSING` for Shot 2.
- The system did not skip Shot 2, delete Shot 2, generate Shot 2, or reuse Shot 1 video for Shot 2.

Quality note:

- Product manager confirmed that the real video candidate appeared, played successfully, and was not black or empty.
- Visual quality is acceptable only as a technical chain proof. Image/video quality tuning is deferred to a later dedicated sprint.

Regression note:

- A read-only `GET /api/projects` check in this environment still returned the E2E project `E2E_SPRINT_27C`. This is recorded as a separate project-list hygiene risk and was not modified during this V1-B2 closeout.

Final boundary:

- No second ComfyUI `/prompt` call was made by Codex.
- No second real video was generated by Codex.
- No auto-adoption was performed by Codex.
- `GET /api/projects/{project_id}/timeline`
- Project export APIs under `/api/projects/{project_id}/exports`

## Existing Wan Workflow Contract

Only the committed workflow below is in scope:

- `F:\LocalDramaStudio\workflows\video_wan22_14b_flf2v_v1.json`
- Manifest: `F:\LocalDramaStudio\workflows\video_wan22_14b_flf2v_v1.manifest.json`
- Workflow ID: `video_wan22_14b_flf2v_v1`
- Mode: `first_last_frame_to_video`

Current node mapping:

| Purpose | Node | Class | Input |
| --- | --- | --- | --- |
| Start frame | `80` | `LoadImage` | `image` |
| End frame | `89` | `LoadImage` | `image` |
| Positive prompt | `90` | `CLIPTextEncode` | `text` |
| Negative prompt | `78` | `CLIPTextEncode` | `text` |
| Width | `81` | `WanFirstLastFrameToVideo` | `width` |
| Height | `81` | `WanFirstLastFrameToVideo` | `height` |
| Length frames | `81` | `WanFirstLastFrameToVideo` | `length`, computed as `duration_seconds * fps + 1` |
| FPS | `86` | `CreateVideo` | `fps` |
| Seed | `84` | `KSamplerAdvanced` | `noise_seed` |
| Output | `83` | `SaveVideo` | output node |

The workflow file currently contains neutral placeholder image names `lds_start_frame_placeholder.png` and `lds_end_frame_placeholder.png`. No absolute path or temporary V1-B1 input filename was observed in the committed workflow during Phase 2.

## Real Project Read-only State

Real project: `8c6200f3-23b0-4af5-a4db-6a2bd9cd6702`

Shots:

| Order | Shot ID | Name |
| ---: | --- | --- |
| 1 | `8b56399b-3d2a-4150-bdf9-4c840058a357` | `镜头 1` |
| 2 | `9f97efaf-2b24-48c6-aa2e-0fe557331f0f` | `镜头 2` |

Shot 1 selected keyframes:

| Purpose | Output ID | Run ID | Task ID | MediaAsset ID |
| --- | --- | --- | --- | --- |
| `first_frame` | `6eb7c146-e7e9-41d9-8689-aebec0cb8448` | `0e18414a-6a29-4b1d-b45b-0d39d5597b90` | `b348cf86-3828-4723-9110-a25c3cc392e5` | `f1ec98a0-f375-4cad-af0b-ec0f0a5b59d8` |
| `end_frame` | `f5c0ef03-c455-4da4-afce-495d71057165` | `d7a4279d-2b2e-4e8a-ae45-54a2f3dfb01a` | `ad207e64-0436-403f-a881-568ca51bc046` | `9c2b821e-1a3e-4ee1-ac07-6428d590af80` |

Shot 1 video state:

- Existing video tasks: 6
- Latest useful Wan task observed: `adbd1fc2-0926-44c8-9938-16a7f93978fc`, status `ready`, workflow `video_wan22_14b_flf2v_v1`
- Existing video runs: 1
- Existing run: `3cdaf724-74d1-4ef0-8aa3-3b5555660d71`, status `failed`, error `video_comfyui_timeout`
- Existing video outputs: 0

This confirms V1-B2 must create the first real platform video candidate through the existing platform flow. It also confirms that old failed video task/run state may affect selectors and production status if not handled carefully in later phases.

## Phase 2 Conclusions

1. The platform already has a complete video domain model: task, role-based inputs, run, output, and MediaAsset linkage.
2. The platform already has unified Quick Generate preview, execute, and sync-output endpoints. V1-B2 must reuse them and must not add parallel `/wan-video` or `/generate-video-v2` endpoints.
3. The runner already uploads input images to ComfyUI instead of asking ComfyUI to read platform storage paths directly. This is the right direction for Windows safety.
4. The committed Wan workflow and manifest still match the expected node contract.
5. Real shot 1 has adopted first and end frame outputs, but no video output. A historical Wan run exists and failed by timeout.
6. Phase 3 should validate the workflow contract more deeply before any code change.
7. Phase 4 should focus on UTF-8 prompt injection through the existing workflow builder/provider path.
8. Phase 5 should implement or centralize adopted first/end frame resolution using Output -> Run -> Task, not by assuming output rows contain purpose directly.
9. Later phases should repair video production status selection so old draft/failed tasks do not show misleading active states.
10. No blockers were found in Phase 2 that require a new API family, new database model, or new workflow file.

## Phase 3: Fixed Workflow Node Contract

Phase 3 re-read the committed workflow and manifest directly:

- `workflows/video_wan22_14b_flf2v_v1.json`
- `workflows/video_wan22_14b_flf2v_v1.manifest.json`

Validation results:

| Check | Result |
| --- | --- |
| Workflow JSON parses | pass |
| Manifest JSON parses | pass |
| Workflow file in manifest | `video_wan22_14b_flf2v_v1.json` |
| Manifest mode | `first_last_frame_to_video` |
| Required roles | `start_frame`, `end_frame` |
| Output node IDs | `83` |
| Windows absolute path present | no |
| Data URI / base64 present | no |
| V1-B1 temp image names present | no |

Current node contract:

| Purpose | Node | Expected class | Input | Check |
| --- | --- | --- | --- | --- |
| Start frame image | `80` | `LoadImage` | `image` | pass |
| End frame image | `89` | `LoadImage` | `image` | pass |
| Positive prompt | `90` | `CLIPTextEncode` | `text` | pass |
| Negative prompt | `78` | `CLIPTextEncode` | `text` | pass |
| Video settings | `81` | `WanFirstLastFrameToVideo` | `width`, `height`, `length` | pass |
| FPS | `86` | `CreateVideo` | `fps` | pass |
| Seed | `84` | `KSamplerAdvanced` | `noise_seed` | pass |
| Output | `83` | `SaveVideo` | manifest output node | pass |

Model names found in the committed workflow:

- `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors`
- `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`
- `umt5_xxl_fp8_e4m3fn_scaled.safetensors`
- `wan_2.1_vae.safetensors`

Phase 3 conclusion: the committed workflow and manifest match the expected V1-B2 contract. No workflow JSON or manifest changes are needed before implementing UTF-8-safe platform prompt injection.

## Phase 4: UTF-8 Prompt Injection

Existing implementation path:

1. Frontend and API exchange JSON payloads.
2. `VideoGenerationTaskRecord.prompt` and `negative_prompt` store Python `str` values.
3. `VideoGenerationService._build_run_snapshot()` stores prompt text in `VideoRunSnapshot`.
4. `VideoGenerationService.build_provider_workflow()` maps snapshot text into `VideoWorkflowMappingValues`.
5. `VideoWorkflowRegistry.build_workflow()` deep-copies the committed workflow and writes prompt strings into manifest-bound nodes.
6. `ComfyUIVideoGenerationProvider.submit()` submits a Python dict through `httpx.AsyncClient.post(..., json={...})`.

No shell command or PowerShell stdin path is used by the platform prompt submission path.

Phase 4 code/test change:

- Updated `apps/api/tests/test_video_generation.py` helper `workflow_mapping_values()` to accept a custom positive prompt.
- Added `test_wan_workflow_preserves_utf8_prompts_in_payload`.

The new test asserts that the following survive workflow injection and UTF-8 JSON roundtrip exactly:

- Pure Chinese text.
- Chinese punctuation.
- Mixed Chinese and English.
- Newlines.
- Double quotes.
- Single quotes.
- Backslashes.
- Emoji.
- Negative prompt text.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\pytest.exe tests\test_video_generation.py -k "utf8_prompts or wan_workflow_builds_real_mapping or wan_workflow_negative_prompt"
```

Result:

- 3 passed
- 15 deselected
- 1 existing Starlette/httpx deprecation warning

Phase 4 conclusion: the platform workflow payload path preserves UTF-8 prompt strings at the Python dict and JSON payload level. The V1-B1 question-mark corruption came from the temporary PowerShell/Python workflow-writing path, not from the committed platform workflow builder path.

## Phase 5: Adopted First/End Frame Resolution

Existing risk found:

- Quick Generate video preview and execute only checked for the first selected keyframe output by `project_id`, `shot_id`, and `purpose`.
- The code did correctly join `Output -> Run -> Task` for purpose lookup, but it did not centralize validation of media existence, media type, backing file existence, or duplicate selected outputs.
- Production Status previously judged video input readiness from existing `VideoTaskInput` rows only. If a shot had adopted first/end frame outputs but an older draft video task had no inputs, it could still surface `video_missing_start_frame` or `video_missing_end_frame`.

Phase 5 backend changes:

- Added `SelectedKeyframeOutputData` and `QuickGenerateRepository.list_selected_keyframe_outputs()`.
- Added Quick Generate adopted video input resolution that follows:
  `Shot -> KeyframeGenerationTask -> KeyframeGenerationRun -> KeyframeGenerationOutput -> MediaAsset`.
- Quick Generate video preview and execute now share the same adopted input resolver.
- The resolver returns explicit blocker codes for:
  - missing adopted first frame
  - missing adopted end frame
  - duplicate selected first frame outputs
  - duplicate selected end frame outputs
  - missing media asset
  - non-image media asset
  - missing backing file
- The resolver allows the same image as both first and end frame, but returns `same_start_and_end_frame` as a warning.
- Production Status now treats adopted first/end frame outputs as available video inputs when a VideoTask has not yet stored explicit `start_frame` / `end_frame` inputs.

Phase 5 safety notes:

- No database writes are performed during preview/resolution.
- No selected/adopted state is repaired automatically.
- No source image is modified, cropped, copied, or deleted.
- No real project IDs or MediaAsset IDs are hard-coded in business code.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\quick_generate_service.py app\repository\quick_generate_repository.py app\service\production_status_service.py tests\test_quick_generate.py tests\test_production_status.py
.\.venv\Scripts\pytest.exe tests\test_quick_generate.py tests\test_production_status.py -q
```

Result:

- Ruff targeted check passed.
- 17 passed
- 1 existing Starlette/httpx deprecation warning

Phase 5 conclusion: platform video preview/execute now resolves adopted first and end frames through the correct Output -> Run -> Task relationship, validates media/file availability before execution, and Production Status no longer depends solely on existing VideoTask input rows to know that adopted first/end frames exist.

## Phase 6: Stale MediaAsset Metadata

Known issue:

- Existing adopted keyframe images may have stale `media_assets.size_bytes`, `media_assets.sha256`, width, height, or MIME metadata compared with the current file on disk.
- This sprint must not perform a full-library repair, nor silently mutate real project media records during preview.

Phase 6 backend changes:

- Added `MediaStorageService.inspect_image_file(relative_path)`.
- The method is read-only:
  - resolves the existing storage-relative path safely
  - reads the file
  - verifies it as an image
  - computes current size, SHA-256, width, height, and MIME type
  - returns metadata without writing to the database
- Quick Generate adopted video input resolution now compares actual file metadata with the stored `MediaAssetRecord`.
- If the image file exists and is readable but metadata differs, preview returns `media_metadata_stale` as a warning, not a blocker.
- Missing files still block with `adopted_first_frame_file_missing` / `adopted_end_frame_file_missing`.
- Files that exist but cannot be validated as images block with `adopted_first_frame_not_image` / `adopted_end_frame_not_image`.

Safety notes:

- No migration was added.
- No real project media rows are refreshed automatically.
- No preview path writes to the database.
- Newly generated videos still use the existing generated-video storage path, which records metadata from the actual saved bytes.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\media_storage_service.py app\service\quick_generate_service.py tests\test_quick_generate.py
.\.venv\Scripts\pytest.exe tests\test_quick_generate.py -q
```

Result:

- Ruff targeted check passed.
- 11 passed
- 1 existing Starlette/httpx deprecation warning

Phase 6 conclusion: stale image metadata no longer blocks video preview or execution when the file itself is present and readable; the platform surfaces a safe warning and keeps the database unchanged.

## Phase 7: V1 Video Parameter Contract

V1 product contract:

- Users provide only:
  - video action prompt
  - optional negative prompt
  - duration preset
  - FPS
  - optional seed
- The platform resolves project, shot, adopted start/end frames, workflow, dimensions, frame count, and internal workflow/model settings.
- UI must not expose loader names, model filenames, CFG, steps, sampler, scheduler, noise switch, or workflow node IDs.

Phase 7 backend changes:

- Extended the existing Quick Generate request schema with optional:
  - `duration_preset`: `short_test` or `standard_short`
  - `fps`
  - `seed`
- Quick Generate video execute now uses V1 low-cost Wan defaults:
  - `short_test`: 320 x 576, duration_seconds `2.0`, default FPS `8`
  - `standard_short`: 320 x 576, duration_seconds `4.0`, default FPS `8`
- If `fps` is provided, it overrides the preset FPS.
- If `seed` is provided, it is stored on the VideoTask and then fixed into the run snapshot by the existing VideoGenerationService path.
- If `seed` is omitted, the existing run snapshot builder generates a legal random seed at run creation time and persists it in `submitted_payload_snapshot`.
- Workflow frame count remains computed by the existing manifest binding:
  `length = duration_seconds * fps + 1`.

No changes were made to:

- workflow JSON
- workflow manifest
- ComfyUI provider
- runner submission path
- database schema

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\api\schemas\quick_generate.py app\service\quick_generate_service.py tests\test_quick_generate.py
.\.venv\Scripts\pytest.exe tests\test_quick_generate.py -q
```

Result:

- Ruff targeted check passed.
- 12 passed
- 1 existing Starlette/httpx deprecation warning

Phase 7 conclusion: Quick Generate video execution now uses the V1 low-cost Wan parameter contract and supports explicit FPS/seed without exposing internal workflow settings.

## Phase 8: Video Preview Contract

Endpoint reused:

- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/preview`

No new preview endpoint was added.

Preview remains read-only:

- does not create VideoTask
- does not create VideoRun
- does not create VideoOutput
- does not create MediaAsset
- does not copy input images
- does not submit ComfyUI
- does not modify workflow files
- does not modify Shot data
- does not modify adopted state

Phase 8 backend changes:

- Extended `QuickGeneratePreviewResponse` while preserving the existing `route` field for backward compatibility.
- Added top-level preview fields:
  - `ready`
  - `can_execute`
  - `blockers`
  - `warnings`
  - `capability`
  - `workflow_id`
  - `resolved_inputs`
  - `resolved_parameters`
  - `estimated_output`
  - `active_run`
- Video `resolved_inputs` reports:
  - `start_frame_media_asset_id`
  - `end_frame_media_asset_id`
  - `start_frame_available`
  - `end_frame_available`
- Video `resolved_parameters` reports:
  - `width`
  - `height`
  - `frame_count`
  - `fps`
  - `seed`
  - `expected_duration`
- Video `estimated_output` reports video type, dimensions, FPS, frame count, and expected duration.

Preview blocker mapping:

| Internal route issue | Preview blocker |
| --- | --- |
| `prompt` | `invalid_prompt` |
| `adopted_first_frame` | `missing_start_frame` |
| `adopted_end_frame` | `missing_end_frame` |
| `adopted_first_frame_file_missing` | `start_frame_file_missing` |
| `adopted_end_frame_file_missing` | `end_frame_file_missing` |
| `adopted_first_frame_not_image` | `invalid_start_media_type` |
| `adopted_end_frame_not_image` | `invalid_end_media_type` |
| `multiple_adopted_first_frame` | `ambiguous_adopted_start_frame` |
| `multiple_adopted_end_frame` | `ambiguous_adopted_end_frame` |
| route missing models | `missing_model` |
| route missing nodes | `missing_node` |
| active queued/running run | `active_run_exists` |

Preview warnings currently include:

- `media_metadata_stale`
- `same_start_and_end_frame`
- `low_resolution_preset`
- `no_negative_prompt`

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\api\schemas\quick_generate.py app\service\quick_generate_service.py tests\test_quick_generate.py
.\.venv\Scripts\pytest.exe tests\test_quick_generate.py -q
```

Result:

- Ruff targeted check passed.
- 12 passed
- 1 existing Starlette/httpx deprecation warning

Phase 8 conclusion: video preview now exposes the minimum UI-facing readiness contract without creating tasks, runs, outputs, media assets, ComfyUI work, or database mutations.

## Phase 9: Workflow Capability Detection

Existing implementation confirmed:

- Video workflow availability is resolved by `VideoGenerationService.list_workflows()`.
- The service checks:
  - provider/ComfyUI health
  - committed workflow file existence
  - workflow JSON parsing/safety
  - required node types against `/object_info`
  - model filenames against actual Loader dropdown options from `/object_info`
- Model detection is based on Loader input names:
  - `UNETLoader.unet_name`
  - `CLIPLoader.clip_name`
  - `VAELoader.vae_name`
- The check therefore follows ComfyUI Loader-visible values rather than hard-coded historical folders such as `unet` or `clip`.

Phase 9 backend changes:

- Extended `WorkflowCapabilityResponse` with:
  - `available`
  - `blockers`
  - `checked_at`
- `available` mirrors the executable workflow availability check.
- `blockers` contains the workflow missing requirements.
- `checked_at` records the request-time capability check timestamp.
- Existing fields remain for compatibility:
  - `executable`
  - `missing_models`
  - `missing_nodes`
  - `missing_requirements`

Wan capability expectations:

- With the V1-B1 confirmed Loader values, `video_wan22_14b_flf2v_v1` reports `available=true`.
- If any Wan model is absent from the corresponding Loader options, the workflow reports `available=false` and includes `model_file_missing:...`.
- If a required node class is absent from `/object_info`, the workflow reports `node_type_missing:...`.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\api\schemas\quick_generate.py app\service\workflow_capability_registry.py tests\test_quick_generate.py
.\.venv\Scripts\pytest.exe tests\test_quick_generate.py -q
```

Result:

- Ruff targeted check passed.
- 12 passed
- 1 existing Starlette/httpx deprecation warning

Phase 9 conclusion: capability responses now expose availability, blockers, and check time while preserving existing workflow/model/node detection behavior based on real ComfyUI `/object_info` Loader options.

## Phase 10: VideoTask And VideoRun Creation

Endpoint reused:

- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate`

No parallel video execute endpoint was added.

Existing model reuse:

- `video_generation_tasks`
- `video_generation_task_inputs`
- `video_generation_runs`
- `quick_generate_requests`

Phase 10 backend changes:

- Extended existing `VideoRunSnapshot` JSON with:
  - `project_id`
  - `request_id`
  - `start_frame_media_asset_id`
  - `end_frame_media_asset_id`
  - `frame_count`
- Extended `VideoGenerationService.create_run()` with optional `request_id`.
- Quick Generate video execute passes `payload.request_id` into VideoRun snapshot creation.
- No migration was added because existing `submitted_payload_snapshot` JSON stores these run parameters safely.

Run persistence coverage:

| Required item | Storage location |
| --- | --- |
| `project_id` | `video_generation_runs.project_id` and snapshot |
| `shot_id` | snapshot |
| `video_task_id` | `video_generation_runs.video_task_id` and snapshot |
| `workflow_id` | `video_generation_runs.workflow_id` and snapshot |
| `prompt` | snapshot |
| `negative_prompt` | snapshot |
| `seed` | snapshot |
| `width` | snapshot |
| `height` | snapshot |
| `frame_count` | snapshot |
| `fps` | snapshot |
| `start_frame_media_asset_id` | snapshot |
| `end_frame_media_asset_id` | snapshot |
| `request_id` | `quick_generate_requests.request_id` and snapshot |
| `created_at` | `video_generation_runs.created_at` |

Existing runner behavior remains responsible for:

- saving `provider_job_id` after ComfyUI submission
- setting `started_at`
- setting `completed_at`
- setting failed status and safe error fields

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\api\schemas\video_generation.py app\service\video_generation_service.py app\service\quick_generate_service.py tests\test_quick_generate.py
.\.venv\Scripts\pytest.exe tests\test_quick_generate.py tests\test_video_generation.py -q
```

Result:

- Ruff targeted check passed.
- 30 passed
- 4 existing Starlette/httpx deprecation warnings

Phase 10 conclusion: video quick-generate execution creates/reuses the existing VideoTask, creates a VideoRun only after explicit execute, and persists the V1 run contract in existing run/request records without a migration.

## Phase 11: Idempotency And Concurrency Protection

Existing mechanism reused:

- `quick_generate_requests` stores `project_id`, `shot_id`, `mode`, `request_id`, `task_id`, `run_id`, `run_type`, and serialized response JSON.
- Quick Generate execution checks an existing request before doing work.
- Quick Generate also checks active queued/running runs for the same shot and mode.
- A process-local lock serializes same project/shot/mode execution inside the API process.

Phase 11 behavior:

- Same `request_id` returns the same Run response and does not create another Run.
- Different `request_id` while a video Run is queued/running returns the current active Run.
- Failed runs do not block later new video candidates.
- Completed runs do not block later new video candidates.
- Historical runs and outputs are not deleted or overwritten.
- Backend protection exists independently from frontend button disabled state.

Current limitation:

- Cross-process race protection still depends on the existing database request uniqueness and active-run checks. No new distributed lock or migration was added in this phase.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check tests\test_quick_generate.py app\service\quick_generate_service.py
.\.venv\Scripts\pytest.exe tests\test_quick_generate.py -q
```

Result:

- Ruff targeted check passed.
- 15 passed
- 1 existing Starlette/httpx deprecation warning

Phase 11 conclusion: video Quick Generate now has explicit automated coverage for request-id idempotency, active-run reuse, and new candidate creation after failed/completed terminal runs.

## Phase 12: ComfyUI Input File Preparation

Runner path checked:

- `VideoGenerationRunner._upload_inputs()`
- `VideoGenerationRunner._read_input_image()`
- `VideoGenerationRunner._safe_input_filename()`
- `ComfyUIVideoGenerationProvider.upload_input_image()`

Phase 12 backend changes:

- Re-resolves each required input role from the immutable `VideoRunSnapshot`.
- Re-loads the `MediaAsset` within the current project before upload.
- Verifies the source file still exists under `STORAGE_ROOT`.
- Reads the real source bytes without modifying, cropping, or re-encoding them.
- Re-inspects the actual image file and uses the detected legal image extension rather than trusting stale database metadata.
- Computes SHA-256 from the source bytes.
- Sends exactly those bytes to ComfyUI `/upload/image`.
- Re-computes SHA-256 from the uploaded payload bytes after the upload call returns and requires it to match the source SHA-256.
- Keeps source media untouched and never deletes source files.
- Marks the Run failed with the existing safe reference-upload error if input preparation or upload fails.

Safe filename rule implemented:

```text
lds_video_<shot_short>_<run_short>_start.<ext>
lds_video_<shot_short>_<run_short>_end.<ext>
```

Where:

- `shot_short` = first 8 characters of the Shot ID from the Run snapshot.
- `run_short` = first 8 characters of the Video Run ID.
- role suffix is `start` or `end`.
- extension comes from actual detected image format.

The generated ComfyUI workflow receives only the returned uploaded file name. It does not include Windows absolute paths, storage paths, project names, Chinese shot names, or original upload file names.

Note on post-copy verification:

- The current provider boundary uploads via ComfyUI HTTP `/upload/image` and does not expose a read-back API for the remote input file.
- The runner therefore verifies that the exact bytes read from storage are the exact bytes passed to the provider after the upload returns.
- A future local-input-directory provider may add true destination read-back SHA-256 without changing the public task contract.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\video_generation_runner.py app\service\media_storage_service.py tests\test_video_generation.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py -q
```

Result:

- Ruff targeted check passed.
- 18 passed
- 4 existing Starlette/httpx deprecation warnings

Phase 12 conclusion: ComfyUI input preparation now uses deterministic safe filenames, actual source image format, project-scoped media resolution, and SHA-256 payload verification before submitting the Wan workflow.

## Phase 13: ComfyUI Submission And Polling

Existing provider/runner path reused:

- `ComfyUIVideoGenerationProvider.submit()`
- `ComfyUIVideoGenerationProvider.get_status()`
- `VideoGenerationRunner.run_task()`
- `VideoGenerationRunner._poll_provider_job()`

No frontend direct ComfyUI call was added.

Phase 13 behavior:

- Backend submits ComfyUI `/prompt` through the existing provider.
- Request body is JSON and preserves UTF-8 prompt text.
- ComfyUI `prompt_id` is stored as `video_generation_runs.provider_job_id`.
- Non-empty `node_errors` from `/prompt` immediately fail submission with the existing safe node-error code.
- Polling reads `/history/{prompt_id}` first.
- Queue state is read from `/queue` only when history is not terminal.
- A Run is treated as completed only when the matching history item is successful/completed and contains outputs.
- History `execution_error`, `failed`, or `error` maps to failed.
- Timeout uses the existing runner timeout setting.
- No automatic retry, seed replacement, frame-count reduction, or workflow replacement was added.
- No new status enum was added; existing queued/running/completed/failed/interrupted statuses remain in use.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\infrastructure\generation\comfyui_video_provider.py tests\test_video_generation.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py -q
```

Result:

- Ruff targeted check passed.
- 20 passed
- 4 existing Starlette/httpx deprecation warnings

Phase 13 conclusion: video submission and polling now have explicit coverage for node-error failure and for history success/completed status before marking a Run completed.

## Phase 14: Output Discovery And Path Safety

Existing provider path reused:

- `ComfyUIVideoGenerationProvider.fetch_video_outputs()`
- `ComfyUIVideoGenerationProvider._output_file_refs()`

Phase 14 behavior:

- Output discovery reads only the matching ComfyUI `prompt_id` history.
- Output discovery uses only manifest `output_node_ids`.
- Output discovery walks only manifest `output_file_keys`.
- Output discovery accepts only manifest `allowed_output_extensions`.
- It does not scan the ComfyUI output directory.
- It does not guess by file modification time.
- It does not use fixed smoke-test output filenames.

Path safety filtering added:

- Reject filename containing `/` or `\`.
- Reject Windows absolute paths or drive-prefixed paths.
- Reject Unix absolute paths.
- Reject `..` path components.
- Reject unsafe `subfolder` values.
- Reject output `type` outside the accepted ComfyUI output/temp categories.
- The platform copies only downloaded bytes returned by the existing provider `/view` request and stores them through `MediaStorageService`.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\infrastructure\generation\comfyui_video_provider.py tests\test_video_generation.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py -q
```

Result:

- Ruff targeted check passed.
- 20 passed
- 4 existing Starlette/httpx deprecation warnings

Phase 14 conclusion: video output discovery remains prompt-history based and now filters unsafe ComfyUI output references before download/storage.

## Phase 15: FFprobe And Video Compatibility

Existing FFmpeg service reused:

- `FfmpegService.probe()`
- `FfmpegService.normalize_clip()`

Phase 15 backend changes:

- `VideoProbe` now records:
  - `format_name`
  - `duration_seconds`
  - `size_bytes`
  - `codec`
  - `codec_type`
  - `width`
  - `height`
  - `pixel_format`
  - `average_frame_rate`
  - `frame_count`
  - `audio_stream_count`
- FFprobe now reads all streams, selects the first video stream, and counts audio streams.
- Video runner probes each downloaded/saved ComfyUI output before creating `MediaAsset` / `VideoOutput`.
- Successful video requirements:
  - video stream exists
  - duration > 0
  - size > 0
  - width > 0
  - height > 0
  - frame count > 1
  - FPS > 0
- Browser direct-compatible outputs are used as-is when `codec=h264` and `pix_fmt=yuv420p`.
- Non-compatible outputs are converted once using the existing FFmpeg normalization path:
  - MP4/H.264
  - yuv420p
  - same detected width/height
  - same detected FPS
  - no audio track is added
- Failed probe/transcode marks the Run failed through the existing output-save error path.
- No upscaling, interpolation, quality enhancement, audio creation, or multiple transcodes were added.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\video_generation_runner.py app\service\export\ffmpeg_service.py tests\test_video_generation.py tests\test_ffmpeg_service.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py tests\test_ffmpeg_service.py -q
```

Result:

- Ruff targeted check passed.
- 25 passed
- 4 existing Starlette/httpx deprecation warnings

Phase 15 conclusion: generated video outputs now pass through FFprobe validation before output records are created, with one conservative compatibility transcode when needed.

## Phase 16: Video Sync To Project Storage

Existing storage path reused:

- `MediaStorageService.store_generated_video()`
- `VideoGenerationRunner._save_outputs()`

Target storage directory:

```text
storage/projects/<project_id>/media/generated-videos/
```

Phase 16 behavior:

- Provider output bytes are saved through `MediaStorageService`; no unsafe path concatenation was added.
- Final stored video filename is generated from the MediaAsset UUID.
- Final file SHA-256 and size are computed from the actual stored bytes.
- FFprobe metadata is used for VideoOutput width, height, duration, and FPS.
- `MediaAsset` is created only after the output has passed storage and FFprobe validation.
- `VideoOutput` is linked to the exact `VideoRun`.
- `VideoRun` is marked completed only after output save/sync succeeds.
- Outputs are created with `is_selected=false`; no automatic adoption was added.
- Existing idempotency prevents duplicate `VideoOutput` records for the same provider filename/subfolder/type/output index.
- Canvas output sync is invoked after video outputs are saved, using the existing `CanvasOutputSyncService`.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check tests\test_video_generation.py app\service\video_generation_runner.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py -q
```

Result:

- Ruff targeted check passed.
- 22 passed
- 4 existing Starlette/httpx deprecation warnings

Phase 16 conclusion: ComfyUI video outputs now create project-scoped `MediaAsset(video)` and `VideoOutput` records from verified stored bytes and FFprobe metadata, without auto-adoption.

## Phase 17: Video Poster

Existing data model reused:

- Video output poster is exposed through the existing video `MediaAsset.thumbnail_relative_path`.
- No `VideoOutput.poster_media_asset_id` field or migration was added.
- Existing `media_asset.thumbnail_url` response field locates the poster.

Phase 17 backend changes:

- `FfmpegService.extract_poster()` extracts one PNG frame at 0.2 seconds.
- Poster target directory:

```text
storage/projects/<project_id>/media/generated-video-posters/
```

- Poster filename:

```text
<video_output_id>.png
```

- Poster path is generated by `MediaStorageService`.
- Poster file is validated with existing image inspection.
- Video thumbnail endpoint now returns the thumbnail file's actual MIME type, so existing WebP thumbnails and new PNG video posters both serve correctly.

Failure behavior:

- Poster generation failure logs a warning.
- Poster generation failure does not fail an otherwise successful video Run.
- UI can still use the existing video placeholder when `thumbnail_url` is null.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\video_generation_runner.py app\service\export\ffmpeg_service.py app\service\media_storage_service.py app\api\characters.py app\service\video_generation_service.py tests\test_video_generation.py tests\test_ffmpeg_service.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py tests\test_ffmpeg_service.py -q
```

Result:

- Ruff targeted check passed.
- 26 passed
- 4 existing Starlette/httpx deprecation warnings

Phase 17 conclusion: completed video outputs now get a best-effort PNG poster through the existing media thumbnail path, without blocking successful video runs.

## Phase 18: Video Candidates API

Existing API reused:

- `GET /api/projects/{project_id}/shots/{shot_id}/video-tasks`
- `GET /api/projects/{project_id}/video-tasks/{task_id}/runs`
- `GET /api/projects/{project_id}/video-runs/{run_id}`

No parallel candidate endpoint was added.

Candidate data source:

- Active Run: runs with `queued` or `running` status from the existing runs list.
- Latest completed Run: existing runs list sorted by `run_number desc`, `created_at desc`, `id desc`.
- Completed candidates: `VideoRun.outputs` for completed runs only.
- Failed history: failed/interrupted runs remain visible as runs, but are not candidates.
- Adopted video: existing `VideoOutput.is_selected` / `VideoTask.selected_output`.

Candidate response fields are available through existing response shape:

- `VideoOutput.id`
- `VideoOutput.media_asset_id`
- `VideoOutput.run_id`
- `VideoOutput.width`
- `VideoOutput.height`
- `VideoOutput.fps`
- `VideoOutput.duration_seconds`
- `VideoOutput.seed`
- `VideoOutput.is_selected`
- `VideoOutput.media_asset.content_url`
- `VideoOutput.media_asset.thumbnail_url`
- prompt/negative prompt/frame count from `VideoRun.submitted_payload_snapshot`

The API does not expose:

- ComfyUI loader names
- model paths
- internal workflow node IDs
- storage relative paths

## Phase 19: Video Adoption

Existing API reused:

- `POST /api/projects/{project_id}/video-outputs/{output_id}/select`
- `DELETE /api/projects/{project_id}/video-outputs/{output_id}/select`

Phase 19 backend changes:

- Adoption remains explicit; no video output is auto-selected after generation.
- Selection verifies the output belongs to the project.
- Selection verifies the parent Run is `completed`.
- Selection verifies the `MediaAsset(video)` exists.
- Selection verifies the media file exists under storage.
- Selection runs FFprobe and requires a valid video stream, positive duration, positive size, positive dimensions, frame count > 1, and FPS > 0.
- Selection remains idempotent for the same output.
- Selecting a new output clears previous selected outputs for the same VideoTask in one transaction.
- Old candidates and old selected files are not deleted.
- Real project adoption remains manual-only and must be done in the formal UI.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\video_generation_service.py tests\test_video_generation.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py -q
```

Result:

- Ruff targeted check passed.
- 25 passed
- 6 existing Starlette/httpx deprecation warnings

Phase 18-19 conclusion: video candidates continue to use the existing task/run/output API, and adoption now has service-layer media/run/file/FFprobe guards before changing selected state.

## Phase 20: Media Video Playback

Existing endpoint reused:

- `GET /api/media/{media_asset_id}/content`
- `GET /api/media/{media_asset_id}/thumbnail`

Phase 20 findings:

- Starlette `FileResponse` already supports HTTP byte range requests.
- No custom Range implementation was required.
- Video content response returns:
  - `206 Partial Content` for valid `Range` requests
  - `Accept-Ranges: bytes`
  - correct `Content-Range`
  - `video/mp4`
- The endpoint still resolves only stored media paths through `MediaStorageService`; no project-external path read was added.
- Existing image content and download behavior remain on the same endpoint.

Related Phase 17 fix:

- Thumbnail responses now infer MIME type from the actual thumbnail/poster file, so video PNG posters are served as `image/png` while existing WebP thumbnails remain supported.

Targeted test command:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check tests\test_video_generation.py app\api\characters.py
.\.venv\Scripts\python.exe -m pytest tests\test_video_generation.py -q
```

Result:

- Ruff targeted check passed.
- 26 passed
- 6 existing Starlette/httpx deprecation warnings

Phase 20 conclusion: browser video playback has covered byte-range support through the existing media content endpoint without adding a custom media serving path.

## Phase 22: Minimal ShotWorkbench Video UI

Existing quick-generate UI was reused instead of adding a second video form.

Changed files:

- `apps/web/src/features/project-canvas/quick-generate-api.ts`
- `apps/web/src/features/project-canvas/components/canvas-quick-generate-panel.tsx`
- `apps/web/src/pages/shot-workbench-page.tsx`
- `apps/web/src/features/shots/ShotRoutes.test.tsx`

Phase 22 behavior:

- The shot workbench right panel now renders the real Quick Generate panel for the current shot.
- Video mode exposes low-cost preset controls: short test / standard short, FPS, and optional seed.
- Preview displays resolved inputs, warnings, blockers, capability status, and estimated output.
- Workflow IDs are not presented as a user-facing concept in the quick panel.
- Advanced professional task details remain available behind the existing advanced toggle.
- No video output is auto-adopted.

Targeted verification:

```powershell
cd F:\LocalDramaStudio\apps\web
npm run typecheck
npm test -- ShotRoutes ProjectCanvasPage
```

Result:

- Typecheck passed.
- 57 frontend tests passed.

## Phase 23-24: Storyboard Video Status Sync

Changed files:

- `apps/web/src/features/studio-workspace/storyboard.ts`
- `apps/web/src/features/studio-workspace/storyboard.test.ts`

Status priority now follows the V1-B2 user-facing rule:

1. True queued/running video Run: generating.
2. Adopted video output: adopted.
3. Completed unadopted candidate: waiting for adoption.
4. Latest failed Run without active/adopted/candidate: failed.
5. Workflow/ComfyUI unavailable: capability unavailable.
6. Missing adopted first/end frame or draft/ready-only task: not ready.
7. No video work: not generated.

This prevents historical failed runs or draft tasks from falsely overriding a valid adopted/candidate state, and prevents a non-running task from being displayed as "video generating".

Targeted verification:

```powershell
cd F:\LocalDramaStudio\apps\web
npm run typecheck
npm test -- storyboard StudioWorkspacePage ShotRoutes
```

Result:

- Typecheck passed.
- 58 frontend tests passed.

## Phase 25: Timeline Sync

Existing Timeline API remains the only timeline data source:

- `GET /api/projects/{project_id}/timeline`

Phase 25 changes:

- Timeline repository now only accepts selected video outputs whose parent `VideoGenerationRun` is `completed`.
- Unadopted candidates do not enter Timeline.
- Failed/running selected-output inconsistencies do not enter Timeline.
- Shot order continues to use `Shot.order_index`, then `created_at`, then `id`.
- When FFprobe is available, Timeline reads adopted video duration, dimensions, and FPS from the actual media file.
- If the adopted file is missing or cannot be probed, the clip becomes blocked with a safe Chinese blocker.
- No second Timeline model or endpoint was added.

Targeted verification:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\project_timeline_service.py app\repository\project_timeline_repository.py app\service\project_export_service.py app\service\export\export_runner.py app\service\export\ffmpeg_service.py tests\test_project_timeline_exports.py
.\.venv\Scripts\python.exe -m pytest tests\test_project_timeline_exports.py -q
```

Result:

- Ruff targeted check passed.
- 11 backend tests passed.
- 1 existing Starlette/httpx deprecation warning.

## Phase 26: Final Export Sync

Existing FFmpeg Project Export remains the only final export path:

- `GET /api/projects/{project_id}/exports`
- `POST /api/projects/{project_id}/exports`
- `POST /api/projects/{project_id}/exports/{export_id}/mark-ready`
- `POST /api/projects/{project_id}/exports/{export_id}/start`

Phase 26 changes:

- Export snapshots continue to read Timeline/adopted video data only.
- Snapshot duration uses the Timeline's actual FFprobe duration when FFprobe is available.
- Runner FFprobes every source clip before standardization.
- Runner validates the final MP4 after concat before registering it as a `MediaAsset(video)`.
- Final MP4 must be H.264, `yuv420p`, target width/height, target FPS, positive duration, positive frame count, and no audio stream for v1.
- Export failure writes a safe Chinese error summary and does not expose local paths or FFmpeg stderr.
- Source videos are not deleted or modified.
- Export output remains scoped under `storage/projects/{project_id}/exports/{export_id}/final.mp4`, so each export ID has its own output path.

Targeted verification:

```powershell
cd F:\LocalDramaStudio\apps\api
.\.venv\Scripts\python.exe -m ruff check app\service\project_timeline_service.py app\repository\project_timeline_repository.py app\service\project_export_service.py app\service\export\export_runner.py app\service\export\ffmpeg_service.py tests\test_project_timeline_exports.py
.\.venv\Scripts\python.exe -m pytest tests\test_project_timeline_exports.py -q
```

Result:

- Ruff targeted check passed.
- 11 backend tests passed.
- 1 existing Starlette/httpx deprecation warning.
