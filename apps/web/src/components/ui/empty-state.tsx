import { FolderOpen } from "lucide-react";
import type React from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <section className="flex min-h-[280px] items-center justify-center rounded-md border border-dashed border-border bg-panel/60 p-8 text-center">
      <div className="max-w-md">
        <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-md bg-panelRaised text-muted">
          <FolderOpen className="h-5 w-5" aria-hidden="true" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
        {action && <div className="mt-5 flex justify-center">{action}</div>}
      </div>
    </section>
  );
}
