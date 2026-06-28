# Sprint 5: Shot Reference Recommendations

Sprint 5 adds a real-time, explainable recommendation layer for shot reference binding.
It does not train, fine-tune, or call any external or local vision model. It also does
not create recommendation history tables, persistent caches, background jobs, automatic
binding, ComfyUI calls, generation workflows, or AI analysis buttons.

The product may label the feature as "智能推荐", but the behavior is rule based:

```text
推荐结果根据镜头参数和资产元数据进行规则匹配，不使用训练模型，也不会自动绑定。
```

Do not describe the result as AI confidence, model probability, model accuracy, or deep
learning recommendation.

## Flow

```text
Shot metadata
+ ShotCharacter and selected look
+ selected SceneState
+ CharacterReference and SceneReference metadata
+ existing ShotReference bindings
=> hard filters
=> deterministic scoring
=> suggested purpose
=> user confirms
=> existing ShotReference create API writes the binding
```

Recommendations are computed on each request and are not stored. The response uses
`generated_from_updated_at`, which is copied from the current shot `updated_at`, so the
same business input produces stable recommendation items, scores, purposes, reasons, and
ordering.

## API

```text
GET /api/projects/{project_id}/shots/{shot_id}/recommendations?limit=5
```

`limit` defaults to 5 and is constrained to 1-20. The same limit is applied per shot
character group and to the scene recommendation group.

The response returns explicit safe fields only:

- reference id and media asset id
- thumbnail and content URLs
- source look or scene state summary
- official reference metadata used for scoring
- score, suggested purpose, reasons, bound purposes, and already-bound flag

It must not return `relative_path`, `stored_filename`, absolute paths, storage roots,
Windows drive letters, `file://` URLs, or ORM relationship objects.

Scene recommendation `status_code` values are stable:

- `ready`
- `scene_state_required`
- `no_references`

## Character Scoring

Hard filters:

- Candidate reference must belong to the same project.
- Candidate reference must belong to the same Character as the ShotCharacter.
- MediaAsset must exist.
- Missing media database records are skipped; the service does not check the filesystem.

Weights:

- exact look match: +40
- exact shot scale match: +20
- close shot scale match: +12
- exact view angle match: +15
- close view angle match: +8
- identity anchor: +10
- primary reference: +5
- expression keyword match: +10
- pose keyword match: +5

Scores are capped at 100. Reasons are de-duplicated. `different_look` and
`already_bound_other_purpose` are explanatory reasons only and do not add or subtract score.

Stable sort:

```text
score desc
is_identity_anchor desc
is_primary desc
created_at asc
id asc
```

## Character Purpose Priority

Purpose is selected separately from score:

1. Clear expression match -> `expression`
2. Clear pose match -> `pose`
3. Identity anchor, or clear front close reference with calm identity-safe expression -> `identity`
4. Matching look and clothing/body-friendly shot type -> `appearance`
5. Clear shot scale match -> `framing`
6. Fallback -> `general`

Not every front close image is identity. Strong crying, angry, fearful, or exaggerated
expression images should become `expression` when the shot text clearly asks for that
expression.

## Scene Scoring

Hard filters:

- Shot must have a selected `scene_state_id`.
- Candidate reference must belong to that exact SceneState.
- Candidate reference must belong to the same project.
- MediaAsset must exist.

Weights:

- exact shot scale match: +25
- close shot scale match: +15
- exact camera position match: +20
- close camera position match: +10
- exact view direction match: +15
- close view direction match: +8
- exact composition match: +15
- spatial anchor: +10
- primary reference: +5
- empty plate: +5
- lighting keyword match: +10

Scores are capped at 100. Stable sort:

```text
score desc
is_spatial_anchor desc
is_primary desc
created_at asc
id asc
```

## Scene Purpose Priority

1. `is_spatial_anchor=true` -> `spatial`
2. Clear composition match -> `composition`
3. Clear camera position or view direction match -> `camera_reference`
4. Clear lighting keyword match -> `lighting`
5. Primary or wide environment reference -> `environment`
6. Fallback -> `general`

## Keyword Matching

Keyword matching is conservative and deterministic:

- Text is trimmed, lowercased for English, and normalized for common punctuation and whitespace.
- Only a centralized finite dictionary is used.
- Chinese normal keywords should be at least two characters, except explicit one-character
  emotion terms such as "哭".
- Multiple synonyms in the same category count once.
- Candidate-side text uses only `tags` and `description`.
- Shot-side text uses `visual_description`, `story_description`, `mood_description`, and
  `action_summary`; character-specific action, expression, and position descriptions are also
  used for character recommendations.
- Internal `notes` do not participate in scoring.
- No segmentation library, fuzzy similarity, edit distance, embedding, vector database, RAG,
  or external NLP dependency is used.

## Binding State

Candidates already bound for the suggested purpose remain visible, show "已绑定", and cannot
send another create request. Candidates bound only for other purposes remain visible, show
"已绑定其他用途", and may still be bound for the suggested purpose.

`bound_purposes` are de-duplicated and sorted by the stable purpose order.

## Query Strategy

The backend uses batch-oriented reads:

- Load the shot once.
- Load all ShotCharacters for the shot in one query.
- Batch load Characters, selected Looks, candidate CharacterReferences, and MediaAssets.
- Batch load SceneReferences for the selected SceneState and MediaAssets.
- Batch load existing ShotReference bindings once.

The recommendation service combines these records in memory and does not trigger per-character
or per-candidate lazy-load loops.

## Future Vision Models

Local Drama Studio does not plan to train visual foundation models from scratch. Future visual
understanding should connect replaceable cloud or local multimodal models through provider-neutral
adapters. Model output should remain suggestions until a Service-layer confirmation flow validates
and applies user-approved metadata.
