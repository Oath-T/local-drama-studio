import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ExternalLink, Play, RefreshCw, RotateCcw, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { Badge } from "@/features/characters/components/status-badge";
import type { KeyframeTask } from "@/features/keyframe-tasks/types";
import { shotKeys } from "@/features/shots/api";
import { ApiClientError } from "@/lib/api-client";

import {
  fetchKeyframeRuns,
  fetchKeyframeWorkflows,
  fetchSystemCapabilities,
  retryKeyframeRun,
  selectKeyframeOutput,
  startKeyframeRun,
  unselectKeyframeOutput
} from "../api";
import { keyframeGenerationCopy, missingRequirementText } from "../copy";
import type { KeyframeOutput, KeyframeRun, KeyframeWorkflow } from "../types";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

export function KeyframeGenerationSection({
  projectId,
  task,
  onMessage,
  invalidateTaskData
}: {
  projectId: string;
  task: KeyframeTask;
  onMessage: (message: { tone: "success" | "error"; text: string } | null) => void;
  invalidateTaskData: (taskId?: string) => Promise<void>;
}) {
  const queryClient = useQueryClient();
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>("");
  const capabilitiesQuery = useQuery({
    queryKey: shotKeys.systemCapabilities(),
    queryFn: fetchSystemCapabilities
  });
  const workflowsQuery = useQuery({
    queryKey: shotKeys.keyframeWorkflows(projectId),
    queryFn: () => fetchKeyframeWorkflows(projectId)
  });
  const runsQuery = useQuery({
    queryKey: shotKeys.keyframeRuns(projectId, task.id),
    queryFn: () => fetchKeyframeRuns(projectId, task.id),
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.items.some(isActiveRun) ? 2000 : false;
    }
  });

  const workflows = workflowsQuery.data?.items ?? [];
  const selectedWorkflow = workflows.find((item) => item.workflow_id === selectedWorkflowId);
  const activeRun = runsQuery.data?.items.find(isActiveRun);
  const provider = capabilitiesQuery.data?.keyframe_generation;
  const providerOnline = provider?.available === true && provider.status === "online";
  const disabledReasons = generationDisabledReasons(
    task,
    providerOnline,
    selectedWorkflow,
    Boolean(activeRun)
  );

  const invalidateGenerationData = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: shotKeys.keyframeRuns(projectId, task.id) }),
      queryClient.invalidateQueries({ queryKey: shotKeys.keyframeTask(projectId, task.id) }),
      invalidateTaskData(task.id)
    ]);
  };

  const startMutation = useMutation({
    mutationFn: () =>
      startKeyframeRun(projectId, task.id, { workflow_id: selectedWorkflowId }),
    onSuccess: async () => {
      await invalidateGenerationData();
      onMessage({ tone: "success", text: keyframeGenerationCopy.generated });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeGenerationCopy.startFailed)
      })
  });
  const retryMutation = useMutation({
    mutationFn: (runId: string) => retryKeyframeRun(projectId, runId),
    onSuccess: async () => {
      await invalidateGenerationData();
      onMessage({ tone: "success", text: keyframeGenerationCopy.retryStarted });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeGenerationCopy.startFailed)
      })
  });
  const selectMutation = useMutation({
    mutationFn: ({ output, selected }: { output: KeyframeOutput; selected: boolean }) =>
      selected
        ? unselectKeyframeOutput(projectId, output.id)
        : selectKeyframeOutput(projectId, output.id),
    onSuccess: async () => {
      await invalidateGenerationData();
      onMessage({ tone: "success", text: keyframeGenerationCopy.selectUpdated });
    },
    onError: (error) =>
      onMessage({
        tone: "error",
        text: getErrorText(error, keyframeGenerationCopy.selectFailed)
      })
  });
  const canStart = disabledReasons.length === 0 && !startMutation.isPending;

  useEffect(() => {
    if (!selectedWorkflowId && workflows.length > 0) {
      setSelectedWorkflowId(workflows[0].workflow_id);
    }
  }, [selectedWorkflowId, workflows]);

  const runs = runsQuery.data?.items ?? [];
  const allOutputs = useMemo(
    () => runs.flatMap((run) => run.outputs.map((output) => ({ output, run }))),
    [runs]
  );

  return (
    <section className="grid gap-4 border-t border-border pt-4">
      <div>
        <h3 className="text-sm font-semibold text-foreground">
          {keyframeGenerationCopy.title}
        </h3>
        <p className="mt-1 text-xs leading-5 text-muted">{keyframeGenerationCopy.localOnly}</p>
      </div>
      <StatusMessage tone="neutral">{keyframeGenerationCopy.noReferenceInputs}</StatusMessage>

      <div className="grid gap-3 rounded-md border border-border bg-background p-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={providerOnline ? "success" : "default"}>
            {providerOnline
              ? keyframeGenerationCopy.providerStatus.online
              : keyframeGenerationCopy.providerStatus[provider?.status as "offline"] ??
                keyframeGenerationCopy.providerStatus.offline}
          </Badge>
          {capabilitiesQuery.isError && (
            <span className="text-xs text-danger">
              {keyframeGenerationCopy.capabilitiesLoadFailed}
            </span>
          )}
        </div>

        <div className="grid gap-2 md:grid-cols-[minmax(0,1fr)_auto]">
          <Select
            value={selectedWorkflowId}
            onValueChange={setSelectedWorkflowId}
            disabled={workflows.length === 0}
          >
            <SelectTrigger aria-label={keyframeGenerationCopy.workflow}>
              <SelectValue placeholder={keyframeGenerationCopy.workflow} />
            </SelectTrigger>
            <SelectContent>
              {workflows.map((workflow) => (
                <SelectItem key={workflow.workflow_id} value={workflow.workflow_id}>
                  {workflow.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            type="button"
            disabled={!canStart}
            onClick={() => startMutation.mutate()}
          >
            <Play className="h-4 w-4" aria-hidden="true" />
            {startMutation.isPending ? keyframeGenerationCopy.starting : keyframeGenerationCopy.start}
          </Button>
        </div>

        <p className="text-xs text-muted">
          {
            keyframeGenerationCopy.promptLanguage[
              task.prompt_en?.trim() ? "en" : "zh"
            ]
          }
        </p>
        <WorkflowStatus workflow={selectedWorkflow} />
        {disabledReasons.length > 0 && (
          <div className="grid gap-1 text-xs text-muted">
            {disabledReasons.map((reason) => (
              <p key={reason}>{reason}</p>
            ))}
          </div>
        )}
        {workflowsQuery.isLoading && <Skeleton className="h-10" />}
        {workflowsQuery.isError && (
          <StatusMessage tone="error">{keyframeGenerationCopy.workflowLoadFailed}</StatusMessage>
        )}
      </div>

      <section className="grid gap-3">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-xs font-semibold text-muted">{keyframeGenerationCopy.runList}</h4>
          <Button type="button" variant="secondary" size="sm" onClick={() => void runsQuery.refetch()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            刷新
          </Button>
        </div>
        {runsQuery.isLoading ? (
          <Skeleton className="h-28" />
        ) : runsQuery.isError ? (
          <StatusMessage tone="error">{keyframeGenerationCopy.loadFailed}</StatusMessage>
        ) : runs.length === 0 ? (
          <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted">
            {keyframeGenerationCopy.noRuns}
          </p>
        ) : (
          <div className="grid gap-2">
            {runs.map((run) => (
              <RunCard
                key={run.id}
                run={run}
                retryDisabled={retryMutation.isPending || isActiveRun(run)}
                onRetry={() => retryMutation.mutate(run.id)}
              />
            ))}
          </div>
        )}
      </section>

      <section className="grid gap-3">
        <h4 className="text-xs font-semibold text-muted">
          {keyframeGenerationCopy.outputGallery}
        </h4>
        {allOutputs.length === 0 ? (
          <p className="rounded-md border border-dashed border-border p-3 text-sm text-muted">
            {keyframeGenerationCopy.noOutputs}
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {allOutputs.map(({ output, run }) => (
              <OutputCard
                key={output.id}
                output={output}
                run={run}
                disabled={selectMutation.isPending}
                onToggleSelect={() =>
                  selectMutation.mutate({ output, selected: output.is_selected })
                }
              />
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

function WorkflowStatus({ workflow }: { workflow?: KeyframeWorkflow }) {
  if (!workflow) {
    return null;
  }
  if (workflow.available) {
    return (
      <p className="text-xs text-success">
        {workflow.display_name} v{workflow.version} 可用
      </p>
    );
  }
  return (
    <div className="grid gap-1 text-xs text-danger">
      {workflow.missing_requirements.map((item) => (
        <p key={item}>{missingRequirementText(item)}</p>
      ))}
    </div>
  );
}

function RunCard({
  run,
  retryDisabled,
  onRetry
}: {
  run: KeyframeRun;
  retryDisabled: boolean;
  onRetry: () => void;
}) {
  const canRetry = run.status === "failed" || run.status === "interrupted";
  return (
    <article className="rounded-md border border-border bg-background p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={run.status === "completed" ? "success" : "default"}>
              {keyframeGenerationCopy.status[run.status]}
            </Badge>
            <span className="text-xs text-muted">#{run.run_number}</span>
          </div>
          <p className="mt-2 text-xs text-muted">
            seed {run.submitted_payload_snapshot.seed} · {run.workflow_id}
          </p>
          <p className="mt-1 text-xs text-muted">{formatDate(run.created_at)}</p>
        </div>
        {canRetry && (
          <Button type="button" variant="secondary" size="sm" onClick={onRetry} disabled={retryDisabled}>
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
            {keyframeGenerationCopy.retry}
          </Button>
        )}
      </div>
      {run.error_message_safe && (
        <p className="mt-2 rounded-md border border-danger/40 bg-danger/10 p-2 text-xs text-danger">
          {run.error_message_safe}
        </p>
      )}
    </article>
  );
}

function OutputCard({
  output,
  run,
  disabled,
  onToggleSelect
}: {
  output: KeyframeOutput;
  run: KeyframeRun;
  disabled: boolean;
  onToggleSelect: () => void;
}) {
  const media = output.media_asset;
  return (
    <article className="rounded-md border border-border bg-background p-2">
      {media ? (
        <img src={media.thumbnail_url} alt="" className="aspect-video w-full rounded object-cover" />
      ) : (
        <div className="aspect-video rounded border border-dashed border-border" />
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {output.is_selected && <Badge tone="success">{keyframeGenerationCopy.selected}</Badge>}
        <span className="text-xs text-muted">Run #{run.run_number}</span>
        <span className="text-xs text-muted">seed {output.seed ?? run.submitted_payload_snapshot.seed}</span>
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <Button type="button" variant="secondary" size="sm" onClick={onToggleSelect} disabled={disabled}>
          <Star className="h-4 w-4" aria-hidden="true" />
          {output.is_selected ? keyframeGenerationCopy.unselect : keyframeGenerationCopy.useVersion}
        </Button>
        {media && (
          <>
            <Button type="button" variant="secondary" size="sm" asChild>
              <a href={media.content_url} target="_blank" rel="noreferrer">
                <ExternalLink className="h-4 w-4" aria-hidden="true" />
                {keyframeGenerationCopy.openOriginal}
              </a>
            </Button>
            <Button type="button" variant="secondary" size="sm" asChild>
              <a href={media.content_url} download>
                <Download className="h-4 w-4" aria-hidden="true" />
                {keyframeGenerationCopy.download}
              </a>
            </Button>
          </>
        )}
      </div>
    </article>
  );
}

function generationDisabledReasons(
  task: KeyframeTask,
  providerOnline: boolean,
  workflow: KeyframeWorkflow | undefined,
  hasActiveRun: boolean
): string[] {
  const reasons: string[] = [];
  if (task.status !== "ready") reasons.push(keyframeGenerationCopy.disabledReasons.notReadyStatus);
  if (task.readiness.readiness_status !== "ready") {
    reasons.push(keyframeGenerationCopy.disabledReasons.notReadyReadiness);
  }
  if (task.output_count !== 1) {
    reasons.push(keyframeGenerationCopy.disabledReasons.outputCountUnsupported);
  }
  if (!providerOnline) reasons.push(keyframeGenerationCopy.disabledReasons.providerOffline);
  if (!workflow) reasons.push(keyframeGenerationCopy.disabledReasons.workflowMissing);
  if (workflow && !workflow.available) {
    reasons.push(keyframeGenerationCopy.disabledReasons.workflowUnavailable);
  }
  if (hasActiveRun) reasons.push(keyframeGenerationCopy.disabledReasons.activeRun);
  return reasons;
}

function isActiveRun(run: KeyframeRun): boolean {
  return ACTIVE_STATUSES.has(run.status);
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString();
}

function getErrorText(error: unknown, fallback: string) {
  return error instanceof ApiClientError ? error.message : fallback;
}
