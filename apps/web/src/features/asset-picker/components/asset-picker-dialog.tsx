import { useQuery } from "@tanstack/react-query";
import { RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";

import { fetchPickerOptions } from "../api";
import { assetPickerCopy } from "../copy";
import { assetPickerKeys } from "../queryKeys";
import type { PickerAssetType, PickerOptionItem, PickerScope } from "../types";
import { AssetCard } from "./asset-card";
import { AssetPickerEmptyState } from "./asset-picker-empty-state";
import { AssetPickerPreview } from "./asset-picker-preview";

export function AssetPickerDialog({
  open,
  onOpenChange,
  projectId,
  scope,
  assetType,
  shotId,
  title,
  description,
  confirmLabel = assetPickerCopy.confirm,
  disabledItemIds = [],
  onConfirm
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  scope: PickerScope;
  assetType: PickerAssetType;
  shotId?: string;
  title: string;
  description?: string;
  confirmLabel?: string;
  disabledItemIds?: string[];
  onConfirm: (item: PickerOptionItem) => void;
}) {
  const [queryText, setQueryText] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const disabledIds = useMemo(() => new Set(disabledItemIds), [disabledItemIds]);
  const params = {
    projectId,
    scope,
    assetType,
    shotId,
    q: queryText,
    limit: 40
  };
  const optionsQuery = useQuery({
    queryKey: assetPickerKeys.options(params),
    queryFn: () => fetchPickerOptions(params),
    enabled: open && projectId.length > 0
  });
  const items = optionsQuery.data?.items ?? [];
  const selectedItem = items.find((item) => item.id === selectedId) ?? null;

  useEffect(() => {
    if (!open) {
      setQueryText("");
      setSelectedId("");
    }
  }, [open]);

  useEffect(() => {
    if (selectedId && items.every((item) => item.id !== selectedId)) {
      setSelectedId("");
    }
  }, [items, selectedId]);

  function isDisabled(item: PickerOptionItem) {
    return item.is_selected || disabledIds.has(item.id);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[980px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        <div className="grid gap-4">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
            <Input
              value={queryText}
              onChange={(event) => setQueryText(event.currentTarget.value)}
              className="pl-9"
              placeholder={assetPickerCopy.searchPlaceholder}
              aria-label={assetPickerCopy.searchPlaceholder}
            />
          </label>

          {optionsQuery.isLoading && (
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_260px]">
              <div className="grid gap-3 md:grid-cols-2">
                <Skeleton className="h-44" />
                <Skeleton className="h-44" />
              </div>
              <Skeleton className="h-44" />
            </div>
          )}

          {optionsQuery.isError && (
            <div className="grid gap-3 rounded-md border border-border bg-background p-3">
              <StatusMessage tone="error">{assetPickerCopy.loadFailed}</StatusMessage>
              <Button type="button" variant="secondary" onClick={() => void optionsQuery.refetch()}>
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                {assetPickerCopy.retry}
              </Button>
            </div>
          )}

          {optionsQuery.isSuccess && items.length === 0 && (
            <AssetPickerEmptyState
              title={assetPickerCopy.emptyTitle}
              description={assetPickerCopy.emptyDescription[assetType]}
            />
          )}

          {optionsQuery.isSuccess && items.length > 0 && (
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
              <div className="grid max-h-[460px] gap-3 overflow-y-auto pr-1 md:grid-cols-2">
                {items.map((item) => (
                  <AssetCard
                    key={item.id}
                    item={item}
                    active={item.id === selectedId}
                    disabled={isDisabled(item)}
                    onSelect={() => setSelectedId(item.id)}
                  />
                ))}
              </div>
              <AssetPickerPreview item={selectedItem} />
            </div>
          )}

          {selectedItem && isDisabled(selectedItem) && (
            <StatusMessage tone="neutral">{assetPickerCopy.disabledSelected}</StatusMessage>
          )}

          <div className="flex justify-end gap-2 border-t border-border pt-4">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              {assetPickerCopy.cancel}
            </Button>
            <Button
              type="button"
              disabled={!selectedItem || isDisabled(selectedItem)}
              onClick={() => {
                if (selectedItem && !isDisabled(selectedItem)) {
                  onConfirm(selectedItem);
                  onOpenChange(false);
                }
              }}
            >
              {confirmLabel}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
