# Sprint V1-A 视频闭环审计报告

审计时间：2026-07-19

本轮只做只读审计和方案确认。未下载模型，未安装节点，未修改平台代码，未修改数据库，未创建 VideoTask/VideoRun/Output，未提交，未推送。

## 1. Git 状态

- 分支：`main`
- `HEAD`：`214ad3fbe63b7291e3126626305b0540e25678f4`
- `origin/main`：`214ad3fbe63b7291e3126626305b0540e25678f4`
- 开工前工作区：clean
- 最近提交：
  - `214ad3f refactor: simplify studio around core image generation flow`
  - `382d52f test: add e2e data safety guards`
  - `ed9726f feat: add studio workspace shell and smart resume entry`

## 2. 运行路径、进程和端口

| 项 | 结果 |
| --- | --- |
| 项目目录 | `F:\LocalDramaStudio` 存在 |
| ComfyUI 目录 | `F:\AI\ComfyUI\ComfyUI\ComfyUI` 存在 |
| ComfyUI Python | `F:\AI\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe` 存在 |
| API | `http://127.0.0.1:8000/api/health` 返回 200 |
| Web | `http://127.0.0.1:5173` 返回 200 |
| ComfyUI | `http://127.0.0.1:8188` 当前无监听，`/system_stats`、`/object_info`、`/queue` 均连接失败 |
| FFmpeg | `ffmpeg version 8.1.1-essentials_build-www.gyan.dev` |
| FFprobe | `ffprobe version 8.1.1-essentials_build-www.gyan.dev` |

端口审计结果：

- `127.0.0.1:5173` 由 Node/Vite 进程监听，命令来自 `F:\LocalDramaStudio\apps\web\node_modules\...\vite\bin\vite.js`。
- `127.0.0.1:8000` 当前监听 PID 是 Codex runtime Python：`C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`。
- 同时存在一个项目 `.venv` Python uvicorn 进程：`F:\LocalDramaStudio\apps\api\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`，但它不是当前 8000 监听者。
- 未发现 8188 监听进程。

风险：API 存在重复 uvicorn 进程，需要 V1-B 前统一为项目 `.venv` 单实例启动；本轮未关闭或重启任何进程。

## 3. 硬件、显存、磁盘

| 项 | 结果 |
| --- | --- |
| CPU | AMD Ryzen 7 9700X 8-Core Processor |
| GPU | NVIDIA GeForce RTX 5060 Ti |
| GPU 数量 | 1 |
| NVIDIA Driver | 596.21 |
| 显存 | 16311 MiB，总占用约 207 MiB，空闲约 15846 MiB |
| 系统内存 | 33408954368 bytes，约 31.1 GiB |
| F 盘剩余 | 约 555 GB |
| C 盘剩余 | 约 50 GB |
| D 盘剩余 | 约 166 GB |
| E 盘剩余 | 约 146 GB |

判断：磁盘空间足够容纳 Wan2.2 14B FP8 最小包。16GB VRAM 对 14B FP8 FLF2V 属于“可能可运行但需要 offload / 低规格参数 / 长时间等待”的档位，不建议直接按 5 秒高分辨率做首验。

## 4. ComfyUI 基础环境

- ComfyUI commit：`f6c162ddcfbd7eefb39c06fe5b8d4c46e8d09f40`
- ComfyUI 版本日志：`f6c162dd ComfyUI v0.26.0`
- ComfyUI 工作区存在大量未提交改动；本轮未修改。
- Python：3.13.12
- PyTorch：`2.10.0+cu130`
- CUDA runtime：13.0
- `torch.cuda.is_available()`：True
- `torch.cuda.get_device_name()`：NVIDIA GeForce RTX 5060 Ti
- xformers：未安装
- SageAttention：未安装
- Flash Attention：未安装
- `extra_model_paths.yaml`：未发现

当前 ComfyUI 未运行，因此无法用 `/object_info` 实时确认 Loader 下拉值。基于文件系统审计，Wan 所需模型未放入目标目录。

## 5. Custom Nodes

