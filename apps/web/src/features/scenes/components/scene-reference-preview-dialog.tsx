import type { ReactNode } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { sceneCopy } from "@/features/scenes/copy";
import type { SceneReference } from "@/features/scenes/types";

interface SceneReferencePreviewDialogProps {
  reference: SceneReference;
  trigger: ReactNode;
}

export function SceneReferencePreviewDialog({
  reference,
  trigger
}: SceneReferencePreviewDialogProps) {
  const media = reference.media_asset;

  return (
    <Dialog>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-[920px]">
        <DialogHeader>
          <DialogTitle>{sceneCopy.previewOriginal}</DialogTitle>
          <DialogDescription>{media.original_filename}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="flex max-h-[68vh] items-center justify-center overflow-hidden rounded-md border border-border bg-background">
            <img src={media.content_url} alt="" className="max-h-[68vh] w-full object-contain" />
          </div>
          <dl className="grid content-start gap-3 text-sm">
            <Meta label={sceneCopy.fields.originalFilename} value={media.original_filename} />
            <Meta label={sceneCopy.fields.imageSize} value={`${media.width} x ${media.height}`} />
            <Meta label={sceneCopy.fields.fileType} value={media.mime_type} />
            <Meta label={sceneCopy.fields.fileSize} value={formatBytes(media.size_bytes)} />
            <Meta label={sceneCopy.fields.shotScale} value={sceneCopy.shotScale[reference.shot_scale]} />
            <Meta label={sceneCopy.fields.cameraPosition} value={displayCustom(sceneCopy.cameraPosition[reference.camera_position], reference.custom_camera_position)} />
            <Meta label={sceneCopy.fields.viewDirection} value={displayCustom(sceneCopy.viewDirection[reference.view_direction], reference.custom_view_direction)} />
            <Meta label={sceneCopy.fields.compositionType} value={displayCustom(sceneCopy.compositionType[reference.composition_type], reference.custom_composition)} />
            <Meta label={sceneCopy.fields.tags} value={reference.tags.length ? reference.tags.join(" / ") : sceneCopy.noValue} />
            <Meta label={sceneCopy.fields.isPrimary} value={reference.is_primary ? sceneCopy.primaryReference : sceneCopy.noValue} />
            <Meta label={sceneCopy.fields.isSpatialAnchor} value={reference.is_spatial_anchor ? sceneCopy.spatialAnchor : sceneCopy.noValue} />
            <Meta label={sceneCopy.fields.isEmptyPlate} value={reference.is_empty_plate ? sceneCopy.emptyPlate : sceneCopy.noValue} />
          </dl>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-1 break-words text-foreground">{value}</dd>
    </div>
  );
}

function displayCustom(label: string, customValue: string | null): string {
  return customValue ? `${label} / ${customValue}` : label;
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
