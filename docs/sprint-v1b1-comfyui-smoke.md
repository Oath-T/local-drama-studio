# Sprint V1-B1: Wan2.2 FP8 Model Landing And Native ComfyUI Smoke

## Scope

Sprint V1-B1 completed the approved Wan2.2 FP8 model landing and one native ComfyUI first-last-frame video smoke test.

This round did not modify Local Drama Studio platform code, database schema, manifest files, workflow JSON in `workflows/`, runner/provider code, frontend code, backend code, or project business data. It did not create platform `VideoGenerationTask`, `VideoGenerationRun`, or `VideoGenerationOutput` records.

## V1-A Commit Baseline

- V1-A audit document commit: `1680625b0d5ba8bf19b54ee5e6f273ca970139b7`
- Branch after V1-A push: `main`
- `HEAD == origin/main`: yes before starting V1-B1

## Local Environment

- Project path: `F:\LocalDramaStudio`
- ComfyUI path: `F:\AI\ComfyUI\ComfyUI\ComfyUI`
- ComfyUI startup command used: `F:\AI\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188`
- Listener PID: `238012`
- Current ComfyUI version observed in startup log: `0.27.0`
- Frontend package observed in startup log: `1.45.20`
- GPU: NVIDIA GeForce RTX 5060 Ti, 16311 MiB VRAM
- F drive free space before model landing: about 555 GB
- F drive free space after model landing and smoke artifacts: about 481 GB

Note: Windows reported the running process executable as `F:\AI\ComfyUI\ComfyUI\standalone-env\python.exe`, while the command line was launched through `F:\AI\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe`. This appears to be ComfyUI standalone launcher behavior and was recorded without changing the environment.

## Download Method

- Official source repository: `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`
- Download methods used:
  - `huggingface_hub` from the ComfyUI virtual environment for the VAE file.
  - `curl.exe -L --fail --retry 5 --retry-delay 10 -C -` against official Hugging Face `resolve/main` URLs for the large files.
- No Git LFS clone was used.
- No Python, Torch, CUDA, ComfyUI, or custom node dependency was installed or upgraded.

## Downloaded Model Files

| Role | Source path in official repo | Final file | Size bytes | SHA-256 | Check |
| --- | --- | --- | ---: | --- | --- |
| VAE | `split_files/vae/wan_2.1_vae.safetensors` | `models\vae\wan_2.1_vae.safetensors` | 253815318 | `2FC39D31359A4B0A64F55876D8FF7FA8D780956AE2CB13463B0223E15148976B` | pass |
| Text encoder | `split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6735906897 | `C3355D30191F1F066B26D93FBA017AE9809DCE6C627DDA5F6A66EAA651204F68` | pass |
| High noise diffusion model | `split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | `models\diffusion_models\wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 14294742832 | `6122E79D55E0F235698D11D657F3B196C5273C830DA00B2B013C5A048D5E6A42` | pass |
| Low noise diffusion model | `split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | `models\diffusion_models\wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 14294742832 | `5471A457B6AC404202A5FBE6C11595A3D5641FC766B00F38763F72303FFFC21E` | pass |

Final model paths:

- `F:\AI\ComfyUI\ComfyUI\ComfyUI\models\vae\wan_2.1_vae.safetensors`
- `F:\AI\ComfyUI\ComfyUI\ComfyUI\models\text_encoders\umt5_xxl_fp8_e4m3fn_scaled.safetensors`
- `F:\AI\ComfyUI\ComfyUI\ComfyUI\models\diffusion_models\wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors`
- `F:\AI\ComfyUI\ComfyUI\ComfyUI\models\diffusion_models\wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`

Temporary staging note: the formal model files were moved into the correct ComfyUI model directories. A stale Hugging Face incomplete cache file remains under `F:\AI\ComfyUI\wan-v1b-download-staging\.cache\huggingface\download\...` with size about 3.15 GB. Cleanup was not retried after the shell policy rejected the removal command. It is not in the Local Drama Studio repository and is not used by ComfyUI loaders.

## ComfyUI Loader Verification

The following ComfyUI endpoints were reachable after startup:

- `http://127.0.0.1:8188/system_stats`
- `http://127.0.0.1:8188/object_info`
- `http://127.0.0.1:8188/queue`
- `http://127.0.0.1:8188/history`

