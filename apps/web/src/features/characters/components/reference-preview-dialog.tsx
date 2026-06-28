import { Eye } from "lucide-react";
import { type ReactNode } from "react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from "@/components/ui/dialog";
import { Badge } from "@/features/characters/components/status-badge";
import { characterCopy } from "@/features/characters/copy";
import type { CharacterReference } from "@/features/characters/types";

interface ReferencePreviewDialogProps {
  reference: CharacterReference;
  trigger: ReactNode;
}

export function ReferencePreviewDialog({ reference, trigger }: ReferencePreviewDialogProps) {
  const media = reference.media_asset;
  const expression =
    reference.expression === "custom" && reference.custom_expression
      ? reference.custom_expression
      : characterCopy.expression[reference.expression];
  const pose =
    reference.pose_type === "custom" && reference.custom_pose
      ? reference.custom_pose
      : characterCopy.poseType[reference.pose_type];

  return (
    <Dialog>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-[920px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Eye className="h-4 w-4" aria-hidden="true" />
            {characterCopy.previewOriginal}
          </DialogTitle>
          <DialogDescription>{media.original_filename}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
          <div className="overflow-hidden rounded-md border border-border bg-background">
            <img
              src={media.content_url}
              alt={media.original_filename}
              className="max-h-[64vh] w-full object-contain"
            />
          </div>
          <dl className="grid content-start gap-3 text-sm">
            <MetadataRow label={characterCopy.fields.originalFilename} value={media.original_filename} />
            <MetadataRow
              label={characterCopy.fields.imageSize}
              value={`${media.width} × ${media.height}`}
            />
            <MetadataRow label={characterCopy.fields.fileType} value={media.mime_type} />
            <MetadataRow label={characterCopy.fields.fileSize} value={formatFileSize(media.size_bytes)} />
            <MetadataRow label={characterCopy.fields.shotType} value={characterCopy.shotType[reference.shot_type]} />
            <MetadataRow label={characterCopy.fields.viewAngle} value={characterCopy.viewAngle[reference.view_angle]} />
            <MetadataRow label={characterCopy.fields.expression} value={expression} />
            <MetadataRow label={characterCopy.fields.poseType} value={pose} />
            <div className="grid gap-2">
              <dt className="text-xs text-muted">{characterCopy.fields.tags}</dt>
              <dd className="flex flex-wrap gap-2 text-foreground">
                {reference.tags.length > 0
                  ? reference.tags.map((tag) => <Badge key={tag}>{tag}</Badge>)
                  : characterCopy.noValue}
              </dd>
            </div>
            <MetadataRow
              label={characterCopy.fields.isPrimary}
              value={reference.is_primary ? characterCopy.yes : characterCopy.no}
            />
            <MetadataRow
              label={characterCopy.fields.isIdentityAnchor}
              value={reference.is_identity_anchor ? characterCopy.yes : characterCopy.no}
            />
          </dl>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function MetadataRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="break-words text-foreground">{value}</dd>
    </div>
  );
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / 1024 / 1024).toFixed(1)} MB`;
}
