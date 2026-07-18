import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type StudioStatusTone =
  | "draft"
  | "ready"
  | "running"
  | "success"
  | "warning"
  | "danger"
  | "info";

const toneClassName: Record<StudioStatusTone, string> = {
  draft: "border-[var(--studio-color-draft)]/50 bg-[var(--studio-color-draft-soft)] text-[var(--studio-color-text-secondary)]",
  ready: "border-[var(--studio-color-primary)]/50 bg-[var(--studio-color-primary-soft)] text-[#cfd2ff]",
  running: "border-[var(--studio-color-info)]/50 bg-[var(--studio-color-info-soft)] text-[#bfdbfe]",
  success: "border-[var(--studio-color-success)]/50 bg-[var(--studio-color-success-soft)] text-[#a7f3d0]",
  warning: "border-[var(--studio-color-warning)]/50 bg-[var(--studio-color-warning-soft)] text-[#fde68a]",
  danger: "border-[var(--studio-color-danger)]/50 bg-[var(--studio-color-danger-soft)] text-[#fecaca]",
  info: "border-[var(--studio-color-info)]/50 bg-[var(--studio-color-info-soft)] text-[#bfdbfe]"
};

interface StudioStatusBadgeProps {
  children: ReactNode;
  tone?: StudioStatusTone;
  className?: string;
}

export function StudioStatusBadge({
  children,
  tone = "draft",
  className
}: StudioStatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex min-h-6 items-center rounded-[var(--studio-radius-badge)] border px-2 text-xs font-medium",
        toneClassName[tone],
        className
      )}
    >
      {children}
    </span>
  );
}
