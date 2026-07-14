import { cn } from "@/lib/utils";

export function Badge({
  children,
  tone = "default"
}: {
  children: string;
  tone?: "default" | "success" | "primary" | "danger";
}) {
  return (
    <span
      className={cn(
        "rounded-sm border px-2 py-1 text-xs",
        tone === "success" && "border-success/50 bg-success/10 text-success",
        tone === "primary" && "border-primary/50 bg-primarySoft text-foreground",
        tone === "danger" && "border-danger/50 bg-danger/10 text-danger",
        tone === "default" && "border-border bg-panel text-muted"
      )}
    >
      {children}
    </span>
  );
}
