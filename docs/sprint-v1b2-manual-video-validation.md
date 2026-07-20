# Sprint V1-B2 Manual Video Validation

本文件用于产品经理手动完成 Wan2.2 平台视频闭环验收。Codex 在 V1-B2 收口阶段只负责代码、自动化测试、只读 Preview 和文档，不执行真实视频生成、不调用 ComfyUI `/prompt`、不自动采用视频。

## 固定验收对象

- 项目 ID：`8c6200f3-23b0-4af5-a4db-6a2bd9cd6702`
- 镜头 ID：`8b56399b-3d2a-4150-bdf9-4c840058a357`
- 镜头页面：
  `http://127.0.0.1:5173/projects/8c6200f3-23b0-4af5-a4db-6a2bd9cd6702/shots/8b56399b-3d2a-4150-bdf9-4c840058a357?intent=generate&returnTo=studio`
- 工作流：`video_wan22_14b_flf2v_v1`
- 推荐冒烟参数：320 x 576、17 帧、8 FPS、Seed `27002`

## 启动前检查

1. API：打开 `http://127.0.0.1:8000/api/health`，应返回 `status=ok`。
2. Web：打开 `http://127.0.0.1:5173`，应可访问项目列表或项目入口。
3. ComfyUI：打开 `http://127.0.0.1:8188/system_stats`，应可访问。
4. ComfyUI Queue：打开 `http://127.0.0.1:8188/queue`，开始前应没有正在运行或排队的视频任务。
5. ComfyUI Loader：在 ComfyUI 或 `/object_info` 中确认以下模型可见：
   - `wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors`
   - `wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors`
   - `umt5_xxl_fp8_e4m3fn_scaled.safetensors`
   - `wan_2.1_vae.safetensors`

## Preview 验收

在镜头页面的视频生成区域填写：

Positive Prompt：

```text
镜头固定，人物缓慢抬头并自然呼吸，衣摆和发丝轻微摆动，环境光保持稳定，动作连续平滑，从首帧自然过渡到尾帧，不切换镜头。
```

Negative Prompt：

```text
切镜，镜头跳动，快速摇镜，人物变形，面部变化，多余肢体，闪烁，光线突变，画面撕裂，严重模糊，文字，水印。
```

参数：

- 时长预设：短测试
- FPS：8
- Seed：27002
- 工作流：Wan2.2 首尾帧视频

Preview 应确认：

- workflow 为 `video_wan22_14b_flf2v_v1`
- 首帧已解析
- 尾帧已解析
- width = 320
- height = 576
- frame_count = 17
- fps = 8
- seed = 27002
- expected_duration 约 2.125 秒
- 中文 Prompt 与 Negative Prompt 未损坏

允许 warning：

- `media_metadata_stale`
- `low_resolution_preset`

若 ComfyUI 未启动，可出现 `provider_offline`，此时不要点击生成，先恢复 ComfyUI。

## 生成视频

只有 Preview 显示可执行、没有 blocker 后，产品经理手动点击“生成视频”。

要求：

1. 不要重复点击。
2. 不要同时启动多个视频 Run。
3. 如页面显示已有 queued/running Run，等待它结束或确认状态后再操作。
4. 不要手动修改数据库。
5. 不要通过脚本调用 execute API。

生成后观察：

- ComfyUI Queue 出现任务。
- 平台 Run 进入 queued/running。
- HTTP 请求不应等待整个视频采样完成。
- 完成后 Run 为 completed。
- ShotWorkbench 出现视频候选。
- 候选未自动采用。

## 候选检查

候选出现后检查：

1. 浏览器可播放视频。
2. 视频不是空文件。
3. 首尾帧过渡方向合理。
4. 没有明显错误文件、损坏文件或非视频内容。
5. Prompt 中中文语义没有被问号或乱码替换。

可用 ffprobe 检查 MP4：

```powershell
ffprobe -v error -show_streams -show_format "<候选视频文件>"
```

重点确认：

- codec_name 为 H.264 或平台已转码为 H.264。
- pix_fmt 为 yuv420p。
- width = 320。
- height = 576。
- FPS = 8。
- frame_count = 17 或与实际输出一致。
- duration > 0。

## 手动采用

确认候选可用后，由产品经理在正式页面手动点击“采用”。

采用后检查：

1. 当前 VideoOutput 显示已采用。
2. 同一 VideoTask 下没有两个 selected output。
3. ShotWorkbench 已采用视频置顶或明确显示。
4. 返回 Studio 后，镜头卡显示“视频已采用”。
5. 刷新页面后 adopted 状态仍存在。

## Timeline 检查

打开：

```text
http://127.0.0.1:5173/projects/8c6200f3-23b0-4af5-a4db-6a2bd9cd6702/timeline
```

检查：

- 镜头 1 可读取 adopted video。
- 镜头 1 duration 使用实际视频时长。
- 镜头 2 如果仍没有 adopted video，应显示明确 blocker。
- 不得自动跳过镜头 2 并宣称完整导出可用。

