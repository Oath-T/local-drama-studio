import { AlertCircle, CheckCircle2 } from "lucide-react";
import type React from "react";

import { cn } from "@/lib/utils";

interface StatusMessageProps {
  tone: "success" | "error" | "neutral";
  children: React.ReactNode;
}

export function StatusMessage({ tone, children }: StatusMessageProps) {
  const Icon = tone === "success" ? CheckCircle2 : AlertCircle;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border px-3 py-2 text-sm",
        tone === "success" && "border-success/40 bg-success/10 text-success",
        tone === "error" && "border-danger/40 bg-danger/10 text-danger",
        tone === "neutral" && "border-border bg-panel text-muted"
      )}
      role={tone === "error" ? "alert" : "status"}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}
