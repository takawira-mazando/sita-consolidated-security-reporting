from datetime import datetime

from pydantic import BaseModel


class Alert(BaseModel):
    id: str
    rule_id: str
    title: str
    description: str | None = None
    severity: str
    source: str | None = None
    target_id: str | None = None
    status: str
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None
    first_triggered: datetime
    last_triggered: datetime
    last_dispatched_at: datetime | None = None
    resolved_at: datetime | None = None
    dedup_count: int | None = None
    channels: list[str] | None = None
    enriched_data: dict | None = None
    created_at: datetime