Loader checks from `/object_info`:

- `UNETLoader` lists `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors`: yes
- `UNETLoader` lists `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`: yes
- `CLIPLoader` lists `umt5_xxl_fp8_e4m3fn_scaled.safetensors`: yes
- `VAELoader` lists `wan_2.1_vae.safetensors`: yes

Startup log did not show custom node import failures. One non-blocking warning was observed: ControlNet Aux / DWPose acceleration fallback related to `onnxruntime`.

## Native Smoke Workflow

Formal repository workflow files were not modified. The smoke test used a temporary copy:

- Base workflow: `F:\LocalDramaStudio\workflows\video_wan22_14b_flf2v_v1.json`
- Temporary smoke workflow: `F:\LocalDramaStudio\.tmp\sprint-v1b1\wan22-flf2v-smoke.workflow.json`

Static checks passed:

- JSON parse: pass
- API workflow shape: pass
- No UI workflow top-level `nodes`, `links`, or `groups`: pass
- No Windows absolute paths in workflow values: pass
- No data URI or base64 payloads: pass
- Required image bindings set to `lds_v1b1_start.png` and `lds_v1b1_end.png`: pass

Key temporary workflow parameters:

- Width: 320
- Height: 576
- Length: 17 frames
- FPS: 8
- Candidate count / batch size: 1
- Node 84 `noise_seed`: 27001
- Node 87 `noise_seed`: 0, with exported no-noise semantics retained
- SaveVideo filename prefix: `video/lds_v1b1_smoke`

Encoding deviation: the intended Chinese positive and negative prompts were corrupted into question marks in the temporary workflow/history because the PowerShell-to-Python stdin path used during patching did not preserve Chinese text. The run remains valid as a loader and end-to-end video pipeline smoke, but it should not be used as a prompt quality assessment.

## Input Frames

Input images came from existing adopted keyframe outputs for project `8c6200f3-23b0-4af5-a4db-6a2bd9cd6702`, shot `8b56399b-3d2a-4150-bdf9-4c840058a357`. The database was queried read-only and no platform task/output/adoption records were created or changed.

Start frame:

- Keyframe output ID: `6eb7c146-e7e9-41d9-8689-aebec0cb8448`
- Run ID: `0e18414a-6a29-4b1d-b45b-0d39d5597b90`
- Task ID: `b348cf86-3828-4723-9110-a25c3cc392e5`
- MediaAsset ID: `f1ec98a0-f375-4cad-af0b-ec0f0a5b59d8`
- Copied to ComfyUI input as: `lds_v1b1_start.png`
- Actual copied file SHA-256: `C2976FB0EB6D7CE753313E7244B43F611B66A6903807CB6480DF90F9057D9C5E`
- Copy verification: source and destination hashes matched

End frame:

- Keyframe output ID: `f5c0ef03-c455-4da4-afce-495d71057165`
- Run ID: `d7a4279d-2b2e-4e8a-ae45-54a2f3dfb01a`
- Task ID: `ad207e64-0436-403f-a881-568ca51bc046`
- MediaAsset ID: `9c2b821e-1a3e-4ee1-ac07-6428d590af80`
- Copied to ComfyUI input as: `lds_v1b1_end.png`
- Actual copied file SHA-256: `74A301129949D661AEFA611F35D0EE0887A5ED9F92331F9567A85B164067430C`
- Copy verification: source and destination hashes matched

Observed data issue: the current disk file size/hash values did not match the stored `media_assets.size_bytes` / `sha256` values for these two media records. This was only recorded and not repaired in V1-B1.

## Prompt Submission And Runtime

