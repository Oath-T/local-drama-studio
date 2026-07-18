import json
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.api.schemas.project_canvas import (
    CanvasEdgeCreateRequest,
    CanvasEdgeData,
    CanvasEdgeResponse,
    CanvasEdgeUpsert,
    CanvasEntityBatchPreview,
    CanvasEntityBatchRequest,
    CanvasNodeCreateRequest,
    CanvasNodeData,
    CanvasNodePatchRequest,
    CanvasNodeResponse,
    CanvasNodeUpsert,
    CanvasViewport,
    ProjectCanvasResponse,
    ProjectCanvasSaveRequest,
)
from app.core.errors import AppError
from app.domain.project_canvas import (
    CanvasEdgeType,
    CanvasNodeType,
    CanvasViewMode,
    ProjectCanvasErrorCode,
    normalize_title,
    utc_now,
)
from app.infrastructure.models.project_canvas import (
    ProjectCanvasEdgeRecord,
    ProjectCanvasNodeRecord,
    ProjectCanvasRecord,
)
from app.repository.project_canvas_repository import ProjectCanvasRepository

ERROR_MESSAGES: dict[ProjectCanvasErrorCode, str] = {
    ProjectCanvasErrorCode.PROJECT_NOT_FOUND: "项目不存在或已被删除。",
    ProjectCanvasErrorCode.CANVAS_NOT_FOUND: "项目画布不存在或已被删除。",
    ProjectCanvasErrorCode.NODE_NOT_FOUND: "画布节点不存在或已被删除。",
    ProjectCanvasErrorCode.EDGE_NOT_FOUND: "画布连线不存在或已被删除。",
    ProjectCanvasErrorCode.REVISION_CONFLICT: "数据已在其他页面更新，请重新加载或覆盖。",
    ProjectCanvasErrorCode.INVALID_VIEW_MODE: "画布视图模式无效。",
    ProjectCanvasErrorCode.INVALID_NODE_TYPE: "画布节点类型无效。",
    ProjectCanvasErrorCode.INVALID_EDGE_TYPE: "画布连线类型无效。",
    ProjectCanvasErrorCode.INVALID_ENTITY: "节点关联的项目资产不存在或不属于当前项目。",
    ProjectCanvasErrorCode.INVALID_CONNECTION: "连线两端必须属于同一个项目画布。",
    ProjectCanvasErrorCode.INVALID_NODE_DATA: "节点 UI 数据格式无效。",
}

ENTITY_NODE_TYPES = {
    CanvasNodeType.CHARACTER.value,
    CanvasNodeType.SCENE.value,
    CanvasNodeType.SHOT.value,
    CanvasNodeType.IMAGE.value,
    CanvasNodeType.VIDEO.value,
    CanvasNodeType.EXPORT.value,
}

MANUAL_EDGE_NODE_TYPES: dict[CanvasEdgeType, set[tuple[str, str]]] = {
    CanvasEdgeType.USES_CHARACTER: {("character", "shot")},
    CanvasEdgeType.USES_SCENE: {("scene", "shot")},
    CanvasEdgeType.SHOT_REFERENCE: {("image", "shot")},
    CanvasEdgeType.IDENTITY_REFERENCE: {("image", "shot")},
    CanvasEdgeType.LOOK_REFERENCE: {("image", "shot")},
    CanvasEdgeType.SCENE_REFERENCE: {("image", "shot")},
    CanvasEdgeType.POSE_REFERENCE: {("image", "shot")},
    CanvasEdgeType.START_FRAME: {("image", "shot")},
    CanvasEdgeType.END_FRAME: {("image", "shot")},
    CanvasEdgeType.CONTINUITY_FROM: {("shot", "shot")},
    CanvasEdgeType.INCLUDED_IN_EXPORT: {("video", "export")},
}

SYSTEM_GENERATED_ENTITY_TYPES = {"keyframe_output", "video_output"}


