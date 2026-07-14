import { useMutation } from "@tanstack/react-query";
import { Clipboard, FileText, Plus, RefreshCw, RotateCcw, Wand2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { StatusMessage } from "@/components/ui/status-message";
import { Textarea } from "@/components/ui/textarea";

import { buildPromptDraft } from "../api";
import { promptBuilderCopy } from "../copy";
import type {
  DirectorContext,
  DirectorOverrides,
  PromptDraftOverrides,
  PromptDraftResponse,
  PromptDraftStyle,
  PromptDraftTarget
} from "../types";

interface PromptDraftCardProps {
  projectId: string;
  shotId: string;
  target?: PromptDraftTarget;
  onDraft?: (draft: PromptDraftResponse) => void;
  onCreateFirstFrameTask?: (draft: PromptDraftResponse) => void | Promise<void>;
  onCreateEndFrameTask?: (draft: PromptDraftResponse) => void | Promise<void>;
  onCreateVideoTask?: (draft: PromptDraftResponse) => void | Promise<void>;
}

const styleOptions: PromptDraftStyle[] = [
  "cinematic_short_drama",
  "ultra_realistic",
  "rain_night_neon",
  "office_drama",
  "emotional_closeup",
  "action_tension"
];

const emptyOverrides: Record<keyof PromptDraftOverrides, string> = {
  start_action: "",
  end_action: "",
  motion_direction: "",
  camera_motion: "",
  visual_style: "",
  mood: ""
};

const templateOptions = [
  "enter_room_shock",
  "door_open_reveal",
  "character_walks_forward",
  "character_turns_head",
  "emotional_closeup",
  "two_person_confrontation",
  "phone_reveal",
  "meeting_room_wide",
  "authority_stands_up",
  "crowd_reaction",
  "character_leaves",
  "establishing_scene"
] as const;

const autoTemplateValue = "__auto__";

const emptyDirectorOverrides: Record<keyof DirectorOverrides, string> = {
  subject_position: "",
  start_action: "",
  end_action: "",
  crowd_action: "",
  crowd_emotion: "",
  camera_movement: "",
  composition: "",
  environment_motion: ""
};

export function PromptDraftCard({
  projectId,
  shotId,
  target = "all",
  onDraft,
  onCreateFirstFrameTask,
  onCreateEndFrameTask,
  onCreateVideoTask
}: PromptDraftCardProps) {
  const [draft, setDraft] = useState<PromptDraftResponse | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [creatingTaskType, setCreatingTaskType] = useState<
    "first_frame" | "end_frame" | "video" | null
  >(null);
  const [style, setStyle] = useState<PromptDraftStyle>("cinematic_short_drama");
  const [templateId, setTemplateId] = useState<string>(autoTemplateValue);
  const [overrides, setOverrides] =
    useState<Record<keyof PromptDraftOverrides, string>>(emptyOverrides);
  const [directorOverrides, setDirectorOverrides] =
    useState<Record<keyof DirectorOverrides, string>>(emptyDirectorOverrides);
  const mutation = useMutation({
    mutationFn: () =>
      buildPromptDraft(projectId, shotId, {
        target,
        style,
        language: "en",
        include_negative_prompt: true,
        overrides: compactOverrides(overrides),
        template_id: templateId === autoTemplateValue ? null : templateId,
        director_overrides: compactDirectorOverrides(directorOverrides)
      }),
    onSuccess: (result) => {
      setDraft(result);
      onDraft?.(result);
    }
  });

  async function copyText(label: string, text: string) {
    await navigator.clipboard?.writeText(text);
    setCopied(label);
    window.setTimeout(() => setCopied(null), 1200);
  }

  function updateOverride(field: keyof PromptDraftOverrides, value: string) {
    setOverrides((current) => ({ ...current, [field]: value }));
  }

  function updateDirectorOverride(field: keyof DirectorOverrides, value: string) {
    setDirectorOverrides((current) => ({ ...current, [field]: value }));
  }

  async function handleCreateTask(type: "first_frame" | "end_frame" | "video") {
    if (!draft) {
      return;
    }
    const callback =
      type === "first_frame"
        ? onCreateFirstFrameTask
        : type === "end_frame"
          ? onCreateEndFrameTask
          : onCreateVideoTask;
    if (!callback) {
      return;
    }
    const confirmed = window.confirm(createConfirmMessage(type, draft.warnings.length));
    if (!confirmed) {
      return;
    }
    setCreatingTaskType(type);
    try {
      await callback(draft);
    } finally {
      setCreatingTaskType(null);
    }
  }

  return (
    <section className="grid gap-3 rounded-md border border-border bg-background p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
            {promptBuilderCopy.title}
          </h3>
          <p className="mt-1 text-xs leading-5 text-muted">{promptBuilderCopy.description}</p>
        </div>
        <Button
          type="button"
          size="sm"
          variant={draft ? "secondary" : "default"}
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          {draft ? (
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Wand2 className="h-4 w-4" aria-hidden="true" />
          )}
          {mutation.isPending
            ? promptBuilderCopy.generating
            : draft
              ? promptBuilderCopy.regenerate
              : promptBuilderCopy.generate}
        </Button>
      </div>

      <div className="grid gap-3 rounded-md border border-border bg-panel p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="text-xs font-semibold text-muted">
            {promptBuilderCopy.generationSettings}
          </div>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setOverrides(emptyOverrides)}
            disabled={mutation.isPending}
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            {promptBuilderCopy.clearOverrides}
          </Button>
        </div>
        <label className="grid gap-1 text-xs text-muted">
          {promptBuilderCopy.stylePreset}
          <Select value={style} onValueChange={(value) => setStyle(value as PromptDraftStyle)}>
            <SelectTrigger aria-label={promptBuilderCopy.stylePreset}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {styleOptions.map((option) => (
                <SelectItem key={option} value={option}>
                  {promptBuilderCopy.styleLabels[option]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <label className="grid gap-1 text-xs text-muted">
          {promptBuilderCopy.shotTemplate}
          <Select value={templateId} onValueChange={setTemplateId}>
            <SelectTrigger aria-label={promptBuilderCopy.shotTemplate}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={autoTemplateValue}>{promptBuilderCopy.autoTemplate}</SelectItem>
              {templateOptions.map((option) => (
                <SelectItem key={option} value={option}>
                  {promptBuilderCopy.templateLabels[option]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </label>
        <div className="grid gap-2 lg:grid-cols-2">
          <OverrideTextarea
            label={promptBuilderCopy.startActionOverride}
            value={overrides.start_action}
            onChange={(value) => updateOverride("start_action", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.endActionOverride}
            value={overrides.end_action}
            onChange={(value) => updateOverride("end_action", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.motionDirectionOverride}
            value={overrides.motion_direction}
            onChange={(value) => updateOverride("motion_direction", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.cameraMotionOverride}
            value={overrides.camera_motion}
            onChange={(value) => updateOverride("camera_motion", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.visualStyleOverride}
            value={overrides.visual_style}
            onChange={(value) => updateOverride("visual_style", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.moodOverride}
            value={overrides.mood}
            onChange={(value) => updateOverride("mood", value)}
          />
        </div>
      </div>

      <div className="grid gap-3 rounded-md border border-border bg-panel p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-xs font-semibold text-muted">
              {promptBuilderCopy.directorSettings}
            </div>
            <p className="mt-1 text-xs leading-5 text-muted">
              {promptBuilderCopy.directorSafeNote}
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={() => setDirectorOverrides(emptyDirectorOverrides)}
            disabled={mutation.isPending}
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            {promptBuilderCopy.clearDirectorOverrides}
          </Button>
        </div>
        <div className="grid gap-2 lg:grid-cols-2">
          <OverrideTextarea
            label={promptBuilderCopy.subjectPositionOverride}
            value={directorOverrides.subject_position}
            onChange={(value) => updateDirectorOverride("subject_position", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.directorStartActionOverride}
            value={directorOverrides.start_action}
            onChange={(value) => updateDirectorOverride("start_action", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.directorEndActionOverride}
            value={directorOverrides.end_action}
            onChange={(value) => updateDirectorOverride("end_action", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.crowdActionOverride}
            value={directorOverrides.crowd_action}
            onChange={(value) => updateDirectorOverride("crowd_action", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.crowdEmotionOverride}
            value={directorOverrides.crowd_emotion}
            onChange={(value) => updateDirectorOverride("crowd_emotion", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.directorCameraMotionOverride}
            value={directorOverrides.camera_movement}
            onChange={(value) => updateDirectorOverride("camera_movement", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.compositionOverride}
            value={directorOverrides.composition}
            onChange={(value) => updateDirectorOverride("composition", value)}
          />
          <OverrideTextarea
            label={promptBuilderCopy.environmentMotionOverride}
            value={directorOverrides.environment_motion}
            onChange={(value) => updateDirectorOverride("environment_motion", value)}
          />
        </div>
      </div>

      <StatusMessage tone="neutral">{promptBuilderCopy.safeNote}</StatusMessage>
      {mutation.isError && (
        <StatusMessage tone="error">{promptBuilderCopy.loadFailed}</StatusMessage>
      )}

      {draft ? (
        <div className="grid gap-3">
          <DraftText
            label={promptBuilderCopy.contextSummary}
            value={draft.context_summary_zh}
            copied={copied}
            onCopy={copyText}
          />
          <DirectorContextPreview draft={draft} />
          <DraftText
            label={promptBuilderCopy.firstFramePrompt}
            value={draft.first_frame_prompt_en}
            copied={copied}
            onCopy={copyText}
          />
          <DraftText
            label={promptBuilderCopy.endFramePrompt}
            value={draft.end_frame_prompt_en}
            copied={copied}
            onCopy={copyText}
          />
          <DraftText
            label={promptBuilderCopy.motionPrompt}
            value={draft.motion_prompt_en}
            copied={copied}
            onCopy={copyText}
          />
          <DraftText
            label={promptBuilderCopy.negativePrompt}
            value={draft.negative_prompt_en}
            copied={copied}
            onCopy={copyText}
          />
          {draft.camera_motion && (
            <DraftText
              label={promptBuilderCopy.cameraMotion}
              value={draft.camera_motion}
              copied={copied}
              onCopy={copyText}
            />
          )}
          {(onCreateFirstFrameTask || onCreateEndFrameTask || onCreateVideoTask) && (
            <div className="grid gap-2 rounded-md border border-border bg-panel p-3">
              <div className="text-xs font-semibold text-muted">
                {promptBuilderCopy.createTaskSection}
              </div>
              <div className="flex flex-wrap gap-2">
                {onCreateFirstFrameTask && (
                  <CreateTaskButton
                    label={promptBuilderCopy.createFirstFrameTask}
                    busy={creatingTaskType === "first_frame"}
                    disabled={Boolean(creatingTaskType)}
                    onClick={() => void handleCreateTask("first_frame")}
                  />
                )}
                {onCreateEndFrameTask && (
                  <CreateTaskButton
                    label={promptBuilderCopy.createEndFrameTask}
                    busy={creatingTaskType === "end_frame"}
                    disabled={Boolean(creatingTaskType)}
                    onClick={() => void handleCreateTask("end_frame")}
                  />
                )}
                {onCreateVideoTask && (
                  <CreateTaskButton
                    label={promptBuilderCopy.createVideoTaskDraft}
                    busy={creatingTaskType === "video"}
                    disabled={Boolean(creatingTaskType)}
                    onClick={() => void handleCreateTask("video")}
                  />
                )}
              </div>
            </div>
          )}
          <div className="rounded-md border border-border bg-panel p-2">
            <div className="text-xs font-semibold text-muted">{promptBuilderCopy.warnings}</div>
            {draft.warnings.length > 0 ? (
              <ul className="mt-2 grid gap-1 text-xs text-muted">
                {draft.warnings.map((warning) => (
                  <li key={warning.code}>
                    <span className="text-foreground">{warning.code}</span> - {warning.message}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-muted">{promptBuilderCopy.noWarnings}</p>
            )}
          </div>
        </div>
      ) : (
        <p className="rounded-md border border-dashed border-border px-3 py-4 text-sm text-muted">
          {promptBuilderCopy.noDraft}
        </p>
      )}
    </section>
  );
}

function DirectorContextPreview({ draft }: { draft: PromptDraftResponse }) {
  const context = draft.director_context;
  if (!context) {
    return null;
  }
  return (
    <div className="grid gap-2 rounded-md border border-border bg-panel p-3 text-xs text-muted">
      <div className="flex flex-wrap gap-2 text-foreground">
        <span>
          {promptBuilderCopy.recommendedTemplate}:{" "}
          {templateLabel(draft.recommended_template_id)}
        </span>
        <span>
          {promptBuilderCopy.appliedTemplate}: {templateLabel(draft.applied_template_id)}
        </span>
        <span>
          {promptBuilderCopy.workflowHint}: {draft.workflow_hint}
        </span>
      </div>
      <div className="text-xs font-semibold text-muted">{promptBuilderCopy.directorContext}</div>
      <DirectorContextRows context={context} />
    </div>
  );
}

function DirectorContextRows({ context }: { context: DirectorContext }) {
  const primary = context.subjects.find((subject) => subject.role === "primary");
  const rows = [
    ["主体", primary?.identity ?? "未指定"],
    ["位置", primary?.position ?? "未指定"],
    ["首帧动作", primary?.start_action ?? "未指定"],
    ["尾帧动作", primary?.end_action ?? "未指定"],
    [
      "群众反应",
      [context.reaction.crowd_action, context.reaction.crowd_emotion]
        .filter(Boolean)
        .join(" / ") || "未指定"
    ],
    ["场景", [context.scene.name, context.scene.state].filter(Boolean).join(" / ") || "未指定"],
    ["构图", context.camera.composition],
    ["镜头运动", context.camera.movement]
  ];
  return (
    <dl className="grid gap-1">
      {rows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[72px_1fr] gap-2">
          <dt className="text-muted">{label}</dt>
          <dd className="text-foreground">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function CreateTaskButton({
  label,
  busy,
  disabled,
  onClick
}: {
  label: string;
  busy: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <Button type="button" size="sm" variant="secondary" onClick={onClick} disabled={disabled}>
      <Plus className="h-4 w-4" aria-hidden="true" />
      {busy ? promptBuilderCopy.creatingTask : label}
    </Button>
  );
}

function OverrideTextarea({
  label,
  value,
  onChange
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-xs text-muted">
      {label}
      <Textarea
        value={value}
        rows={2}
        placeholder={promptBuilderCopy.overridePlaceholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function DraftText({
  label,
  value,
  copied,
  onCopy
}: {
  label: string;
  value: string;
  copied: string | null;
  onCopy: (label: string, value: string) => void | Promise<void>;
}) {
  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-muted">{label}</span>
        <Button type="button" size="sm" variant="ghost" onClick={() => void onCopy(label, value)}>
          <Clipboard className="h-4 w-4" aria-hidden="true" />
          {copied === label ? promptBuilderCopy.copied : promptBuilderCopy.copy}
        </Button>
      </div>
      <Textarea value={value} readOnly rows={label === promptBuilderCopy.contextSummary ? 3 : 4} />
    </div>
  );
}

function compactOverrides(
  overrides: Record<keyof PromptDraftOverrides, string>
): PromptDraftOverrides | undefined {
  const entries = Object.entries(overrides)
    .map(([key, value]) => [key, value.trim()] as const)
    .filter(([, value]) => value.length > 0);
  if (entries.length === 0) {
    return undefined;
  }
  return Object.fromEntries(entries) as PromptDraftOverrides;
}

function compactDirectorOverrides(
  overrides: Record<keyof DirectorOverrides, string>
): DirectorOverrides | undefined {
  const entries = Object.entries(overrides)
    .map(([key, value]) => [key, value.trim()] as const)
    .filter(([, value]) => value.length > 0);
  if (entries.length === 0) {
    return undefined;
  }
  return Object.fromEntries(entries) as DirectorOverrides;
}

function templateLabel(templateId: string) {
  return promptBuilderCopy.templateLabels[
    templateId as keyof typeof promptBuilderCopy.templateLabels
  ] ?? templateId;
}

function createConfirmMessage(
  type: "first_frame" | "end_frame" | "video",
  warningCount: number
) {
  const base =
    type === "first_frame"
      ? promptBuilderCopy.confirmFirstFrameTask
      : type === "end_frame"
        ? promptBuilderCopy.confirmEndFrameTask
        : promptBuilderCopy.confirmVideoTask;
  return warningCount > 0
    ? `${base}\n${promptBuilderCopy.warningConfirmLine(warningCount)}`
    : base;
}