- Submitted exactly one prompt to native ComfyUI `/prompt`.
- Client ID: `3e3f2517-5311-462d-8dc9-db4c9045e85b`
- Prompt ID: `02538e5b-7a8d-4a86-9004-f8f51b4586db`
- Node errors in submit response: `{}`
- Queue before run: empty
- Final history status: success
- Approximate wall-clock runtime: about 1 minute
- Peak observed VRAM during monitor sampling: 12925 MiB used of 16311 MiB
- Post-run queue: empty
- OOM observed: no
- Retry required: no

Runtime evidence files:

- `F:\LocalDramaStudio\.tmp\sprint-v1b1\prompt-submit.json`
- `F:\LocalDramaStudio\.tmp\sprint-v1b1\runtime-samples.json`
- `F:\LocalDramaStudio\.tmp\sprint-v1b1\history-smoke.json`
- `F:\LocalDramaStudio\.tmp\sprint-v1b1\queue-before.json`
- `F:\LocalDramaStudio\.tmp\sprint-v1b1\queue-after.json`
- `F:\LocalDramaStudio\.tmp\sprint-v1b1\nvidia-before.txt`
- `F:\LocalDramaStudio\.tmp\sprint-v1b1\nvidia-after.txt`

## Output Video

- Output file: `F:\AI\ComfyUI\ComfyUI\ComfyUI\output\video\lds_v1b1_smoke_00001_.mp4`
- File size: 473657 bytes
- SHA-256: `FCD5BECDB237F2274F9AA2047E7C14A190817E3774E81AB4991EB452BAAED493`
- Local playback launch: `Start-Process` returned without error
- Decode check: `ffmpeg -v error -i <output> -f null -` completed without error

FFprobe summary:

- Format: `mov,mp4,m4a,3gp,3g2,mj2`
- Duration: `2.125000` seconds
- Video stream count: 1
- Audio stream count: 0
- Codec: `h264`
- Width: 320
- Height: 576
- Pixel format: `yuv420p`
- Average frame rate: `8/1`
- Frame count: `17`

Extracted verification frames:

- `F:\LocalDramaStudio\.tmp\sprint-v1b1\smoke-first-frame.png`
- `F:\LocalDramaStudio\.tmp\sprint-v1b1\smoke-last-frame.png`

Visual note: the extracted first and last frames reflect the actual existing adopted keyframes used as inputs. They are not modern office imagery, so this smoke test validates the Wan2.2 FLF2V execution chain rather than target creative quality.

## Classification

Result: pass for V1-B1 technical smoke.

Confirmed:

- All four approved Wan2.2 FP8 model files are present in the expected ComfyUI model directories.
- File sizes and SHA-256 hashes match expected values.
- ComfyUI starts and exposes `/system_stats` and `/object_info`.
- Loaders recognize VAE, UMT5 text encoder, high-noise diffusion model, and low-noise diffusion model.
- The existing Wan2.2 FLF2V API workflow can be run natively in ComfyUI with low-cost parameters.
- One MP4 was generated successfully.
- The generated MP4 probes as H.264, 320x576, yuv420p, 8 fps, 17 frames, no audio.
- No Local Drama Studio platform data was written by the smoke test.

Not claimed:

- No platform video task/run/output was created.
- No Local Drama Studio video execution path was tested in V1-B1.
- No prompt quality or short-drama quality was validated.
- No final export pipeline was tested.

## Known Issues And Follow-up

1. The temporary smoke workflow prompt text suffered Chinese encoding corruption. V1-B2 should ensure prompt injection uses UTF-8 safe file or API paths before platform-level execution.
2. The two existing adopted keyframe MediaAsset database hashes/sizes differ from the actual files on disk. This should be audited separately before using hashes as integrity gates.
3. A stale Hugging Face incomplete cache remains under the model download staging directory. It is outside the repository and outside the formal model directories.
4. The current ComfyUI process reports a standalone Python executable path even though it was launched through the ComfyUI `.venv` command line. This should be recorded but is not blocking loader or execution behavior.
5. V1-B2 can proceed to platform video-chain validation only after confirming the platform provider uses the same ComfyUI instance and the workflow availability check sees these exact loader values.
