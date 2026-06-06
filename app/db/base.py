from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


supervisor_gateways = Table(
    "supervisor_gateways",
    Base.metadata,
    Column("supervisor_id", UUID(as_uuid=True), ForeignKey("supervisors.id"), primary_key=True),
    Column("gateway_id", UUID(as_uuid=True), ForeignKey("gateways.id"), primary_key=True),
)
