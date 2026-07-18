import json
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.api.schemas.canvas_binding import (
    CanvasBindingApplyRequest,
    CanvasBindingDeleteMode,
    CanvasBindingDeleteRequest,
    CanvasBindingEdgeStatus,
    CanvasBindingPayload,
    CanvasBindingPreviewRequest,
    CanvasBindingPreviewResponse,
)
from app.api.schemas.project_canvas import CanvasEdgeData, ProjectCanvasResponse
from app.core.errors import AppError
from app.domain.media_asset import MediaType
from app.domain.project_canvas import CanvasEdgeType, ProjectCanvasErrorCode, utc_now
from app.domain.shot import CharacterReferencePurpose, MediaReferencePurpose, SceneReferencePurpose
from app.domain.video_generation import VIDEO_INPUT_ROLE_ORDER, VideoInputRole
from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.project_canvas import (
    ProjectCanvasEdgeRecord,
    ProjectCanvasNodeRecord,
    ProjectCanvasRecord,
)
from app.infrastructure.models.scene import SceneRecord, SceneReferenceRecord, SceneStateRecord
from app.infrastructure.models.shot import ShotCharacterRecord, ShotRecord, ShotReferenceRecord
from app.infrastructure.models.video_generation import (
    VideoGenerationTaskInputRecord,
    VideoGenerationTaskRecord,
)
from app.service.project_canvas_service import ProjectCanvasService