| Custom Node | 本地路径 | Git 状态/commit | 启动可确认性 | V1 是否必要 |
| --- | --- | --- | --- | --- |
| ComfyUI_IPAdapter_plus | `custom_nodes\ComfyUI_IPAdapter_plus` | `a0f451a` | 8188 离线，不能实时确认 | 否，Wan FLF2V 不依赖 |
| comfyui-controlnet-aux | `custom_nodes\comfyui-controlnet-aux` | `83463c2` | 8188 离线，不能实时确认 | 否 |
| ComfyUI-Impact-Pack | `custom_nodes\ComfyUI-Impact-Pack` | `429d015` | 8188 离线，不能实时确认 | 否 |
| ComfyUI-Impact-Subpack | `custom_nodes\ComfyUI-Impact-Subpack` | `50c7b71` | 8188 离线，不能实时确认 | 否 |
| ComfyUI-VideoHelperSuite | `custom_nodes\ComfyUI-VideoHelperSuite` | `4ee72c0` | 8188 离线，不能实时确认 | 当前内置 API workflow 使用原生 `CreateVideo` + `SaveVideo`，不依赖 VHS |

当前候选 `video_wan22_14b_flf2v_v1.json` 只依赖原生 ComfyUI 视频节点，不依赖 IPAdapter、ControlNet Aux、Impact Pack 或 VideoHelperSuite。

## 6. 模型盘点

已存在：

| 目录 | 文件 | 大小 |
| --- | --- | --- |
| `models\checkpoints` | `sd_xl_base_1.0.safetensors` | 6,938,078,334 bytes |
| `models\vae` | `sdxl_vae.safetensors` | 334,641,162 bytes |
| `models\clip_vision` | `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | 2,528,373,448 bytes |
| `models\clip_vision` | `WRONG_bigG_misnamed_CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | 3,689,912,664 bytes |
| `models\ipadapter` | `ip-adapter-plus_sdxl_vit-h.safetensors` | 847,517,512 bytes |
| `models\ipadapter` | `ip-adapter-plus-face_sdxl_vit-h.safetensors` | 847,517,512 bytes |
| `models\controlnet` | `controlnet-canny-sdxl-1.0.safetensors` | 5,004,167,864 bytes |

Wan 14B FLF2V 缺失：

