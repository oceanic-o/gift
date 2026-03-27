from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, ConfigDict
from app.models.models import InteractionType, ModelType
from app.schemas.gift import GiftResponse


class InteractionCreate(BaseModel):
    gift_id: int
    interaction_type: InteractionType
    rating: Optional[float] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[float], info) -> Optional[float]:
        if v is not None and not (1.0 <= v <= 5.0):
            raise ValueError("Rating must be between 1.0 and 5.0")
        return v


class InteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    gift_id: int
    interaction_type: InteractionType
    rating: Optional[float]
    timestamp: datetime


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    gift_id: int
    score: float
    model_type: ModelType
    created_at: datetime


class RecommendationWithGift(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gift_id: int
    score: float
    model_type: ModelType
    title: str
    description: Optional[str]
    price: float
    occasion: Optional[str]
    relationship: Optional[str]
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    category_name: Optional[str] = None
    # Per-gift validity and similarity diagnostics for model comparison UI
    is_valid_recommendation: Optional[bool] = None
    validity_score: Optional[float] = None
    validity_reasons: Optional[list[str]] = None
    query_cosine_similarity: Optional[float] = None
    content_cosine_similarity: Optional[float] = None
    collaborative_cosine_similarity: Optional[float] = None
    knowledge_similarity: Optional[float] = None
    rag_similarity: Optional[float] = None
    occasion_match: Optional[bool] = None
    relationship_match: Optional[bool] = None
    age_match: Optional[bool] = None
    gender_match: Optional[bool] = None
    price_match: Optional[bool] = None
    hobby_overlap: Optional[float] = None


class MinimalRecommendation(BaseModel):
    gift_id: int
    title: str
    price: Optional[float] = None
    image_url: Optional[str] = None
    score: float
    rank: int


class GiftMetrics(BaseModel):
    # Model scores
    hybrid_score: float
    content_score: float
    collab_score: float
    knowledge_score: Optional[float] = None
    # Confidence is a normalized score ~[0,1] over current candidate pool
    confidence: float
    # Feature matches
    occasion_match: Optional[bool] = None
    relationship_match: Optional[bool] = None
    age_group_match: Optional[bool] = None
    price_fit: Optional[bool] = None
    hobby_overlap: Optional[float] = None  # 0..1
    tags_matched: Optional[list[str]] = None
    # Optional global evaluation snapshot for reference
    model_precision: Optional[float] = None
    model_recall: Optional[float] = None
    model_f1: Optional[float] = None
    model_accuracy: Optional[float] = None
    model_error_rate: Optional[float] = None
    model_mae: Optional[float] = None
    model_rmse: Optional[float] = None
    model_coverage: Optional[float] = None
    model_confusion_matrix: Optional[list[list[int]]] = None
    model_tp: Optional[int] = None
    model_fp: Optional[int] = None
    model_tn: Optional[int] = None
    model_fn: Optional[int] = None
    model_metrics_mode: Optional[str] = None


class GiftDetailsWithMetrics(BaseModel):
    gift: GiftResponse
    metrics: GiftMetrics


class ModelMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    evaluated_at: datetime


class EvaluationResult(BaseModel):
    model_name: str
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    confusion_matrix: list[list[int]]
    cross_val_scores: Optional[list[float]] = None


class RAGQueryCreate(BaseModel):
    query: str
    top_k: int = 5
    budget_max: Optional[float] = None
    occasion: Optional[str] = None
    relationship: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    hobbies: Optional[str] = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Query must be at least 3 characters")
        if len(v) > 1000:
            raise ValueError("Query must not exceed 1000 characters")
        return v


class RAGQueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    query: str
    response: Optional[str]
    created_at: datetime


class ModelResult(BaseModel):
    """Results from a single recommendation model."""
    model: str                          # "content" | "collaborative" | "hybrid" | "rag"
    label: str                          # Human-readable name
    gifts: list[RecommendationWithGift]
    is_cold_start: bool = False         # True if user had no history (collaborative falls back)
    metrics: dict                       # precision, recall, f1, coverage, etc.
    explanation: Optional[str] = None   # RAG narrative text (only for rag model)


class CompareResponse(BaseModel):
    """Response from /recommendations/compare — all 4 models side by side."""
    user_has_history: bool
    models: list[ModelResult]


class AdminStats(BaseModel):
    total_users: int
    total_gifts: int
    total_interactions: int
    total_recommendations: int
    popular_categories: list[dict]
    best_model: Optional[dict]
    interaction_breakdown: dict


class DatasetMetadataResponse(BaseModel):
    file_path: str
    schema_version: Optional[str] = None
    generator_version: Optional[str] = None
    image_source: Optional[str] = None
    image_license: Optional[str] = None
    total_products: int
    total_users: Optional[int] = None
    categories: list[str]
    occasions: list[str]
    age_ranges: list[str]
    product_fields: list[str]


class TableColumnResponse(BaseModel):
    name: str
    type: str
    nullable: bool
    default: Optional[str] = None


class TableForeignKeyResponse(BaseModel):
    constrained_columns: list[str]
    referred_table: str
    referred_columns: list[str]


class TableSchemaResponse(BaseModel):
    name: str
    columns: list[TableColumnResponse]
    foreign_keys: list[TableForeignKeyResponse]


class DatabaseSchemaResponse(BaseModel):
    tables: list[TableSchemaResponse]


class AdminQueryRequest(BaseModel):
    sql: str
    max_rows: int = 200


class AdminQueryResponse(BaseModel):
    columns: list[str]
    rows: list[list]

class EnvSettingsResponse(BaseModel):
    backend: dict[str, str]
    frontend: dict[str, str]


class EnvSettingsUpdate(BaseModel):
    backend: Optional[dict[str, str]] = None
    frontend: Optional[dict[str, str]] = None
