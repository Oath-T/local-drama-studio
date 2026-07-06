import { Badge } from "@/features/characters/components/status-badge";

import { assetPickerCopy } from "../copy";
import type { PickerOptionItem } from "../types";

export function AssetPickerPreview({ item }: { item: PickerOptionItem | null }) {
  if (!item) {
    return (
      <aside className="rounded-md border border-dashed border-border bg-background p-3 text-sm text-muted">
        {assetPickerCopy.noPreview}
      </aside>
    );
  }

  return (
    <aside className="grid gap-3 rounded-md border border-border bg-background p-3">
      {item.thumbnail_url || item.content_url ? (
        <img
          src={item.thumbnail_url ?? item.content_url ?? ""}
          alt=""
          className="aspect-video w-full rounded object-cover"
        />
      ) : null}
      <div>
        <h3 className="text-sm font-semibold text-foreground">{item.name}</h3>
        <p className="mt-1 text-xs text-muted">{item.source.label}</p>
        {item.description && <p className="mt-2 text-xs leading-5 text-muted">{item.description}</p>}
      </div>
      <div className="flex flex-wrap gap-1">
        {item.badges.map((badge) => (
          <Badge key={badge}>{badge}</Badge>
        ))}
      </div>
    </aside>
  );
}
