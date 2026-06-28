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

## Routes

- `/projects`: project list.
- `/projects/:projectId`: project detail.
- `/projects/:projectId/characters`: project character library.
- `/projects/:projectId/characters/:characterId`: character details, looks, and reference images.
- `/projects/:projectId/scenes`: project scene library.
- `/projects/:projectId/scenes/:sceneId`: scene details, states, and reference images.
- `/characters`, `/scenes`, `/shots`, `/tasks`: top-level guide or empty states when no project context is selected.

User-visible product copy defaults to Simplified Chinese. Keep future language expansion lightweight and avoid large i18n frameworks until explicitly needed.