SUPPORTED_MANUAL_CONNECTIONS: dict[CanvasEdgeType, set[tuple[str, str]]] = {
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


class CanvasBindingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def preview_binding(
        self, project_id: UUID, payload: CanvasBindingPreviewRequest
    ) -> CanvasBindingPreviewResponse:
        canvas, source, target = self._load_canvas_and_nodes(
            str(project_id), payload.source_node_id, payload.target_node_id
        )
        del canvas
        is_supported = self._is_supported_connection(source, target, payload.semantic_type)
        required: list[str] = []
        warnings: list[str] = []
        can_apply = is_supported
        summary = "确认后会把该画布关系应用到真实业务数据。"
        if not is_supported:
            warnings.append(self._invalid_connection_message(payload.semantic_type))
            summary = self._invalid_connection_message(payload.semantic_type)
        elif payload.semantic_type == CanvasEdgeType.USES_CHARACTER:
            required = ["look_id"]
            summary = "确认后会把角色加入镜头，或更新已有镜头角色。"
        elif payload.semantic_type == CanvasEdgeType.USES_SCENE:
            summary = "确认后会更新镜头场景；如替换已有场景，需要显式确认。"
        elif payload.semantic_type == CanvasEdgeType.SHOT_REFERENCE:
            summary = "确认后会把该图片设为镜头参考图。"
        elif payload.semantic_type in {
            CanvasEdgeType.IDENTITY_REFERENCE,
            CanvasEdgeType.LOOK_REFERENCE,
            CanvasEdgeType.POSE_REFERENCE,
            CanvasEdgeType.SCENE_REFERENCE,
        }:
            if payload.semantic_type == CanvasEdgeType.SCENE_REFERENCE:
                required = ["scene_reference_id 或可解析的场景参考图"]
            else:
                required = ["character_reference_id 或可解析的人物参考图", "shot_character_id"]
            summary = "确认后会创建镜头参考图绑定。普通媒体图只能保留为画布草稿关系。"
        elif payload.semantic_type in {CanvasEdgeType.START_FRAME, CanvasEdgeType.END_FRAME}:
            required = ["video_task_id"]
            summary = "确认后会把图片写入视频任务的起始帧或结束帧输入。"
        elif payload.semantic_type == CanvasEdgeType.CONTINUITY_FROM:
            warnings.append("连续性关系当前仅保存为已确认的画布关系，不创建生成任务。")
            summary = "确认后会记录该素材作为当前镜头的连续性参考。"
        elif payload.semantic_type == CanvasEdgeType.INCLUDED_IN_EXPORT:
            warnings.append("成片导出快照不可被画布直接修改；该关系仅标记为成片候选。")
            summary = "确认后会记录为成片候选关系。"
        elif payload.semantic_type == CanvasEdgeType.GENERATED_FROM:
            can_apply = False
            warnings.append("生成来源关系只能由系统写入，不能手动创建。")
        else:
            can_apply = False

        return CanvasBindingPreviewResponse(
            semantic_type=payload.semantic_type,
            can_apply=can_apply,
            title=self._title_for(payload.semantic_type),
            summary=summary,
            warnings=warnings,
            required_fields=required,
        )

    def apply_binding(
        self, project_id: UUID, payload: CanvasBindingApplyRequest
    ) -> ProjectCanvasResponse:
        project_id_str = str(project_id)
        canvas, source, target = self._load_canvas_and_nodes(
            project_id_str, payload.source_node_id, payload.target_node_id
        )
        self._ensure_revision(canvas, payload.expected_revision)
        self._ensure_supported_connection(source, target, payload.semantic_type)
        now = utc_now()
        edge = self._get_or_create_edge(canvas, payload, now)
        try:
            if payload.apply_business:
                business_type, business_id = self._apply_business(
                    project_id_str, source, target, payload.semantic_type, payload.payload
                )
                edge.data_json = CanvasEdgeData(
                    note=payload.payload.notes,
                    status=CanvasBindingEdgeStatus.APPLIED.value,
                    business_entity_type=business_type,
                    business_entity_id=business_id,
                    applied_at=now,
                    binding_payload=payload.payload.model_dump(exclude_none=True),
                ).model_dump_json(exclude_none=True)
            else:
                edge.data_json = CanvasEdgeData(
                    note=payload.payload.notes,
                    status=CanvasBindingEdgeStatus.DRAFT.value,
                    binding_payload=payload.payload.model_dump(exclude_none=True),
                ).model_dump_json(exclude_none=True)
            edge.updated_at = now
            canvas.revision += 1
            canvas.updated_at = now
            self.session.commit()
        except AppError:
            self.session.rollback()
            self._mark_edge_failed(project_id_str, canvas.id, edge.id, payload, now)
        except SQLAlchemyError:
            self.session.rollback()
            self._mark_edge_failed(project_id_str, canvas.id, edge.id, payload, now)
        return ProjectCanvasService(self.session).get_canvas(project_id)

    def delete_binding(
        self, project_id: UUID, edge_id: UUID, payload: CanvasBindingDeleteRequest
    ) -> ProjectCanvasResponse:
        project_id_str = str(project_id)
        canvas = self._get_canvas(project_id_str)
        self._ensure_revision(canvas, payload.expected_revision)
        edge = self._get_edge(canvas.id, str(edge_id))
        data = self._edge_data(edge)
        if (
            edge.semantic_type == CanvasEdgeType.GENERATED_FROM.value
            and payload.mode == CanvasBindingDeleteMode.UNBIND_BUSINESS
        ):
            self._raise(
                "CANVAS_GENERATED_FROM_READ_ONLY",
                "生成来源关系只能隐藏显示，不能解除真实业务来源。",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if payload.mode == CanvasBindingDeleteMode.UNBIND_BUSINESS:
            self._unbind_business(data)
        self.session.delete(edge)
        canvas.revision += 1
        canvas.updated_at = utc_now()
        self.session.commit()
        return ProjectCanvasService(self.session).get_canvas(project_id)

    def import_business_relations_preview(self, project_id: UUID) -> dict[str, int]:
        project_id_str = str(project_id)
        canvas = self._get_canvas(project_id_str)
        shot_ids = [
            node.entity_id for node in canvas.nodes if node.node_type == "shot" and node.entity_id
        ]
        existing = self._existing_edge_keys(canvas)
        character_edges = 0
        scene_edges = 0
        reference_edges = 0
        if shot_ids:
            character_edges = self._count_importable_character_edges(shot_ids, existing)
            scene_edges = self._count_importable_scene_edges(project_id_str, shot_ids, existing)
            reference_edges = self._count_importable_reference_edges(shot_ids, existing)
        return {
            "character_edges": character_edges,
            "scene_edges": scene_edges,
            "reference_edges": reference_edges,
            "total_edges": character_edges + scene_edges + reference_edges,
        }

    def import_business_relations(
        self, project_id: UUID, expected_revision: int
    ) -> ProjectCanvasResponse:
        project_id_str = str(project_id)
        canvas = self._get_canvas(project_id_str)
        self._ensure_revision(canvas, expected_revision)
        node_by_entity = {
            (node.entity_type, node.entity_id): node
            for node in canvas.nodes
            if node.entity_type and node.entity_id
        }
        existing = self._existing_edge_keys(canvas)
        now = utc_now()
        added = 0
        for shot_character in self.session.scalars(
            select(ShotCharacterRecord)
            .join(ShotRecord)
            .where(ShotRecord.project_id == project_id_str)
        ):
            source = node_by_entity.get(("character", shot_character.character_id))
            target = node_by_entity.get(("shot", shot_character.shot_id))
            added += self._add_imported_edge(
                canvas,
                source,
                target,
                CanvasEdgeType.USES_CHARACTER,
                shot_character.id,
                existing,
                now,
            )
        for shot in self.session.scalars(
            select(ShotRecord).where(ShotRecord.project_id == project_id_str)
        ):
            if not shot.scene_id:
                continue
            source = node_by_entity.get(("scene", shot.scene_id))
            target = node_by_entity.get(("shot", shot.id))
            added += self._add_imported_edge(
                canvas, source, target, CanvasEdgeType.USES_SCENE, shot.id, existing, now
            )
        for reference in self.session.scalars(
            select(ShotReferenceRecord)
            .join(ShotRecord)
            .where(ShotRecord.project_id == project_id_str)
        ):
            reference_id = (
                reference.character_reference_id
                or reference.scene_reference_id
                or reference.media_asset_id
            )
            source = self._node_for_reference_media(node_by_entity, reference)
            target = node_by_entity.get(("shot", reference.shot_id))
            semantic = self._semantic_from_reference(reference)
            added += self._add_imported_edge(
                canvas,
                source,
                target,
                semantic,
                reference.id if reference_id else None,
                existing,
                now,
            )
        if added:
            canvas.revision += 1
            canvas.updated_at = now
        self.session.commit()
        return ProjectCanvasService(self.session).get_canvas(project_id)

    def _is_supported_connection(
        self,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        semantic_type: CanvasEdgeType,
    ) -> bool:
        if semantic_type == CanvasEdgeType.GENERATED_FROM:
            return False
        if source.id == target.id:
            return False
        return (source.node_type, target.node_type) in SUPPORTED_MANUAL_CONNECTIONS.get(
            semantic_type, set()
        )

    def _ensure_supported_connection(
        self,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        semantic_type: CanvasEdgeType,
    ) -> None:
        if not self._is_supported_connection(source, target, semantic_type):
            self._raise(
                "CANVAS_BINDING_INVALID_CONNECTION",
                self._invalid_connection_message(semantic_type),
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

    @staticmethod
    def _invalid_connection_message(semantic_type: CanvasEdgeType) -> str:
        if semantic_type == CanvasEdgeType.GENERATED_FROM:
            return "生成来源关系只能由系统建立。"
        return "这两类节点目前不能直接连接。"

    def _apply_business(
        self,
        project_id: str,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        semantic_type: CanvasEdgeType,
        payload: CanvasBindingPayload,
    ) -> tuple[str, str]:
        if semantic_type == CanvasEdgeType.USES_CHARACTER:
            return "shot_character", self._bind_character(project_id, source, target, payload)
        if semantic_type == CanvasEdgeType.USES_SCENE:
            return "shot_scene_binding", self._bind_scene(project_id, source, target, payload)
        if semantic_type in {
            CanvasEdgeType.SHOT_REFERENCE,
            CanvasEdgeType.IDENTITY_REFERENCE,
            CanvasEdgeType.LOOK_REFERENCE,
            CanvasEdgeType.POSE_REFERENCE,
            CanvasEdgeType.SCENE_REFERENCE,
        }:
            return "shot_reference", self._bind_shot_reference(
                project_id, source, target, semantic_type, payload
            )
        if semantic_type in {CanvasEdgeType.START_FRAME, CanvasEdgeType.END_FRAME}:
            return "video_task_input", self._bind_video_input(
                project_id, source, target, semantic_type, payload
            )
        if semantic_type == CanvasEdgeType.CONTINUITY_FROM:
            return "canvas_continuity_reference", target.entity_id or target.id
        if semantic_type == CanvasEdgeType.INCLUDED_IN_EXPORT:
            return "canvas_export_candidate", target.entity_id or target.id
        self._raise(
            "CANVAS_BINDING_NOT_ALLOWED",
            "该连线类型不能手动应用。",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    def _bind_character(
        self,
        project_id: str,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        payload: CanvasBindingPayload,
    ) -> str:
        if (
            source.node_type != "character"
            or target.node_type != "shot"
            or not source.entity_id
            or not target.entity_id
        ):
            self._raise("CANVAS_BINDING_INVALID_CONNECTION", "角色只能绑定到镜头节点。", 422)
        shot = self._get_project_shot(project_id, target.entity_id)
        character = self._get_project_character(project_id, source.entity_id)
        look_id = self._validate_look(character.id, payload.look_id)
        record = self.session.scalars(
            select(ShotCharacterRecord).where(
                ShotCharacterRecord.shot_id == shot.id,
                ShotCharacterRecord.character_id == character.id,
            )
        ).first()
        now = utc_now()
        if record is None:
            order_index = (
                int(
                    self.session.scalar(
                        select(func.count())
                        .select_from(ShotCharacterRecord)
                        .where(ShotCharacterRecord.shot_id == shot.id)
                    )
                    or 0
                )
                + 1
            )
            record = ShotCharacterRecord(
                id=str(uuid4()),
                shot_id=shot.id,
                character_id=character.id,
                look_id=look_id,
                action_description=self._clean(payload.action_description),
                expression_description=self._clean(payload.expression_description),
                position_description=self._clean(payload.position_description),
                is_primary_subject=bool(payload.is_primary_subject),
                order_index=order_index,
                notes=self._clean(payload.notes),
                created_at=now,
                updated_at=now,
            )
            self.session.add(record)
        else:
            record.look_id = look_id
            if payload.action_description is not None:
                record.action_description = self._clean(payload.action_description)
            if payload.expression_description is not None:
                record.expression_description = self._clean(payload.expression_description)
            if payload.position_description is not None:
                record.position_description = self._clean(payload.position_description)
            if payload.is_primary_subject is not None:
                record.is_primary_subject = payload.is_primary_subject
            if payload.notes is not None:
                record.notes = self._clean(payload.notes)
            record.updated_at = now
        shot.updated_at = now
        self.session.flush()
        return record.id

    def _bind_scene(
        self,
        project_id: str,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        payload: CanvasBindingPayload,
    ) -> str:
        if (
            source.node_type != "scene"
            or target.node_type != "shot"
            or not source.entity_id
            or not target.entity_id
        ):
            self._raise("CANVAS_BINDING_INVALID_CONNECTION", "场景只能绑定到镜头节点。", 422)
        scene = self._get_project_scene(project_id, source.entity_id)
        shot = self._get_project_shot(project_id, target.entity_id)
        if shot.scene_id and shot.scene_id != scene.id and not payload.replace_existing_scene:
            self._raise(
                "CANVAS_SCENE_REPLACE_CONFIRM_REQUIRED", "镜头已有场景，请确认后再替换。", 409
            )
        state_id = payload.scene_state_id
        if state_id:
            state = self.session.scalars(
                select(SceneStateRecord).where(
                    SceneStateRecord.id == state_id,
                    SceneStateRecord.scene_id == scene.id,
                )
            ).first()
            if state is None:
                self._raise("CANVAS_SCENE_STATE_MISMATCH", "场景状态不属于所选场景。", 422)
        scene_changed = shot.scene_id != scene.id
        shot.scene_id = scene.id
        shot.scene_state_id = state_id
        shot.updated_at = utc_now()
        if scene_changed:
            for reference in self.session.scalars(
                select(ShotReferenceRecord).where(
                    ShotReferenceRecord.shot_id == shot.id,
                    ShotReferenceRecord.reference_type == "scene",
                )
            ):
                self.session.delete(reference)
        return shot.id

    def _bind_shot_reference(
        self,
        project_id: str,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        semantic_type: CanvasEdgeType,
        payload: CanvasBindingPayload,
    ) -> str:
        if (
            source.node_type != "image"
            or target.node_type != "shot"
            or not source.entity_id
            or not target.entity_id
        ):
            self._raise("CANVAS_BINDING_INVALID_CONNECTION", "图片参考只能绑定到镜头节点。", 422)
        shot = self._get_project_shot(project_id, target.entity_id)
        media = self._get_project_media(project_id, source.entity_id)
        if media.media_type != MediaType.IMAGE.value:
            self._raise("CANVAS_MEDIA_TYPE_INVALID", "参考图必须是图片素材。", 422)
        if semantic_type == CanvasEdgeType.SHOT_REFERENCE:
            return self._create_or_get_shot_reference(
                shot.id,
                "media",
                None,
                None,
                media.id,
                None,
                MediaReferencePurpose.GENERAL.value,
                payload.notes,
            )
        if semantic_type == CanvasEdgeType.SCENE_REFERENCE:
            reference = self._scene_reference_from_payload(project_id, media.id, payload)
            if shot.scene_state_id is None or reference.state_id != shot.scene_state_id:
                self._raise(
                    "CANVAS_SCENE_REFERENCE_MISMATCH", "场景参考图必须属于镜头当前场景状态。", 422
                )
            purpose = self._scene_reference_purpose(payload.purpose)
            return self._create_or_get_shot_reference(
                shot.id, "scene", None, reference.id, None, None, purpose, payload.notes
            )
        reference = self._character_reference_from_payload(project_id, media.id, payload)
        shot_character_id = payload.shot_character_id or self._matching_shot_character_id(
            shot.id, reference
        )
        if shot_character_id is None:
            self._raise("CANVAS_SHOT_CHARACTER_REQUIRED", "请先选择该参考图对应的镜头角色。", 422)
        purpose = self._character_reference_purpose(semantic_type, payload.purpose)
        return self._create_or_get_shot_reference(
            shot.id,
            "character",
            reference.id,
            None,
            None,
            shot_character_id,
            purpose,
            payload.notes,
        )

    def _bind_video_input(
        self,
        project_id: str,
        source: ProjectCanvasNodeRecord,
        target: ProjectCanvasNodeRecord,
        semantic_type: CanvasEdgeType,
        payload: CanvasBindingPayload,
    ) -> str:
        if source.node_type != "image" or not source.entity_id:
            self._raise("CANVAS_BINDING_INVALID_CONNECTION", "视频输入必须来自图片节点。", 422)
        if target.node_type == "video":
            self._raise("CANVAS_VIDEO_NODE_NOT_TASK", "该节点是视频素材，不是视频生成任务。", 422)
        media = self._get_project_media(project_id, source.entity_id)
        if media.media_type != MediaType.IMAGE.value:
            self._raise("CANVAS_MEDIA_TYPE_INVALID", "视频输入必须是图片素材。", 422)
        if not payload.video_task_id:
            self._raise("CANVAS_VIDEO_TASK_REQUIRED", "请选择目标视频生成任务。", 422)
        task = self.session.scalars(
            select(VideoGenerationTaskRecord).where(
                VideoGenerationTaskRecord.project_id == project_id,
                VideoGenerationTaskRecord.id == payload.video_task_id,
            )
        ).first()
        if task is None:
            self._raise("CANVAS_VIDEO_TASK_NOT_FOUND", "视频生成任务不存在或不属于当前项目。", 404)
        if target.node_type == "shot" and target.entity_id and task.shot_id != target.entity_id:
            self._raise("CANVAS_VIDEO_TASK_SHOT_MISMATCH", "视频生成任务不属于目标镜头。", 422)
        role = (
            VideoInputRole.START_FRAME
            if semantic_type == CanvasEdgeType.START_FRAME
            else VideoInputRole.END_FRAME
        )
        now = utc_now()
        record = self.session.scalars(
            select(VideoGenerationTaskInputRecord).where(
                VideoGenerationTaskInputRecord.task_id == task.id,
                VideoGenerationTaskInputRecord.role == role.value,
            )
        ).first()
        if record is None:
            record = VideoGenerationTaskInputRecord(
                id=str(uuid4()),
                project_id=project_id,
                task_id=task.id,
                role=role.value,
                media_asset_id=media.id,
                source_keyframe_output_id=None,
                source_keyframe_task_id=None,
                sort_order=VIDEO_INPUT_ROLE_ORDER[role.value],
                created_at=now,
                updated_at=now,
            )
            self.session.add(record)
        else:
            record.media_asset_id = media.id
            record.source_keyframe_output_id = None
            record.source_keyframe_task_id = None
            record.updated_at = now
        if role == VideoInputRole.START_FRAME:
            task.input_media_asset_id = media.id
            task.source_keyframe_output_id = None
            task.source_keyframe_task_id = None
        task.status = "draft"
        task.updated_at = now
        self.session.flush()
        return record.id

    def _create_or_get_shot_reference(
        self,
        shot_id: str,
        reference_type: str,
        character_reference_id: str | None,
        scene_reference_id: str | None,
        media_asset_id: str | None,
        shot_character_id: str | None,
        purpose: str,
        notes: str | None,
    ) -> str:
        duplicate = self.session.scalars(
            select(ShotReferenceRecord).where(
                ShotReferenceRecord.shot_id == shot_id,
                ShotReferenceRecord.reference_type == reference_type,
                ShotReferenceRecord.character_reference_id == character_reference_id,
                ShotReferenceRecord.scene_reference_id == scene_reference_id,
                ShotReferenceRecord.media_asset_id == media_asset_id,
                ShotReferenceRecord.purpose == purpose,
                ShotReferenceRecord.shot_character_id == shot_character_id,
            )
        ).first()
        if duplicate:
            return duplicate.id
        order_index = (
            int(
                self.session.scalar(
                    select(func.count())
                    .select_from(ShotReferenceRecord)
                    .where(ShotReferenceRecord.shot_id == shot_id)
                )
                or 0
            )
            + 1
        )
        now = utc_now()
        record = ShotReferenceRecord(
            id=str(uuid4()),
            shot_id=shot_id,
            reference_type=reference_type,
            character_reference_id=character_reference_id,
            scene_reference_id=scene_reference_id,
            media_asset_id=media_asset_id,
            shot_character_id=shot_character_id,
            purpose=purpose,
            order_index=order_index,
            notes=self._clean(notes),
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        self.session.flush()
        return record.id

    def _unbind_business(self, data: CanvasEdgeData) -> None:
        if not data.business_entity_type or not data.business_entity_id:
            return
        if data.business_entity_type == "shot_character":
            record = self.session.get(ShotCharacterRecord, data.business_entity_id)
            if record:
                self.session.delete(record)
        elif data.business_entity_type == "shot_reference":
            record = self.session.get(ShotReferenceRecord, data.business_entity_id)
            if record:
                self.session.delete(record)
        elif data.business_entity_type == "video_task_input":
            record = self.session.get(VideoGenerationTaskInputRecord, data.business_entity_id)
            if record:
                self.session.delete(record)
        elif data.business_entity_type == "shot_scene_binding":
            shot = self.session.get(ShotRecord, data.business_entity_id)
            if shot:
                shot.scene_id = None
                shot.scene_state_id = None
                shot.updated_at = utc_now()

    def _get_or_create_edge(
        self,
        canvas: ProjectCanvasRecord,
        payload: CanvasBindingApplyRequest,
        now,
    ) -> ProjectCanvasEdgeRecord:
        if payload.edge_id:
            edge = self._get_edge(canvas.id, payload.edge_id)
            edge.source_node_id = payload.source_node_id
            edge.target_node_id = payload.target_node_id
            edge.semantic_type = payload.semantic_type.value
            return edge
        existing = self.session.scalars(
            select(ProjectCanvasEdgeRecord).where(
                ProjectCanvasEdgeRecord.canvas_id == canvas.id,
                ProjectCanvasEdgeRecord.source_node_id == payload.source_node_id,
                ProjectCanvasEdgeRecord.target_node_id == payload.target_node_id,
                ProjectCanvasEdgeRecord.semantic_type == payload.semantic_type.value,
            )
        ).first()
        if existing is not None:
            return existing
        edge = ProjectCanvasEdgeRecord(
            id=str(uuid4()),
            canvas_id=canvas.id,
            source_node_id=payload.source_node_id,
            target_node_id=payload.target_node_id,
            source_handle=None,
            target_handle=None,
            semantic_type=payload.semantic_type.value,
            data_json="{}",
            created_at=now,
            updated_at=now,
        )
        self.session.add(edge)
        return edge

    def _mark_edge_failed(
        self,
        project_id: str,
        canvas_id: str,
        edge_id: str,
        payload: CanvasBindingApplyRequest,
        now,
    ) -> None:
        canvas = self._get_canvas(project_id)
        edge = self.session.get(ProjectCanvasEdgeRecord, edge_id)
        if edge is None:
            edge = ProjectCanvasEdgeRecord(
                id=edge_id,
                canvas_id=canvas_id,
                source_node_id=payload.source_node_id,
                target_node_id=payload.target_node_id,
                source_handle=None,
                target_handle=None,
                semantic_type=payload.semantic_type.value,
                data_json="{}",
                created_at=now,
                updated_at=now,
            )
            self.session.add(edge)
        edge.data_json = CanvasEdgeData(
            status=CanvasBindingEdgeStatus.FAILED.value,
            error_message="绑定失败，请检查节点和选项后重试。",
            binding_payload=payload.payload.model_dump(exclude_none=True),
        ).model_dump_json(exclude_none=True)
        edge.updated_at = now
        canvas.revision += 1
        canvas.updated_at = now
        self.session.commit()

    def _load_canvas_and_nodes(
        self, project_id: str, source_node_id: str, target_node_id: str
    ) -> tuple[ProjectCanvasRecord, ProjectCanvasNodeRecord, ProjectCanvasNodeRecord]:
        canvas = self._get_canvas(project_id)
        source = self._get_node(canvas.id, source_node_id)
        target = self._get_node(canvas.id, target_node_id)
        return canvas, source, target

    def _get_canvas(self, project_id: str) -> ProjectCanvasRecord:
        canvas = self.session.scalars(
            select(ProjectCanvasRecord).where(ProjectCanvasRecord.project_id == project_id)
        ).first()
        if canvas is None:
            self._raise(ProjectCanvasErrorCode.CANVAS_NOT_FOUND.value, "项目画布不存在。", 404)
        return canvas

    def _get_node(self, canvas_id: str, node_id: str) -> ProjectCanvasNodeRecord:
        node = self.session.scalars(
            select(ProjectCanvasNodeRecord).where(
                ProjectCanvasNodeRecord.canvas_id == canvas_id,
                ProjectCanvasNodeRecord.id == node_id,
            )
        ).first()
        if node is None:
            self._raise(ProjectCanvasErrorCode.NODE_NOT_FOUND.value, "画布节点不存在。", 404)
        return node

    def _get_edge(self, canvas_id: str, edge_id: str) -> ProjectCanvasEdgeRecord:
        edge = self.session.scalars(
            select(ProjectCanvasEdgeRecord).where(
                ProjectCanvasEdgeRecord.canvas_id == canvas_id,
                ProjectCanvasEdgeRecord.id == edge_id,
            )
        ).first()
        if edge is None:
            self._raise(ProjectCanvasErrorCode.EDGE_NOT_FOUND.value, "画布连线不存在。", 404)
        return edge

    def _ensure_revision(self, canvas: ProjectCanvasRecord, expected_revision: int) -> None:
        if canvas.revision != expected_revision:
            self._raise(
                ProjectCanvasErrorCode.REVISION_CONFLICT.value, "画布已经更新，请刷新后重试。", 409
            )

    def _get_project_character(self, project_id: str, character_id: str) -> CharacterRecord:
        record = self.session.scalars(
            select(CharacterRecord).where(
                CharacterRecord.project_id == project_id,
                CharacterRecord.id == character_id,
            )
        ).first()
        if record is None:
            self._raise("CANVAS_CHARACTER_NOT_FOUND", "角色不存在或不属于当前项目。", 404)
        return record

    def _get_project_scene(self, project_id: str, scene_id: str) -> SceneRecord:
        record = self.session.scalars(
            select(SceneRecord).where(
                SceneRecord.project_id == project_id, SceneRecord.id == scene_id
            )
        ).first()
        if record is None:
            self._raise("CANVAS_SCENE_NOT_FOUND", "场景不存在或不属于当前项目。", 404)
        return record

    def _get_project_shot(self, project_id: str, shot_id: str) -> ShotRecord:
        record = self.session.scalars(
            select(ShotRecord).where(ShotRecord.project_id == project_id, ShotRecord.id == shot_id)
        ).first()
        if record is None:
            self._raise("CANVAS_SHOT_NOT_FOUND", "镜头不存在或不属于当前项目。", 404)
        return record

    def _get_project_media(self, project_id: str, media_asset_id: str) -> MediaAssetRecord:
        record = self.session.scalars(
            select(MediaAssetRecord).where(
                MediaAssetRecord.project_id == project_id,
                MediaAssetRecord.id == media_asset_id,
            )
        ).first()
        if record is None:
            self._raise("CANVAS_MEDIA_NOT_FOUND", "媒体素材不存在或不属于当前项目。", 404)
        return record

    def _validate_look(self, character_id: str, look_id: str | None) -> str | None:
        if not look_id:
            return None
        look = self.session.scalars(
            select(CharacterLookRecord).where(
                CharacterLookRecord.id == look_id,
                CharacterLookRecord.character_id == character_id,
            )
        ).first()
        if look is None:
            self._raise("CANVAS_LOOK_MISMATCH", "造型不属于该角色。", 422)
        return look.id

    def _character_reference_from_payload(
        self, project_id: str, media_asset_id: str, payload: CanvasBindingPayload
    ) -> CharacterReferenceRecord:
        statement = (
            select(CharacterReferenceRecord)
            .join(CharacterLookRecord)
            .join(CharacterRecord)
            .where(CharacterRecord.project_id == project_id)
            .options(joinedload(CharacterReferenceRecord.look))
        )
        if payload.character_reference_id:
            statement = statement.where(
                CharacterReferenceRecord.id == payload.character_reference_id
            )
        else:
            statement = statement.where(CharacterReferenceRecord.media_asset_id == media_asset_id)
        reference = self.session.scalars(statement).first()
        if reference is None:
            self._raise(
                "CANVAS_CHARACTER_REFERENCE_NOT_FOUND", "该图片不是可绑定的人物参考图。", 404
            )
        return reference

    def _scene_reference_from_payload(
        self, project_id: str, media_asset_id: str, payload: CanvasBindingPayload
    ) -> SceneReferenceRecord:
        statement = (
            select(SceneReferenceRecord)
            .join(SceneStateRecord)
            .join(SceneRecord)
            .where(SceneRecord.project_id == project_id)
        )
        if payload.scene_reference_id:
            statement = statement.where(SceneReferenceRecord.id == payload.scene_reference_id)
        else:
            statement = statement.where(SceneReferenceRecord.media_asset_id == media_asset_id)
        reference = self.session.scalars(statement).first()
        if reference is None:
            self._raise("CANVAS_SCENE_REFERENCE_NOT_FOUND", "该图片不是可绑定的场景参考图。", 404)
        return reference

    def _matching_shot_character_id(
        self, shot_id: str, reference: CharacterReferenceRecord
    ) -> str | None:
        record = self.session.scalars(
            select(ShotCharacterRecord).where(
                ShotCharacterRecord.shot_id == shot_id,
                ShotCharacterRecord.character_id == reference.look.character_id,
            )
        ).first()
        return record.id if record else None

    def _character_reference_purpose(
        self, semantic_type: CanvasEdgeType, purpose: str | None
    ) -> str:
        if purpose:
            try:
                return CharacterReferencePurpose(purpose).value
            except ValueError:
                self._raise("CANVAS_REFERENCE_PURPOSE_INVALID", "人物参考图用途无效。", 422)
        return {
            CanvasEdgeType.IDENTITY_REFERENCE: CharacterReferencePurpose.IDENTITY.value,
            CanvasEdgeType.LOOK_REFERENCE: CharacterReferencePurpose.APPEARANCE.value,
            CanvasEdgeType.POSE_REFERENCE: CharacterReferencePurpose.POSE.value,
        }.get(semantic_type, CharacterReferencePurpose.GENERAL.value)

    def _scene_reference_purpose(self, purpose: str | None) -> str:
        if purpose:
            try:
                return SceneReferencePurpose(purpose).value
            except ValueError:
                self._raise("CANVAS_REFERENCE_PURPOSE_INVALID", "场景参考图用途无效。", 422)
        return SceneReferencePurpose.ENVIRONMENT.value

    def _edge_data(self, edge: ProjectCanvasEdgeRecord) -> CanvasEdgeData:
        return CanvasEdgeData.model_validate(json.loads(edge.data_json or "{}"))

    def _existing_edge_keys(self, canvas: ProjectCanvasRecord) -> set[tuple[str, str, str]]:
        return {
            (edge.source_node_id, edge.target_node_id, edge.semantic_type) for edge in canvas.edges
        }

    def _count_importable_character_edges(
        self, shot_ids: list[str], existing: set[tuple[str, str, str]]
    ) -> int:
        del existing
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(ShotCharacterRecord)
                .where(ShotCharacterRecord.shot_id.in_(shot_ids))
            )
            or 0
        )

    def _count_importable_scene_edges(
        self, project_id: str, shot_ids: list[str], existing: set[tuple[str, str, str]]
    ) -> int:
        del existing
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(ShotRecord)
                .where(
                    ShotRecord.project_id == project_id,
                    ShotRecord.id.in_(shot_ids),
                    ShotRecord.scene_id.is_not(None),
                )
            )
            or 0
        )

    def _count_importable_reference_edges(
        self, shot_ids: list[str], existing: set[tuple[str, str, str]]
    ) -> int:
        del existing
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(ShotReferenceRecord)
                .where(ShotReferenceRecord.shot_id.in_(shot_ids))
            )
            or 0
        )

    def _add_imported_edge(
        self,
        canvas: ProjectCanvasRecord,
        source: ProjectCanvasNodeRecord | None,
        target: ProjectCanvasNodeRecord | None,
        semantic_type: CanvasEdgeType,
        business_id: str | None,
        existing: set[tuple[str, str, str]],
        now,
    ) -> int:
        if source is None or target is None or business_id is None:
            return 0
        key = (source.id, target.id, semantic_type.value)
        if key in existing:
            return 0
        self.session.add(
            ProjectCanvasEdgeRecord(
                id=str(uuid4()),
                canvas_id=canvas.id,
                source_node_id=source.id,
                target_node_id=target.id,
                source_handle=None,
                target_handle=None,
                semantic_type=semantic_type.value,
                data_json=CanvasEdgeData(
                    status=CanvasBindingEdgeStatus.APPLIED.value,
                    business_entity_id=business_id,
                    applied_at=now,
                ).model_dump_json(exclude_none=True),
                created_at=now,
                updated_at=now,
            )
        )
        existing.add(key)
        return 1

    def _node_for_reference_media(
        self,
        node_by_entity: dict[tuple[str | None, str | None], ProjectCanvasNodeRecord],
        reference: ShotReferenceRecord,
    ) -> ProjectCanvasNodeRecord | None:
        media_id: str | None = None
        if reference.character_reference_id:
            character_ref = self.session.get(
                CharacterReferenceRecord, reference.character_reference_id
            )
            media_id = character_ref.media_asset_id if character_ref else None
        if reference.scene_reference_id:
            scene_ref = self.session.get(SceneReferenceRecord, reference.scene_reference_id)
            media_id = scene_ref.media_asset_id if scene_ref else None
        if reference.media_asset_id:
            media_id = reference.media_asset_id
        return node_by_entity.get(("image", media_id))

    def _semantic_from_reference(self, reference: ShotReferenceRecord) -> CanvasEdgeType:
        if reference.reference_type == "media":
            return CanvasEdgeType.SHOT_REFERENCE
        if reference.reference_type == "scene":
            return CanvasEdgeType.SCENE_REFERENCE
        if reference.purpose == CharacterReferencePurpose.IDENTITY.value:
            return CanvasEdgeType.IDENTITY_REFERENCE
        if reference.purpose == CharacterReferencePurpose.POSE.value:
            return CanvasEdgeType.POSE_REFERENCE
        return CanvasEdgeType.LOOK_REFERENCE

    @staticmethod
    def _clean(value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @staticmethod
    def _title_for(semantic_type: CanvasEdgeType) -> str:
        return {
            CanvasEdgeType.USES_CHARACTER: "绑定角色到镜头",
            CanvasEdgeType.USES_SCENE: "绑定场景到镜头",
            CanvasEdgeType.SHOT_REFERENCE: "设为镜头参考图",
            CanvasEdgeType.IDENTITY_REFERENCE: "绑定身份参考图",
            CanvasEdgeType.LOOK_REFERENCE: "绑定造型参考图",
            CanvasEdgeType.SCENE_REFERENCE: "绑定场景参考图",
            CanvasEdgeType.POSE_REFERENCE: "绑定姿态参考图",
            CanvasEdgeType.START_FRAME: "设置起始帧",
            CanvasEdgeType.END_FRAME: "设置结束帧",
            CanvasEdgeType.CONTINUITY_FROM: "设置连续性参考",
            CanvasEdgeType.GENERATED_FROM: "生成来源",
            CanvasEdgeType.INCLUDED_IN_EXPORT: "加入成片候选",
        }[semantic_type]

    @staticmethod
    def _raise(code: str, message: str, status_code: int) -> None:
        raise AppError(code=code, message=message, status_code=status_code)
