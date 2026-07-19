# Sprint R1: Core Link Contraction

Sprint R1 removes the complex Studio 2.0 demo shell from the formal product path and restores a single reliable creator flow:

```text
/projects
-> /projects/:projectId/studio
-> /projects/:projectId/shots/:shotId?intent=generate&returnTo=studio
-> generate first frame / end frame / video through existing task APIs
-> manually adopt outputs
-> return to Studio storyboard
```

## Formal Studio Scope

- Shows only real project shots.
- Hides `E2E_` and `__E2E_` projects from the normal project list.
- Shows adopted first-frame and end-frame status when available.
- Shows a simplified video status: adopted, generating, waiting adoption, not generated, unavailable, or failed.
- Uses one primary shot action: `打开生成`.
- Preserves only a minimal Studio session: selected shot, scroll position, and timestamp.

## Removed From The Formal Entry

- `/dev/studio-ui` demo route and demo shell.
- Smart continuation demo surfaces.
- Density controls, filters, multi-select, focus mode, drag sorting, copy, delete, and placeholder consoles from the unfinished Sprint 27C storyboard.
- Left shot list, right complex Inspector, bottom dock, and resizable shell from the formal Studio page.

## Preserved Systems

- Character, scene, shot, reference, task, run, output, adopted, media, Canvas, Quick Generate, generation center, timeline, and export APIs remain intact.
- Old Canvas, generation center, timeline/export, media library, and production board remain reachable as secondary links.
- E2E safety protection remains in code and tests.

## Known Limits

- The Studio storyboard does not create, delete, duplicate, or sort shots.
- It does not start video generation directly.
- It does not replace the existing shot workbench; it links into that workbench.
- Real dual-shot FFmpeg export smoke testing remains pending until the platform has at least two adopted video outputs.