## Final Export

只有项目中需要导出的所有镜头都有 adopted video 后，才执行最终导出。

导出设置建议：

- 768 x 1360
- 16 FPS
- libx264
- yuv420p
- video only

导出完成后检查：

- ProjectExport 状态从 ready/queued/running 到 completed。
- final MP4 可播放。
- 媒体库能看到最终导出视频。
- FFprobe 显示 H.264、yuv420p、目标分辨率和目标 FPS。

## 失败时收集信息

失败时不要自动重试。请记录：

- 项目 ID 和镜头 ID。
- VideoTask ID。
- VideoRun ID。
- VideoOutput ID，如已创建。
- 错误码和安全错误消息。
- ComfyUI Queue / History 状态。
- 是否有 active Run。
- 候选视频是否存在。
- FFprobe 输出摘要。
- 浏览器 Console 和 Network 中的安全摘要。

## 防重复点击

开始生成前确认：

1. 当前没有 queued/running 视频 Run。
2. 当前页面没有显示“正在生成”。
3. ComfyUI Queue 为空。
4. 只点击一次“生成视频”。

如果误点多次，后端应通过 request_id 幂等和 active Run 防重复保护复用当前 Run，而不是创建多个真实视频 Run。

## 2026-07-20 人工验收结果补充

产品经理已经在真实页面中手动生成并手动采用一个 Wan2.2 视频候选。Codex 在本次最终收口中只做只读核验和文档记录：

- 未调用 ComfyUI `/prompt`。
- 未创建第二个真实 `VideoRun`。
- 未创建新的 `VideoOutput` 或 `MediaAsset`。
- 未自动采用视频。
- 未执行新的真实模型推理。
- 未执行最终成片导出。

固定验收对象：

- 项目：`8c6200f3-23b0-4af5-a4db-6a2bd9cd6702`
- 镜头：`8b56399b-3d2a-4150-bdf9-4c840058a357`
- 最新真实 `VideoRun`：`293dcae3-a97f-4f82-ae4b-9d65c1c2470a`
- request_id：`f5bf01d1-9609-499b-8271-78ced649bb77`
- ComfyUI prompt_id：`9cf93e3b-2b1a-4b12-9a97-73a08b04c476`
- `VideoOutput`：`459e9063-0abb-44fe-9ae8-dd4af15dd2f5`
- 视频 `MediaAsset`：`b8a618c6-0e63-426b-adf1-cd1ee68437f9`
- Poster：当前实现为视频 `MediaAsset.thumbnail_relative_path`，不是独立 MediaAsset。
- adopted 状态：已采用。
- 同一镜头 adopted 视频数量：`1`。
- 同一镜头 completed 视频候选数量：`2`。
- active 视频 Run：`0`。

视频文件只读核验：

- Relative path：`projects/8c6200f3-23b0-4af5-a4db-6a2bd9cd6702/media/generated-videos/9ba08954-f32d-4e76-bcbb-961e993d5474.mp4`
- 文件存在：是。
- 文件大小：`957994` bytes。
- SHA-256：`dba82e0c3dd3fa7c1b6cef606b4d8a6794b895ac688caca122ef33bf88753da6`
- codec：`h264`
- pixel format：`yuv420p`
- 分辨率：`320 x 576`
- FPS：`8`
- 帧数：`33`
- 时长：`4.125` 秒。
- 浏览器读取：媒体接口支持 Range 读取，返回 `206 Partial Content`、`video/mp4`、`accept-ranges: bytes`。

Prompt 核验：

```text
镜头固定，人物缓慢抬头并自然呼吸，衣摆和发丝轻微摆动，环境光保持稳定，动作连续平滑，从首帧自然过渡到尾帧，不切换镜头。
```

Negative Prompt 核验：

```text
切镜，镜头跳动，快速摇镜，人物变形，面部变化，多余肢体，闪烁，光线突变，画面撕裂，严重模糊，文字，水印。
```

Production Status 核验：

- 首帧：已采用。
- 尾帧：已采用。
- 视频：已采用。
- 历史 failed run 未覆盖 adopted 状态。
- 当前无 queued/running 视频 Run。

Timeline 核验：

- 镜头 1 进入 Timeline，使用 adopted video。
- 镜头 1 Timeline 参数来自真实视频：`duration=4.125`、`width=320`、`height=576`、`fps=8`。
- 镜头 2 仍存在，且没有 adopted video。
- Timeline 不自动跳过镜头 2。
- Timeline 不把镜头 1 视频复用于镜头 2。
- 完整导出当前不可用，blocker 为镜头 2 尚未采用视频。

验收结论：

- 视频候选成功出现。
- 视频可以正常播放。
- 视频不是黑屏或空文件。
- 画面质量一般，但平台视频文件、采用状态、媒体读取、故事板/生产状态和时间线链路正常。
- 画质优化、导演构图和动作质量问题后续进入独立质量 Sprint。
