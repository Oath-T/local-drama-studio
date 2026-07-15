import "@xyflow/react/dist/style.css";

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type OnConnect,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow
} from "@xyflow/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Boxes,
  Check,
  Clapperboard,
  Download,
  FileText,
  Film,
  GitBranch,
  Image,
  Images,
  LayoutDashboard,
  Move,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  Undo2,
  UserRound
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusMessage } from "@/components/ui/status-message";
import { fetchCharacters, characterKeys } from "@/features/characters/api";
import { Badge } from "@/features/characters/components/status-badge";
import type { Character } from "@/features/characters/types";
import { fetchGenerationTasks, generationTaskKeys } from "@/features/generation-tasks/api";
import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import {
  addCanvasEntityBatch,
  createCanvasEdge,
  createCanvasNode,
  deleteCanvasEdge,
  deleteCanvasNode,
  fetchCanvasEntityBatchPreview,
  fetchProjectCanvas,
  patchCanvasNode,
  projectCanvasKeys,
  saveProjectCanvas
} from "@/features/project-canvas/api";
import { canvasNodeTypes, projectCanvasCopy } from "@/features/project-canvas/copy";
import {
  type CanvasEdgeInput,
  type CanvasEdgeType,
  type CanvasNodeInput,
  type CanvasNodeType,
  type CanvasViewMode,
  type ProjectCanvas,
  type ProjectCanvasEdge,
  type ProjectCanvasNode
} from "@/features/project-canvas/types";
import { CanvasErrorBoundary } from "@/features/project-canvas/components/canvas-error-boundary";
import {
  projectCanvasNodeTypes,
  type CanvasFlowNodeData
} from "@/features/project-canvas/components/canvas-node-card";
import { fetchProject, projectKeys } from "@/features/projects/api";
import { fetchScenes, sceneKeys } from "@/features/scenes/api";
import type { Scene } from "@/features/scenes/types";
import { fetchShots, shotKeys } from "@/features/shots/api";
import type { Shot } from "@/features/shots/types";
import {
  fetchProjectProductionStatus,
  productionStatusKeys
} from "@/features/production-status/api";
import type { ShotProductionStatus } from "@/features/production-status/types";
import { ApiClientError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface ProjectCanvasWorkspaceProps {
  projectId: string;
}

type CanvasFlowNode = Node<CanvasFlowNodeData>;
type CanvasFlowEdge = Edge;

interface ContextMenuState {
  clientX: number;
  clientY: number;
  flowX: number;
  flowY: number;
}

interface NodeMenuState {
  clientX: number;
  clientY: number;
  nodeId: string;
}

const defaultNodeSize = {
  width: 240,
  height: 120
};

const semanticEdgeTypes: CanvasEdgeType[] = [
  "uses_character",
  "uses_scene",
  "identity_reference",
  "look_reference",
  "scene_reference",
  "pose_reference",
  "start_frame",
  "end_frame",
  "continuity_from",
  "generated_from",
  "included_in_export"
];

const entityNodeTypes = new Set<CanvasNodeType>([
  "character",
  "scene",
  "shot",
  "image",
  "video",
  "export"
]);

export function ProjectCanvasWorkspace({ projectId }: ProjectCanvasWorkspaceProps) {
  return (
    <ReactFlowProvider>
      <ProjectCanvasWorkspaceInner projectId={projectId} />
    </ReactFlowProvider>
  );
}

function ProjectCanvasWorkspaceInner({ projectId }: ProjectCanvasWorkspaceProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const reactFlow = useReactFlow<CanvasFlowNode, CanvasFlowEdge>();
  const [viewMode, setViewMode] = useState<CanvasViewMode>("workflow");
  const [canvas, setCanvas] = useState<ProjectCanvas | null>(null);
  const [nodes, setNodes] = useState<CanvasFlowNode[]>([]);
  const [edges, setEdges] = useState<CanvasFlowEdge[]>([]);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [nodeMenu, setNodeMenu] = useState<NodeMenuState | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedEdgeIds, setSelectedEdgeIds] = useState<string[]>([]);
  const [drawerCollapsed, setDrawerCollapsed] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error" | "neutral"; text: string } | null>(
    null
  );
  const [undoStack, setUndoStack] = useState<ProjectCanvas[]>([]);
  const [redoStack, setRedoStack] = useState<ProjectCanvas[]>([]);
  const nodeSaveTimer = useRef<number | null>(null);
  const viewportSaveTimer = useRef<number | null>(null);

  const projectQuery = useQuery({
    queryKey: projectKeys.detail(projectId),
    queryFn: () => fetchProject(projectId),
    enabled: projectId.length > 0
  });
  const canvasQuery = useQuery({
    queryKey: projectCanvasKeys.detail(projectId),
    queryFn: () => fetchProjectCanvas(projectId),
    enabled: projectId.length > 0
  });
  const charactersQuery = useQuery({
    queryKey: characterKeys.lists(projectId),
    queryFn: () => fetchCharacters(projectId),
    enabled: projectId.length > 0
  });
  const scenesQuery = useQuery({
    queryKey: sceneKeys.lists(projectId),
    queryFn: () => fetchScenes(projectId),
    enabled: projectId.length > 0
  });
  const shotsQuery = useQuery({
    queryKey: shotKeys.lists(projectId),
    queryFn: () => fetchShots(projectId),
    enabled: projectId.length > 0
  });
  const generationTasksQuery = useQuery({
    queryKey: generationTaskKeys.lists(projectId),
    queryFn: () => fetchGenerationTasks(projectId),
    enabled: projectId.length > 0
  });
  const productionQuery = useQuery({
    queryKey: productionStatusKeys.project(projectId),
    queryFn: () => fetchProjectProductionStatus(projectId),
    enabled: projectId.length > 0,
    refetchInterval: (query) =>
      query.state.data?.items?.some((shot) =>
        ["in_progress", "ready_for_video"].includes(shot.overall_status)
      )
        ? 5000
        : false
  });
  const batchPreviewQuery = useQuery({
    queryKey: projectCanvasKeys.batchPreview(projectId),
    queryFn: () => fetchCanvasEntityBatchPreview(projectId),
    enabled: projectId.length > 0
  });

  const acceptServerCanvas = useCallback(
    (nextCanvas: ProjectCanvas, options?: { preserveViewMode?: boolean }) => {
      setCanvas(nextCanvas);
      setViewMode(options?.preserveViewMode ? viewMode : nextCanvas.view_mode);
      setNodes(toFlowNodes(nextCanvas));
      setEdges(toFlowEdges(nextCanvas));
      queryClient.setQueryData(projectCanvasKeys.detail(projectId), nextCanvas);
    },
    [projectId, queryClient, viewMode]
  );

  useEffect(() => {
    if (canvasQuery.data) {
      acceptServerCanvas(canvasQuery.data);
    }
  }, [acceptServerCanvas, canvasQuery.data]);

  const runMutation = useMutation({
    mutationFn: (nextCanvas: ProjectCanvas) =>
      saveProjectCanvas(projectId, {
        expected_revision: canvas?.revision ?? nextCanvas.revision,
        view_mode: viewMode,
        viewport: viewportFromReactFlow(reactFlow),
        nodes: nextCanvas.nodes.map(toNodeInput),
        edges: nextCanvas.edges.map(toEdgeInput)
      }),
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setMessage({ tone: "success", text: "画布已恢复。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const saveViewMutation = useMutation({
    mutationFn: (nextViewMode: CanvasViewMode) =>
      saveProjectCanvas(projectId, {
        expected_revision: canvas?.revision ?? 0,
        view_mode: nextViewMode,
        viewport: viewportFromReactFlow(reactFlow),
        nodes: canvas?.nodes.map(toNodeInput) ?? [],
        edges: canvas?.edges.map(toEdgeInput) ?? []
      }),
    onSuccess: (nextCanvas) => acceptServerCanvas(nextCanvas),
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const saveViewportMutation = useMutation({
    mutationFn: () => {
      requireCanvas(canvas);
      return saveProjectCanvas(projectId, {
        expected_revision: canvas.revision,
        view_mode: viewMode,
        viewport: viewportFromReactFlow(reactFlow),
        nodes: canvas.nodes.map(toNodeInput),
        edges: canvas.edges.map(toEdgeInput)
      });
    },
    onSuccess: (nextCanvas) => acceptServerCanvas(nextCanvas, { preserveViewMode: true }),
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const createNodeMutation = useMutation({
    mutationFn: (input: {
      nodeType: CanvasNodeType;
      title?: string;
      x: number;
      y: number;
      entityType?: string | null;
      entityId?: string | null;
    }) => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return createCanvasNode(projectId, {
        expected_revision: canvas.revision,
        node_type: input.nodeType,
        title: input.title ?? projectCanvasCopy.nodeType[input.nodeType],
        position_x: input.x,
        position_y: input.y,
        width: defaultNodeSize.width,
        height: defaultNodeSize.height,
        entity_type: input.entityType ?? null,
        entity_id: input.entityId ?? null,
        data: {}
      });
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setMessage({ tone: "success", text: "节点已添加。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const patchNodeMutation = useMutation({
    mutationFn: (input: {
      nodeId: string;
      position?: { x: number; y: number };
      title?: string;
      data?: ProjectCanvasNode["data"];
    }) => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return patchCanvasNode(projectId, input.nodeId, {
        expected_revision: canvas.revision,
        ...(input.position
          ? {
              position_x: input.position.x,
              position_y: input.position.y
            }
          : {}),
        ...(input.title !== undefined ? { title: input.title } : {}),
        ...(input.data !== undefined ? { data: input.data } : {})
      });
    },
    onSuccess: (nextCanvas) => acceptServerCanvas(nextCanvas, { preserveViewMode: true }),
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const deleteNodeMutation = useMutation({
    mutationFn: (nodeId: string) => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return deleteCanvasNode(projectId, nodeId, canvas.revision);
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setSelectedNodeIds([]);
      setMessage({ tone: "success", text: "节点已删除。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const createEdgeMutation = useMutation({
    mutationFn: (input: { source: string; target: string; semanticType: CanvasEdgeType }) => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return createCanvasEdge(projectId, {
        expected_revision: canvas.revision,
        source_node_id: input.source,
        target_node_id: input.target,
        source_handle: null,
        target_handle: null,
        semantic_type: input.semanticType,
        data: {}
      });
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setMessage({ tone: "success", text: "语义连线已保存。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const deleteEdgeMutation = useMutation({
    mutationFn: (edgeId: string) => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return deleteCanvasEdge(projectId, edgeId, canvas.revision);
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setSelectedEdgeIds([]);
      setMessage({ tone: "success", text: "连线已删除。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const batchMutation = useMutation({
    mutationFn: () => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return addCanvasEntityBatch(projectId, {
        expected_revision: canvas.revision,
        include_characters: true,
        include_scenes: true,
        include_shots: true
      });
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setMessage({ tone: "success", text: "已将现有角色、场景和镜头加入画布。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const autoLayoutMutation = useMutation({
    mutationFn: () => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      const nextNodes = autoLayoutNodes(canvas.nodes);
      return saveProjectCanvas(projectId, {
        expected_revision: canvas.revision,
        view_mode: viewMode,
        viewport: viewportFromReactFlow(reactFlow),
        nodes: nextNodes.map(toNodeInput),
        edges: canvas.edges.map(toEdgeInput)
      });
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      window.setTimeout(() => reactFlow.fitView({ padding: 0.16 }), 0);
      setMessage({ tone: "success", text: "画布已自动整理。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const selectedCanvasNode = useMemo(
    () => canvas?.nodes.find((node) => node.id === selectedNodeIds[0]) ?? null,
    [canvas?.nodes, selectedNodeIds]
  );
  const selectedCanvasEdge = useMemo(
    () => canvas?.edges.find((edge) => edge.id === selectedEdgeIds[0]) ?? null,
    [canvas?.edges, selectedEdgeIds]
  );

  const onNodesChange = useCallback((changes: NodeChange<CanvasFlowNode>[]) => {
    setNodes((current) => applyNodeChanges(changes, current));
  }, []);

  const onEdgesChange = useCallback((changes: EdgeChange<CanvasFlowEdge>[]) => {
    setEdges((current) => applyEdgeChanges(changes, current));
  }, []);

  const onNodeDragStop = useCallback(
    (_event: MouseEvent | TouchEvent, node: CanvasFlowNode) => {
      if (nodeSaveTimer.current) {
        window.clearTimeout(nodeSaveTimer.current);
      }
      nodeSaveTimer.current = window.setTimeout(() => {
        patchNodeMutation.mutate({
          nodeId: node.id,
          position: node.position
        });
      }, 650);
    },
    [patchNodeMutation]
  );

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (!connection.source || !connection.target) return;
      createEdgeMutation.mutate({
        source: connection.source,
        target: connection.target,
        semanticType: suggestedEdgeType(connection.source, connection.target, canvas?.nodes ?? [])
      });
    },
    [canvas?.nodes, createEdgeMutation]
  );

  function changeViewMode(nextViewMode: CanvasViewMode) {
    setViewMode(nextViewMode);
    if (canvas && nextViewMode !== canvas.view_mode) {
      saveViewMutation.mutate(nextViewMode);
    }
  }

  function addNodeAt(nodeType: CanvasNodeType, position?: { x: number; y: number }) {
    const fallback = reactFlow.screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2
    });
    createNodeMutation.mutate({
      nodeType,
      x: position?.x ?? fallback.x,
      y: position?.y ?? fallback.y
    });
    setContextMenu(null);
  }

  function duplicateNode(node: ProjectCanvasNode) {
    createNodeMutation.mutate({
      nodeType: node.node_type,
      title: `${node.title} 副本`,
      x: node.position_x + 40,
      y: node.position_y + 40,
      entityType: node.entity_type,
      entityId: node.entity_id
    });
    setNodeMenu(null);
  }

  function bringNodeToFront(node: ProjectCanvasNode) {
    if (!canvas) return;
    remember(canvas, setUndoStack, setRedoStack);
    const maxZIndex = Math.max(0, ...canvas.nodes.map((item) => item.z_index));
    void saveProjectCanvas(projectId, {
      expected_revision: canvas.revision,
      view_mode: viewMode,
      viewport: viewportFromReactFlow(reactFlow),
      nodes: canvas.nodes
        .map((item) => (item.id === node.id ? { ...item, z_index: maxZIndex + 1 } : item))
        .map(toNodeInput),
      edges: canvas.edges.map(toEdgeInput)
    })
      .then((nextCanvas) => {
        acceptServerCanvas(nextCanvas, { preserveViewMode: true });
        setMessage({ tone: "success", text: "节点已置于顶层。" });
      })
      .catch((error: unknown) => setMessage({ tone: "error", text: canvasErrorText(error) }));
    setNodeMenu(null);
  }

  function addEntityNode(entity: EntityAssetItem) {
    const center = reactFlow.screenToFlowPosition({
      x: window.innerWidth / 2,
      y: window.innerHeight / 2
    });
    createNodeMutation.mutate({
      nodeType: entity.nodeType,
      title: entity.title,
      x: center.x,
      y: center.y,
      entityType: entity.entityType,
      entityId: entity.id
    });
  }

  function undo() {
    if (!canvas || undoStack.length === 0) return;
    const previous = undoStack[undoStack.length - 1];
    setUndoStack((stack) => stack.slice(0, -1));
    setRedoStack((stack) => [canvas, ...stack]);
    runMutation.mutate(previous);
  }

  function redo() {
    if (!canvas || redoStack.length === 0) return;
    const next = redoStack[0];
    setRedoStack((stack) => stack.slice(1));
    setUndoStack((stack) => [...stack, canvas]);
    runMutation.mutate(next);
  }

  function connectSelected() {
    if (selectedNodeIds.length < 2) return;
    createEdgeMutation.mutate({
      source: selectedNodeIds[0],
      target: selectedNodeIds[1],
      semanticType: suggestedEdgeType(selectedNodeIds[0], selectedNodeIds[1], canvas?.nodes ?? [])
    });
  }

  function deleteSelected() {
    if (selectedNodeIds[0]) {
      if (!window.confirm("确定删除选中的画布节点吗？相关画布连线也会删除。")) return;
      deleteNodeMutation.mutate(selectedNodeIds[0]);
      return;
    }
    if (selectedEdgeIds[0]) {
      if (!window.confirm("确定删除选中的画布连线吗？")) return;
      deleteEdgeMutation.mutate(selectedEdgeIds[0]);
    }
  }

  function importExistingEntities() {
    const preview = batchPreviewQuery.data;
    const confirmed = window.confirm(
      `将添加 ${preview?.character_count ?? 0} 个角色、${preview?.scene_count ?? 0} 个场景、${preview?.shot_count ?? 0} 个镜头到画布。是否继续？`
    );
    if (confirmed) {
      batchMutation.mutate();
    }
  }

  if (projectQuery.isLoading || canvasQuery.isLoading) {
    return <Skeleton className="h-[760px]" />;
  }

  if (projectQuery.isError || canvasQuery.isError || !canvas) {
    return (
      <section className="rounded-md border border-border bg-panel p-6">
        <StatusMessage tone="error">创作画布加载失败。</StatusMessage>
        <Button
          type="button"
          variant="secondary"
          className="mt-4"
          onClick={() => {
            void projectQuery.refetch();
            void canvasQuery.refetch();
          }}
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          重试
        </Button>
      </section>
    );
  }

  const assetItems = buildAssetItems({
    characters: charactersQuery.data?.items ?? [],
    scenes: scenesQuery.data?.items ?? [],
    shots: shotsQuery.data?.items ?? [],
    tasks: generationTasksQuery.data?.items ?? []
  });
  const productionByShotId = new Map(
    (productionQuery.data?.items ?? []).map((item) => [item.shot_id, item])
  );

  return (
    <div className="flex h-[calc(100vh-112px)] min-h-[720px] flex-col overflow-hidden">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border bg-background pb-3">
        <div className="flex min-w-0 items-center gap-3">
          <Button asChild variant="ghost">
            <Link to={`/projects/${projectId}`}>
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              返回项目
            </Link>
          </Button>
          <div className="min-w-0">
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">
              Project Canvas & Storyboard
            </div>
            <h1 className="truncate text-xl font-semibold text-foreground">
              {projectQuery.data?.name ?? projectCanvasCopy.title}
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <SegmentedSwitch value={viewMode} onChange={changeViewMode} />
          <Badge tone="primary">{`revision ${canvas.revision}`}</Badge>
        </div>
      </header>

      {message && (
        <div className="mt-3 shrink-0">
          <StatusMessage tone={message.tone}>{message.text}</StatusMessage>
        </div>
      )}

      <div className="mt-3 grid min-h-0 flex-1 grid-cols-[auto_minmax(0,1fr)_360px] gap-3">
        <CanvasErrorBoundary title="资产抽屉加载失败">
          <AssetDrawer
            collapsed={drawerCollapsed}
            onToggle={() => setDrawerCollapsed((value) => !value)}
            loading={charactersQuery.isLoading || scenesQuery.isLoading || shotsQuery.isLoading}
            items={assetItems}
            onAdd={addEntityNode}
          />
        </CanvasErrorBoundary>

        <section className="relative min-w-0 overflow-hidden rounded-md border border-border bg-[#111418]">
          {viewMode === "workflow" ? (
            <CanvasErrorBoundary title="工作流画布加载失败">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={projectCanvasNodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeDragStop={onNodeDragStop}
                onConnect={onConnect}
                fitView
                minZoom={0.2}
                maxZoom={1.8}
                deleteKeyCode={null}
                onPaneContextMenu={(event) => {
                  event.preventDefault();
                  const position = reactFlow.screenToFlowPosition({
                    x: event.clientX,
                    y: event.clientY
                  });
                  setNodeMenu(null);
                  setContextMenu({
                    clientX: event.clientX,
                    clientY: event.clientY,
                    flowX: position.x,
                    flowY: position.y
                  });
                }}
                onPaneClick={() => {
                  setContextMenu(null);
                  setNodeMenu(null);
                  setSelectedNodeIds([]);
                  setSelectedEdgeIds([]);
                }}
                onMoveEnd={() => {
                  if (viewportSaveTimer.current) {
                    window.clearTimeout(viewportSaveTimer.current);
                  }
                  viewportSaveTimer.current = window.setTimeout(() => {
                    if (canvas) {
                      saveViewportMutation.mutate();
                    }
                  }, 650);
                }}
                onNodeContextMenu={(event, node) => {
                  event.preventDefault();
                  setContextMenu(null);
                  setNodeMenu({ clientX: event.clientX, clientY: event.clientY, nodeId: node.id });
                  setSelectedNodeIds([node.id]);
                  setSelectedEdgeIds([]);
                }}
                onSelectionChange={({ nodes: selectedNodes, edges: selectedEdges }) => {
                  setSelectedNodeIds(selectedNodes.map((node) => node.id));
                  setSelectedEdgeIds(selectedEdges.map((edge) => edge.id));
                }}
              >
                <Background color="#2d3540" gap={24} />
                <MiniMap
                  pannable
                  zoomable
                  className="!bg-panel !border !border-border"
                  nodeColor="#6f93c2"
                />
                <Controls className="!border-border !bg-panel !text-foreground" />
                {nodes.length === 0 && (
                  <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center p-8">
                    <EmptyState
                      title={projectCanvasCopy.emptyTitle}
                      description={projectCanvasCopy.emptyDescription}
                      action={
                        <div className="pointer-events-auto flex flex-wrap justify-center gap-2">
                          <Button type="button" onClick={() => addNodeAt("shot")}>
                            <Plus className="h-4 w-4" aria-hidden="true" />
                            添加镜头节点
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={importExistingEntities}
                            disabled={batchMutation.isPending}
                          >
                            <Boxes className="h-4 w-4" aria-hidden="true" />
                            {projectCanvasCopy.addExisting}
                          </Button>
                        </div>
                      }
                    />
                  </div>
                )}
              </ReactFlow>
              {contextMenu && (
                <CanvasContextMenu
                  state={contextMenu}
                  onClose={() => setContextMenu(null)}
                  onAdd={(nodeType) =>
                    addNodeAt(nodeType, { x: contextMenu.flowX, y: contextMenu.flowY })
                  }
                />
              )}
              {nodeMenu && (
                <NodeContextMenu
                  state={nodeMenu}
                  node={canvas.nodes.find((item) => item.id === nodeMenu.nodeId) ?? null}
                  projectId={projectId}
                  onClose={() => setNodeMenu(null)}
                  onDuplicate={duplicateNode}
                  onBringToFront={bringNodeToFront}
                  onDelete={(node) => {
                    if (window.confirm(`确定删除节点“${node.title}”吗？相关画布连线也会删除。`)) {
                      deleteNodeMutation.mutate(node.id);
                    }
                    setNodeMenu(null);
                  }}
                  onToggleCollapse={(node) => {
                    patchNodeMutation.mutate({
                      nodeId: node.id,
                      data: { ...node.data, collapsed: !node.data.collapsed }
                    });
                    setNodeMenu(null);
                  }}
                />
              )}
              <CanvasToolbar
                undoDisabled={undoStack.length === 0 || runMutation.isPending}
                redoDisabled={redoStack.length === 0 || runMutation.isPending}
                connectDisabled={selectedNodeIds.length < 2}
                deleteDisabled={selectedNodeIds.length === 0 && selectedEdgeIds.length === 0}
                batchLabel={
                  batchPreviewQuery.data
                    ? `导入现有内容 (${batchPreviewQuery.data.total})`
                    : projectCanvasCopy.addExisting
                }
                batchDisabled={batchMutation.isPending}
                onAdd={() => addNodeAt("text")}
                onUndo={undo}
                onRedo={redo}
                onConnect={connectSelected}
                onDelete={deleteSelected}
                onBatch={importExistingEntities}
                onAutoLayout={() => autoLayoutMutation.mutate()}
                onFitView={() => reactFlow.fitView({ padding: 0.16 })}
              />
            </CanvasErrorBoundary>
          ) : (
            <CanvasErrorBoundary title="故事板加载失败">
              <StoryboardView
                projectId={projectId}
                shots={shotsQuery.data?.items ?? []}
                loading={shotsQuery.isLoading}
                productionByShotId={productionByShotId}
                onOpenShot={(shotId) => navigate(`/projects/${projectId}/shots/${shotId}`)}
              />
            </CanvasErrorBoundary>
          )}
        </section>

        <CanvasErrorBoundary title="Inspector 加载失败">
          <NodeInspector
            projectId={projectId}
            node={selectedCanvasNode}
            edge={selectedCanvasEdge}
            assetItems={assetItems}
            onOpenShot={(shotId) => navigate(`/projects/${projectId}/shots/${shotId}`)}
            onToggleCollapse={(node) =>
              patchNodeMutation.mutate({
                nodeId: node.id,
                data: { ...node.data, collapsed: !node.data.collapsed }
              })
            }
          />
        </CanvasErrorBoundary>
      </div>
    </div>
  );
}

function SegmentedSwitch({
  value,
  onChange
}: {
  value: CanvasViewMode;
  onChange: (value: CanvasViewMode) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-1 rounded-md border border-border bg-panel p-1">
      {(["workflow", "storyboard"] as const).map((item) => (
        <button
          key={item}
          type="button"
          className={cn(
            "rounded px-3 py-1.5 text-sm transition-colors",
            value === item ? "bg-primarySoft text-foreground" : "text-muted hover:text-foreground"
          )}
          onClick={() => onChange(item)}
        >
          {item === "workflow" ? projectCanvasCopy.workflow : projectCanvasCopy.storyboard}
        </button>
      ))}
    </div>
  );
}

interface EntityAssetItem {
  id: string;
  title: string;
  subtitle: string;
  nodeType: CanvasNodeType;
  entityType: string;
}

function AssetDrawer({
  collapsed,
  loading,
  items,
  onToggle,
  onAdd
}: {
  collapsed: boolean;
  loading: boolean;
  items: EntityAssetItem[];
  onToggle: () => void;
  onAdd: (item: EntityAssetItem) => void;
}) {
  const [keyword, setKeyword] = useState("");
  const filtered = items.filter((item) =>
    `${item.title} ${item.subtitle}`.toLowerCase().includes(keyword.trim().toLowerCase())
  );

  return (
    <aside
      className={cn(
        "min-h-0 overflow-hidden rounded-md border border-border bg-panel transition-[width]",
        collapsed ? "w-[56px]" : "w-[280px]"
      )}
    >
      <div className="flex items-center justify-between border-b border-border p-3">
        <div className={cn("min-w-0", collapsed && "sr-only")}>
          <div className="text-sm font-semibold text-foreground">资产抽屉</div>
          <div className="text-xs text-muted">拖入计划将在 Sprint 25 接入，本轮可点击添加。</div>
        </div>
        <Button type="button" variant="ghost" size="icon" onClick={onToggle}>
          <Boxes className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
      {!collapsed && (
        <div className="grid min-h-0 gap-3 p-3">
          <input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="搜索角色、场景、镜头"
            className="h-9 rounded-md border border-border bg-background px-3 text-sm outline-none focus:border-primary"
          />
          {loading && <Skeleton className="h-36" />}
          {!loading && filtered.length === 0 && (
            <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted">
              暂无可添加资产。
            </div>
          )}
          <div className="grid max-h-[calc(100vh-270px)] gap-2 overflow-y-auto pr-1">
            {filtered.map((item) => (
              <button
                key={`${item.entityType}-${item.id}`}
                type="button"
                className="rounded-md border border-border bg-background p-3 text-left transition-colors hover:border-primary"
                onClick={() => onAdd(item)}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-foreground">{item.title}</span>
                  <Badge>{projectCanvasCopy.nodeType[item.nodeType]}</Badge>
                </div>
                <div className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{item.subtitle}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}

function CanvasContextMenu({
  state,
  onAdd,
  onClose
}: {
  state: ContextMenuState;
  onAdd: (nodeType: CanvasNodeType) => void;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed z-50 w-56 rounded-md border border-border bg-panel p-2 shadow-workbench"
      style={{ left: state.clientX, top: state.clientY }}
      role="menu"
    >
      <div className="px-2 py-1 text-xs text-muted">添加节点</div>
      {canvasNodeTypes.map((nodeType) => (
        <button
          key={nodeType}
          type="button"
          className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-sm text-foreground hover:bg-panelRaised"
          onClick={() => onAdd(nodeType)}
        >
          <Plus className="h-4 w-4 text-primary" aria-hidden="true" />
          {projectCanvasCopy.nodeType[nodeType]}
        </button>
      ))}
      <button
        type="button"
        className="mt-1 w-full rounded px-2 py-2 text-left text-sm text-muted hover:bg-panelRaised"
        onClick={onClose}
      >
        取消
      </button>
    </div>
  );
}

function NodeContextMenu({
  state,
  node,
  projectId,
  onClose,
  onDuplicate,
  onBringToFront,
  onDelete,
  onToggleCollapse
}: {
  state: NodeMenuState;
  node: ProjectCanvasNode | null;
  projectId: string;
  onClose: () => void;
  onDuplicate: (node: ProjectCanvasNode) => void;
  onBringToFront: (node: ProjectCanvasNode) => void;
  onDelete: (node: ProjectCanvasNode) => void;
  onToggleCollapse: (node: ProjectCanvasNode) => void;
}) {
  if (!node) {
    return null;
  }

  return (
    <div
      className="fixed z-50 w-56 rounded-md border border-border bg-panel p-2 shadow-workbench"
      style={{ left: state.clientX, top: state.clientY }}
      role="menu"
    >
      <div className="truncate px-2 py-1 text-xs text-muted">{node.title}</div>
      {node.node_type === "shot" && node.entity_id && (
        <Link
          to={`/projects/${projectId}/shots/${node.entity_id}`}
          className="block rounded px-2 py-2 text-sm text-foreground hover:bg-panelRaised"
          onClick={onClose}
        >
          打开详情
        </Link>
      )}
      {node.node_type === "character" && node.entity_id && (
        <Link
          to={`/projects/${projectId}/characters/${node.entity_id}`}
          className="block rounded px-2 py-2 text-sm text-foreground hover:bg-panelRaised"
          onClick={onClose}
        >
          打开详情
        </Link>
      )}
      {node.node_type === "scene" && node.entity_id && (
        <Link
          to={`/projects/${projectId}/scenes/${node.entity_id}`}
          className="block rounded px-2 py-2 text-sm text-foreground hover:bg-panelRaised"
          onClick={onClose}
        >
          打开详情
        </Link>
      )}
      <button
        type="button"
        className="block w-full rounded px-2 py-2 text-left text-sm text-foreground hover:bg-panelRaised"
        onClick={() => onDuplicate(node)}
      >
        复制节点
      </button>
      <button
        type="button"
        className="block w-full rounded px-2 py-2 text-left text-sm text-foreground hover:bg-panelRaised"
        onClick={() => onBringToFront(node)}
      >
        置于顶层
      </button>
      <button
        type="button"
        className="block w-full rounded px-2 py-2 text-left text-sm text-foreground hover:bg-panelRaised"
        onClick={() => onToggleCollapse(node)}
      >
        收起 / 展开
      </button>
      <button
        type="button"
        className="block w-full rounded px-2 py-2 text-left text-sm text-danger hover:bg-danger/10"
        onClick={() => onDelete(node)}
      >
        删除节点
      </button>
    </div>
  );
}

function CanvasToolbar({
  undoDisabled,
  redoDisabled,
  connectDisabled,
  deleteDisabled,
  batchLabel,
  batchDisabled,
  onAdd,
  onUndo,
  onRedo,
  onConnect,
  onDelete,
  onBatch,
  onAutoLayout,
  onFitView
}: {
  undoDisabled: boolean;
  redoDisabled: boolean;
  connectDisabled: boolean;
  deleteDisabled: boolean;
  batchLabel: string;
  batchDisabled: boolean;
  onAdd: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onConnect: () => void;
  onDelete: () => void;
  onBatch: () => void;
  onAutoLayout: () => void;
  onFitView: () => void;
}) {
  return (
    <div className="absolute bottom-4 left-1/2 z-20 flex -translate-x-1/2 items-center gap-1 rounded-md border border-border bg-panel/95 p-1 shadow-workbench backdrop-blur">
      <Button type="button" size="sm" onClick={onAdd}>
        <Plus className="h-4 w-4" aria-hidden="true" />
        添加
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onUndo} disabled={undoDisabled}>
        <Undo2 className="h-4 w-4" aria-hidden="true" />
        撤销
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onRedo} disabled={redoDisabled}>
        <Undo2 className="h-4 w-4 rotate-180" aria-hidden="true" />
        重做
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onConnect} disabled={connectDisabled}>
        <GitBranch className="h-4 w-4" aria-hidden="true" />
        连接所选
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onAutoLayout}>
        <Move className="h-4 w-4" aria-hidden="true" />
        {projectCanvasCopy.autoLayout}
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onFitView}>
        <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
        适配
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onBatch} disabled={batchDisabled}>
        <Boxes className="h-4 w-4" aria-hidden="true" />
        {batchLabel}
      </Button>
      <Button type="button" size="sm" variant="danger" onClick={onDelete} disabled={deleteDisabled}>
        <Trash2 className="h-4 w-4" aria-hidden="true" />
        删除所选
      </Button>
    </div>
  );
}

function StoryboardView({
  projectId,
  shots,
  loading,
  productionByShotId,
  onOpenShot
}: {
  projectId: string;
  shots: Shot[];
  loading: boolean;
  productionByShotId: Map<string, ShotProductionStatus>;
  onOpenShot: (shotId: string) => void;
}) {
  const orderedShots = [...shots].sort((left, right) => left.order_index - right.order_index);

  if (loading) {
    return <Skeleton className="h-full" />;
  }

  if (orderedShots.length === 0) {
    return (
      <div className="p-6">
        <EmptyState
          title="暂无镜头"
          description="创建镜头后，故事板会按镜头顺序展示画面、人物、场景和生产状态。"
          action={
            <Button asChild>
              <Link to={`/projects/${projectId}/shots`}>
                <Clapperboard className="h-4 w-4" aria-hidden="true" />
                创建镜头
              </Link>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="grid gap-3 xl:grid-cols-2 2xl:grid-cols-3">
        {orderedShots.map((shot) => {
          const production = productionByShotId.get(shot.id);
          const videoUrl = production?.steps.video?.content_url;
          const imageUrl =
            videoUrl ??
            production?.steps.first_frame?.content_url ??
            production?.steps.end_frame?.content_url;
          return (
            <article
              key={shot.id}
              className="rounded-md border border-border bg-panel p-3 transition-colors hover:border-primary"
            >
              <button
                type="button"
                className="block w-full text-left"
                onClick={() => onOpenShot(shot.id)}
              >
                <div className="aspect-video overflow-hidden rounded-md border border-border bg-background">
                  {imageUrl ? (
                    videoUrl ? (
                      <video src={videoUrl} className="h-full w-full object-cover" muted />
                    ) : (
                      <img src={imageUrl} alt="" className="h-full w-full object-cover" />
                    )
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-muted">
                      暂无画面
                    </div>
                  )}
                </div>
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-xs text-muted">#{shot.order_index}</span>
                  <Badge tone={production?.overall_status === "completed" ? "success" : "primary"}>
                    {productionStatusLabel(production?.overall_status)}
                  </Badge>
                </div>
                <h2 className="mt-2 truncate text-sm font-semibold text-foreground">{shot.name}</h2>
                <p className="mt-1 text-xs text-muted">
                  {shot.duration_seconds ? `${shot.duration_seconds}s` : "未设置时长"} /{" "}
                  {shot.character_count} 人物 / {shot.scene?.name ?? "未选场景"}
                </p>
              </button>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function NodeInspector({
  projectId,
  node,
  edge,
  assetItems,
  onOpenShot,
  onToggleCollapse
}: {
  projectId: string;
  node: ProjectCanvasNode | null;
  edge: ProjectCanvasEdge | null;
  assetItems: EntityAssetItem[];
  onOpenShot: (shotId: string) => void;
  onToggleCollapse: (node: ProjectCanvasNode) => void;
}) {
  const linkedAsset = node?.entity_id
    ? assetItems.find((item) => item.id === node.entity_id && item.entityType === node.entity_type)
    : null;

  return (
    <aside className="min-h-0 overflow-y-auto rounded-md border border-border bg-panel">
      <div className="border-b border-border p-4">
        <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Inspector / 助手</div>
        <h2 className="mt-2 text-base font-semibold text-foreground">
          {node ? node.title : edge ? projectCanvasCopy.edgeType[edge.semantic_type] : projectCanvasCopy.assistantTitle}
        </h2>
      </div>
      <div className="grid gap-4 p-4">
        {!node && !edge && (
          <>
            <StatusMessage tone="neutral">{projectCanvasCopy.assistantSoon}</StatusMessage>
            <InspectorPanel title="下一步建议">
              <ul className="grid gap-2 text-sm text-muted">
                <li>1. 从左侧资产抽屉添加角色、场景和镜头。</li>
                <li>2. 在工作流视图中连接资产与镜头。</li>
                <li>3. 在故事板视图中检查镜头顺序和生产状态。</li>
              </ul>
            </InspectorPanel>
          </>
        )}
        {edge && !node && (
          <InspectorPanel title="语义连线">
            <div className="grid gap-2 text-sm text-muted">
              <InfoRow label="类型" value={projectCanvasCopy.edgeType[edge.semantic_type]} />
              <InfoRow label="来源节点" value={edge.source_node_id} />
              <InfoRow label="目标节点" value={edge.target_node_id} />
              <p>本轮连线只保存画布语义，不会修改镜头或生成任务。</p>
            </div>
          </InspectorPanel>
        )}
        {node && (
          <>
            <InspectorPanel title="节点信息">
              <div className="grid gap-2 text-sm">
                <InfoRow label="类型" value={projectCanvasCopy.nodeType[node.node_type]} />
                <InfoRow label="标题" value={node.title} />
                <InfoRow label="业务关联" value={node.entity_type ? "已关联" : "画布草稿"} />
                {linkedAsset && <InfoRow label="来源" value={linkedAsset.subtitle} />}
              </div>
            </InspectorPanel>
            <InspectorPanel title="可执行操作">
              <div className="grid gap-2">
                {node.node_type === "shot" && node.entity_id && (
                  <Button type="button" onClick={() => onOpenShot(node.entity_id ?? "")}>
                    <Clapperboard className="h-4 w-4" aria-hidden="true" />
                    {projectCanvasCopy.openShotWorkspace}
                  </Button>
                )}
                {node.node_type === "character" && node.entity_id && (
                  <Button asChild variant="secondary">
                    <Link to={`/projects/${projectId}/characters/${node.entity_id}`}>
                      <UserRound className="h-4 w-4" aria-hidden="true" />
                      打开角色详情
                    </Link>
                  </Button>
                )}
                {node.node_type === "scene" && node.entity_id && (
                  <Button asChild variant="secondary">
                    <Link to={`/projects/${projectId}/scenes/${node.entity_id}`}>
                      <Images className="h-4 w-4" aria-hidden="true" />
                      打开场景详情
                    </Link>
                  </Button>
                )}
                <Button type="button" variant="secondary" onClick={() => onToggleCollapse(node)}>
                  <Check className="h-4 w-4" aria-hidden="true" />
                  {projectCanvasCopy.collapse}
                </Button>
              </div>
            </InspectorPanel>
            <InspectorPanel title="说明">
              <p className="text-sm leading-6 text-muted">
                {node.node_type === "shot"
                  ? "镜头节点可进入 Sprint 23 快速创作工作台进行详细编辑。"
                  : node.node_type === "video"
                    ? "视频节点用于展示输出与连续性规划，本轮不触发生成。"
                    : node.node_type === "export"
                      ? "导出节点用于表达最终时间线归档，本轮不创建导出任务。"
                      : "节点用于项目级创作规划和关系可视化。"}
              </p>
            </InspectorPanel>
          </>
        )}
      </div>
    </aside>
  );
}

function InspectorPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-border bg-background p-3">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex justify-between gap-3 border-b border-border/60 pb-2 last:border-b-0 last:pb-0">
      <span className="text-muted">{label}</span>
      <span className="min-w-0 truncate text-right text-foreground">{value ?? "未设置"}</span>
    </div>
  );
}

function toFlowNodes(canvas: ProjectCanvas): CanvasFlowNode[] {
  return canvas.nodes.map((node) => ({
    id: node.id,
    type: node.node_type,
    position: { x: node.position_x, y: node.position_y },
    width: node.width,
    height: node.height,
    zIndex: node.z_index,
    data: {
      canvasNode: node
    }
  }));
}

function toFlowEdges(canvas: ProjectCanvas): CanvasFlowEdge[] {
  return canvas.edges.map((edge) => ({
    id: edge.id,
    source: edge.source_node_id,
    target: edge.target_node_id,
    label: projectCanvasCopy.edgeType[edge.semantic_type],
    animated: edge.semantic_type === "generated_from" || edge.semantic_type === "continuity_from",
    data: edge.data as Record<string, unknown>,
    style: { stroke: "#6f93c2" },
    labelBgStyle: { fill: "#151a20", fillOpacity: 0.92 },
    labelStyle: { fill: "#d7dee8", fontSize: 11 }
  }));
}

function toNodeInput(node: ProjectCanvasNode): CanvasNodeInput {
  return {
    id: node.id,
    node_type: node.node_type,
    title: node.title,
    position_x: node.position_x,
    position_y: node.position_y,
    width: node.width,
    height: node.height,
    z_index: node.z_index,
    entity_type: node.entity_type,
    entity_id: node.entity_id,
    data: node.data
  };
}

function toEdgeInput(edge: ProjectCanvasEdge): CanvasEdgeInput {
  return {
    id: edge.id,
    source_node_id: edge.source_node_id,
    target_node_id: edge.target_node_id,
    source_handle: edge.source_handle,
    target_handle: edge.target_handle,
    semantic_type: edge.semantic_type,
    data: edge.data
  };
}

function viewportFromReactFlow(
  reactFlow: ReturnType<typeof useReactFlow<CanvasFlowNode, CanvasFlowEdge>>
) {
  const viewport = reactFlow.getViewport();
  return { x: viewport.x, y: viewport.y, zoom: viewport.zoom };
}

function requireCanvas(canvas: ProjectCanvas | null): asserts canvas is ProjectCanvas {
  if (!canvas) {
    throw new Error("Canvas is not loaded.");
  }
}

function remember(
  canvas: ProjectCanvas,
  setUndoStack: React.Dispatch<React.SetStateAction<ProjectCanvas[]>>,
  setRedoStack: React.Dispatch<React.SetStateAction<ProjectCanvas[]>>
) {
  setUndoStack((stack) => [...stack.slice(-19), canvas]);
  setRedoStack([]);
}

function autoLayoutNodes(nodes: ProjectCanvasNode[]): ProjectCanvasNode[] {
  const order: CanvasNodeType[] = ["text", "character", "scene", "shot", "image", "video", "export"];
  const grouped = new Map<CanvasNodeType, ProjectCanvasNode[]>();
  for (const node of nodes) {
    grouped.set(node.node_type, [...(grouped.get(node.node_type) ?? []), node]);
  }

  return order.flatMap((nodeType, columnIndex) =>
    [...(grouped.get(nodeType) ?? [])]
      .sort((left, right) => left.created_at.localeCompare(right.created_at) || left.id.localeCompare(right.id))
      .map((node, rowIndex) => ({
        ...node,
        position_x: 80 + columnIndex * 320,
        position_y: 80 + rowIndex * 180,
        z_index: columnIndex + rowIndex
      }))
  );
}

function suggestedEdgeType(
  sourceId: string,
  targetId: string,
  nodes: ProjectCanvasNode[]
): CanvasEdgeType {
  const source = nodes.find((node) => node.id === sourceId);
  const target = nodes.find((node) => node.id === targetId);
  if (source?.node_type === "character" && target?.node_type === "shot") return "uses_character";
  if (source?.node_type === "scene" && target?.node_type === "shot") return "uses_scene";
  if (source?.node_type === "image" && target?.node_type === "shot") return "scene_reference";
  if (source?.node_type === "shot" && target?.node_type === "video") return "generated_from";
  if (source?.node_type === "video" && target?.node_type === "export") return "included_in_export";
  return "continuity_from";
}

function buildAssetItems({
  characters,
  scenes,
  shots,
  tasks
}: {
  characters: Character[];
  scenes: Scene[];
  shots: Shot[];
  tasks: GenerationTaskSummary[];
}): EntityAssetItem[] {
  return [
    ...characters.map((item) => ({
      id: item.id,
      title: item.name,
      subtitle: `角色 / ${item.look_count} 套造型 / ${item.reference_count} 张参考图`,
      nodeType: "character" as const,
      entityType: "character"
    })),
    ...scenes.map((item) => ({
      id: item.id,
      title: item.name,
      subtitle: `场景 / ${item.state_count} 个状态 / ${item.reference_count} 张参考图`,
      nodeType: "scene" as const,
      entityType: "scene"
    })),
    ...shots.map((item) => ({
      id: item.id,
      title: item.name,
      subtitle: `镜头 #${item.order_index} / ${item.character_count} 人物 / ${item.reference_count} 参考`,
      nodeType: "shot" as const,
      entityType: "shot"
    })),
    ...tasks
      .filter((item) => item.has_outputs)
      .map((item) => ({
        id: item.task_id,
        title: item.task_name,
        subtitle: `${item.task_type === "video" ? "视频输出" : "图片输出"} / ${item.shot_name}`,
        nodeType: item.task_type === "video" ? ("video" as const) : ("image" as const),
        entityType: item.task_type
      }))
  ];
}

function canvasErrorText(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.status === 409 || error.code === "PROJECT_CANVAS_REVISION_CONFLICT") {
      return projectCanvasCopy.conflict;
    }
    return error.message;
  }
  return "创作画布操作失败，请稍后重试。";
}

function productionStatusLabel(status: string | undefined) {
  if (status === "completed") return "已完成";
  if (status === "ready_for_video") return "可生成视频";
  if (status === "in_progress") return "生产中";
  return "待补齐";
}

void semanticEdgeTypes;
void entityNodeTypes;
