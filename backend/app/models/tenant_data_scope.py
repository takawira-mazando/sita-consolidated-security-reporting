from sqlalchemy import Column, String


class TenantDataScope:
    tenant_workspace_id = Column(String(36), index=True)
    tenant_scope_level_key = Column(String(64), index=True)
