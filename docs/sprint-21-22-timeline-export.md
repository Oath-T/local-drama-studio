# Sprint 21-22: Timeline & Final Export v1

Sprint 21-22 introduces the first project-level timeline and final MP4 export path.

## Scope

- `GET /api/projects/{project_id}/timeline` returns shots in shot order and only uses explicitly adopted video outputs.
- `project_exports` stores final export drafts, progress, status, settings, a stable timeline snapshot, and the final output media id.
- Final export uses local FFmpeg/FFprobe only. It does not call ComfyUI, modify generation tasks, or adopt outputs.
- The web app adds `/projects/:projectId/timeline`, shows preflight blockers, export settings, export history, and final video playback/download.
- The media library shows completed final export MP4 files.

## Snapshot Rule

Creating an export stores the current ready timeline clips and export settings in `ProjectExport.snapshot`.
Later changes to adopted video outputs do not alter that existing export. Users should create a new export draft when they want a fresh timeline snapshot.

## FFmpeg Behavior

The backend reads:

```text
LDS_API_FFMPEG_BIN=ffmpeg
LDS_API_FFPROBE_BIN=ffprobe
LDS_API_EXPORT_TIMEOUT_SECONDS=1800
```

Each source clip is probed with FFprobe, normalized with FFmpeg to:

- H.264 `libx264`
- `yuv420p`
- no audio
- target width, height, and fps
- scale with preserved aspect ratio plus padding
- `+faststart`

Normalized clips are concatenated into:

```text
storage/projects/{project_id}/exports/{export_id}/final.mp4
```

The final file is registered as a video `MediaAsset`. API responses expose only media ids and safe `/api/media/{id}/content` URLs.

## Safety

- No shell command strings are executed; subprocess calls use argument lists with `shell=False`.
- Source and output paths are resolved under `STORAGE_ROOT`.
- Missing FFmpeg/FFprobe blocks mark-ready/start in the API and disables export actions in the UI.
- Missing source videos or non-video adopted media block the timeline/export.
- Runner failures set the export to `failed` with a safe Chinese error message.

## Current Limits

- No audio.
- No subtitles.
- No transitions.
- No timeline trimming, drag editing, or shot reordering.
- No ComfyUI workflow changes.
- No cloud export worker.
- Export runs in the API process background task; long exports should later move to a local worker queue.
- Real two-shot FFmpeg export smoke testing is still pending. The current local database does not yet contain at least two completed and adopted video outputs backed by real video files, so `mark-ready -> start -> running -> completed`, final `ffprobe`, browser playback, download, and media-library verification must be completed after the platform produces those adopted outputs through the normal workflow.

## Manual Acceptance

1. Make sure every shot has an explicitly adopted video output.
2. Install FFmpeg and FFprobe on PATH, or set `LDS_API_FFMPEG_BIN` / `LDS_API_FFPROBE_BIN`.
3. Open `/projects/:projectId/timeline`.
4. Confirm all timeline cards are ready and no blocker is shown.
5. Create an export draft.
6. Mark it ready.
7. Start export.
8. Wait for completion, then play or download the final MP4 from the export card or media library.
