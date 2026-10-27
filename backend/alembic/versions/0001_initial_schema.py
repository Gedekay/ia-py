"""Initial SAAJD schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


role_enum = sa.Enum("ENQUETEUR", "MAGISTRAT", "ADMIN", name="user_role")
dossier_status_enum = sa.Enum("OUVERT", "EN_ANALYSE", "CLOS", name="statut_dossier")
piece_type_enum = sa.Enum(
    "PROCES_VERBAL",
    "INTERROGATOIRE",
    "SAISIE",
    "CERTIFICAT_MEDICAL",
    "TEMOIGNAGE",
    "EXPERTISE",
    "NOTIFICATION_DROITS",
    "AUTRE",
    name="type_piece",
)
analysis_status_enum = sa.Enum("PENDING", "RUNNING", "DONE", "ERROR", name="statut_analyse")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "dossiers",
        sa.Column("numero_dossier", sa.String(length=100), nullable=False),
        sa.Column("date_ouverture", sa.Date(), nullable=False),
        sa.Column("infraction_type", sa.String(length=160), nullable=False),
        sa.Column("statut", dossier_status_enum, nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("numero_dossier"),
    )
    op.create_index("ix_dossiers_numero_dossier", "dossiers", ["numero_dossier"], unique=True)
    op.create_table(
        "documents",
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("type_piece", piece_type_enum, nullable=False),
        sa.Column("file_key", sa.String(length=500), nullable=False),
        sa.Column("file_hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extraction_status", sa.String(length=32), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_key"),
    )
    op.create_index("ix_documents_dossier_id", "documents", ["dossier_id"])
    op.create_table(
        "analyses",
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("statut", analysis_status_enum, nullable=False),
        sa.Column("resultat", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_model", sa.String(length=120), nullable=True),
        sa.Column("llm_tokens_used", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyses_dossier_id", "analyses", ["dossier_id"])
    op.create_table(
        "constitutional_articles",
        sa.Column("numero", sa.String(length=16), nullable=False),
        sa.Column("alinea", sa.String(length=16), nullable=True),
        sa.Column("texte", sa.Text(), nullable=False),
        sa.Column("theme", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_constitutional_articles_numero", "constitutional_articles", ["numero"])
    op.create_index("ix_constitutional_articles_theme", "constitutional_articles", ["theme"])
    op.create_index(
        "ix_constitutional_articles_embedding",
        "constitutional_articles",
        ["embedding"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_constitutional_articles_embedding", table_name="constitutional_articles")
    op.drop_index("ix_constitutional_articles_theme", table_name="constitutional_articles")
    op.drop_index("ix_constitutional_articles_numero", table_name="constitutional_articles")
    op.drop_table("constitutional_articles")
    op.drop_index("ix_analyses_dossier_id", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_documents_dossier_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_dossiers_numero_dossier", table_name="dossiers")
    op.drop_table("dossiers")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS statut_analyse")
    op.execute("DROP TYPE IF EXISTS type_piece")
    op.execute("DROP TYPE IF EXISTS statut_dossier")
    op.execute("DROP TYPE IF EXISTS user_role")