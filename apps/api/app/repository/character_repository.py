from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.models.character import (
    CharacterLookRecord,
    CharacterRecord,
    CharacterReferenceRecord,
    MediaAssetRecord,
)
from app.infrastructure.models.project import ProjectRecord


class CharacterRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def project_exists(self, project_id: str) -> bool:
        return self.session.get(ProjectRecord, project_id) is not None

    def list_characters(self, project_id: str) -> tuple[list[CharacterRecord], int]:
        statement = (
            select(CharacterRecord)
            .where(CharacterRecord.project_id == project_id)
            .order_by(
                CharacterRecord.updated_at.desc(),
                CharacterRecord.created_at.desc(),
                CharacterRecord.id.asc(),
            )
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(CharacterRecord)
                .where(CharacterRecord.project_id == project_id)
            )
            or 0
        )
        return list(self.session.scalars(statement).all()), total

    def get_character(self, project_id: str, character_id: str) -> CharacterRecord | None:
        statement = (
            select(CharacterRecord)
            .where(CharacterRecord.project_id == project_id, CharacterRecord.id == character_id)
            .options(joinedload(CharacterRecord.looks))
        )
        return self.session.scalars(statement).unique().first()

    def create_character(self, character: CharacterRecord) -> CharacterRecord:
        self.session.add(character)
        self.session.commit()
        self.session.refresh(character)
        return character

    def update_character(
        self, character: CharacterRecord, values: dict[str, object]
    ) -> CharacterRecord:
        for key, value in values.items():
            setattr(character, key, value)
        self.session.commit()
        self.session.refresh(character)
        return character

    def delete_character(self, character: CharacterRecord) -> None:
        self.session.delete(character)
        self.session.commit()

    def delete_character_and_media_assets(
        self, character: CharacterRecord, media_asset_ids: list[str]
    ) -> None:
        try:
            self.session.delete(character)
            if media_asset_ids:
                self.session.execute(
                    delete(MediaAssetRecord).where(MediaAssetRecord.id.in_(media_asset_ids))
                )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def list_looks(self, character_id: str) -> tuple[list[CharacterLookRecord], int]:
        statement = (
            select(CharacterLookRecord)
            .where(CharacterLookRecord.character_id == character_id)
            .order_by(
                CharacterLookRecord.is_default.desc(),
                CharacterLookRecord.created_at.asc(),
                CharacterLookRecord.id.asc(),
            )
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(CharacterLookRecord)
                .where(CharacterLookRecord.character_id == character_id)
            )
            or 0
        )
        return list(self.session.scalars(statement).all()), total

    def get_look(self, character_id: str, look_id: str) -> CharacterLookRecord | None:
        statement = select(CharacterLookRecord).where(
            CharacterLookRecord.character_id == character_id,
            CharacterLookRecord.id == look_id,
        )
        return self.session.scalars(statement).first()

    def create_look(self, look: CharacterLookRecord) -> CharacterLookRecord:
        self.session.add(look)
        self.session.commit()
        self.session.refresh(look)
        return look

    def update_look(
        self, look: CharacterLookRecord, values: dict[str, object]
    ) -> CharacterLookRecord:
        for key, value in values.items():
            setattr(look, key, value)
        self.session.commit()
        self.session.refresh(look)
        return look

    def clear_default_looks(self, character_id: str) -> None:
        self.session.execute(
            update(CharacterLookRecord)
            .where(CharacterLookRecord.character_id == character_id)
            .values(is_default=False)
        )

    def delete_look(self, look: CharacterLookRecord) -> None:
        self.session.delete(look)
        self.session.commit()

    def delete_look_and_media_assets(
        self,
        look: CharacterLookRecord,
        media_asset_ids: list[str],
        next_default_look: CharacterLookRecord | None = None,
    ) -> None:
        try:
            self.session.delete(look)
            if next_default_look is not None:
                next_default_look.is_default = True
                next_default_look.updated_at = next_default_look.updated_at
            if media_asset_ids:
                self.session.execute(
                    delete(MediaAssetRecord).where(MediaAssetRecord.id.in_(media_asset_ids))
                )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def list_references(self, look_id: str) -> tuple[list[CharacterReferenceRecord], int]:
        statement = (
            select(CharacterReferenceRecord)
            .where(CharacterReferenceRecord.look_id == look_id)
            .options(joinedload(CharacterReferenceRecord.media_asset))
            .order_by(
                CharacterReferenceRecord.is_primary.desc(),
                CharacterReferenceRecord.created_at.asc(),
                CharacterReferenceRecord.id.asc(),
            )
        )
        total = (
            self.session.scalar(
                select(func.count())
                .select_from(CharacterReferenceRecord)
                .where(CharacterReferenceRecord.look_id == look_id)
            )
            or 0
        )
        return list(self.session.scalars(statement).all()), total

    def get_reference(
        self,
        look_id: str,
        reference_id: str,
    ) -> CharacterReferenceRecord | None:
        statement = (
            select(CharacterReferenceRecord)
            .where(
                CharacterReferenceRecord.look_id == look_id,
                CharacterReferenceRecord.id == reference_id,
            )
            .options(joinedload(CharacterReferenceRecord.media_asset))
        )
        return self.session.scalars(statement).first()

    def create_reference(
        self,
        media_asset: MediaAssetRecord,
        reference: CharacterReferenceRecord,
    ) -> CharacterReferenceRecord:
        self.session.add(media_asset)
        self.session.add(reference)
        self.session.commit()
        self.session.refresh(reference)
        return reference

    def update_reference(
        self, reference: CharacterReferenceRecord, values: dict[str, object]
    ) -> CharacterReferenceRecord:
        for key, value in values.items():
            setattr(reference, key, value)
        self.session.commit()
        self.session.refresh(reference)
        return reference

    def clear_primary_references(self, look_id: str) -> None:
        self.session.execute(
            update(CharacterReferenceRecord)
            .where(CharacterReferenceRecord.look_id == look_id)
            .values(is_primary=False)
        )

    def delete_reference(self, reference: CharacterReferenceRecord) -> None:
        self.session.delete(reference)
        self.session.commit()

    def delete_reference_and_media_asset(
        self,
        reference: CharacterReferenceRecord,
        media_asset_id: str,
        next_primary_reference: CharacterReferenceRecord | None = None,
    ) -> None:
        try:
            self.session.delete(reference)
            self.session.execute(
                delete(MediaAssetRecord).where(MediaAssetRecord.id == media_asset_id)
            )
            if next_primary_reference is not None:
                next_primary_reference.is_primary = True
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def delete_media_asset(self, media_asset_id: str) -> None:
        self.session.execute(delete(MediaAssetRecord).where(MediaAssetRecord.id == media_asset_id))
        self.session.commit()

    def get_media_asset(self, media_asset_id: str) -> MediaAssetRecord | None:
        return self.session.get(MediaAssetRecord, media_asset_id)
