import { useMutation, useQuery } from "@tanstack/react-query";
import { RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import type { CharacterReference } from "@/features/characters/types";
import type { SceneReference } from "@/features/scenes/types";
import { ApiClientError } from "@/lib/api-client";

import {
  confirmCharacterReferenceAnalysis,
  confirmSceneReferenceAnalysis,
  fetchLatestCharacterReferenceAnalysisTask,
  fetchLatestSceneReferenceAnalysisTask,
  fetchVisionAnalysisTask,
  rejectCharacterReferenceAnalysis,
  rejectSceneReferenceAnalysis,
  startCharacterReferenceAnalysis,
  startSceneReferenceAnalysis,
  visionAnalysisKeys
} from "../api";
import { visionAnalysisCopy } from "../copy";
import type {
  AnalysisConfirmInput,
  CharacterVisionAnalysisSuggestion,
  SceneVisionAnalysisSuggestion,
  VisionAnalysisTask
} from "../types";

interface CharacterReferenceAnalysisDialogProps {
  projectId: string;
  characterId: string;
  reference: CharacterReference;
  onUpdated: () => Promise<void>;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

interface SceneReferenceAnalysisDialogProps {
  projectId: string;
  sceneId: string;
  reference: SceneReference;
  onUpdated: () => Promise<void>;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}

type AnalysisKind = "character" | "scene";

export function CharacterReferenceAnalysisDialog({
  projectId,
  characterId,
  reference,
  onUpdated,
  onSuccess,
  onError
}: CharacterReferenceAnalysisDialogProps) {
  return (
    <ReferenceAnalysisDialog
      kind="character"
      projectId={projectId}
      parentId={characterId}
      containerId={reference.look_id}
      reference={reference}
      onUpdated={onUpdated}
      onSuccess={onSuccess}
      onError={onError}
    />
  );
}

export function SceneReferenceAnalysisDialog({
  projectId,
  sceneId,
  reference,
  onUpdated,
  onSuccess,
  onError
}: SceneReferenceAnalysisDialogProps) {
  return (
    <ReferenceAnalysisDialog
      kind="scene"
      projectId={projectId}
      parentId={sceneId}
      containerId={reference.state_id}
      reference={reference}
      onUpdated={onUpdated}
      onSuccess={onSuccess}
      onError={onError}
    />
  );
}

function ReferenceAnalysisDialog({
  kind,
  projectId,
  parentId,
  containerId,
  reference,
  onUpdated,
  onSuccess,
  onError
}: {
  kind: AnalysisKind;
  projectId: string;
  parentId: string;
  containerId: string;
  reference: CharacterReference | SceneReference;
  onUpdated: () => Promise<void>;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [settledTaskId, setSettledTaskId] = useState<string | null>(null);
  const suggestions = reference.analysis_suggestions;
  const fields = useMemo(() => buildFields(kind, reference, suggestions), [kind, reference, suggestions]);
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  const [values, setValues] = useState<Record<string, string | boolean>>({});

  useEffect(() => {
    if (!open) {
      return;
    }
    const defaults = fields.filter((field) => field.defaultSelected).map((field) => field.key);
    setSelectedFields(defaults);
    setValues(Object.fromEntries(fields.map((field) => [field.key, field.initialValue])));
  }, [fields, open]);

  const latestQuery = useQuery({
    queryKey:
      kind === "character"
        ? visionAnalysisKeys.characterLatest(projectId, parentId, containerId, reference.id)
        : visionAnalysisKeys.sceneLatest(projectId, parentId, containerId, reference.id),
    queryFn: () =>
      kind === "character"
        ? fetchLatestCharacterReferenceAnalysisTask(projectId, parentId, containerId, reference.id)
        : fetchLatestSceneReferenceAnalysisTask(projectId, parentId, containerId, reference.id),
    enabled: open || reference.analysis_status === "pending"
  });

  const effectiveTaskId = taskId ?? latestQuery.data?.task?.id ?? null;
  const taskQuery = useQuery({
    queryKey: effectiveTaskId
      ? visionAnalysisKeys.task(projectId, effectiveTaskId)
      : ["vision-analysis", "idle"],
    queryFn: () => fetchVisionAnalysisTask(projectId, effectiveTaskId ?? ""),
    enabled: Boolean(effectiveTaskId),
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "running"
        ? 2000
        : false
  });

  useEffect(() => {
    const task = taskQuery.data;
    if (!task || task.id === settledTaskId) {
      return;
    }
    if (task.status === "completed" || task.status === "failed") {
      setSettledTaskId(task.id);
      void onUpdated();
    }
  }, [onUpdated, settledTaskId, taskQuery.data]);

  const startMutation = useMutation({
    mutationFn: () =>
      kind === "character"
        ? startCharacterReferenceAnalysis(projectId, parentId, containerId, reference.id)
        : startSceneReferenceAnalysis(projectId, parentId, containerId, reference.id),
    onSuccess: (task) => {
      setTaskId(task.id);
      setSettledTaskId(null);
      onSuccess(visionAnalysisCopy.started);
    },
    onError: (error) => onError(errorMessage(error, visionAnalysisCopy.startFailed))
  });

  const confirmMutation = useMutation({
    mutationFn: (payload: AnalysisConfirmInput) =>
      kind === "character"
        ? confirmCharacterReferenceAnalysis(projectId, parentId, containerId, reference.id, payload)
        : confirmSceneReferenceAnalysis(projectId, parentId, containerId, reference.id, payload),
    onSuccess: async () => {
      await onUpdated();
      onSuccess(visionAnalysisCopy.accepted);
      setOpen(false);
    },
    onError: (error) => onError(errorMessage(error, visionAnalysisCopy.confirmFailed))
  });

  const rejectMutation = useMutation({
    mutationFn: () =>
      kind === "character"
        ? rejectCharacterReferenceAnalysis(projectId, parentId, containerId, reference.id)
        : rejectSceneReferenceAnalysis(projectId, parentId, containerId, reference.id),
    onSuccess: async () => {
      await onUpdated();
      onSuccess(visionAnalysisCopy.rejected);
      setOpen(false);
    },
    onError: (error) => onError(errorMessage(error, visionAnalysisCopy.rejectFailed))
  });

  const task = taskQuery.data ?? latestQuery.data?.task ?? null;
  const isBusy =
    startMutation.isPending ||
    confirmMutation.isPending ||
    rejectMutation.isPending ||
    task?.status === "pending" ||
    task?.status === "running";
  const buttonText =
    reference.analysis_status === "completed"
      ? visionAnalysisCopy.viewSuggestions
      : reference.analysis_status === "failed"
        ? visionAnalysisCopy.reanalyzeImage
        : reference.analysis_status === "pending"
          ? visionAnalysisCopy.analyzing
          : visionAnalysisCopy.analyzeImage;

  function submitSelected() {
    const payloadValues: Record<string, unknown> = {};
    for (const field of fields) {
      if (!selectedFields.includes(field.key)) {
        continue;
      }
      payloadValues[field.key] =
        field.kind === "tags" && typeof values[field.key] === "string"
          ? String(values[field.key])
              .split(",")
              .map((tag) => tag.trim())
              .filter(Boolean)
          : values[field.key];
    }
    confirmMutation.mutate({ accepted_fields: selectedFields, values: payloadValues });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button type="button" size="sm" variant="secondary" disabled={startMutation.isPending}>
          <Search className="h-4 w-4" aria-hidden="true" />
          {buttonText}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-[860px]">
        <DialogHeader>
          <DialogTitle>{visionAnalysisCopy.title}</DialogTitle>
          <DialogDescription>{visionAnalysisCopy.description}</DialogDescription>
        </DialogHeader>

        <p className="rounded-md border border-border bg-background p-3 text-sm text-muted">
          {visionAnalysisCopy.privacyNotice}
        </p>

        <TaskStatus task={task} hasSuggestions={Boolean(suggestions)} />

        {!suggestions && (
          <div className="rounded-md border border-border bg-background p-4 text-sm text-muted">
            {visionAnalysisCopy.noSuggestion}
          </div>
        )}

        {suggestions && (
          <div className="overflow-hidden rounded-md border border-border">
            <div className="grid grid-cols-[72px_140px_1fr_1fr_1fr] bg-background px-3 py-2 text-xs font-medium text-muted">
              <span>{visionAnalysisCopy.selectField}</span>
              <span>字段</span>
              <span>{visionAnalysisCopy.currentValue}</span>
              <span>{visionAnalysisCopy.suggestedValue}</span>
              <span>{visionAnalysisCopy.finalValue}</span>
            </div>
            {fields.map((field) => (
              <label
                key={field.key}
                className="grid grid-cols-[72px_140px_1fr_1fr_1fr] items-center gap-2 border-t border-border px-3 py-2 text-sm"
              >
                <input
                  type="checkbox"
                  checked={selectedFields.includes(field.key)}
                  onChange={(event) =>
                    setSelectedFields((current) =>
                      event.target.checked
                        ? [...current, field.key]
                        : current.filter((item) => item !== field.key)
                    )
                  }
                />
                <span className="text-muted">{field.label}</span>
                <span className="text-muted">{displayValue(field.currentValue)}</span>
                <span className="text-foreground">{displayValue(field.suggestedValue)}</span>
                {field.kind === "boolean" ? (
                  <input
                    type="checkbox"
                    checked={Boolean(values[field.key])}
                    onChange={(event) =>
                      setValues((current) => ({
                        ...current,
                        [field.key]: event.target.checked
                      }))
                    }
                  />
                ) : (
                  <input
                    className="h-8 rounded-md border border-border bg-panel px-2 text-sm text-foreground"
                    value={String(values[field.key] ?? "")}
                    onChange={(event) =>
                      setValues((current) => ({
                        ...current,
                        [field.key]: event.target.value
                      }))
                    }
                  />
                )}
              </label>
            ))}
          </div>
        )}

        <div className="flex flex-wrap justify-between gap-2">
          <Button
            type="button"
            variant="secondary"
            disabled={isBusy}
            onClick={() => startMutation.mutate()}
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            {reference.analysis_status === "completed"
              ? visionAnalysisCopy.reanalyzeImage
              : visionAnalysisCopy.analyzeImage}
          </Button>
          <div className="flex flex-wrap gap-2">
            {suggestions && (
              <Button
                type="button"
                variant="danger"
                disabled={isBusy}
                onClick={() => rejectMutation.mutate()}
              >
                {visionAnalysisCopy.rejectSuggestion}
              </Button>
            )}
            {suggestions && (
              <Button
                type="button"
                disabled={isBusy || selectedFields.length === 0}
                onClick={submitSelected}
              >
                {visionAnalysisCopy.acceptSelected}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface FieldRow {
  key: string;
  label: string;
  currentValue: unknown;
  suggestedValue: unknown;
  initialValue: string | boolean;
  defaultSelected: boolean;
  kind: "text" | "tags" | "boolean";
}

function buildFields(
  kind: AnalysisKind,
  reference: CharacterReference | SceneReference,
  suggestions: CharacterVisionAnalysisSuggestion | SceneVisionAnalysisSuggestion | null
): FieldRow[] {
  if (!suggestions) {
    return [];
  }
  if (kind === "character") {
    const characterReference = reference as CharacterReference;
    const characterSuggestion = suggestions as CharacterVisionAnalysisSuggestion;
    return [
      field("shot_type", characterReference.shot_type, characterSuggestion.shot_type),
      field("view_angle", characterReference.view_angle, characterSuggestion.view_angle),
      field("expression", characterReference.expression, characterSuggestion.expression),
      field("custom_expression", characterReference.custom_expression, characterSuggestion.custom_expression),
      field("pose_type", characterReference.pose_type, characterSuggestion.pose_type),
      field("custom_pose", characterReference.custom_pose, characterSuggestion.custom_pose),
      field("tags", characterReference.tags, characterSuggestion.tags, "tags"),
      field("description", characterReference.description, characterSuggestion.description),
      field(
        "is_identity_anchor",
        characterReference.is_identity_anchor,
        characterSuggestion.identity_anchor_recommended,
        "boolean"
      )
    ].filter((item) => hasSuggestedValue(item.suggestedValue));
  }
  const sceneReference = reference as SceneReference;
  const sceneSuggestion = suggestions as SceneVisionAnalysisSuggestion;
  return [
    field("shot_scale", sceneReference.shot_scale, sceneSuggestion.shot_scale),
    field("camera_position", sceneReference.camera_position, sceneSuggestion.camera_position),
    field(
      "custom_camera_position",
      sceneReference.custom_camera_position,
      sceneSuggestion.custom_camera_position
    ),
    field("view_direction", sceneReference.view_direction, sceneSuggestion.view_direction),
    field(
      "custom_view_direction",
      sceneReference.custom_view_direction,
      sceneSuggestion.custom_view_direction
    ),
    field("composition_type", sceneReference.composition_type, sceneSuggestion.composition_type),
    field("custom_composition", sceneReference.custom_composition, sceneSuggestion.custom_composition),
    field("tags", sceneReference.tags, sceneSuggestion.tags, "tags"),
    field("description", sceneReference.description, sceneSuggestion.description),
    field(
      "is_spatial_anchor",
      sceneReference.is_spatial_anchor,
      sceneSuggestion.spatial_anchor_recommended,
      "boolean"
    ),
    field(
      "is_empty_plate",
      sceneReference.is_empty_plate,
      sceneSuggestion.empty_plate_recommended,
      "boolean"
    )
  ].filter((item) => hasSuggestedValue(item.suggestedValue));
}

function field(
  key: string,
  currentValue: unknown,
  suggestedValue: unknown,
  kind: FieldRow["kind"] = "text"
): FieldRow {
  const isBoolean = kind === "boolean";
  return {
    key,
    label: visionAnalysisCopy.fieldLabels[key] ?? key,
    currentValue,
    suggestedValue,
    initialValue:
      kind === "tags" && Array.isArray(suggestedValue)
        ? suggestedValue.join(", ")
        : isBoolean
          ? Boolean(suggestedValue)
          : String(suggestedValue ?? ""),
    defaultSelected: !isBoolean && isEmptyOfficialValue(currentValue),
    kind
  };
}

function hasSuggestedValue(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  return value !== null && value !== undefined && value !== "" && value !== "unknown";
}

function isEmptyOfficialValue(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.length === 0;
  }
  return value === null || value === undefined || value === "" || value === "unknown";
}

function displayValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : visionAnalysisCopy.empty;
  }
  if (typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (value === null || value === undefined || value === "" || value === "unknown") {
    return visionAnalysisCopy.empty;
  }
  return String(value);
}

function TaskStatus({
  task,
  hasSuggestions
}: {
  task: VisionAnalysisTask | null;
  hasSuggestions: boolean;
}) {
  if (!task) {
    return null;
  }
  const label =
    task.status === "completed"
      ? visionAnalysisCopy.completed
      : task.status === "failed"
        ? visionAnalysisCopy.failed
        : task.status === "running"
          ? visionAnalysisCopy.analyzing
          : visionAnalysisCopy.pending;
  return (
    <div className="rounded-md border border-border bg-background p-3 text-sm text-muted">
      <span className="font-medium text-foreground">{label}</span>
      {task.status === "failed" && task.error_message_safe && (
        <span className="ml-2">{task.error_message_safe}</span>
      )}
      {task.status === "failed" && hasSuggestions && (
        <span className="ml-2 text-success">{visionAnalysisCopy.oldSuggestionKept}</span>
      )}
    </div>
  );
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiClientError ? error.message : fallback;
}
