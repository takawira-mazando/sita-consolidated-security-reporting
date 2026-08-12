from sqlalchemy import Column, String

from app.models.base import Base


class Province(Base):
    __tablename__ = "provinces"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    name = Column(String(60), nullable=False)
    code = Column(String(20), unique=True, nullable=False)


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    name = Column(String(120), nullable=False)
    code = Column(String(60), unique=True, nullable=False)
    province_id = Column(String(20), index=True)


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    department_id = Column(String(36), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    code = Column(String(60), unique=True, nullable=False)
