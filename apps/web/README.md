# Local Drama Studio Web

React + TypeScript + Vite frontend for the Local Drama Studio workbench.

## Run

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

## Test

```powershell
npm run typecheck
npm run test
```

## Shot Recommendations

The shot workbench includes a "智能推荐" tab in the reference panel. Recommendations are
computed from shot parameters and existing asset metadata, do not use trained models, and
never bind automatically. Manual character reference, scene reference, and selected-asset
tabs remain available.

## Routes

- `/projects`: project list.
- `/projects/:projectId`: project detail.
- `/projects/:projectId/characters`: project character library.
- `/projects/:projectId/characters/:characterId`: character details, looks, and reference images.
- `/projects/:projectId/scenes`: project scene library.
- `/projects/:projectId/scenes/:sceneId`: scene details, states, and reference images.
- `/projects/:projectId/shots`: project shot workbench.
- `/projects/:projectId/shots/:shotId`: shot detail, bindings, and recommendations.
- `/characters`, `/scenes`, `/shots`, `/tasks`: top-level guide or empty states when no project context is selected.

User-visible product copy defaults to Simplified Chinese. Keep future language expansion lightweight and avoid large i18n frameworks until explicitly needed.
