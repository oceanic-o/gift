from datetime import datetime, timezone
from typing import Optional
import enum

from sqlalchemy import (
    String, Text, Float, Integer, DateTime, ForeignKey, JSON,
    Enum as SAEnum, CheckConstraint, Index, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm import relationship as orm_relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class InteractionType(str, enum.Enum):
    click = "click"
    rating = "rating"
    purchase = "purchase"


class ModelType(str, enum.Enum):
    content_based = "content_based"
    collaborative = "collaborative"
    hybrid = "hybrid"
    rag = "rag"
    knowledge_based = "knowledge_based"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="local")
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    given_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    family_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    locale: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole"), nullable=False, default=UserRole.user
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    interactions: Mapped[list["Interaction"]] = orm_relationship(
        "Interaction", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = orm_relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan"
    )
    rag_queries: Mapped[list["RAGQuery"]] = orm_relationship(
        "RAGQuery", back_populates="user", cascade="all, delete-orphan"
    )
    profile: Mapped[Optional["UserProfile"]] = orm_relationship(
        "UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("length(email) >= 5", name="ck_users_email_length"),
        CheckConstraint("length(name) >= 1", name="ck_users_name_length"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    age: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hobbies: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    relationship: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    occasion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    budget_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    favorite_categories: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    occasions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    gifting_for_ages: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    interests: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = orm_relationship("User", back_populates="profile")

    __table_args__ = (
        CheckConstraint("budget_min IS NULL OR budget_min >= 0", name="ck_user_profiles_budget_min"),
        CheckConstraint("budget_max IS NULL OR budget_max >= 0", name="ck_user_profiles_budget_max"),
    )

    def __repr__(self) -> str:
        return f"<UserProfile id={self.id} user_id={self.user_id}>"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Relationships
    gifts: Mapped[list["Gift"]] = orm_relationship("Gift", back_populates="category")

    __table_args__ = (
        CheckConstraint("length(name) >= 1", name="ck_categories_name_length"),
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name}>"


class Gift(Base):
    __tablename__ = "gifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    occasion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    relationship: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    age_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ORM Relationships (named with _rel suffix to avoid shadowing the 'relationship' column)
    category: Mapped["Category"] = orm_relationship("Category", back_populates="gifts")
    interactions: Mapped[list["Interaction"]] = orm_relationship(
        "Interaction", back_populates="gift", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["Recommendation"]] = orm_relationship(
        "Recommendation", back_populates="gift", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_gifts_price_non_negative"),
        CheckConstraint("length(title) >= 1", name="ck_gifts_title_length"),
        Index("ix_gifts_occasion_relationship", "occasion", "relationship"),
        Index(
            "ix_gifts_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<Gift id={self.id} title={self.title} price={self.price}>"


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gift_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    interaction_type: Mapped[InteractionType] = mapped_column(
        SAEnum(InteractionType, name="interactiontype"), nullable=False
    )
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    user: Mapped["User"] = orm_relationship("User", back_populates="interactions")
    gift: Mapped["Gift"] = orm_relationship("Gift", back_populates="interactions")

    __table_args__ = (
        CheckConstraint(
            "(interaction_type = 'rating' AND rating IS NOT NULL AND rating >= 1 AND rating <= 5) OR "
            "(interaction_type != 'rating')",
            name="ck_interactions_rating_valid",
        ),
        Index("ix_interactions_user_gift", "user_id", "gift_id"),
    )

    def __repr__(self) -> str:
        return f"<Interaction id={self.id} user_id={self.user_id} gift_id={self.gift_id} type={self.interaction_type}>"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gift_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    model_type: Mapped[ModelType] = mapped_column(
        SAEnum(ModelType, name="modeltype"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = orm_relationship("User", back_populates="recommendations")
    gift: Mapped["Gift"] = orm_relationship("Gift", back_populates="recommendations")

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 1", name="ck_recommendations_score_range"),
        Index("ix_recommendations_user_model", "user_id", "model_type"),
    )

    def __repr__(self) -> str:
        return f"<Recommendation id={self.id} user_id={self.user_id} gift_id={self.gift_id} score={self.score}>"


class WebGift(Base):
    __tablename__ = "web_gifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    gift_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gifts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    gift: Mapped["Gift"] = orm_relationship("Gift")

    __table_args__ = (
        UniqueConstraint("gift_id", name="uq_web_gifts_gift_id"),
        UniqueConstraint("source_url", name="uq_web_gifts_source_url"),
    )

    def __repr__(self) -> str:
        return f"<WebGift id={self.id} gift_id={self.gift_id} source={self.source}>"


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    f1_score: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("precision >= 0 AND precision <= 1", name="ck_metrics_precision_range"),
        CheckConstraint("recall >= 0 AND recall <= 1", name="ck_metrics_recall_range"),
        CheckConstraint("f1_score >= 0 AND f1_score <= 1", name="ck_metrics_f1_range"),
        CheckConstraint("accuracy >= 0 AND accuracy <= 1", name="ck_metrics_accuracy_range"),
    )

    def __repr__(self) -> str:
        return f"<ModelMetric id={self.id} model={self.model_name} f1={self.f1_score}>"


class RAGQuery(Base):
    __tablename__ = "rag_queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = orm_relationship("User", back_populates="rag_queries")

    def __repr__(self) -> str:
        return f"<RAGQuery id={self.id} user_id={self.user_id}>"

