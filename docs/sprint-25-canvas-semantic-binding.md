# Sprint 25: Canvas Semantic Binding v1

## Scope

Sprint 25 connects the project canvas to existing business entities without changing the generation runner, ComfyUI provider, workflow files, Run, Output, or adopted-output logic.

The canvas now supports:

- Dragging existing project assets from the asset drawer onto the canvas.
- Detecting duplicate business entities and focusing the existing node instead of creating a duplicate.
- Creating semantic edges through a confirmation dialog.
- Saving an edge as a canvas-only draft relation.
- Applying supported semantic edges to real business data through the backend Service layer.
- Marking failed semantic edges and retrying them from the Edge Inspector.
- Hiding canvas edges or, for applied edges, removing the related business binding when supported.
- Previewing and importing existing shot business relations as canvas edges without duplication.

## Applied Business Bindings

The following semantic bindings can write real business data:

- `uses_character`: creates or updates a `ShotCharacter`.
- `uses_scene`: updates a shot's scene and optional scene state, with explicit replacement confirmation.
- `identity_reference`, `look_reference`, `pose_reference`: creates a shot character reference only when the source media belongs to an existing character reference.
- `scene_reference`: creates a shot scene reference only when the source media belongs to an existing scene reference.
- `start_frame`, `end_frame`: writes a selected existing image media asset to a selected video generation task input.

The following semantic bindings remain canvas-level planning relations in v1:

- `continuity_from`: only `shot -> shot`.
- `included_in_export`: only `video -> export`.

`generated_from` is system-owned and cannot be manually created from the canvas UI or binding API.

Unsupported node pairs, such as `scene -> character`, are rejected before creating a draft edge.

## Media Upload Boundary

This sprint does not add a general project-level media upload API.

Local file drag-and-drop therefore shows:

> 本地文件上传即将支持，请先从资产库添加已有素材。

It intentionally does not reuse video-task frame upload as a generic media upload path.

## Known Limits

- Ordinary image or video `MediaAsset` records that are not owned by a character reference, scene reference, or supported video task input cannot be silently converted into shot references.
- Start/end frame binding targets an existing video generation task selected in the confirmation dialog, not a plain video node.
- Undo/redo remains canvas-state oriented and is not a full business-transaction history.
- Local image and video uploads should be handled in a later sprint through a formal project media upload API with validation and storage ownership checks.
