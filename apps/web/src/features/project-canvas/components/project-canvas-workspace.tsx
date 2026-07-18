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
  type OnNodeDrag,
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
import type { Character, MediaAsset } from "@/features/characters/types";
import { fetchGenerationTasks, generationTaskKeys } from "@/features/generation-tasks/api";
import type { GenerationTaskSummary } from "@/features/generation-tasks/types";
import {
  addCanvasEntityBatch,
  applyCanvasBinding,
  createCanvasNode,
  deleteCanvasBinding,
  deleteCanvasNode,
  fetchCanvasBusinessRelationsPreview,
  fetchCanvasEntityBatchPreview,
  fetchProjectCanvas,
  importCanvasBusinessRelations,
  patchCanvasNode,
  projectCanvasKeys,
  saveProjectCanvas
} from "@/features/project-canvas/api";
import { CanvasQuickGeneratePanel } from "@/features/project-canvas/components/canvas-quick-generate-panel";
import {
  type CanvasBindingPayload,
  type CanvasEdgeInput,
  type CanvasEdgeStatus,
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
import { fetchProjectProductionStatus, productionStatusKeys } from "@/features/production-status/api";
import type { ShotProductionStatus } from "@/features/production-status/types";
import { fetchScenes, sceneKeys } from "@/features/scenes/api";
import type { Scene } from "@/features/scenes/types";
import { fetchShots, shotKeys } from "@/features/shots/api";
import type { Shot } from "@/features/shots/types";
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

interface BindingDialogState {
  sourceNodeId: string;
  targetNodeId: string;
  semanticType: CanvasEdgeType;
  edgeId?: string | null;
}

interface EntityAssetItem {
  id: string;
  title: string;
  subtitle: string;
  nodeType: CanvasNodeType;
  entityType: string;
  thumbnailUrl?: string | null;
}

const defaultNodeSize = {
  width: 240,
  height: 120
};

const nodeTypeLabel: Record<CanvasNodeType, string> = {
  text: "文本",
  character: "角色",
  scene: "场景",
  shot: "镜头",
  image: "图片",
  video: "视频",
  export: "导出"
};

const edgeTypeLabel: Record<CanvasEdgeType, string> = {
  uses_character: "使用角色",
  uses_scene: "使用场景",
  shot_reference: "镜头参考",
  identity_reference: "身份参考",
  look_reference: "造型参考",
  scene_reference: "场景参考",
  pose_reference: "姿态参考",
  start_frame: "首帧",
  end_frame: "尾帧",
  continuity_from: "连续自",
  generated_from: "生成自",
  included_in_export: "加入导出"
};

const edgeStatusLabel: Record<CanvasEdgeStatus, string> = {
  draft: "草稿",
  applied: "已绑定",
  failed: "失败"
};

const invalidConnectionMessage = "这两类节点目前不能直接连接。";

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
  const [bindingDialog, setBindingDialog] = useState<BindingDialogState | null>(null);
  const [selectedNodeIds, setSelectedNodeIds] = useState<string[]>([]);
  const [selectedEdgeIds, setSelectedEdgeIds] = useState<string[]>([]);
  const [drawerCollapsed, setDrawerCollapsed] = useState(false);
  const [showAllRelations, setShowAllRelations] = useState(false);
  const [message, setMessage] = useState<{ tone: "success" | "error" | "neutral"; text: string } | null>(
    null
  );
  const [undoStack, setUndoStack] = useState<ProjectCanvas[]>([]);
  const [redoStack, setRedoStack] = useState<ProjectCanvas[]>([]);
  const nodeSaveTimer = useRef<number | null>(null);
  const viewportSaveTimer = useRef<number | null>(null);
  const canvasRef = useRef<ProjectCanvas | null>(null);
  const viewModeRef = useRef<CanvasViewMode>("workflow");

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
  const businessRelationsPreviewQuery = useQuery({
    queryKey: projectCanvasKeys.businessRelationsPreview(projectId),
    queryFn: () => fetchCanvasBusinessRelationsPreview(projectId),
    enabled: projectId.length > 0
  });

  const acceptServerCanvas = useCallback(
    (nextCanvas: ProjectCanvas, options?: { preserveViewMode?: boolean }) => {
      canvasRef.current = nextCanvas;
      const nextViewMode = options?.preserveViewMode ? viewModeRef.current : nextCanvas.view_mode;
      setCanvas(nextCanvas);
      setViewMode(nextViewMode);
      viewModeRef.current = nextViewMode;
      setNodes(toFlowNodes(nextCanvas));
      setEdges(toFlowEdges(nextCanvas));
      queryClient.setQueryData(projectCanvasKeys.detail(projectId), nextCanvas);
    },
    [projectId, queryClient]
  );

  useEffect(() => {
    canvasRef.current = canvas;
  }, [canvas]);

  useEffect(() => {
    viewModeRef.current = viewMode;
  }, [viewMode]);

  useEffect(() => {
    if (canvasQuery.data) {
      acceptServerCanvas(canvasQuery.data);
    }
  }, [acceptServerCanvas, canvasQuery.data]);

  useEffect(
    () => () => {
      if (nodeSaveTimer.current) window.clearTimeout(nodeSaveTimer.current);
      if (viewportSaveTimer.current) window.clearTimeout(viewportSaveTimer.current);
    },
    []
  );

  const runMutation = useMutation({
    mutationFn: (input: ProjectCanvas) =>
      saveProjectCanvas(projectId, {
        expected_revision: input.revision,
        view_mode: viewModeRef.current,
        viewport: viewportFromReactFlow(reactFlow),
        nodes: input.nodes.map(toNodeInput),
        edges: input.edges.map(toEdgeInput)
      }),
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setMessage({ tone: "success", text: "画布已保存。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const saveViewportMutation = useMutation({
    mutationFn: () => {
      const currentCanvas = getRequiredCanvas(canvasRef);
      return saveProjectCanvas(projectId, {
        expected_revision: currentCanvas.revision,
        view_mode: viewModeRef.current,
        viewport: viewportFromReactFlow(reactFlow),
        nodes: currentCanvas.nodes.map(toNodeInput),
        edges: currentCanvas.edges.map(toEdgeInput)
      });
    },
    onSuccess: (nextCanvas) => acceptServerCanvas(nextCanvas, { preserveViewMode: true }),
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const createNodeMutation = useMutation({
    mutationFn: (input: {
      nodeType: CanvasNodeType;
      title?: string | null;
      entityType?: string | null;
      entityId?: string | null;
      data?: ProjectCanvasNode["data"];
      x?: number;
      y?: number;
    }) => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return createCanvasNode(projectId, {
        expected_revision: canvas.revision,
        node_type: input.nodeType,
        title: input.title ?? null,
        position_x: input.x ?? 120 + canvas.nodes.length * 32,
        position_y: input.y ?? 120 + canvas.nodes.length * 28,
        width: defaultNodeSize.width,
        height: defaultNodeSize.height,
        entity_type: input.entityType ?? null,
        entity_id: input.entityId ?? null,
        data: input.data ?? {}
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
      const currentCanvas = getRequiredCanvas(canvasRef);
      remember(currentCanvas, setUndoStack, setRedoStack);
      return patchCanvasNode(projectId, input.nodeId, {
        expected_revision: currentCanvas.revision,
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

  const applyBindingMutation = useMutation({
    mutationFn: (input: {
      sourceNodeId: string;
      targetNodeId: string;
      semanticType: CanvasEdgeType;
      edgeId?: string | null;
      applyBusiness: boolean;
      payload: CanvasBindingPayload;
    }) => {
      const currentCanvas = getRequiredCanvas(canvasRef);
      remember(currentCanvas, setUndoStack, setRedoStack);
      return applyCanvasBinding(projectId, {
        expected_revision: currentCanvas.revision,
        edge_id: input.edgeId ?? null,
        source_node_id: input.sourceNodeId,
        target_node_id: input.targetNodeId,
        semantic_type: input.semanticType,
        apply_business: input.applyBusiness,
        payload: input.payload
      });
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      const handledEdge = bindingDialog?.edgeId
        ? nextCanvas.edges.find((edge) => edge.id === bindingDialog.edgeId)
        : nextCanvas.edges.at(-1);
      setBindingDialog(null);
      setSelectedEdgeIds(handledEdge ? [handledEdge.id] : []);
      void queryClient.invalidateQueries({ queryKey: shotKeys.all(projectId) });
      void queryClient.invalidateQueries({ queryKey: generationTaskKeys.lists(projectId) });
      void queryClient.invalidateQueries({ queryKey: productionStatusKeys.project(projectId) });
      void queryClient.invalidateQueries({
        queryKey: projectCanvasKeys.businessRelationsPreview(projectId)
      });
      setMessage({
        tone: handledEdge?.data.status === "failed" ? "error" : "success",
        text:
          handledEdge?.data.status === "failed"
            ? "真实绑定失败，已保留为失败连线，可在 Inspector 重试。"
            : "画布关系已处理。"
      });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const deleteBindingMutation = useMutation({
    mutationFn: (input: { edgeId: string; mode: "hide_only" | "unbind_business" }) => {
      const currentCanvas = getRequiredCanvas(canvasRef);
      remember(currentCanvas, setUndoStack, setRedoStack);
      return deleteCanvasBinding(projectId, input.edgeId, {
        expected_revision: currentCanvas.revision,
        mode: input.mode
      });
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      setSelectedEdgeIds([]);
      void queryClient.invalidateQueries({ queryKey: shotKeys.all(projectId) });
      void queryClient.invalidateQueries({ queryKey: generationTaskKeys.lists(projectId) });
      void queryClient.invalidateQueries({ queryKey: productionStatusKeys.project(projectId) });
      void queryClient.invalidateQueries({
        queryKey: projectCanvasKeys.businessRelationsPreview(projectId)
      });
      setMessage({ tone: "success", text: "画布连线已处理。" });
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
      setMessage({ tone: "success", text: "现有角色、场景和镜头已导入画布。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const importRelationsMutation = useMutation({
    mutationFn: () => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      return importCanvasBusinessRelations(projectId, canvas.revision);
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      void queryClient.invalidateQueries({
        queryKey: projectCanvasKeys.businessRelationsPreview(projectId)
      });
      setMessage({ tone: "success", text: "现有镜头绑定关系已同步到画布。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const autoLayoutMutation = useMutation({
    mutationFn: () => {
      requireCanvas(canvas);
      remember(canvas, setUndoStack, setRedoStack);
      const layoutNodes = autoLayoutNodes(canvas.nodes);
      return saveProjectCanvas(projectId, {
        expected_revision: canvas.revision,
        view_mode: viewMode,
        viewport: viewportFromReactFlow(reactFlow),
        nodes: layoutNodes.map(toNodeInput),
        edges: canvas.edges.map(toEdgeInput)
      });
    },
    onSuccess: (nextCanvas) => {
      acceptServerCanvas(nextCanvas, { preserveViewMode: true });
      window.requestAnimationFrame(() => reactFlow.fitView({ padding: 0.16 }));
      setMessage({ tone: "success", text: "画布已自动整理。" });
    },
    onError: (error) => setMessage({ tone: "error", text: canvasErrorText(error) })
  });

  const onNodesChange = useCallback(
    (changes: NodeChange<CanvasFlowNode>[]) => {
      setNodes((currentNodes) => applyNodeChanges<CanvasFlowNode>(changes, currentNodes));
    },
    []
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange<CanvasFlowEdge>[]) => {
      setEdges((currentEdges) => applyEdgeChanges<CanvasFlowEdge>(changes, currentEdges));
    },
    []
  );

  const onNodeDragStop: OnNodeDrag<CanvasFlowNode> = useCallback(
    (_event, node) => {
      if (nodeSaveTimer.current) window.clearTimeout(nodeSaveTimer.current);
      nodeSaveTimer.current = window.setTimeout(() => {
        patchNodeMutation.mutate({ nodeId: node.id, position: node.position });
      }, 300);
    },
    [patchNodeMutation]
  );

  const onConnect: OnConnect = useCallback(
    (_connection: Connection) => {
      setMessage({
        tone: "neutral",
        text: "请在右侧 Inspector 使用明确按钮完成绑定。关系线当前仅作为辅助展示。"
      });
    },
    []
  );

  const selectedCanvasNode = canvas?.nodes.find((node) => node.id === selectedNodeIds[0]) ?? null;
  const selectedCanvasEdge = canvas?.edges.find((edge) => edge.id === selectedEdgeIds[0]) ?? null;
  const visibleEdges = useMemo(
    () =>
      filterVisibleEdges(edges, {
        showAllRelations,
        selectedNodeId: selectedCanvasNode?.id ?? null,
        selectedEdgeId: selectedCanvasEdge?.id ?? null
      }),
    [edges, selectedCanvasEdge?.id, selectedCanvasNode?.id, showAllRelations]
  );

  function changeViewMode(nextMode: CanvasViewMode) {
    const currentCanvas = canvasRef.current;
    if (!currentCanvas || nextMode === viewModeRef.current) return;
    remember(currentCanvas, setUndoStack, setRedoStack);
    saveProjectCanvas(projectId, {
      expected_revision: currentCanvas.revision,
      view_mode: nextMode,
      viewport: viewportFromReactFlow(reactFlow),
      nodes: currentCanvas.nodes.map(toNodeInput),
      edges: currentCanvas.edges.map(toEdgeInput)
    })
      .then((nextCanvas) => acceptServerCanvas(nextCanvas))
      .catch((error: unknown) => setMessage({ tone: "error", text: canvasErrorText(error) }));
  }

  function addNodeAt(nodeType: CanvasNodeType, position?: { x: number; y: number }) {
    createNodeMutation.mutate({
      nodeType,
      title: nodeType === "text" ? "文本备注" : undefined,
      x: position?.x,
      y: position?.y
    });
    setContextMenu(null);
  }

  function addEntityNode(entity: EntityAssetItem) {
    addEntityNodeAt(entity);
  }

  function addEntityNodeAt(entity: EntityAssetItem, position?: { x: number; y: number }) {
    const existing = canvas?.nodes.find(
      (node) => node.entity_id === entity.id && node.entity_type === entity.entityType
    );
    if (existing) {
      setSelectedNodeIds([existing.id]);
      setSelectedEdgeIds([]);
      reactFlow.setCenter(existing.position_x, existing.position_y, { zoom: 1, duration: 360 });
      setMessage({ tone: "neutral", text: "该素材已在画布中，已定位到已有节点。" });
      return;
    }
    createNodeMutation.mutate({
      nodeType: entity.nodeType,
      title: entity.title,
      entityType: entity.entityType,
      entityId: entity.id,
      data: entity.thumbnailUrl ? { thumbnail_override: entity.thumbnailUrl } : {},
      x: position?.x,
      y: position?.y
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
    setMessage({
      tone: "neutral",
      text: "手工连线入口已降级。请选择节点，在右侧 Inspector 使用绑定按钮。"
    });
  }

  function deleteSelected() {
    if (selectedNodeIds[0]) {
      if (!window.confirm("确定删除选中的画布节点吗？相关画布连线也会删除。")) return;
      deleteNodeMutation.mutate(selectedNodeIds[0]);
      return;
    }
    if (!selectedEdgeIds[0]) return;
    const edge = canvas?.edges.find((item) => item.id === selectedEdgeIds[0]);
    if (edge?.data.status === "applied") {
      const unbind = window.confirm(
        "这条连线已经应用到业务数据。点击“确定”会同时解除业务绑定，点击“取消”仅隐藏画布连线。"
      );
      deleteBindingMutation.mutate({
        edgeId: selectedEdgeIds[0],
        mode: unbind ? "unbind_business" : "hide_only"
      });
      return;
    }
    if (!window.confirm("确定删除选中的画布连线吗？")) return;
    deleteBindingMutation.mutate({ edgeId: selectedEdgeIds[0], mode: "hide_only" });
  }

  function importExistingEntities() {
    if (!batchPreviewQuery.data || batchPreviewQuery.data.total === 0) {
      setMessage({ tone: "neutral", text: "当前项目没有可导入的角色、场景或镜头。" });
      return;
    }
    if (window.confirm(`确认导入 ${batchPreviewQuery.data.total} 个现有实体节点吗？`)) {
      batchMutation.mutate();
    }
  }

  function importBusinessRelations() {
    const total = businessRelationsPreviewQuery.data?.total_edges ?? 0;
    if (total === 0) {
      setMessage({ tone: "neutral", text: "当前没有新的业务绑定关系可同步。" });
      return;
    }
    if (window.confirm(`确认把 ${total} 条现有业务关系同步为画布连线吗？不会重复导入。`)) {
      importRelationsMutation.mutate();
    }
  }

  function handleCanvasDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const position = reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    const assetData = event.dataTransfer.getData("application/x-lds-asset");
    if (assetData) {
      addEntityNodeAt(JSON.parse(assetData) as EntityAssetItem, position);
      return;
    }
    if (event.dataTransfer.files?.length) {
      setMessage({
        tone: "neutral",
        text: "本地文件上传即将支持，请先从资产库添加已有素材。"
      });
    }
  }

  const assetItems = useMemo(
    () =>
      buildAssetItems({
        characters: charactersQuery.data?.items ?? [],
        scenes: scenesQuery.data?.items ?? [],
        shots: shotsQuery.data?.items ?? [],
        tasks: generationTasksQuery.data?.items ?? []
      }),
    [charactersQuery.data?.items, scenesQuery.data?.items, shotsQuery.data?.items, generationTasksQuery.data?.items]
  );
  const productionByShotId = new Map(
    (productionQuery.data?.items ?? []).map((item) => [item.shot_id, item])
  );

  useEffect(() => {
    if (!canvas) return;
    setNodes(
      toFlowNodes(canvas, {
        shots: shotsQuery.data?.items ?? [],
        productionByShotId
      })
    );
  }, [canvas, productionQuery.data?.items, shotsQuery.data?.items]);

  if (projectQuery.isLoading || canvasQuery.isLoading) {
    return <Skeleton className="h-[calc(100vh-112px)]" />;
  }

  if (projectQuery.isError || canvasQuery.isError || !canvas) {
    return (
      <section className="rounded-md border border-border bg-panel p-6">
        <StatusMessage tone="error">创作画布加载失败，请重试。</StatusMessage>
        <Button
          type="button"
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
              {projectQuery.data?.name ?? "创作画布"}
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
                edges={visibleEdges}
                nodeTypes={projectCanvasNodeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeDragStop={onNodeDragStop}
                onConnect={onConnect}
                onDrop={handleCanvasDrop}
                onDragOver={(event) => {
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "copy";
                }}
                onNodeClick={(event, node) => {
                  setContextMenu(null);
                  setNodeMenu(null);
                  setSelectedEdgeIds([]);
                  setSelectedNodeIds((current) => {
                    if (!event.shiftKey) return [node.id];
                    return current.includes(node.id)
                      ? current.filter((id) => id !== node.id)
                      : [...current, node.id];
                  });
                }}
                onEdgeClick={(_event, edge) => {
                  setContextMenu(null);
                  setNodeMenu(null);
                  setSelectedNodeIds([]);
                  setSelectedEdgeIds([edge.id]);
                }}
                onEdgeContextMenu={(event, edge) => {
                  event.preventDefault();
                  setSelectedNodeIds([]);
                  setSelectedEdgeIds([edge.id]);
                  setMessage({ tone: "neutral", text: "已选中连线，可在右侧 Inspector 处理。" });
                }}
                onSelectionChange={({ nodes: selectedNodes, edges: selectedEdges }) => {
                  setSelectedNodeIds(selectedNodes.map((node) => node.id));
                  setSelectedEdgeIds(selectedEdges.map((edge) => edge.id));
                }}
                fitView
                minZoom={0.2}
                maxZoom={1.8}
                nodesConnectable={false}
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
                  if (viewportSaveTimer.current) window.clearTimeout(viewportSaveTimer.current);
                  viewportSaveTimer.current = window.setTimeout(() => {
                    if (canvasRef.current) saveViewportMutation.mutate();
                  }, 650);
                }}
                onNodeContextMenu={(event, node) => {
                  event.preventDefault();
                  setContextMenu(null);
                  setNodeMenu({ clientX: event.clientX, clientY: event.clientY, nodeId: node.id });
                  setSelectedNodeIds([node.id]);
                  setSelectedEdgeIds([]);
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
                      title="从这里开始创作"
                      description="把角色、场景、镜头和输出放到画布上，先搭出项目的创作关系。"
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
                            导入现有内容
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
                  onDuplicate={(node) =>
                    createNodeMutation.mutate({
                      nodeType: node.node_type,
                      title: `${node.title} 副本`,
                      entityType: node.entity_type,
                      entityId: null,
                      data: node.data,
                      x: node.position_x + 32,
                      y: node.position_y + 32
                    })
                  }
                  onBringToFront={(node) =>
                    patchNodeMutation.mutate({
                      nodeId: node.id,
                      data: node.data
                    })
                  }
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
                    : "导入现有内容"
                }
                batchDisabled={batchMutation.isPending}
                relationsLabel={
                  businessRelationsPreviewQuery.data
                    ? `同步绑定 (${businessRelationsPreviewQuery.data.total_edges})`
                    : "同步绑定"
                }
                relationsDisabled={importRelationsMutation.isPending}
                showAllRelations={showAllRelations}
                onAdd={() => addNodeAt("text")}
                onUndo={undo}
                onRedo={redo}
                onConnect={connectSelected}
                onDelete={deleteSelected}
                onBatch={importExistingEntities}
                onImportRelations={importBusinessRelations}
                onToggleRelations={() => setShowAllRelations((value) => !value)}
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
            canvas={canvas}
            assetItems={assetItems}
            shots={shotsQuery.data?.items ?? []}
            onOpenShot={(shotId) => navigate(`/projects/${projectId}/shots/${shotId}`)}
            onToggleCollapse={(node) =>
              patchNodeMutation.mutate({
                nodeId: node.id,
                data: { ...node.data, collapsed: !node.data.collapsed }
              })
            }
            onApplyEdge={(edge) =>
              setBindingDialog({
                sourceNodeId: edge.source_node_id,
                targetNodeId: edge.target_node_id,
                semanticType: edge.semantic_type,
                edgeId: edge.id
              })
            }
            onApplyDirectBinding={(sourceNode, targetNode, semanticType, payload) =>
              applyBindingMutation.mutate({
                sourceNodeId: sourceNode.id,
                targetNodeId: targetNode.id,
                semanticType,
                edgeId: null,
                applyBusiness: true,
                payload: payload ?? {}
              })
            }
            onDeleteEdge={(edge, mode) => deleteBindingMutation.mutate({ edgeId: edge.id, mode })}
          />
        </CanvasErrorBoundary>
      </div>

      {bindingDialog && (
        <BindingDialog
          state={bindingDialog}
          canvas={canvas}
          characters={charactersQuery.data?.items ?? []}
          scenes={scenesQuery.data?.items ?? []}
          tasks={generationTasksQuery.data?.items ?? []}
          pending={applyBindingMutation.isPending}
          onCancel={() => setBindingDialog(null)}
          onSubmit={(input) => applyBindingMutation.mutate(input)}
        />
      )}
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
          {item === "workflow" ? "工作流" : "故事板"}
        </button>
      ))}
    </div>
  );
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
          <div className="text-xs text-muted">可拖入已有角色、场景、镜头和可用素材。</div>
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
            placeholder="搜索角色、场景、镜头或素材"
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
                draggable
                className="rounded-md border border-border bg-background p-3 text-left transition-colors hover:border-primary"
                onDragStart={(event) => {
                  event.dataTransfer.setData("application/x-lds-asset", JSON.stringify(item));
                  event.dataTransfer.effectAllowed = "copy";
                }}
                onClick={() => onAdd(item)}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-foreground">{item.title}</span>
                  <Badge>{nodeTypeLabel[item.nodeType]}</Badge>
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
      {(Object.keys(nodeTypeLabel) as CanvasNodeType[]).map((nodeType) => (
        <button
          key={nodeType}
          type="button"
          className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-sm text-foreground hover:bg-panelRaised"
          onClick={() => onAdd(nodeType)}
        >
          <Plus className="h-4 w-4 text-primary" aria-hidden="true" />
          {nodeTypeLabel[nodeType]}
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
  if (!node) return null;

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
  relationsLabel,
  relationsDisabled,
  showAllRelations,
  onAdd,
  onUndo,
  onRedo,
  onConnect,
  onDelete,
  onBatch,
  onImportRelations,
  onToggleRelations,
  onAutoLayout,
  onFitView
}: {
  undoDisabled: boolean;
  redoDisabled: boolean;
  connectDisabled: boolean;
  deleteDisabled: boolean;
  batchLabel: string;
  batchDisabled: boolean;
  relationsLabel: string;
  relationsDisabled: boolean;
  showAllRelations: boolean;
  onAdd: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onConnect: () => void;
  onDelete: () => void;
  onBatch: () => void;
  onImportRelations: () => void;
  onToggleRelations: () => void;
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
        绑定提示
      </Button>
      <Button type="button" size="sm" variant={showAllRelations ? "default" : "secondary"} onClick={onToggleRelations}>
        <GitBranch className="h-4 w-4" aria-hidden="true" />
        {showAllRelations ? "隐藏关系" : "显示关系"}
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onAutoLayout}>
        <Move className="h-4 w-4" aria-hidden="true" />
        整理
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onFitView}>
        <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
        适配
      </Button>
      <Button type="button" size="sm" variant="secondary" onClick={onBatch} disabled={batchDisabled}>
        <Boxes className="h-4 w-4" aria-hidden="true" />
        {batchLabel}
      </Button>
      <Button
        type="button"
        size="sm"
        variant="secondary"
        onClick={onImportRelations}
        disabled={relationsDisabled}
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {relationsLabel}
      </Button>
      <Button type="button" size="sm" variant="danger" onClick={onDelete} disabled={deleteDisabled}>
        <Trash2 className="h-4 w-4" aria-hidden="true" />
        删除所选
      </Button>
    </div>
  );
}

function BindingDialog({
  state,
  canvas,
  characters,
  scenes,
  tasks,
  pending,
  onCancel,
  onSubmit
}: {
  state: BindingDialogState;
  canvas: ProjectCanvas;
  characters: Character[];
  scenes: Scene[];
  tasks: GenerationTaskSummary[];
  pending: boolean;
  onCancel: () => void;
  onSubmit: (input: {
    sourceNodeId: string;
    targetNodeId: string;
    semanticType: CanvasEdgeType;
    edgeId?: string | null;
    applyBusiness: boolean;
    payload: CanvasBindingPayload;
  }) => void;
}) {
  const sourceNode = canvas.nodes.find((node) => node.id === state.sourceNodeId) ?? null;
  const targetNode = canvas.nodes.find((node) => node.id === state.targetNodeId) ?? null;
  const allowedTypes = useMemo(
    () => allowedSemanticTypes(sourceNode, targetNode),
    [sourceNode, targetNode]
  );
  const initialSemanticType = allowedTypes.includes(state.semanticType)
    ? state.semanticType
    : allowedTypes[0];
  const [semanticType, setSemanticType] = useState<CanvasEdgeType | null>(initialSemanticType ?? null);
  const [lookId, setLookId] = useState("");
  const [sceneStateId, setSceneStateId] = useState("");
  const [replaceExistingScene, setReplaceExistingScene] = useState(false);
  const [videoTaskId, setVideoTaskId] = useState("");
  const [notes, setNotes] = useState("");

  const sourceCharacter = sourceNode?.entity_id
    ? characters.find((item) => item.id === sourceNode.entity_id)
    : null;
  const sourceScene = sourceNode?.entity_id ? scenes.find((item) => item.id === sourceNode.entity_id) : null;
  const targetShotId = targetNode?.node_type === "shot" ? targetNode.entity_id : null;
  const videoTasks = tasks.filter((task) => task.task_type === "video" && task.shot_id === targetShotId);

  useEffect(() => {
    setLookId(sourceCharacter?.default_look?.id ?? "");
  }, [sourceCharacter?.default_look?.id]);

  useEffect(() => {
    setSceneStateId(sourceScene?.default_state?.id ?? "");
  }, [sourceScene?.default_state?.id]);

  useEffect(() => {
    setVideoTaskId(videoTasks[0]?.task_id ?? "");
  }, [videoTasks]);

  useEffect(() => {
    if (!semanticType || !allowedTypes.includes(semanticType)) {
      setSemanticType(allowedTypes[0] ?? null);
    }
  }, [allowedTypes, semanticType]);

  function submit(applyBusiness: boolean) {
    if (!semanticType) return;
    onSubmit({
      sourceNodeId: state.sourceNodeId,
      targetNodeId: state.targetNodeId,
      semanticType,
      edgeId: state.edgeId ?? null,
      applyBusiness,
      payload: {
        look_id: lookId || null,
        scene_state_id: sceneStateId || null,
        replace_existing_scene: replaceExistingScene,
        video_task_id: videoTaskId || null,
        notes: notes.trim() || null
      }
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6">
      <section className="w-full max-w-xl rounded-md border border-border bg-panel p-5 shadow-workbench">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Semantic Binding</div>
            <h2 className="mt-2 text-lg font-semibold text-foreground">确认画布关系</h2>
          </div>
          <Button type="button" variant="ghost" onClick={onCancel} disabled={pending}>
            取消
          </Button>
        </div>
        <div className="mt-4 grid gap-3 text-sm">
          <InfoRow label="来源" value={sourceNode?.title ?? "未知节点"} />
          <InfoRow label="目标" value={targetNode?.title ?? "未知节点"} />
          {allowedTypes.length === 0 || !semanticType ? (
            <StatusMessage tone="neutral">{invalidConnectionMessage}</StatusMessage>
          ) : (
            <label className="grid gap-1">
              <span className="text-muted">语义用途</span>
              <select
                aria-label="语义用途"
                value={semanticType}
                onChange={(event) => setSemanticType(event.target.value as CanvasEdgeType)}
                className="h-9 rounded-md border border-border bg-background px-3 text-foreground outline-none focus:border-primary"
              >
                {allowedTypes.map((type) => (
                  <option key={type} value={type}>
                    {edgeTypeLabel[type]}
                  </option>
                ))}
              </select>
            </label>
          )}
          {semanticType === "uses_character" && sourceCharacter?.default_look && (
            <label className="grid gap-1">
              <span className="text-muted">角色造型</span>
              <select
                value={lookId}
                onChange={(event) => setLookId(event.target.value)}
                className="h-9 rounded-md border border-border bg-background px-3 text-foreground outline-none focus:border-primary"
              >
                <option value="">不指定造型</option>
                <option value={sourceCharacter.default_look.id}>
                  {sourceCharacter.default_look.name}（默认）
                </option>
              </select>
            </label>
          )}
          {semanticType === "uses_scene" && sourceScene?.default_state && (
            <>
              <label className="grid gap-1">
                <span className="text-muted">场景状态</span>
                <select
                  value={sceneStateId}
                  onChange={(event) => setSceneStateId(event.target.value)}
                  className="h-9 rounded-md border border-border bg-background px-3 text-foreground outline-none focus:border-primary"
                >
                  <option value="">不指定状态</option>
                  <option value={sourceScene.default_state.id}>
                    {sourceScene.default_state.name}（默认）
                  </option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-muted">
                <input
                  type="checkbox"
                  checked={replaceExistingScene}
                  onChange={(event) => setReplaceExistingScene(event.target.checked)}
                />
                如果镜头已有场景，允许替换并清理不兼容场景参考
              </label>
            </>
          )}
          {(semanticType === "start_frame" || semanticType === "end_frame") && (
            <label className="grid gap-1">
              <span className="text-muted">目标视频任务</span>
              <select
                value={videoTaskId}
                onChange={(event) => setVideoTaskId(event.target.value)}
                className="h-9 rounded-md border border-border bg-background px-3 text-foreground outline-none focus:border-primary"
              >
                <option value="">请选择视频任务</option>
                {videoTasks.map((task) => (
                  <option key={task.task_id} value={task.task_id}>
                    {task.task_name}
                  </option>
                ))}
              </select>
              <span className="text-xs text-muted">首尾帧会写入视频任务输入，不会写到普通视频节点。</span>
            </label>
          )}
          <label className="grid gap-1">
            <span className="text-muted">备注</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
              className="rounded-md border border-border bg-background px-3 py-2 text-foreground outline-none focus:border-primary"
            />
          </label>
          <StatusMessage tone="neutral">
            “仅保留画布关系”不会修改镜头、任务或输出；“确认真实绑定”会由后端 Service 写入允许的业务关系。
          </StatusMessage>
        </div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">
          <Button type="button" variant="secondary" onClick={() => submit(false)} disabled={pending || !semanticType}>
            仅保留画布关系
          </Button>
          <Button type="button" onClick={() => submit(true)} disabled={pending || !semanticType}>
            确认真实绑定
          </Button>
        </div>
      </section>
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

  if (loading) return <Skeleton className="h-full" />;

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
              <button type="button" className="block w-full text-left" onClick={() => onOpenShot(shot.id)}>
                <div className="aspect-video overflow-hidden rounded-md border border-border bg-background">
                  {imageUrl ? (
                    videoUrl ? (
                      <video src={videoUrl} className="h-full w-full object-cover" muted />
                    ) : (
                      <img src={imageUrl} alt="" className="h-full w-full object-cover" />
                    )
                  ) : (
                    <div className="flex h-full items-center justify-center text-sm text-muted">暂无画面</div>
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
  canvas,
  assetItems,
  shots,
  onOpenShot,
  onToggleCollapse,
  onApplyEdge,
  onApplyDirectBinding,
  onDeleteEdge
}: {
  projectId: string;
  node: ProjectCanvasNode | null;
  edge: ProjectCanvasEdge | null;
  canvas: ProjectCanvas;
  assetItems: EntityAssetItem[];
  shots: Shot[];
  onOpenShot: (shotId: string) => void;
  onToggleCollapse: (node: ProjectCanvasNode) => void;
  onApplyEdge: (edge: ProjectCanvasEdge) => void;
  onApplyDirectBinding: (
    sourceNode: ProjectCanvasNode,
    targetNode: ProjectCanvasNode,
    semanticType: CanvasEdgeType,
    payload?: CanvasBindingPayload
  ) => void;
  onDeleteEdge: (edge: ProjectCanvasEdge, mode: "hide_only" | "unbind_business") => void;
}) {
  const linkedAsset = node?.entity_id
    ? assetItems.find((item) => item.id === node.entity_id && item.entityType === node.entity_type)
    : null;
  const sourceNode = edge ? canvas.nodes.find((item) => item.id === edge.source_node_id) : null;
  const targetNode = edge ? canvas.nodes.find((item) => item.id === edge.target_node_id) : null;
  const shot = node?.node_type === "shot" && node.entity_id ? shots.find((item) => item.id === node.entity_id) : null;
  const shotEdges =
    node?.node_type === "shot"
      ? canvas.edges.filter(
          (item) => item.source_node_id === node.id || item.target_node_id === node.id
        )
      : [];

  return (
    <aside className="min-h-0 overflow-y-auto rounded-md border border-border bg-panel">
      <div className="border-b border-border p-4">
        <div className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Inspector / 助手</div>
        <h2 className="mt-2 text-base font-semibold text-foreground">
          {node ? node.title : edge ? edgeTypeLabel[edge.semantic_type] : "项目助手"}
        </h2>
      </div>
      <div className="grid gap-4 p-4">
        {!node && !edge && (
          <>
            <StatusMessage tone="neutral">
              选择节点或连线后，可以查看业务关联、应用状态和下一步操作。
            </StatusMessage>
            <InspectorPanel title="下一步建议">
              <ul className="grid gap-2 text-sm text-muted">
                <li>1. 从左侧资产抽屉拖入角色、场景和镜头。</li>
                <li>2. 连接资产与镜头，并在确认面板中选择真实绑定或草稿关系。</li>
                <li>3. 使用“同步绑定”把已有镜头关系导入为画布连线。</li>
              </ul>
            </InspectorPanel>
          </>
        )}
        {edge && !node && (
          <InspectorPanel title="语义连线">
            <div className="grid gap-2 text-sm">
              <InfoRow label="来源" value={sourceNode?.title ?? edge.source_node_id} />
              <InfoRow label="目标" value={targetNode?.title ?? edge.target_node_id} />
              <InfoRow label="语义" value={edgeTypeLabel[edge.semantic_type]} />
              <InfoRow label="状态" value={edgeStatusLabel[(edge.data.status ?? "draft") as CanvasEdgeStatus]} />
              <InfoRow label="真实业务关联" value={edge.data.business_entity_type ?? "未写入"} />
              {edge.data.error_message && <StatusMessage tone="error">{edge.data.error_message}</StatusMessage>}
              <div className="grid gap-2 pt-2">
                {edge.semantic_type === "generated_from" ? (
                  <StatusMessage tone="neutral">生成来源关系只能由系统建立。</StatusMessage>
                ) : (
                  <Button type="button" onClick={() => onApplyEdge(edge)}>
                    <GitBranch className="h-4 w-4" aria-hidden="true" />
                    {edge.data.status === "failed" ? "重试应用" : "应用 / 编辑绑定"}
                  </Button>
                )}
                <Button type="button" variant="secondary" onClick={() => onDeleteEdge(edge, "hide_only")}>
                  隐藏画布连线
                </Button>
                {edge.data.status === "applied" && (
                  <Button type="button" variant="danger" onClick={() => onDeleteEdge(edge, "unbind_business")}>
                    解除业务绑定
                  </Button>
                )}
              </div>
            </div>
          </InspectorPanel>
        )}
        {node && (
          <>
            <InspectorPanel title="节点信息">
              <div className="grid gap-2 text-sm">
                <InfoRow label="类型" value={nodeTypeLabel[node.node_type]} />
                <InfoRow label="标题" value={node.title} />
                <InfoRow label="业务关联" value={node.entity_type ? "已关联" : "画布草稿"} />
                {linkedAsset && <InfoRow label="来源" value={linkedAsset.subtitle} />}
              </div>
            </InspectorPanel>
            {node.node_type === "image" && node.entity_id && (
              <ImageReferenceActions
                node={node}
                canvas={canvas}
                shots={shots}
                onApplyDirectBinding={onApplyDirectBinding}
                onDeleteEdge={onDeleteEdge}
              />
            )}
            {node.node_type === "character" && node.entity_id && (
              <CharacterShotActions
                node={node}
                canvas={canvas}
                shots={shots}
                onApplyDirectBinding={onApplyDirectBinding}
              />
            )}
            {node.node_type === "scene" && node.entity_id && (
              <SceneShotActions
                node={node}
                canvas={canvas}
                shots={shots}
                onApplyDirectBinding={onApplyDirectBinding}
              />
            )}
            {shot && (
              <InspectorPanel title="本镜头资产">
                <div className="grid gap-2 text-sm">
                  <InfoRow label="已绑定角色" value={`${shot.character_count} 个`} />
                  <InfoRow label="场景" value={shot.scene?.name ?? "未设置"} />
                  <InfoRow label="场景状态" value={shot.scene_state?.name ?? "未设置"} />
                  <InfoRow label="参考图" value={`${shot.reference_count} 张`} />
                  <InfoRow
                    label="连续性关系"
                    value={`${shotEdges.filter((item) => item.semantic_type === "continuity_from").length} 条`}
                  />
                  <InfoRow
                    label="草稿画布关系"
                    value={`${shotEdges.filter((item) => item.data.status !== "applied").length} 条`}
                  />
                </div>
              </InspectorPanel>
            )}
            {shot && (
              <InspectorPanel title="画布快速生成">
                <CanvasQuickGeneratePanel projectId={projectId} shot={shot} />
              </InspectorPanel>
            )}
            <InspectorPanel title="可执行操作">
              <div className="grid gap-2">
                {node.node_type === "shot" && node.entity_id && (
                  <Button type="button" onClick={() => onOpenShot(node.entity_id ?? "")}>
                    <Clapperboard className="h-4 w-4" aria-hidden="true" />
                    打开镜头创作工作台
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
                  收起 / 展开节点
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

function ImageReferenceActions({
  node,
  canvas,
  shots,
  onApplyDirectBinding,
  onDeleteEdge
}: {
  node: ProjectCanvasNode;
  canvas: ProjectCanvas;
  shots: Shot[];
  onApplyDirectBinding: (
    sourceNode: ProjectCanvasNode,
    targetNode: ProjectCanvasNode,
    semanticType: CanvasEdgeType,
    payload?: CanvasBindingPayload
  ) => void;
  onDeleteEdge: (edge: ProjectCanvasEdge, mode: "hide_only" | "unbind_business") => void;
}) {
  const shotNodesByShotId = new Map(
    canvas.nodes
      .filter((item) => item.node_type === "shot" && item.entity_id)
      .map((item) => [item.entity_id as string, item])
  );

  return (
    <InspectorPanel title="镜头参考图">
      <div className="grid gap-2">
        {shots.map((shot) => {
          const shotNode = shotNodesByShotId.get(shot.id) ?? null;
          const edge = findEdge(canvas, node.id, shotNode?.id ?? "", "shot_reference");
          const reference = shot.references.find((item) => shotReferenceMediaId(item) === node.entity_id);
          const isBound = Boolean(edge?.data.status === "applied" || reference);
          return (
            <div key={shot.id} className="rounded border border-border bg-background p-2">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-foreground">{shot.name}</div>
                  <div className="mt-1 text-xs text-muted">
                    {isBound ? `已是镜头参考图${reference?.purpose ? ` · ${reference.purpose}` : ""}` : "尚未绑定"}
                  </div>
                </div>
                {isBound ? (
                  edge ? (
                    <Button type="button" size="sm" variant="danger" onClick={() => onDeleteEdge(edge, "unbind_business")}>
                      从镜头参考图移除
                    </Button>
                  ) : (
                    <Button type="button" size="sm" variant="secondary" disabled>
                      已是镜头参考图
                    </Button>
                  )
                ) : (
                  <Button
                    type="button"
                    size="sm"
                    disabled={!shotNode}
                    onClick={() =>
                      shotNode &&
                      onApplyDirectBinding(node, shotNode, "shot_reference", {
                        media_asset_id: node.entity_id,
                        purpose: "general"
                      })
                    }
                  >
                    设为镜头参考图
                  </Button>
                )}
              </div>
              {!shotNode && <div className="mt-2 text-xs text-muted">请先把该镜头添加到画布。</div>}
            </div>
          );
        })}
      </div>
    </InspectorPanel>
  );
}

function CharacterShotActions({
  node,
  canvas,
  shots,
  onApplyDirectBinding
}: {
  node: ProjectCanvasNode;
  canvas: ProjectCanvas;
  shots: Shot[];
  onApplyDirectBinding: (
    sourceNode: ProjectCanvasNode,
    targetNode: ProjectCanvasNode,
    semanticType: CanvasEdgeType,
    payload?: CanvasBindingPayload
  ) => void;
}) {
  const shotNodesByShotId = new Map(
    canvas.nodes
      .filter((item) => item.node_type === "shot" && item.entity_id)
      .map((item) => [item.entity_id as string, item])
  );

  return (
    <InspectorPanel title="镜头人物">
      <div className="grid gap-2">
        {shots.map((shot) => {
          const shotNode = shotNodesByShotId.get(shot.id) ?? null;
          const edge = findEdge(canvas, node.id, shotNode?.id ?? "", "uses_character");
          const isBound = edge?.data.status === "applied";
          return (
            <div key={shot.id} className="flex items-center justify-between gap-2 rounded border border-border bg-background p-2">
              <span className="min-w-0 truncate text-sm text-foreground">{shot.name}</span>
              {isBound ? (
                <Button type="button" size="sm" variant="secondary" disabled>
                  已添加到镜头人物
                </Button>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  disabled={!shotNode}
                  onClick={() => shotNode && onApplyDirectBinding(node, shotNode, "uses_character")}
                >
                  添加到镜头人物
                </Button>
              )}
            </div>
          );
        })}
      </div>
    </InspectorPanel>
  );
}

function SceneShotActions({
  node,
  canvas,
  shots,
  onApplyDirectBinding
}: {
  node: ProjectCanvasNode;
  canvas: ProjectCanvas;
  shots: Shot[];
  onApplyDirectBinding: (
    sourceNode: ProjectCanvasNode,
    targetNode: ProjectCanvasNode,
    semanticType: CanvasEdgeType,
    payload?: CanvasBindingPayload
  ) => void;
}) {
  const shotNodesByShotId = new Map(
    canvas.nodes
      .filter((item) => item.node_type === "shot" && item.entity_id)
      .map((item) => [item.entity_id as string, item])
  );

  return (
    <InspectorPanel title="镜头场景">
      <div className="grid gap-2">
        {shots.map((shot) => {
          const shotNode = shotNodesByShotId.get(shot.id) ?? null;
          const edge = findEdge(canvas, node.id, shotNode?.id ?? "", "uses_scene");
          const isBound = edge?.data.status === "applied" || shot.scene?.id === node.entity_id;
          return (
            <div key={shot.id} className="flex items-center justify-between gap-2 rounded border border-border bg-background p-2">
              <span className="min-w-0 truncate text-sm text-foreground">{shot.name}</span>
              {isBound ? (
                <Button type="button" size="sm" variant="secondary" disabled>
                  已是镜头场景
                </Button>
              ) : (
                <Button
                  type="button"
                  size="sm"
                  disabled={!shotNode}
                  onClick={() =>
                    shotNode &&
                    onApplyDirectBinding(node, shotNode, "uses_scene", {
                      replace_existing_scene: true
                    })
                  }
                >
                  设为镜头场景
                </Button>
              )}
            </div>
          );
        })}
      </div>
    </InspectorPanel>
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

function toFlowNodes(
  canvas: ProjectCanvas,
  context?: {
    shots?: Shot[];
    productionByShotId?: Map<string, ShotProductionStatus>;
  }
): CanvasFlowNode[] {
  return canvas.nodes.map((node) => ({
    id: node.id,
    type: node.node_type,
    position: { x: node.position_x, y: node.position_y },
    width: node.width,
    height: node.height,
    zIndex: node.z_index,
    data: {
      canvasNode: node,
      subtitle: canvasNodeSubtitle(node, canvas, context)
    }
  }));
}

function toFlowEdges(canvas: ProjectCanvas): CanvasFlowEdge[] {
  return canvas.edges.map((edge) => {
    const status = edge.data.status ?? "draft";
    return {
      id: edge.id,
      source: edge.source_node_id,
      target: edge.target_node_id,
      label: `${edgeDisplayLabel(edge.semantic_type)} · ${edgeStatusLabel[status]}`,
      animated: edge.semantic_type === "generated_from" || edge.semantic_type === "continuity_from",
      data: edge.data as Record<string, unknown>,
      style: {
        stroke: status === "failed" ? "#ef4444" : status === "applied" ? "#6f93c2" : "#8b949e",
        strokeDasharray: status === "draft" ? "6 5" : undefined,
        strokeWidth: status === "applied" ? 2.2 : 1.6
      },
      labelBgStyle: { fill: "#151a20", fillOpacity: 0.92 },
      labelStyle: { fill: status === "failed" ? "#fca5a5" : "#d7dee8", fontSize: 11 }
    };
  });
}

function filterVisibleEdges(
  edges: CanvasFlowEdge[],
  options: { showAllRelations: boolean; selectedNodeId: string | null; selectedEdgeId: string | null }
): CanvasFlowEdge[] {
  if (options.showAllRelations) return edges;
  return edges.filter((edge) => {
    if (options.selectedEdgeId && edge.id === options.selectedEdgeId) return true;
    if (!options.selectedNodeId) return false;
    return edge.source === options.selectedNodeId || edge.target === options.selectedNodeId;
  });
}

function findEdge(
  canvas: ProjectCanvas,
  sourceNodeId: string,
  targetNodeId: string,
  semanticType: CanvasEdgeType
): ProjectCanvasEdge | null {
  if (!targetNodeId) return null;
  return (
    canvas.edges.find(
      (edge) =>
        edge.source_node_id === sourceNodeId &&
        edge.target_node_id === targetNodeId &&
        edge.semantic_type === semanticType
    ) ?? null
  );
}

function shotReferenceMediaId(reference: Shot["references"][number]): string | null {
  return reference.media_asset_id ?? reference.media_asset?.id ?? null;
}

function edgeDisplayLabel(edgeType: CanvasEdgeType): string {
  if (edgeType === "generated_from") return "生成结果";
  if (edgeType === "shot_reference") return "镜头参考";
  return edgeTypeLabel[edgeType];
}

function canvasNodeSubtitle(
  node: ProjectCanvasNode,
  canvas: ProjectCanvas,
  context?: {
    shots?: Shot[];
    productionByShotId?: Map<string, ShotProductionStatus>;
  }
): string | undefined {
  if (node.node_type === "shot" && node.entity_id) {
    const shot = context?.shots?.find((item) => item.id === node.entity_id);
    const production = context?.productionByShotId?.get(node.entity_id);
    if (!shot) return undefined;
    return [
      `${shot.character_count} 人物`,
      shot.scene?.name ? `场景：${shot.scene.name}` : "未选场景",
      `${shot.reference_count} 参考图`,
      `首帧：${production?.steps.first_frame?.status ?? "未完成"}`,
      `尾帧：${production?.steps.end_frame?.status ?? "未完成"}`
    ].join(" / ");
  }

  if (node.node_type === "image") {
    const boundShotNames = canvas.edges
      .filter(
        (edge) =>
          edge.source_node_id === node.id &&
          edge.semantic_type === "shot_reference" &&
          edge.data.status === "applied"
      )
      .map((edge) => canvas.nodes.find((item) => item.id === edge.target_node_id))
      .filter((item): item is ProjectCanvasNode => Boolean(item))
      .map((item) => item.title);
    const generatedEdge = canvas.edges.find(
      (edge) => edge.target_node_id === node.id && edge.semantic_type === "generated_from"
    );
    const candidateType =
      node.title.includes("首帧") || node.data.temporary_label?.includes("首帧")
        ? "首帧候选"
        : node.title.includes("尾帧") || node.data.temporary_label?.includes("尾帧")
          ? "尾帧候选"
          : "普通素材";
    return [
      candidateType,
      boundShotNames.length ? `已绑定：${boundShotNames.join("、")}` : "未设为镜头参考",
      generatedEdge ? "生成结果" : "素材"
    ].join(" / ");
  }

  return undefined;
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

function getRequiredCanvas(ref: React.RefObject<ProjectCanvas | null>): ProjectCanvas {
  if (!ref.current) {
    throw new Error("Canvas is not loaded.");
  }
  return ref.current;
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
): CanvasEdgeType | null {
  const source = nodes.find((node) => node.id === sourceId);
  const target = nodes.find((node) => node.id === targetId);
  return allowedSemanticTypes(source ?? null, target ?? null)[0] ?? null;
}

function allowedSemanticTypes(
  source: Pick<ProjectCanvasNode, "id" | "node_type"> | null,
  target: Pick<ProjectCanvasNode, "id" | "node_type"> | null
): CanvasEdgeType[] {
  if (!source || !target || source.id === target.id) return [];
  if (source.node_type === "character" && target.node_type === "shot") return ["uses_character"];
  if (source.node_type === "scene" && target.node_type === "shot") return ["uses_scene"];
  if (source.node_type === "image" && target.node_type === "shot") {
    return ["shot_reference"];
  }
  if (source.node_type === "shot" && target.node_type === "shot") return ["continuity_from"];
  if (source.node_type === "video" && target.node_type === "export") return ["included_in_export"];
  return [];
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
  const mediaItems = uniqueMediaAssets(shots.flatMap((shot) => shot.references.map((reference) => reference.media_asset)));
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
    ...mediaItems.map((item) => ({
      id: item.id,
      title: item.original_filename,
      subtitle: `已有媒体 / ${item.media_type}`,
      nodeType: item.media_type === "video" ? ("video" as const) : ("image" as const),
      entityType: item.media_type === "video" ? "video" : "image",
      thumbnailUrl: item.thumbnail_url
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

function uniqueMediaAssets(items: Array<MediaAsset | null>): MediaAsset[] {
  const seen = new Set<string>();
  const result: MediaAsset[] = [];
  for (const item of items) {
    if (!item || seen.has(item.id)) continue;
    seen.add(item.id);
    result.push(item);
  }
  return result;
}

function canvasErrorText(error: unknown) {
  if (error instanceof ApiClientError) {
    if (error.status === 409 || error.code === "PROJECT_CANVAS_REVISION_CONFLICT") {
      return "画布数据已在其他页面更新，请重新加载后再试。";
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
