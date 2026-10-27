from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdTimestampMixin


class ConstitutionalArticle(IdTimestampMixin, Base):
    __tablename__ = "constitutional_articles"

    numero: Mapped[str] = mapped_column(String(16), index=True)
    alinea: Mapped[str | None] = mapped_column(String(16), nullable=True)
    texte: Mapped[str] = mapped_column(Text)
    theme: Mapped[str] = mapped_column(String(120), index=True)
    source: Mapped[str] = mapped_column(String(255), default="Constitution RDC 2006 révisée")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)


Index(
    "ix_constitutional_articles_embedding",
    ConstitutionalArticle.embedding,
    postgresql_using="ivfflat",
    postgresql_ops={"embedding": "vector_cosine_ops"},
)