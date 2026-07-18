# Sprint 27A: UI Foundation And Resizable App Shell

## Scope

Sprint 27A establishes the Studio 2.0 UI foundation without changing backend business logic, ComfyUI workflows, generation runners, database schema, or existing production flows.

The development-only route is:

```text
/dev/studio-ui
```

It is intentionally not listed in the formal product navigation.

## Design Tokens

The first token set lives in `apps/web/src/index.css` as CSS custom properties and is also exposed through Tailwind under the `studio` color namespace.

It covers:

- Dark professional studio surfaces.
- Low-saturation blue primary actions.
- Success, warning, error, info, and draft states.
- Radius tokens for buttons, inputs, cards, previews, floating panels, and badges.
- Spacing scale.
- Motion durations with reduced-motion protection.
- Z-index tiers for panels, popovers, dialogs, and toasts.

## Resizable Shell

The demo shell validates the target Studio 2.0 structure:

```text
top project control bar
├── left global nav
├── left context panel
├── center main workspace
├── right Inspector
└── bottom expandable workspace
```

Panel behavior:

- Global nav collapses between 200px and 64px.
- Left context panel: min 220px, default 280px, max 480px.
- Right Inspector: min 360px, default 440px, max 720px.
- Bottom workspace: min 160px, default 260px, max 560px, collapsed by default to a lightweight status bar.
- Splitters support drag resize and double-click reset.
- Layout persists in localStorage by schema version and project/demo id.
- Invalid persisted layout data falls back to defaults.
- Explicit reset restores defaults.
- Tab toggles focus mode unless focus is inside an editable control.

## Shared Component Baseline

The demo route shows the initial style baseline for:

- Primary, secondary, ghost, danger, disabled, and loading buttons.
- Input and select-like controls.
- Status badges.
- Empty and inline error states.

## Boundaries

This sprint does not implement Canvas 2.0, intelligent continuation, full storyboard behavior, media preview, generation changes, ComfyUI changes, backend API changes, database migrations, or workflow changes.

The existing Sprint 23-26 production and canvas flows remain untouched except for adding the independent demo route.
