from sqlalchemy import Boolean, Column, Date, DateTime, Numeric, String, func

from app.models.base import Base


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    app_name = Column(String(255), nullable=False)
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    ministry_id = Column(String(36), index=True)
    cluster_id = Column(String(36), index=True)
    endpoint = Column(String, nullable=False)
    method = Column(String(10), nullable=False, default="GET")
    is_shadow = Column(Boolean, nullable=False, default=False)
    exposure_score = Column(Numeric(5, 1), nullable=False, default=0)
    discovered_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    last_seen = Column(DateTime(timezone=True), nullable=False, default=func.now())


class WafBlock(Base):
    __tablename__ = "waf_blocks"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    app_name = Column(String(255), nullable=False)
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    ministry_id = Column(String(36), index=True)
    cluster_id = Column(String(36), index=True)
    attack_type = Column(String(100))
    request_uri = Column(String)
    action = Column(String(20), nullable=False, default="block")
    src_ip = Column(String(45))
    block_time = Column(DateTime(timezone=True), nullable=False, default=func.now())


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    metric = Column(String(50), nullable=False)
    value = Column(Numeric(8, 2), nullable=False)
    unit = Column(String(20), nullable=False, default="%")
    recorded_at = Column(DateTime(timezone=True), nullable=False, default=func.now())


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)
    version = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="online")
    host = Column(String(100))
    last_seen = Column(DateTime(timezone=True), nullable=False, default=func.now())


class SloMetric(Base):
    __tablename__ = "slo_metrics"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    metric = Column(String(20), nullable=False)
    week_start = Column(Date, nullable=False)
    value_hours = Column(Numeric(6, 2), nullable=False)


class DatabaseInventory(Base):
    __tablename__ = "database_inventory"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    ministry_id = Column(String(36), index=True)
    cluster_id = Column(String(36), index=True)
    engine = Column(String(50))
    monitored = Column(Boolean, nullable=False, default=True)
    agent_version = Column(String(30))
    last_heartbeat = Column(DateTime(timezone=True), nullable=False, default=func.now())
