import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Clapperboard,
  Download,
  FileText,
  Film,
  Image,
  Images,
  UserRound
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/features/characters/components/status-badge";
import { projectCanvasCopy } from "@/features/project-canvas/copy";
import type { CanvasNodeType, ProjectCanvasNode } from "@/features/project-canvas/types";
import { cn } from "@/lib/utils";

export interface CanvasFlowNodeData extends Record<string, unknown> {
  canvasNode: ProjectCanvasNode;
  subtitle?: string;
}

const iconByType: Record<CanvasNodeType, LucideIcon> = {
  text: FileText,
  character: UserRound,
  scene: Images,
  shot: Clapperboard,
  image: Image,
  video: Film,
  export: Download
};

const toneByType: Record<CanvasNodeType, string> = {
  text: "border-border bg-panel",
  character: "border-sky-500/30 bg-sky-500/10",
  scene: "border-emerald-500/30 bg-emerald-500/10",
  shot: "border-primary/40 bg-primarySoft/60",
  image: "border-cyan-500/30 bg-cyan-500/10",
  video: "border-violet-500/30 bg-violet-500/10",
  export: "border-amber-500/30 bg-amber-500/10"
};

export function CanvasNodeCard({ data, selected }: NodeProps) {
  const node = data.canvasNode as ProjectCanvasNode | undefined;

  if (!node) {
    return (
      <article className="min-w-[180px] rounded-md border border-danger/40 bg-danger/10 p-3 text-xs text-danger">
        节点数据异常
      </article>
    );
  }

  const Icon = iconByType[node.node_type];
  const collapsed = Boolean(node.data.collapsed);
  const thumbnailUrl = node.node_type === "image" ? node.data.thumbnail_override : null;

  return (
    <article
      className={cn(
        "min-w-[210px] rounded-md border p-3 shadow-workbench transition-colors",
        toneByType[node.node_type],
        selected && "ring-2 ring-primary"
      )}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-background/80 text-foreground">
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-foreground">{node.title}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <Badge>{projectCanvasCopy.nodeType[node.node_type]}</Badge>
            {node.entity_type && <Badge tone="primary">已关联</Badge>}
          </div>
        </div>
      </div>
      {!collapsed && (
        <>
          {thumbnailUrl && (
            <div className="mt-3 overflow-hidden rounded border border-border bg-background">
              <img src={thumbnailUrl} alt="" className="max-h-28 w-full object-contain" />
            </div>
          )}
          <div className="mt-3 text-xs leading-5 text-muted">
            {(data.subtitle as string | undefined) ??
              node.data.temporary_label ??
              node.data.note ??
              (node.entity_type ? "来自项目业务数据，只在画布中展示关系。" : "画布草稿节点。")}
          </div>
        </>
      )}
      <Handle
        type="target"
        position={Position.Left}
        className="pointer-events-none opacity-0"
        isConnectable={false}
      />
      <Handle
        type="source"
        position={Position.Right}
        className="pointer-events-none opacity-0"
        isConnectable={false}
      />
    </article>
  );
}

export const projectCanvasNodeTypes = {
  text: CanvasNodeCard,
  character: CanvasNodeCard,
  scene: CanvasNodeCard,
  shot: CanvasNodeCard,
  image: CanvasNodeCard,
  video: CanvasNodeCard,
  export: CanvasNodeCard
};
