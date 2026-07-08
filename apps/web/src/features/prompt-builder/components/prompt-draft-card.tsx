import { useMutation } from "@tanstack/react-query";
import { Clipboard, FileText, RefreshCw, Wand2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status-message";
import { Textarea } from "@/components/ui/textarea";

import { buildPromptDraft } from "../api";
import { promptBuilderCopy } from "../copy";
import type { PromptDraftResponse, PromptDraftTarget } from "../types";

interface PromptDraftCardProps {
  projectId: string;
  shotId: string;
  target?: PromptDraftTarget;
  onDraft?: (draft: PromptDraftResponse) => void;
}

export function PromptDraftCard({
  projectId,
  shotId,
  target = "all",
  onDraft
}: PromptDraftCardProps) {
  const [draft, setDraft] = useState<PromptDraftResponse | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      buildPromptDraft(projectId, shotId, {
        target,
        style: "cinematic_short_drama",
        language: "en",
        include_negative_prompt: true
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
          <div className="rounded-md border border-border bg-panel p-2">
            <div className="text-xs font-semibold text-muted">{promptBuilderCopy.warnings}</div>
            {draft.warnings.length > 0 ? (
              <ul className="mt-2 grid gap-1 text-xs text-muted">
                {draft.warnings.map((warning) => (
                  <li key={warning.code}>
                    <span className="text-foreground">{warning.code}</span> · {warning.message}
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
