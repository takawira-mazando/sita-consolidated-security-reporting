from datetime import datetime, timedelta
import json

class DLQManager:
    def __init__(self, db_session):
        self.session = db_session

    async def write(self, batch_id: str, source: str, raw_payload: dict,
                    rejection_reason: str, rejection_code: str) -> str:
        from app.models.dlq import RejectedRecord
        import uuid
        record = RejectedRecord(
            id=str(uuid.uuid4()),
            batch_id=batch_id,
            source=source,
            raw_payload=raw_payload,
            rejection_reason=rejection_reason,
            rejection_code=rejection_code,
            rejected_at=datetime.utcnow(),
            ttl_expires_at=datetime.utcnow() + timedelta(days=30),
        )
        self.session.add(record)
        await self.session.commit()
        return record.id

    async def reprocess(self, record_id: str) -> dict | None:
        from sqlalchemy import select
        from app.models.dlq import RejectedRecord
        result = await self.session.execute(
            select(RejectedRecord).where(RejectedRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        record.reprocessed = True
        record.reprocessed_at = datetime.utcnow()
        await self.session.commit()
        return record.raw_payload
