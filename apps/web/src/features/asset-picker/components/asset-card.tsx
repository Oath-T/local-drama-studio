import { CheckCircle2, ImageIcon } from "lucide-react";

import { Badge } from "@/features/characters/components/status-badge";
import { cn } from "@/lib/utils";

import { assetPickerCopy } from "../copy";
import type { PickerOptionItem } from "../types";

export function AssetCard({
  item,
  active,
  disabled,
  onSelect
}: {
  item: PickerOptionItem;
  active: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={cn(
        "grid gap-3 rounded-md border bg-background p-3 text-left transition-colors hover:border-primary disabled:cursor-not-allowed disabled:opacity-60",
        active ? "border-primary bg-primarySoft" : "border-border"
      )}
      disabled={disabled}
      onClick={onSelect}
    >
      <div className="relative overflow-hidden rounded border border-border bg-panel">
        {item.thumbnail_url || item.content_url ? (
          <img
            src={item.thumbnail_url ?? item.content_url ?? ""}
            alt=""
            className="aspect-video w-full object-cover"
          />
        ) : (
          <div className="flex aspect-video items-center justify-center text-muted">
            <ImageIcon className="h-6 w-6" aria-hidden="true" />
          </div>
        )}
        {active && (
          <span className="absolute right-2 top-2 rounded-full bg-primary p-1 text-white">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          </span>
        )}
      </div>
      <div className="min-w-0">
        <div className="truncate text-sm font-semibold text-foreground">{item.name}</div>
        <div className="mt-1 text-xs text-muted">{item.source.label}</div>
        {item.description && (
          <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted">{item.description}</p>
        )}
      </div>
      <div className="flex flex-wrap gap-1">
        {item.badges.map((badge) => (
          <Badge key={badge}>{badge}</Badge>
        ))}
        {active && <Badge tone="primary">{assetPickerCopy.selected}</Badge>}
      </div>
    </button>
  );
}
