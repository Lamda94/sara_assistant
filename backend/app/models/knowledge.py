import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index
from app.db.postgres import Base


class KgNode(Base):
    __tablename__ = "kg_nodes"
    __table_args__ = (
        UniqueConstraint("label", "session_id", name="uq_kg_node_label_session"),
        Index("ix_kg_nodes_session", "session_id"),
    )

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    label       = Column(String, nullable=False)
    type        = Column(String, default="concept")   # tecnología, proyecto, persona, concepto…
    session_id  = Column(String, nullable=False)
    created_at  = Column(DateTime, default=datetime.now)


class KgEdge(Base):
    __tablename__ = "kg_edges"
    __table_args__ = (
        UniqueConstraint("source_id", "target_id", "relation", name="uq_kg_edge"),
        Index("ix_kg_edges_session", "session_id"),
    )

    id          = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id   = Column(String, ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False)
    target_id   = Column(String, ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=False)
    relation    = Column(String, nullable=False)
    session_id  = Column(String, nullable=False)
    created_at  = Column(DateTime, default=datetime.now)