class ProjectCanvasService:
    def __init__(self, session: Session) -> None:
        self.repository = ProjectCanvasRepository(session)

    def get_canvas(self, project_id: UUID) -> ProjectCanvasResponse:
        canvas = self._get_or_create_canvas(str(project_id))
        return self._response(canvas)

    def save_canvas(
        self,
        project_id: UUID,
        payload: ProjectCanvasSaveRequest,
    ) -> ProjectCanvasResponse:
        canvas = self._get_or_create_canvas(str(project_id))
        self._ensure_revision(canvas, payload.expected_revision)

        node_records = [
            self._node_record_from_payload(str(project_id), canvas.id, node)
            for node in payload.nodes
        ]
        node_by_id = {record.id: record for record in node_records}
        edge_records = [
            self._edge_record_from_payload(canvas.id, edge, node_by_id) for edge in payload.edges
        ]
        payload_edge_ids = {edge.id for edge in payload.edges if edge.id}
        edge_records.extend(
            self._preserved_edge_record_from_existing(canvas.id, edge, node_by_id)
            for edge in canvas.edges
            if edge.id not in payload_edge_ids
            and edge.source_node_id in node_by_id
            and edge.target_node_id in node_by_id
        )
        now = utc_now()
        canvas.view_mode = payload.view_mode.value
        canvas.viewport_json = payload.viewport.model_dump_json()
        canvas.revision += 1
        canvas.updated_at = now
        self.repository.clear_canvas(canvas.id)
        self.repository.flush()
        for record in node_records:
            self.repository.add(record)
        self.repository.flush()
        for record in edge_records:
            self.repository.add(record)
        self.repository.commit()
        refreshed = self.repository.get_canvas(str(project_id))
        if refreshed is None:
            raise_canvas_error(ProjectCanvasErrorCode.CANVAS_NOT_FOUND, 404)
        return self._response(refreshed)

    def create_node(
        self,
        project_id: UUID,
        payload: CanvasNodeCreateRequest,
    ) -> ProjectCanvasResponse:
        canvas = self._get_or_create_canvas(str(project_id))
        self._ensure_revision(canvas, payload.expected_revision)
        record = self._node_record_from_payload(str(project_id), canvas.id, payload)
        canvas.revision += 1
        canvas.updated_at = utc_now()
        self.repository.add(record)
        self.repository.commit()
        return self._response(self._require_canvas(str(project_id)))

    def patch_node(
        self,
        project_id: UUID,
        node_id: UUID,
        payload: CanvasNodePatchRequest,
    ) -> ProjectCanvasResponse:
        canvas = self._get_or_create_canvas(str(project_id))
        self._ensure_revision(canvas, payload.expected_revision)
        record = self.repository.get_node(canvas.id, str(node_id))
        if record is None:
            raise_canvas_error(ProjectCanvasErrorCode.NODE_NOT_FOUND, 404)
        if payload.title is not None:
            record.title = normalize_title(payload.title, record.title)
        if payload.position_x is not None:
            record.position_x = payload.position_x
        if payload.position_y is not None:
            record.position_y = payload.position_y
        if payload.width is not None:
            record.width = payload.width
        if payload.height is not None:
            record.height = payload.height
        if payload.z_index is not None:
            record.z_index = payload.z_index
        if payload.data is not None:
            record.data_json = payload.data.model_dump_json(exclude_none=True)
        now = utc_now()
        record.updated_at = now
        canvas.revision += 1
        canvas.updated_at = now
        self.repository.commit()
        return self._response(self._require_canvas(str(project_id)))

    def delete_node(
        self,
        project_id: UUID,
        node_id: UUID,
        expected_revision: int,
    ) -> ProjectCanvasResponse:
        canvas = self._get_or_create_canvas(str(project_id))
        self._ensure_revision(canvas, expected_revision)
        record = self.repository.get_node(canvas.id, str(node_id))
        if record is None:
            raise_canvas_error(ProjectCanvasErrorCode.NODE_NOT_FOUND, 404)
        canvas.revision += 1
        canvas.updated_at = utc_now()
        self.repository.delete_node(record)
        self.repository.commit()
        return self._response(self._require_canvas(str(project_id)))

    def create_edge(
        self,
        project_id: UUID,
        payload: CanvasEdgeCreateRequest,
    ) -> ProjectCanvasResponse:
        canvas = self._get_or_create_canvas(str(project_id))
        self._ensure_revision(canvas, payload.expected_revision)
        node_by_id = {node.id: node for node in canvas.nodes}
        record = self._edge_record_from_payload(canvas.id, payload, node_by_id)
        canvas.revision += 1
        canvas.updated_at = utc_now()
        self.repository.add(record)
        self.repository.commit()
        return self._response(self._require_canvas(str(project_id)))

    def delete_edge(
        self,
        project_id: UUID,
        edge_id: UUID,
        expected_revision: int,
    ) -> ProjectCanvasResponse:
        canvas = self._get_or_create_canvas(str(project_id))
        self._ensure_revision(canvas, expected_revision)
        record = self.repository.get_edge(canvas.id, str(edge_id))
        if record is None:
            raise_canvas_error(ProjectCanvasErrorCode.EDGE_NOT_FOUND, 404)
        canvas.revision += 1
        canvas.updated_at = utc_now()
        self.repository.delete_edge(record)
        self.repository.commit()
        return self._response(self._require_canvas(str(project_id)))

    def preview_existing_entities(self, project_id: UUID) -> CanvasEntityBatchPreview:
        if not self.repository.project_exists(str(project_id)):
            raise_canvas_error(ProjectCanvasErrorCode.PROJECT_NOT_FOUND, 404)
        character_count, scene_count, shot_count = self.repository.entity_counts(str(project_id))
        return CanvasEntityBatchPreview(
            character_count=character_count,
            scene_count=scene_count,
            shot_count=shot_count,
            total=character_count + scene_count + shot_count,
        )

    def add_existing_entities(
        self,
        project_id: UUID,
        payload: CanvasEntityBatchRequest,
    ) -> ProjectCanvasResponse:
        project_id_str = str(project_id)
        canvas = self._get_or_create_canvas(project_id_str)
        self._ensure_revision(canvas, payload.expected_revision)
        characters, scenes, shots = self.repository.list_entities_for_batch(project_id_str)
        existing = {
            (node.entity_type, node.entity_id)
            for node in canvas.nodes
            if node.entity_type and node.entity_id
        }
        next_z = max([node.z_index for node in canvas.nodes], default=0) + 1
        records: list[ProjectCanvasNodeRecord] = []
        if payload.include_characters:
            for index, character in enumerate(characters):
                if ("character", character.id) not in existing:
                    records.append(
                        self._batch_node(
                            canvas.id, "character", character.name, character.id, 0, index, next_z
                        )
                    )
        if payload.include_scenes:
            for index, scene in enumerate(scenes):
                if ("scene", scene.id) not in existing:
                    records.append(
                        self._batch_node(
                            canvas.id, "scene", scene.name, scene.id, 320, index, next_z
                        )
                    )
        if payload.include_shots:
            for index, shot in enumerate(shots):
                if ("shot", shot.id) not in existing:
                    records.append(
                        self._batch_node(canvas.id, "shot", shot.name, shot.id, 640, index, next_z)
                    )
        now = utc_now()
        for record in records:
            self.repository.add(record)
        if records:
            canvas.revision += 1
            canvas.updated_at = now
        self.repository.commit()
        return self._response(self._require_canvas(project_id_str))

    def _get_or_create_canvas(self, project_id: str) -> ProjectCanvasRecord:
        if not self.repository.project_exists(project_id):
            raise_canvas_error(ProjectCanvasErrorCode.PROJECT_NOT_FOUND, 404)
        canvas = self.repository.get_canvas(project_id)
        if canvas is not None:
            return canvas
        now = utc_now()
        canvas = ProjectCanvasRecord(
            id=str(uuid4()),
            project_id=project_id,
            view_mode=CanvasViewMode.WORKFLOW.value,
            viewport_json=CanvasViewport().model_dump_json(),
            layout_version=1,
            revision=1,
            created_at=now,
            updated_at=now,
        )
        self.repository.add(canvas)
        self.repository.commit()
        return self._require_canvas(project_id)

    def _require_canvas(self, project_id: str) -> ProjectCanvasRecord:
        canvas = self.repository.get_canvas(project_id)
        if canvas is None:
            raise_canvas_error(ProjectCanvasErrorCode.CANVAS_NOT_FOUND, 404)
        return canvas

    def _ensure_revision(self, canvas: ProjectCanvasRecord, expected_revision: int) -> None:
        if canvas.revision != expected_revision:
            raise_canvas_error(ProjectCanvasErrorCode.REVISION_CONFLICT, 409)

    def _node_record_from_payload(
        self,
        project_id: str,
        canvas_id: str,
        node: CanvasNodeUpsert,
    ) -> ProjectCanvasNodeRecord:
        entity_type = node.entity_type
        if node.entity_id and entity_type is None and node.node_type.value in ENTITY_NODE_TYPES:
            entity_type = node.node_type.value
        if node.entity_id is None:
            entity_type = None
        if node.node_type == CanvasNodeType.TEXT and node.entity_id is not None:
            raise_canvas_error(ProjectCanvasErrorCode.INVALID_ENTITY, 422)
        if entity_type is not None or node.entity_id is not None:
            if entity_type != node.node_type.value or node.entity_id is None:
                raise_canvas_error(ProjectCanvasErrorCode.INVALID_ENTITY, 422)
            if not self.repository.entity_belongs_to_project(
                project_id, entity_type, node.entity_id
            ):
                raise_canvas_error(ProjectCanvasErrorCode.INVALID_ENTITY, 422)
        now = utc_now()
        return ProjectCanvasNodeRecord(
            id=node.id or str(uuid4()),
            canvas_id=canvas_id,
            node_type=node.node_type.value,
            title=normalize_title(node.title, self._default_title(node.node_type)),
            position_x=node.position_x,
            position_y=node.position_y,
            width=node.width,
            height=node.height,
            z_index=node.z_index,
            entity_type=entity_type,
            entity_id=node.entity_id,
            data_json=node.data.model_dump_json(exclude_none=True),
            created_at=now,
            updated_at=now,
        )

    def _edge_record_from_payload(
        self,
        canvas_id: str,
        edge: CanvasEdgeUpsert,
        node_by_id: dict[str, ProjectCanvasNodeRecord],
    ) -> ProjectCanvasEdgeRecord:
        source = node_by_id.get(edge.source_node_id)
        target = node_by_id.get(edge.target_node_id)
        if source is None or target is None or edge.source_node_id == edge.target_node_id:
            raise_canvas_error(ProjectCanvasErrorCode.INVALID_CONNECTION, 422)
        self._ensure_edge_allowed(source, target, edge.semantic_type, edge.data)
        now = utc_now()
        return ProjectCanvasEdgeRecord(
            id=edge.id or str(uuid4()),
            canvas_id=canvas_id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            source_handle=edge.source_handle,
            target_handle=edge.target_handle,
            semantic_type=edge.semantic_type.value,
            data_json=edge.data.model_dump_json(exclude_none=True),
            created_at=now,
            updated_at=now,
        )

    def _preserved_edge_record_from_existing(
        self,
        canvas_id: str,
        edge: ProjectCanvasEdgeRecord,
        node_by_id: dict[str, ProjectCanvasNodeRecord],
    ) -> ProjectCanvasEdgeRecord:
        semantic_type = CanvasEdgeType(edge.semantic_type)
        data = CanvasEdgeData.model_validate_json(edge.data_json or "{}")
        source = node_by_id[edge.source_node_id]
        target = node_by_id[edge.target_node_id]
        self._ensure_edge_allowed(source, target, semantic_type, data)
        return ProjectCanvasEdgeRecord(
            id=edge.id,
            canvas_id=canvas_id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            source_handle=edge.source_handle,
            target_handle=edge.target_handle,
            semantic_type=edge.semantic_type,
            data_json=edge.data_json,
            created_at=edge.created_at,
            updated_at=edge.updated_at,
        )

    def _ensure_edge_allowed(
        self,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        semantic_type: CanvasEdgeType,
        data: CanvasEdgeData,
    ) -> None:
        if semantic_type == CanvasEdgeType.GENERATED_FROM:
            payload = data.binding_payload or {}
            if (
                (source.node_type, target.node_type) not in {("shot", "image"), ("shot", "video")}
                or data.status != "applied"
                or data.business_entity_type not in SYSTEM_GENERATED_ENTITY_TYPES
                or not data.business_entity_id
                or payload.get("system") is not True
            ):
                raise AppError(
                    code=ProjectCanvasErrorCode.INVALID_CONNECTION.value,
                    message="生成来源关系只能由系统创建和维护。",
                    status_code=422,
                )
            return
        if (source.node_type, target.node_type) not in MANUAL_EDGE_NODE_TYPES.get(
            semantic_type, set()
        ):
            raise AppError(
                code=ProjectCanvasErrorCode.INVALID_CONNECTION.value,
                message="这两类节点目前不能直接连接。",
                status_code=422,
            )

    def _batch_node(
        self,
        canvas_id: str,
        node_type: str,
        title: str,
        entity_id: str,
        x: float,
        index: int,
        z_index: int,
    ) -> ProjectCanvasNodeRecord:
        now = utc_now()
        return ProjectCanvasNodeRecord(
            id=str(uuid4()),
            canvas_id=canvas_id,
            node_type=node_type,
            title=normalize_title(title, node_type),
            position_x=x,
            position_y=float(index * 180),
            width=240,
            height=150,
            z_index=z_index + index,
            entity_type=node_type,
            entity_id=entity_id,
            data_json=CanvasNodeData().model_dump_json(exclude_none=True),
            created_at=now,
            updated_at=now,
        )

    def _response(self, canvas: ProjectCanvasRecord) -> ProjectCanvasResponse:
        return ProjectCanvasResponse(
            id=canvas.id,
            project_id=canvas.project_id,
            view_mode=CanvasViewMode(canvas.view_mode),
            viewport=CanvasViewport.model_validate(json.loads(canvas.viewport_json)),
            layout_version=canvas.layout_version,
            revision=canvas.revision,
            nodes=[
                self._node_response(node)
                for node in sorted(
                    canvas.nodes, key=lambda item: (item.z_index, item.created_at, item.id)
                )
            ],
            edges=[
                self._edge_response(edge)
                for edge in sorted(canvas.edges, key=lambda item: (item.created_at, item.id))
            ],
            created_at=canvas.created_at,
            updated_at=canvas.updated_at,
        )

    def _node_response(self, node: ProjectCanvasNodeRecord) -> CanvasNodeResponse:
        return CanvasNodeResponse(
            id=node.id,
            node_type=CanvasNodeType(node.node_type),
            title=node.title,
            position_x=node.position_x,
            position_y=node.position_y,
            width=node.width,
            height=node.height,
            z_index=node.z_index,
            entity_type=node.entity_type,
            entity_id=node.entity_id,
            data=CanvasNodeData.model_validate(json.loads(node.data_json or "{}")),
            created_at=node.created_at,
            updated_at=node.updated_at,
        )

    def _edge_response(self, edge: ProjectCanvasEdgeRecord) -> CanvasEdgeResponse:
        return CanvasEdgeResponse(
            id=edge.id,
            source_node_id=edge.source_node_id,
            target_node_id=edge.target_node_id,
            source_handle=edge.source_handle,
            target_handle=edge.target_handle,
            semantic_type=CanvasEdgeType(edge.semantic_type),
            data=CanvasEdgeData.model_validate(json.loads(edge.data_json or "{}")),
            created_at=edge.created_at,
            updated_at=edge.updated_at,
        )

    def _default_title(self, node_type: CanvasNodeType) -> str:
        return {
            CanvasNodeType.TEXT: "文本",
            CanvasNodeType.CHARACTER: "角色",
            CanvasNodeType.SCENE: "场景",
            CanvasNodeType.SHOT: "镜头",
            CanvasNodeType.IMAGE: "图片",
            CanvasNodeType.VIDEO: "视频",
            CanvasNodeType.EXPORT: "导出",
        }[node_type]


def raise_canvas_error(code: ProjectCanvasErrorCode, status_code: int) -> None:
    raise AppError(
        code=code.value,
        message=ERROR_MESSAGES[code],
        status_code=status_code,
    )