| 文件 | 目标目录 | 当前状态 |
| --- | --- | --- |
| `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `models\text_encoders` | 不存在 |
| `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | `models\diffusion_models` | 不存在 |
| `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | `models\diffusion_models` | 不存在 |
| `wan_2.1_vae.safetensors` | `models\vae` | 不存在 |

当前 `models\diffusion_models`、`models\unet`、`models\text_encoders`、`models\clip` 都只有占位文件。由于 8188 离线，本轮不能确认 Loader 实时下拉；文件系统层面已经确认缺失。

## 7. Wan 工作流文件审计

候选工作流：

| 文件 | 用途 | 格式 | 可解析 | 项目引用 |
| --- | --- | --- | --- | --- |
| `workflows\video_wan22_14b_flf2v_v1.json` | 平台 API workflow | API workflow | 是 | 是 |
| `workflows\video_wan22_14b_flf2v_v1.manifest.json` | 平台 manifest | manifest | 是 | 是 |
| `workflows\lds_single_shot_wan22_flf2v_v1.workflow.json` | ComfyUI 可视化编辑版 | UI workflow | 是 | 参考/手工导入 |
| `workflows\strong_first_frame_v1.workflow.json` | 强首帧图像实验 | UI workflow | 是 | 非视频 V1 |
| `workflows\video_i2v_14b_v1.manifest.json` | 旧占位视频 manifest | manifest | 是 | 是，但 workflow 文件缺失 |

最终候选：`workflows\video_wan22_14b_flf2v_v1.json`。

静态检查：

- JSON 可解析。
- 不是 UI workflow，顶层无 `nodes/links/groups`。
- 无 Windows / Unix 用户绝对路径。
- 无 Base64 / data URI。
- 无 `保安.png`、`男主逆袭.png` 等测试素材名。
- required node types 均在工作流 JSON 中出现。
- 输出节点 `83` 为 `SaveVideo`。

关键节点：

| 用途 | 节点 |
| --- | --- |
| CLIP/Text Encoder | node `72` `CLIPLoader`，`clip_name=umt5_xxl_fp8_e4m3fn_scaled.safetensors` |
| 高噪声模型 | node `76` `UNETLoader`，`unet_name=wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` |
| 低噪声模型 | node `77` `UNETLoader`，`unet_name=wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` |
| VAE | node `79` `VAELoader`，`vae_name=wan_2.1_vae.safetensors` |
| 起始帧 | node `80` `LoadImage.image` |
| 结束帧 | node `89` `LoadImage.image` |
| 正向 Prompt | node `90` `CLIPTextEncode.text` |
| 反向 Prompt | node `78` `CLIPTextEncode.text` |
| 宽高/帧数 | node `81` `WanFirstLastFrameToVideo.width/height/length` |
| fps | node `86` `CreateVideo.fps` |
| seed | node `84` `KSamplerAdvanced.noise_seed` |
| 高噪声阶段 | node `84`，`start_at_step=0`，`end_at_step=10` |
| 低噪声阶段 | node `87`，`add_noise=disable`，`noise_seed=0`，`start_at_step=10` |
| 视频保存 | node `83` `SaveVideo`，`filename_prefix=video/ComfyUI` |

结论：工作流结构有效，当前主要缺模型和 ComfyUI 在线校验；暂不需要修改 workflow JSON。

## 8. 官方模型来源

官方 ComfyUI Wan2.2 文档说明 FLF2V 使用 I2V 章节相同模型位置，并要求两个输入图分别进入两个 `Load Image` 节点，尺寸/帧数在 `WanFirstLastFrameToVideo` 节点中设置。官方示例还说明 14B I2V 使用高噪声/低噪声两个 diffusion model、`umt5_xxl_fp8_e4m3fn_scaled.safetensors` text encoder 和 `wan_2.1_vae.safetensors` VAE。

推荐只使用 Comfy-Org Hugging Face 仓库 `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` 的 `split_files` 文件，不使用来源不明网盘或第三方重打包。

| 用途 | 官方仓库路径 | 精确文件名 | 大小 | 目标目录 |
| --- | --- | --- | --- | --- |
| Text Encoder | `split_files/text_encoders` | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | 6,735,906,897 bytes | `models\text_encoders` |
| High Noise I2V | `split_files/diffusion_models` | `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors` | 14,294,742,832 bytes | `models\diffusion_models` |
| Low Noise I2V | `split_files/diffusion_models` | `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors` | 14,294,742,832 bytes | `models\diffusion_models` |
| VAE | `split_files/vae` | `wan_2.1_vae.safetensors` | 253,815,318 bytes | `models\vae` |

预计最小下载总量：35,579,207,879 bytes，约 33.1 GiB。

回答关键问题：

- 这四个文件属于同一套 Wan2.2 14B I2V / FLF2V 官方 ComfyUI 路线。
- high_noise 与 low_noise 都必须存在；当前工作流的 node `76` 和 `77` 分别加载二者。
- 官方 ComfyUI Wan2.2 示例中 14B I2V/FLF2V 使用 `wan_2.1_vae.safetensors`。
- 本工作流不需要 CLIP Vision、IPAdapter、FaceID、InsightFace、LoRA 或额外 tokenizer 文件。
- 当前工作流是 14B FP8，不是 5B。
- FP8 是 16GB VRAM 本地测试的合理优先选项，但仍需要控制分辨率、时长并接受 offload 和慢速。

参考来源：

- ComfyUI 官方 Wan2.2 文档：<https://docs.comfy.org/tutorials/video/wan/wan2_2>
- ComfyUI examples Wan2.2：<https://comfyanonymous.github.io/ComfyUI_examples/wan22/>
- Comfy-Org Hugging Face 仓库：<https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged>
- ComfyUI FLF2V 公告：<https://blog.comfy.org/p/wan22-flf2v-comfyui-native-support>

## 9. 后端视频业务链路

链路状态：

| 链路 | 状态 | 证据 |
| --- | --- | --- |
| Shot -> VideoTask | 已完成 | `video_generation_tasks.shot_id` |
| VideoTask -> VideoRun | 已完成 | `video_generation_runs.video_task_id` |
| VideoRun -> VideoOutput | 已完成但真实项目暂无输出 | `video_generation_outputs` 表存在，项目当前 count=0 |
| VideoOutput -> MediaAsset | 已完成 | `video_generation_outputs.media_asset_id` + repository 创建逻辑 |
| Adopt | 已完成 | `POST/DELETE /video-outputs/{output_id}/select` |
| Storyboard adopted video | 部分完成 | 依赖 Production Status / media 读取，当前无 adopted video 数据可验 |
| Timeline | 已完成 | `/api/projects/{project_id}/timeline` 读取 adopted video |
| Final Export | 已完成但真实视频样本待补验 | `/api/projects/{project_id}/exports` |

当前视频 API：

- `GET /api/projects/{project_id}/video-workflows`
- `POST /api/projects/{project_id}/video-inputs/images`
- `GET /api/projects/{project_id}/shots/{shot_id}/video-tasks`
- `POST /api/projects/{project_id}/shots/{shot_id}/video-tasks`
- `GET /api/projects/{project_id}/video-tasks/{task_id}`
- `PATCH /api/projects/{project_id}/video-tasks/{task_id}`
- `DELETE /api/projects/{project_id}/video-tasks/{task_id}`
- `POST /api/projects/{project_id}/video-tasks/{task_id}/mark-ready`
- `POST /api/projects/{project_id}/video-tasks/{task_id}/mark-draft`
- `POST /api/projects/{project_id}/video-tasks/{task_id}/runs`
- `GET /api/projects/{project_id}/video-tasks/{task_id}/runs`
- `GET /api/projects/{project_id}/video-runs/{run_id}`
- `POST /api/projects/{project_id}/video-outputs/{output_id}/select`
- `DELETE /api/projects/{project_id}/video-outputs/{output_id}/select`
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/preview`
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate`
- `POST /api/projects/{project_id}/shots/{shot_id}/quick-generate/sync-output`

缺口：

- 没有视频候选删除 API。
- 没有取消 queued/running 的 `/interrupt`。
- 没有真实视频 output 数据可验收。
- 旧 `video_i2v_14b_v1` manifest 存在但 workflow 文件缺失，应继续保持 unavailable。

## 10. Capability Registry 与 Router

现状：

- Registry 已注册 keyframe 与 video workflow。
- Router 在 video 模式优先选择含 `flf2v` / `first_last` / `wan22` 的 workflow。
- Preview 是只读，不创建任务或 Run。
- Execute 复用现有 task/run/output API，带 `request_id` 幂等和 active run 防重。
- Output sync 已支持生成 image/video canvas node 和系统 `generated_from` edge。

当前 API 观测：

- `/video-workflows` 返回 `video_wan22_14b_flf2v_v1.available=false`，原因是 `provider_offline`。
- `/quick-generate/preview` 在 video 模式下选择 `video_wan22_14b_flf2v_v1`，`executable=false`，warnings 为 `provider_offline`。
- 因 ComfyUI 离线，当前没有拿到 object_info，因此 API 未能进一步列出 `model_file_missing:*`。V1-B 前需要先启动唯一 ComfyUI 实例再复验。

重要风险：

- `VideoGenerationService._workflow_missing_requirements` 只有在 provider online 且 object_info 可用时才检查 Loader 下拉；离线时只返回 `provider_offline`。
- 当前实现会通过 object_info 对 `CLIPLoader`、`UNETLoader`、`VAELoader` 的模型输入做下拉匹配，方向正确。

## 11. Production Status 与 adopted 首尾帧映射

真实项目：

- 项目：`8c6200f3-23b0-4af5-a4db-6a2bd9cd6702`
- 镜头 1：`8b56399b-3d2a-4150-bdf9-4c840058a357`
- 镜头 2：`9f97efaf-2b24-48c6-aa2e-0fe557331f0f`

镜头 1 当前 adopted 首尾帧：

| purpose | task_id | run_id | output_id | media_asset_id | is_selected |
| --- | --- | --- | --- | --- | --- |
| first_frame | `b348cf86-3828-4723-9110-a25c3cc392e5` | `0e18414a-6a29-4b1d-b45b-0d39d5597b90` | `6eb7c146-e7e9-41d9-8689-aebec0cb8448` | `f1ec98a0-f375-4cad-af0b-ec0f0a5b59d8` | true |
| end_frame | `ad207e64-0436-403f-a881-568ca51bc046` | `d7a4279d-2b2e-4e8a-ae45-54a2f3dfb01a` | `f5c0ef03-c455-4da4-afce-495d71057165` | `9c2b821e-1a3e-4ee1-ac07-6428d590af80` | true |

Production Status 当前返回：

- `first_frame.status=adopted`
- `end_frame.status=adopted`
- `video.status=missing_inputs`
- blockers：`missing_scene`、`video_missing_start_frame`、`video_missing_end_frame`

解释：Production Status 的视频步骤不是从 adopted keyframe 自动推导视频 task inputs，而是读取 `video_generation_task_inputs`。当前视频任务列表按 `updated_at desc` 排序，摘要使用了较新的空 draft 任务 `5e92a996-...`，所以显示 video missing inputs。另一个旧 ready Wan task `adbd1fc2-...` 实际有 start/end inputs，但最新 run 已 failed。该问题应在 V1-B 作为最小修复处理：选择视频摘要任务时应优先 selected output、active run、ready/has inputs 的最新 Wan 任务，或由 Quick Generate video execute 在创建/复用任务时明确更新唯一当前任务。

## 12. 首尾帧媒体兼容性

镜头 1 adopted 首尾帧媒体：

| 用途 | media_asset_id | 格式 | 尺寸 | 大小 | storage 相对路径 |
| --- | --- | --- | --- | --- | --- |
| 首帧 | `f1ec98a0-f375-4cad-af0b-ec0f0a5b59d8` | PNG | 768 x 1360 | 2,102,607 bytes | `projects/.../media/generated-keyframes/...png` |
| 尾帧 | `9c2b821e-1a3e-4ee1-ac07-6428d590af80` | PNG | 768 x 1360 | 1,863,285 bytes | `projects/.../media/generated-keyframes/...png` |

另外旧视频 task 手动输入使用的是 `c0b01672-...` 和 `a711238b-...`，两者为 943 x 1668 PNG，并非 adopted keyframe output。V1-B 应优先使用 adopted keyframe output 作为 start/end frame，而不是旧视频输入或用户手动上传图。

当前 ComfyUI provider 会通过 `/upload/image` 上传输入图，因此不需要 ComfyUI 直接读取平台 storage 路径；这避免 Windows 路径和中文路径问题。

## 13. 视频输入契约

必需输入：

| 字段 | 当前是否存在 | 存储/API | workflow 节点 | V1-B 处理 |
| --- | --- | --- | --- | --- |
| project_id | 是 | path param / task.project_id | 无 | 校验项目隔离 |
| shot_id | 是 | path param / task.shot_id | 无 | 校验镜头归属 |
| adopted start frame | 是 | selected first_frame keyframe output -> media_asset_id | node `80.image` | Quick Generate 自动映射 |
| adopted end frame | 是 | selected end_frame keyframe output -> media_asset_id | node `89.image` | Quick Generate 自动映射 |
| video prompt | 是 | `VideoGenerationTask.prompt` / request prompt | node `90.text` | 用户输入 |

V1 UI 建议只暴露：视频 Prompt、Negative Prompt、时长或帧数二选一、FPS、Seed。其余使用稳定预设。

当前 `length` 由 `duration_seconds * fps + 1` 计算，manifest 已配置白名单 `duration_seconds_times_fps_plus_one`。

## 14. 视频输出契约

当前 workflow 输出：

- node `83`：`SaveVideo`
- `output_file_keys`：`videos`、`files`、`gifs`、`images`
- `allowed_output_extensions`：`mp4`、`webm`、`mov`、`gif`
- provider 从 `/history/{prompt_id}` 指定输出节点中筛选允许扩展名，只保存视频类输出。
- 保存为 `MediaAsset(media_type=video)` 后创建 `VideoGenerationOutput`。
- 用户通过 select API 手动采用；不自动 adopted。
- Storyboard/Timeline/Export 均应读取 selected video output。

FFmpeg/FFprobe 8.1.1 已可用，具备后续 WebM->MP4、H.264、poster/metadata 检查的基础能力；本轮未执行视频转码。

## 15. 运行方案比较

| 方案 | 内容 | 结论 |
| --- | --- | --- |
| A | 当前 Wan2.2 14B FP8 FLF2V | 推荐为 V1 默认方案。模型来源官方，和现有 workflow 匹配；16GB VRAM 有风险但可通过 2 秒、16fps、640x640/低规格首验降低风险。 |
| B | Wan2.2 TI2V 5B | 官方存在，单模型约 10GB，显存压力低；但当前平台 workflow 是 14B FLF2V，需要新增/替换 workflow 与 manifest，不作为 V1-B 首选。 |
| C | 暂不本机运行 | 不推荐作为默认。当前磁盘足够、硬件可能可运行，应先完成 A 方案最小真实验收。 |

V1 默认建议：继续使用现有 `video_wan22_14b_flf2v_v1` + 官方 14B FP8 I2V 双模型 + UMT5 + Wan2.1 VAE。首次真实验收参数：2 秒、16fps、640x640、固定 seed、单 Run。

## 16. 差距清单

| 环节 | 当前状态 | 缺失内容 | 是否阻塞 | 最小修复 |
| --- | --- | --- | --- | --- |
| ComfyUI 服务 | 未完成 | 8188 当前离线 | 是 | V1-B 启动唯一 ComfyUI 实例 |
| Wan 节点 | 无法确认 | object_info 离线 | 是 | 启动后确认 `WanFirstLastFrameToVideo/CreateVideo/SaveVideo` |
| Text Encoder | 未完成 | UMT5 文件缺失 | 是 | 下载官方文件到 `models\text_encoders` |
| High Noise 模型 | 未完成 | I2V high FP8 缺失 | 是 | 下载官方文件到 `models\diffusion_models` |
| Low Noise 模型 | 未完成 | I2V low FP8 缺失 | 是 | 下载官方文件到 `models\diffusion_models` |
| VAE | 未完成 | `wan_2.1_vae.safetensors` 缺失 | 是 | 下载官方文件到 `models\vae` |
| 首帧输入 | 已完成 | adopted -> video task 自动映射需复验 | 否 | 使用 Quick Generate video execute |
| 尾帧输入 | 已完成 | 同上 | 否 | 使用 Quick Generate video execute |
| Prompt | 已完成 | 无 | 否 | 继续用 `VideoGenerationTask.prompt` |
| Negative Prompt | 已完成 | 无 | 否 | 继续用 `negative_prompt` |
| Workflow JSON | 已完成 | 无 | 否 | 不改 JSON |
| API Workflow | 已完成 | object_info 实时校验待补 | 是 | ComfyUI 在线后 preview |
| Capability Registry | 部分完成 | 离线时只报 provider_offline | 否 | 在线后检查模型缺失；可考虑展示文件缺失 |
| Workflow Router | 已完成 | 无 | 否 | 维持 deterministic 规则 |
| Production Status | 部分完成 | 视频摘要可能选中空 draft 任务 | 否 | V1-B 最小修正摘要选择规则 |
| VideoTask | 已完成 | 历史重复 draft 较多 | 否 | 不自动清理；新流程复用/选择明确任务 |
| VideoRun | 已完成 | 无成功视频 run | 是 | 补模型后真实 run |
| Output Sync | 已完成 | 无真实 video output 可验 | 是 | 成功 run 后验收 |
| MediaAsset | 已完成 | 无真实 video media | 是 | 成功输出后创建 |
| Candidate List | 部分完成 | 无真实视频候选 | 是 | 成功输出后验收 |
| Adopt | 已完成 | 无真实视频输出可采用 | 是 | 输出后手动采用 |
| Storyboard | 部分完成 | adopted video 未验 | 是 | 采用后刷新验收 |
| Timeline | 已完成 | 依赖 adopted video | 是 | 两个 adopted video 后验收 |
| Final Export | 已完成 | 依赖 adopted video | 是 | 两个 adopted video 后验收 |

## 17. V1-B 严格执行顺序

1. 模型与 ComfyUI 就绪
   前置：产品确认本报告。范围：只下载四个官方文件到指定目录。验收：文件存在、大小合理、来源记录完整。失败停止：下载来源不明、磁盘不足、文件名不匹配。

2. 工作流静态可加载
   前置：ComfyUI 单实例运行。范围：只读 `/object_info`，不提交 `/prompt`。验收：Loader 下拉含 UMT5、high/low I2V、Wan VAE，节点类型存在。失败停止：节点缺失且需要升级 ComfyUI/PyTorch。

3. 单次手工 ComfyUI 生成验证
   前置：workflow 可加载。范围：在 ComfyUI 用两张测试首尾帧，2 秒/16fps/640x640/固定 seed。验收：产生视频文件。失败停止：OOM、节点错误、模型不匹配。

4. 后端视频预检与输入映射
   前置：手工生成成功。范围：Quick Generate video preview/execute 最小修复，尤其 adopted 首尾帧映射和 Production Status 摘要规则。验收：preview executable=true 且不缺模型/输入。

5. 后端提交与状态轮询
   前置：preview 通过。范围：创建 VideoRun、提交 ComfyUI、轮询。验收：HTTP 立即返回，run queued/running/completed 正常。

6. 输出同步与候选
   前置：run completed。范围：保存视频 MediaAsset、VideoOutput、候选展示。验收：不返回绝对路径，视频可播放。

7. 采用与故事板
   前置：候选存在。范围：手动采用。验收：Storyboard 显示 adopted video。

8. 时间线与导出
   前置：至少两个镜头有 adopted video。范围：Timeline/Export 真实验收。验收：final MP4 通过 ffprobe。

9. 真实项目验收
   前置：以上全部通过。范围：只走真实 UI，不直接改库。验收：从故事板打开生成、视频候选、采用、返回故事板、导出闭环。

## 18. 停止条件

V1-B 不应开始或应立即停止的情况：

- ComfyUI 启动后仍缺 `WanFirstLastFrameToVideo`、`CreateVideo` 或 `SaveVideo`，且修复需要升级核心环境。
- object_info 看不到已放置的官方模型文件。
- 14B FP8 生成在 2 秒/16fps/640x640 下稳定 OOM。
- 下载文件来源不是官方 Comfy-Org/Wan 官方路径。
- 需要修改数据库核心模型但没有迁移方案。
- 视频输出不能进入 MediaAsset。
- Timeline/Export 读取 adopted video 的契约与 VideoOutput 不一致。
- 必须升级 PyTorch/CUDA 且可能破坏现有关键帧链路。

## 19. 已知限制

- 本轮未启动 ComfyUI，因此 Loader 下拉和节点实时可用性只能标为“未确认”。
- 当前 API 监听实例不是项目 `.venv` 进程，这是环境治理风险。
- 真实项目尚无 VideoOutput，无法审计视频候选播放、采用、Storyboard video、Timeline 和 Final Export 的真实输出链路。
- Production Status 对多视频任务的摘要选择存在可能误导，需要 V1-B 修复。
- ComfyUI 工作区自身有大量未提交改动，本轮不处理。

## 20. V1-A 最终建议

建议进入 V1-B，但必须先满足两个前置：

1. 统一服务环境：只保留一个 API 实例，ComfyUI 以 `F:\AI\ComfyUI\ComfyUI\ComfyUI\.venv\Scripts\python.exe` 启动，8188 可访问。
2. 下载并放置四个官方模型文件：UMT5、I2V high FP8、I2V low FP8、Wan2.1 VAE。

V1-B 首验不应扩 UI、不改 workflow JSON、不做 Canvas 2.0，只做模型就绪、workflow 加载、Quick Generate video 输入映射、真实视频候选、手动采用、Storyboard/Timeline/Export 后续验收。
