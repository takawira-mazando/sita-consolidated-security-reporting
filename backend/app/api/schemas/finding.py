from datetime import datetime

from pydantic import BaseModel


class Finding(BaseModel):
    id: str
    source: str
    external_id: str
    app_name: str
    severity: str
    title: str
    description: str | None = None
    category: str | None = None
    # Platform-side OWASP Top 10 classification. `category` remains the OEM's
    # own vocabulary; these are additive. `owasp_status` is always present so a
    # consumer can tell "not mapped" from "not applicable" from "source sent
    # nothing" without inspecting a NULL.
    owasp_id: str | None = None
    owasp_name: str | None = None
    cwe_id: str | None = None
    owasp_status: str | None = None
    taxonomy_version: str | None = None
    first_seen: datetime
    last_seen: datetime
    status: str
    version: int = 1
