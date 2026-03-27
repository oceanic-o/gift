"""Initial schema with pgvector

Revision ID: 001_initial
Revises:
Create Date: 2026-03-02 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Ensure alembic_version can store longer revision ids
    op.execute(
        "ALTER TABLE IF EXISTS alembic_version "
        "ALTER COLUMN version_num TYPE VARCHAR(64)"
    )

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "user", name="userrole"),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(email) >= 5", name="ck_users_email_length"),
        sa.CheckConstraint("length(name) >= 1", name="ck_users_name_length"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    # --- categories ---
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.CheckConstraint("length(name) >= 1", name="ck_categories_name_length"),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
    )
    op.create_index("ix_categories_id", "categories", ["id"])
    op.create_index("ix_categories_name", "categories", ["name"])

    # --- gifts ---
    op.create_table(
        "gifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("occasion", sa.String(length=100), nullable=True),
        sa.Column("relationship", sa.String(length=100), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("price >= 0", name="ck_gifts_price_non_negative"),
        sa.CheckConstraint("length(title) >= 1", name="ck_gifts_title_length"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"],
            name="fk_gifts_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_gifts"),
    )
    op.create_index("ix_gifts_id", "gifts", ["id"])
    op.create_index("ix_gifts_title", "gifts", ["title"])
    op.create_index("ix_gifts_category_id", "gifts", ["category_id"])
    op.create_index("ix_gifts_occasion", "gifts", ["occasion"])
    op.create_index("ix_gifts_relationship", "gifts", ["relationship"])
    op.create_index("ix_gifts_occasion_relationship", "gifts", ["occasion", "relationship"])

    # pgvector IVFFlat index for approximate nearest neighbour search
    op.execute(
        "CREATE INDEX ix_gifts_embedding_ivfflat ON gifts "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # --- interactions ---
    op.create_table(
        "interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("gift_id", sa.Integer(), nullable=False),
        sa.Column(
            "interaction_type",
            sa.Enum("click", "rating", "purchase", name="interactiontype"),
            nullable=False,
        ),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(interaction_type = 'rating' AND rating IS NOT NULL AND rating >= 1 AND rating <= 5) OR "
            "(interaction_type != 'rating')",
            name="ck_interactions_rating_valid",
        ),
        sa.ForeignKeyConstraint(
            ["gift_id"], ["gifts.id"],
            name="fk_interactions_gift_id_gifts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_interactions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_interactions"),
    )
    op.create_index("ix_interactions_id", "interactions", ["id"])
    op.create_index("ix_interactions_user_id", "interactions", ["user_id"])
    op.create_index("ix_interactions_gift_id", "interactions", ["gift_id"])
    op.create_index("ix_interactions_timestamp", "interactions", ["timestamp"])
    op.create_index("ix_interactions_user_gift", "interactions", ["user_id", "gift_id"])

    # --- recommendations ---
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("gift_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "model_type",
            sa.Enum("content_based", "collaborative", "hybrid", name="modeltype"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_recommendations_score_range"),
        sa.ForeignKeyConstraint(
            ["gift_id"], ["gifts.id"],
            name="fk_recommendations_gift_id_gifts",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_recommendations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recommendations"),
    )
    op.create_index("ix_recommendations_id", "recommendations", ["id"])
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])
    op.create_index("ix_recommendations_gift_id", "recommendations", ["gift_id"])
    op.create_index("ix_recommendations_user_model", "recommendations", ["user_id", "model_type"])

    # --- model_metrics ---
    op.create_table(
        "model_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("f1_score", sa.Float(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("precision >= 0 AND precision <= 1", name="ck_metrics_precision_range"),
        sa.CheckConstraint("recall >= 0 AND recall <= 1", name="ck_metrics_recall_range"),
        sa.CheckConstraint("f1_score >= 0 AND f1_score <= 1", name="ck_metrics_f1_range"),
        sa.CheckConstraint("accuracy >= 0 AND accuracy <= 1", name="ck_metrics_accuracy_range"),
        sa.PrimaryKeyConstraint("id", name="pk_model_metrics"),
    )
    op.create_index("ix_model_metrics_id", "model_metrics", ["id"])
    op.create_index("ix_model_metrics_model_name", "model_metrics", ["model_name"])

    # --- rag_queries ---
    op.create_table(
        "rag_queries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_rag_queries_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rag_queries"),
    )
    op.create_index("ix_rag_queries_id", "rag_queries", ["id"])
    op.create_index("ix_rag_queries_user_id", "rag_queries", ["user_id"])


def downgrade() -> None:
    op.drop_table("rag_queries")
    op.drop_table("model_metrics")
    op.drop_table("recommendations")
    op.drop_table("interactions")
    op.drop_table("gifts")
    op.drop_table("categories")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS modeltype")
    op.execute("DROP TYPE IF EXISTS interactiontype")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP EXTENSION IF EXISTS vector")
