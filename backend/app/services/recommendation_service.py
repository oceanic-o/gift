"""
Recommendation Service Layer – orchestrates personalized recommendations.
"""
import asyncio
import math
import time
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
)

from app.core.config import settings
from app.core.logging import logger
from app.core.taxonomy import BUDGET_TO_PRICE, AGE_GROUP_MIDPOINTS, match_age_group
from app.models.models import Recommendation, ModelType, Gift, InteractionType
from app.repositories.interaction_repository import InteractionRepository, RecommendationRepository
from app.repositories.gift_repository import GiftRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.repositories.interaction_repository import ModelMetricRepository
from app.services.recommendation.hybrid import get_recommender
from app.services.recommendation.knowledge_based import (
    KnowledgeBasedRecommender,
    _tokenize,
    _GENDER_KEYWORDS,
)
from app.services.evaluation.evaluator import RecommendationEvaluator

from app.schemas.recommendation import (
    InteractionCreate, RecommendationWithGift, ModelResult, CompareResponse,
    MinimalRecommendation, GiftDetailsWithMetrics, GiftMetrics
)


_METRICS_WARMUP_LAST_RUN = 0.0
_METRICS_WARMUP_LOCK = asyncio.Lock()


def _parse_budget(budget_str: str | None) -> tuple[float | None, float | None]:
    """Convert a budget label (e.g. '$50–$100') to (min_price, max_price).
    Falls back to None, None if the string is unrecognized."""
    if not budget_str:
        return None, None
    entry = BUDGET_TO_PRICE.get(budget_str)
    if entry:
        return entry
    # Try legacy dash-separated format like '50-100' or '500+'
    b = budget_str.replace("$", "").replace(",", "").strip()
    if b.endswith("+"):
        try:
            return float(b[:-1]), None
        except ValueError:
            return None, None
    if "-" in b:
        parts = b.split("-")
        try:
            return float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            return None, None
    return None, None


def _age_group_to_exact(age: str | None) -> int | None:
    """Extract midpoint age from an age group label like 'Child (0-12)'."""
    if not age:
        return None
    return AGE_GROUP_MIDPOINTS.get(age)


async def _maybe_warmup_model_metrics(db: AsyncSession) -> None:
    """Best-effort evaluation run to populate model_metrics for regular users.

    Throttled and guarded so it never blocks or fails user requests.
    """
    global _METRICS_WARMUP_LAST_RUN

    try:
        # throttle to once every 2 hours
        now = time.time()
        if now - _METRICS_WARMUP_LAST_RUN < 2 * 60 * 60:
            return

        async with _METRICS_WARMUP_LOCK:
            now = time.time()
            if now - _METRICS_WARMUP_LAST_RUN < 2 * 60 * 60:
                return

            metric_repo = ModelMetricRepository(db)
            latest = await metric_repo.get_latest_by_model("hybrid")
            if latest and latest.evaluated_at:
                # skip if updated within 24h
                age_seconds = (now - latest.evaluated_at.timestamp())
                if age_seconds < 24 * 60 * 60:
                    _METRICS_WARMUP_LAST_RUN = now
                    return

            gift_repo = GiftRepository(db)
            gifts = await gift_repo.get_all_gifts(limit=800)
            if not gifts:
                _METRICS_WARMUP_LAST_RUN = now
                return

            gift_dicts = [
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description or "",
                    "occasion": g.occasion or "",
                    "relationship": g.relationship or "",
                    "category_name": g.category.name if g.category else "",
                    "tags": g.tags or "",
                    "age_group": getattr(g, "age_group", "") or "",
                    "price": g.price,
                }
                for g in gifts
            ]

            evaluator = RecommendationEvaluator(cross_validate=False)
            await evaluator.evaluate(db, gift_dicts, model_name="hybrid")
            _METRICS_WARMUP_LAST_RUN = now
    except Exception:
        # Best-effort only; never fail user requests.
        return


class InteractionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.interaction_repo = InteractionRepository(db)
        self.gift_repo = GiftRepository(db)

    async def record_interaction(
        self, user_id: int, payload: InteractionCreate
    ):
        from app.models.models import Interaction

        # Verify gift exists
        gift = await self.gift_repo.get_by_id(payload.gift_id)
        if gift is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found.")

        # Validate rating for rating type
        if payload.interaction_type.value == "rating" and payload.rating is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Rating value is required for interaction_type='rating'.",
            )

        interaction = Interaction(
            user_id=user_id,
            gift_id=payload.gift_id,
            interaction_type=payload.interaction_type,
            rating=payload.rating,
        )
        created = await self.interaction_repo.create(interaction)
        # Commit immediately so subsequent recommendation calls can use this signal.
        await self.db.commit()
        await self.db.refresh(created)
        logger.info("interaction.recorded", user_id=user_id, gift_id=payload.gift_id)
        return created


class RecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.interaction_repo = InteractionRepository(db)
        self.rec_repo = RecommendationRepository(db)
        self.gift_repo = GiftRepository(db)
        self.profile_repo = UserProfileRepository(db)
        self.metric_repo = ModelMetricRepository(db)

    async def get_minimal_recommendations(
        self,
        user_id: int,
        top_n: int = settings.TOP_N_RECOMMENDATIONS,
        occasion: str | None = None,
        relationship: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        age: str | None = None,
        gender: str | None = None,
        hobbies: str | None = None,
    ) -> list[MinimalRecommendation]:
        """Return image-only recommendations optimized for a grid UI."""
        recommender = get_recommender()
        if not recommender._trained:
            await recommender.train(self.db)

        profile = await self.profile_repo.get_by_user_id(user_id)
        interactions = await self.interaction_repo.get_user_interactions(user_id, limit=200)
        liked_ids = [
            i.gift_id for i in interactions
            if i.interaction_type.value in ("purchase", "rating") and (i.rating is None or i.rating >= 3)
        ]

        # Build a weighted query emphasizing hobbies/interests
        def _clean(v: str | None) -> str | None:
            if v is None:
                return None
            s = str(v).strip()
            return s or None

        q_parts = []
        if age:
            q_parts.append(f"age {age}")
        if gender:
            q_parts.append(gender)
        if hobbies:
            q_parts.append(hobbies)
        if occasion:
            q_parts.append(occasion)
        if relationship:
            q_parts.append(relationship)
        if profile and getattr(profile, "hobbies", None):
            q_parts.append(str(profile.hobbies))
        query = _clean(" ".join(q_parts))

        age_group_label = match_age_group(age) if age else None

        recs = recommender.recommend(
            user_id=user_id,
            liked_gift_ids=liked_ids,
            top_n=top_n,
            occasion=_clean(occasion) or (profile.occasion if profile else None),
            relationship=_clean(relationship) or (profile.relationship if profile else None),
            min_price=min_price if min_price is not None else (profile.budget_min if profile else None),
            max_price=max_price if max_price is not None else (profile.budget_max if profile else None),
            age_groups=[age_group_label] if age_group_label else None,
            gender=_clean(gender) or (profile.gender if profile else None),
            query_text=query,
        )

        # Map to minimal response used by the grid UI
        if not recs:
            return []

        rec_ids = [r["id"] for r in recs]
        # Fetch gifts for these IDs to get titles and images
        result = await self.db.execute(
            select(Gift).where(Gift.id.in_(rec_ids))
        )
        gift_map = {g.id: g for g in result.scalars().all()}

        score_map = {r["id"]: r["score"] for r in recs}

        return [
            MinimalRecommendation(
                gift_id=rid,
                title=gift_map[rid].title if rid in gift_map else "",
                image_url=gift_map[rid].image_url if rid in gift_map else None,
                price=gift_map[rid].price if rid in gift_map else None,
                score=score_map[rid],
                rank=idx + 1,
            )
            for idx, rid in enumerate(rec_ids)
        ]

    async def get_gift_details_with_metrics(
        self,
        user_id: int,
        gift_id: int,
        occasion: str | None = None,
        relationship: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        age: str | None = None,
        gender: str | None = None,
        hobbies: str | None = None,
    ) -> GiftDetailsWithMetrics:
        """
        Return rich details and per-gift metrics suitable for a details panel with graphs.
        Metrics include model sub-scores, confidence, and feature-match breakdown.
        Also attaches latest global evaluation (precision/recall/f1) for reference.
        """
        recommender = get_recommender()
        if not recommender._trained:
            await recommender.train(self.db)

        gift = await self.gift_repo.get_with_category(gift_id)
        if gift is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found")

        interactions = await self.interaction_repo.get_user_interactions(user_id, limit=200)
        liked_ids = [
            i.gift_id for i in interactions
            if i.interaction_type.value in ("purchase", "rating") and (i.rating is None or i.rating >= 3)
        ]

        # Build query emphasizing hobbies
        def _clean(v: str | None) -> str | None:
            if v is None:
                return None
            s = str(v).strip()
            return s or None

        q_parts = []
        if age:
            q_parts.append(f"age {age}")
        if gender:
            q_parts.append(gender)
        if hobbies:
            q_parts.append(f"{hobbies} {hobbies} {hobbies}")
            g_occasion = None if occasion is None else str(occasion)
            g_relationship = None if relationship is None else str(relationship)
            if g_relationship:
                q_parts.append(g_relationship)
            if g_occasion:
                q_parts.append(g_occasion)
        if max_price is not None:
            q_parts.append(f"under {max_price}")
        query_text = " ".join(q_parts).strip() or None

        # Compute content/collab/hybrid scores across a candidate pool, then extract this gift's scores
        top_pool = max(settings.TOP_N_RECOMMENDATIONS * 3, 60)
        content_results = recommender.content_filter.get_scores_for_user_profile(
            liked_gift_ids=liked_ids,
            top_n=top_pool,
            occasion=_clean(occasion),
            relationship=_clean(relationship),
            min_price=min_price,
            max_price=max_price,
            query_text=query_text,
        )
        content_map = {r["id"]: float(r["score"]) for r in content_results}

        collab_results = recommender.collaborative_filter.get_scores_for_user(
            user_id=user_id,
            top_n=top_pool,
            exclude_gift_ids=liked_ids,
        )
        collab_map = {r["id"]: float(r["score"]) for r in collab_results}

        # Blend as hybrid
        c_w = recommender.content_weight
        cf_w = recommender.collaborative_weight if collab_results else 1.0 - min(0.85, max(0.6, c_w))
        content_score = content_map.get(gift_id, 0.0)
        collab_score = collab_map.get(gift_id, 0.0)
        hybrid_score = round(c_w * content_score + cf_w * collab_score, 6)

        # Build hybrid scored list for metric fallback
        hybrid_scored = []
        for gid in set(content_map.keys()) | set(collab_map.keys()):
            cs = content_map.get(gid, 0.0)
            cfs = collab_map.get(gid, 0.0)
            hybrid_scored.append({"id": gid, "score": float(c_w * cs + cf_w * cfs)})

        # Knowledge-based score for this single gift given inputs
        kb = KnowledgeBasedRecommender()
        kb_scored = kb.score_gifts(
            gifts=[{
                "id": gift.id,
                "title": gift.title,
                "description": gift.description or "",
                "occasion": gift.occasion or "",
                "relationship": gift.relationship or "",
                "category_name": gift.category.name if gift.category else "",
                "tags": getattr(gift, "tags", "") or "",
                "age_group": getattr(gift, "age_group", "") or "",
                "price": gift.price,
            }],
            top_n=1,
            occasion=_clean(occasion),
            relationship=_clean(relationship),
            min_price=min_price,
            max_price=max_price,
            query_text=query_text,
            age=_clean(age),
            gender=_clean(gender),
            hobbies=_clean(hobbies),
        )
        knowledge_score = float(kb_scored[0]["score"]) if kb_scored else 0.0

        # Confidence: normalize hybrid score against candidate pool distribution
        all_hybrid = []
        for gid in set(content_map.keys()) | set(collab_map.keys()):
            cs = content_map.get(gid, 0.0)
            cfs = collab_map.get(gid, 0.0)
            all_hybrid.append(c_w * cs + cf_w * cfs)
        max_h = max(all_hybrid) if all_hybrid else 1.0
        confidence = float(hybrid_score / (max_h + 1e-9)) if max_h > 0 else 0.0

        # Feature-match breakdown
        import re
        def _tokens(text: str) -> set[str]:
            return set(re.findall(r"[a-zA-Z0-9']+", (text or "").lower()))

        hobby_overlap = None
        if hobbies:
            hobby_tokens = _tokens(hobbies)
            gift_tokens = _tokens(" ".join([
                gift.title, gift.description or "", gift.tags or "", gift.category.name if gift.category else "",
            ]))
            if hobby_tokens:
                hobby_overlap = round(len(hobby_tokens & gift_tokens) / max(len(hobby_tokens), 1), 4)

        occasion_match = bool(occasion and gift.occasion and occasion.lower() in gift.occasion.lower())
        relationship_match = bool(relationship and gift.relationship and relationship.lower() in gift.relationship.lower())
        age_group_match = bool(getattr(gift, "age_group", None) and age and age.lower() in gift.age_group.lower()) if age else None
        price_fit = None
        if min_price is not None or max_price is not None:
            price_fit = True
            if min_price is not None and gift.price < min_price:
                price_fit = False
            if max_price is not None and gift.price > max_price:
                price_fit = False

        # Attach latest global metrics for reference (fallback to on-the-fly computation)
        latest_metric = await self.metric_repo.get_latest_by_model("hybrid")
        model_accuracy = None
        model_error_rate = None
        model_mae = None
        model_rmse = None
        model_coverage = None
        model_confusion_matrix = None
        model_tp = None
        model_fp = None
        model_tn = None
        model_fn = None
        model_metrics_mode = None
        if latest_metric:
            model_precision = float(latest_metric.precision)
            model_recall = float(latest_metric.recall)
            model_f1 = float(latest_metric.f1_score)
            model_accuracy = float(latest_metric.accuracy)
        else:
            # Fallback: compute metrics from current hybrid scoring
            all_gifts = await self.gift_repo.get_all_gifts()
            gift_map = {g.id: g for g in all_gifts}
            metric_fallback = self._compute_metrics(
                hybrid_scored,
                set(liked_ids),
                set(gift_map.keys()),
                top_n=min(settings.TOP_N_RECOMMENDATIONS, 10),
                gift_map=gift_map,
                occasion=_clean(occasion),
                relationship=_clean(relationship),
                min_price=min_price,
                max_price=max_price,
                age=_clean(age),
                gender=_clean(gender),
                hobbies=_clean(hobbies),
                prefer_context=True,
            )
            def _num(key: str) -> float | None:
                raw = metric_fallback.get(key)
                if isinstance(raw, (int, float)):
                    return float(raw)
                return None

            model_precision = _num("precision")
            model_recall = _num("recall")
            f1_raw = _num("f1")
            model_f1 = f1_raw if f1_raw is not None else _num("f1_score")
            model_accuracy = _num("accuracy")
            model_error_rate = _num("error_rate")
            model_mae = _num("mae")
            model_rmse = _num("rmse")
            model_coverage = _num("coverage")
            model_confusion_matrix = metric_fallback.get("confusion_matrix")
            model_tp = metric_fallback.get("tp")
            model_fp = metric_fallback.get("fp")
            model_tn = metric_fallback.get("tn")
            model_fn = metric_fallback.get("fn")
            model_metrics_mode = metric_fallback.get("metrics_mode")

        metrics = GiftMetrics(
            hybrid_score=float(hybrid_score),
            content_score=float(content_score),
            collab_score=float(collab_score),
            knowledge_score=float(knowledge_score) if knowledge_score is not None else None,
            confidence=round(confidence, 4),
            occasion_match=occasion_match if occasion is not None else None,
            relationship_match=relationship_match if relationship is not None else None,
            age_group_match=age_group_match,
            price_fit=price_fit,
            hobby_overlap=hobby_overlap,
            tags_matched=None,
            model_precision=model_precision,
            model_recall=model_recall,
            model_f1=model_f1,
            model_accuracy=model_accuracy,
            model_error_rate=model_error_rate,
            model_mae=model_mae,
            model_rmse=model_rmse,
            model_coverage=model_coverage,
            model_confusion_matrix=model_confusion_matrix,
            model_tp=model_tp,
            model_fp=model_fp,
            model_tn=model_tn,
            model_fn=model_fn,
            model_metrics_mode=model_metrics_mode,
        )

        from app.schemas.gift import GiftResponse
        return GiftDetailsWithMetrics(
            gift=GiftResponse.model_validate(gift),
            metrics=metrics,
        )

    def _apply_feature_boosts(
        self,
        scored: list[dict],
        gift_map: dict[int, Gift],
        *,
        hobbies: str | None = None,
        occasion: str | None = None,
        relationship: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        age: str | None = None,
        gender: str | None = None,
    ) -> list[dict]:
        hobby_tokens = _tokenize(hobbies) if hobbies else set()

        # Precompute age group keywords for matching
        age_kws: list[str] = []
        if age:
            from app.services.recommendation.knowledge_based import _AGE_GROUP_GIFT_KEYWORDS
            age_lower = age.lower()
            for prefix, kws in _AGE_GROUP_GIFT_KEYWORDS.items():
                if age_lower.startswith(prefix):
                    age_kws = kws
                    break

        # Precompute gender keywords
        gender_kws: list[str] = []
        if gender:
            from app.services.recommendation.knowledge_based import _GENDER_KEYWORDS
            gender_kws = _GENDER_KEYWORDS.get(gender.lower(), [])

        for item in scored:
            g = gift_map.get(item["id"])
            if not g:
                continue
            boost = 0.0
            gift_text_parts = [
                str(getattr(g, "title", "") or ""),
                str(getattr(g, "description", "") or ""),
                str(getattr(g, "tags", "") or ""),
                str((g.category.name if getattr(g, "category", None) else "") or ""),
            ]
            gift_tokens = _tokenize(" ".join(gift_text_parts))
            # hobby/interest overlap
            if hobby_tokens:
                overlap = len(hobby_tokens & gift_tokens) / max(len(hobby_tokens), 1)
                boost += settings.BOOST_WEIGHT_HOBBIES * overlap
                
                # Additional fixed boost for exact keyword matches in title/tags
                gift_lower = " ".join(gift_text_parts).lower()
                if hobbies:
                    hobby_list = [h.strip().lower() for h in hobbies.split(",") if h.strip()]
                    if any(h in gift_lower for h in hobby_list):
                        boost += 0.25  # Substantial fixed boost for exact hobby match
            # occasion match
            g_occasion = None if getattr(g, "occasion", None) is None else str(getattr(g, "occasion"))
            if occasion and g_occasion and str(occasion).lower() in g_occasion.lower():
                boost += settings.BOOST_WEIGHT_OCCASION
            # relationship match
            g_relationship = None if getattr(g, "relationship", None) is None else str(getattr(g, "relationship"))
            if relationship and g_relationship and str(relationship).lower() in g_relationship.lower():
                boost += settings.BOOST_WEIGHT_RELATIONSHIP
            # age group bonus
            if age_kws:
                gift_age_text = str(getattr(g, "age_group", "") or "").lower()
                gift_lower = " ".join(gift_text_parts).lower()
                if any(kw in gift_age_text or kw in gift_lower for kw in age_kws):
                    boost += settings.BOOST_WEIGHT_AGE
            # gender bonus
            if gender_kws:
                gift_lower = " ".join(gift_text_parts).lower()
                if any(kw in gift_lower for kw in gender_kws):
                    boost += settings.BOOST_WEIGHT_GENDER
            # budget fit
            price_fit = True
            if min_price is not None and g.price < min_price:
                price_fit = False
            if max_price is not None and g.price > max_price:
                price_fit = False
            if price_fit and (min_price is not None or max_price is not None):
                boost += settings.BOOST_WEIGHT_PRICE
            item["score"] = float(min(1.0, item["score"] + boost))
        # re-sort
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _mmr_diversify(
        self,
        scored: list[dict],
        recommender,
        top_n: int,
        lambda_param: float = 0.7,
    ) -> list[dict]:
        """Apply MMR using TF-IDF item-item similarity to diversify top results."""
        if not scored:
            return []
        # Build mapping id->tfidf index
        id_to_idx = {gid: idx for idx, gid in enumerate(recommender.content_filter.gift_ids)}
        tfidf = recommender.content_filter.tfidf_matrix
        if tfidf is None:
            return scored[:top_n]
        # Pre-compute pairwise sims lazily
        selected: list[dict] = []
        candidates = scored.copy()
        while candidates and len(selected) < top_n:
            if not selected:
                selected.append(candidates.pop(0))
                continue
            best_i = 0
            best_val = -1e9
            for i, cand in enumerate(candidates):
                rel = float(cand["score"])  # relevance
                # max similarity to any selected
                max_sim = 0.0
                c_idx = id_to_idx.get(cand["id"]) if id_to_idx else None
                if c_idx is not None:
                    for s in selected:
                        s_idx = id_to_idx.get(s["id"]) if id_to_idx else None
                        if s_idx is not None:
                            sim = float(cosine_similarity(tfidf[c_idx], tfidf[s_idx]).ravel()[0])
                            if sim > max_sim:
                                max_sim = sim
                mmr = lambda_param * rel - (1 - lambda_param) * max_sim
                if mmr > best_val:
                    best_val = mmr
                    best_i = i
            selected.append(candidates.pop(best_i))
        return selected

    async def get_personalized_recommendations(
        self,
        user_id: int,
        top_n: int = settings.TOP_N_RECOMMENDATIONS,
        occasion: str = None,
        relationship: str = None,
        min_price: float = None,
        max_price: float = None,
        age: str = None,
        gender: str = None,
        hobbies: str = None,
    ) -> list[RecommendationWithGift]:
        """
        Generate and persist hybrid recommendations for a user.
        Returns enriched list with gift details.
        """
        recommender = get_recommender()

        if not recommender._trained:
            logger.warning("recommendation.model_not_trained_training_now")
            await recommender.train(self.db)

        profile = await self.profile_repo.get_by_user_id(user_id)
        if asyncio.iscoroutine(profile):
            profile = await profile

        # Get user's interaction history for cold start / profile building
        user_interactions = await self.interaction_repo.get_user_interactions(user_id)
        liked_ids = [
            i.gift_id for i in user_interactions
            if i.interaction_type.value in ("purchase", "rating") and (i.rating is None or i.rating >= 3)
        ]

        resolved_occasion = occasion or (
            profile.occasions[0] if profile and profile.occasions else (profile.occasion if profile else None)
        )
        resolved_relationship = relationship or (profile.relationship if profile else None)
        resolved_min = min_price if min_price is not None else (profile.budget_min if profile else None)
        resolved_max = max_price if max_price is not None else (profile.budget_max if profile else None)
        resolved_age = age or (profile.age if profile else None)
        resolved_gender = gender or (profile.gender if profile else None)
        resolved_hobbies = hobbies or (profile.hobbies if profile else None)
        category_names = profile.favorite_categories if profile and profile.favorite_categories else None
        age_groups = profile.gifting_for_ages if profile and profile.gifting_for_ages else None
        resolved_age_group = match_age_group(resolved_age) if resolved_age else None
        if resolved_age_group:
            age_groups = [resolved_age_group]
        tags = profile.interests if profile and profile.interests else None

        # Build a weighted natural language query from all inputs
        nl_parts = []
        if resolved_relationship:
            nl_parts.append(f"Gift for {resolved_relationship}")
        if resolved_occasion:
            nl_parts.append(f"for {resolved_occasion}")
        if resolved_age:
            nl_parts.append(f"age {resolved_age}")
        if resolved_gender:
            nl_parts.append(resolved_gender)
        if resolved_hobbies:
            nl_parts.append(f"who loves {resolved_hobbies}")
            nl_parts.append(resolved_hobbies)  # extra weight
        if resolved_max:
            nl_parts.append(f"under ${resolved_max:.0f}")
        profile_query = " ".join(nl_parts).strip() or None

        # Run knowledge-based scoring for hybrid blending
        all_gifts = await self.gift_repo.get_all_gifts()
        gift_map = {g.id: g for g in all_gifts}

        def _stringify(value) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            return str(value)

        knowledge_scored = KnowledgeBasedRecommender().score_gifts(
            gifts=[
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description or "",
                    "occasion": g.occasion or "",
                    "relationship": g.relationship or "",
                    "category_name": g.category.name if g.category else "",
                    "tags": _stringify(getattr(g, "tags", "")),
                    "age_group": _stringify(getattr(g, "age_group", "")),
                    "price": g.price,
                }
                for g in all_gifts
            ],
            top_n=top_n * 3,
            occasion=resolved_occasion,
            relationship=resolved_relationship,
            min_price=resolved_min,
            max_price=resolved_max,
            query_text=profile_query,
            age=resolved_age,
            gender=resolved_gender,
            hobbies=resolved_hobbies,
        )

        scored = recommender.recommend(
            user_id=user_id,
            liked_gift_ids=liked_ids,
            top_n=top_n * 3,
            occasion=resolved_occasion,
            relationship=resolved_relationship,
            category_names=category_names,
            age_groups=age_groups,
            tags=tags,
            min_price=resolved_min,
            max_price=resolved_max,
            gender=resolved_gender,
            query_text=profile_query,
            knowledge_gifts=knowledge_scored,
        )

        if not scored:
            logger.info("recommendation.empty_result", user_id=user_id)
            return []

        # Feature boosts (prioritize hobbies > occasion > relationship > age > gender > price-fit)
        scored = self._apply_feature_boosts(
            scored,
            gift_map,
            hobbies=resolved_hobbies,
            occasion=resolved_occasion,
            relationship=resolved_relationship,
            min_price=resolved_min,
            max_price=resolved_max,
            age=resolved_age,
            gender=resolved_gender,
        )
        # MMR diversity
        scored = self._mmr_diversify(scored, recommender, top_n)

        # Persist recommendations (replace old ones)
        await self.rec_repo.delete_user_recommendations(user_id)

        recommendation_objects = []
        gift_id_to_score = {}
        for item in scored:
            rec = Recommendation(
                user_id=user_id,
                gift_id=item["id"],
                score=item["score"],
                model_type=ModelType.hybrid,
            )
            recommendation_objects.append(rec)
            gift_id_to_score[item["id"]] = item["score"]

        await self.rec_repo.bulk_create(recommendation_objects)

        # Fetch full gift details
        all_gifts = await self.gift_repo.get_all_gifts()
        gift_map = {g.id: g for g in all_gifts}

        result = []
        for item in scored:
            gift = gift_map.get(item["id"])
            if gift is None:
                continue
            result.append(
                RecommendationWithGift(
                    gift_id=gift.id,
                    score=item["score"],
                    model_type=ModelType.hybrid,
                    title=gift.title,
                    description=gift.description,
                    price=gift.price,
                    occasion=gift.occasion,
                    relationship=gift.relationship,
                    image_url=gift.image_url,
                    product_url=gift.product_url,
                    category_name=gift.category.name if gift.category else None,
                )
            )

        logger.info("recommendation.generated", user_id=user_id, count=len(result))
        return result

    def _scored_to_gifts(
        self,
        scored: list[dict],
        gift_map: dict,
        model_type: ModelType,
        top_n: int,
        per_gift_meta: dict[int, dict] | None = None,
    ) -> list[RecommendationWithGift]:
        result = []
        for item in scored[:top_n]:
            gift = gift_map.get(item["id"])
            if gift is None:
                continue
            meta = (per_gift_meta or {}).get(gift.id, {})
            result.append(RecommendationWithGift(
                gift_id=gift.id,
                score=item["score"],
                model_type=model_type,
                title=gift.title,
                description=gift.description,
                price=gift.price,
                occasion=gift.occasion,
                relationship=gift.relationship,
                image_url=gift.image_url,
                product_url=gift.product_url,
                category_name=gift.category.name if gift.category else None,
                is_valid_recommendation=meta.get("is_valid_recommendation"),
                validity_score=meta.get("validity_score"),
                validity_reasons=meta.get("validity_reasons"),
                query_cosine_similarity=meta.get("query_cosine_similarity"),
                content_cosine_similarity=meta.get("content_cosine_similarity"),
                collaborative_cosine_similarity=meta.get("collaborative_cosine_similarity"),
                knowledge_similarity=meta.get("knowledge_similarity"),
                rag_similarity=meta.get("rag_similarity"),
                occasion_match=meta.get("occasion_match"),
                relationship_match=meta.get("relationship_match"),
                age_match=meta.get("age_match"),
                gender_match=meta.get("gender_match"),
                price_match=meta.get("price_match"),
                hobby_overlap=meta.get("hobby_overlap"),
            ))
        return result

    def _build_gift_validity(
        self,
        gift: Gift,
        *,
        occasion: str | None = None,
        relationship: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        age: str | None = None,
        gender: str | None = None,
        hobbies: str | None = None,
    ) -> dict:
        def _round(v: float | None) -> float | None:
            if v is None:
                return None
            return round(float(v), 4)

        reasons: list[str] = []
        weighted_hits = 0.0
        weighted_total = 0.0
        hard_fail = False

        gift_title = str(getattr(gift, "title", "") or "")
        gift_desc = str(getattr(gift, "description", "") or "")
        gift_tags = str(getattr(gift, "tags", "") or "")
        gift_cat = str((gift.category.name if getattr(gift, "category", None) else "") or "")
        gift_text = " ".join([gift_title, gift_desc, gift_tags, gift_cat])
        gift_tokens = _tokenize(gift_text)

        occasion_match = None
        if occasion:
            occasion_match = bool(gift.occasion and occasion.lower() in gift.occasion.lower())
            weighted_total += 0.8
            weighted_hits += 0.8 if occasion_match else 0.0
            if not occasion_match:
                reasons.append("occasion_mismatch")

        relationship_match = None
        if relationship:
            relationship_match = bool(gift.relationship and relationship.lower() in gift.relationship.lower())
            weighted_total += 0.8
            weighted_hits += 0.8 if relationship_match else 0.0
            if not relationship_match:
                reasons.append("relationship_mismatch")

        price_match = None
        if min_price is not None or max_price is not None:
            price_match = True
            if min_price is not None and gift.price < min_price:
                price_match = False
            if max_price is not None and gift.price > max_price:
                price_match = False
            weighted_total += 1.2
            weighted_hits += 1.2 if price_match else 0.0
            if not price_match:
                reasons.append("budget_mismatch")
                hard_fail = True

        age_match = None
        if age:
            target_age = match_age_group(age) or age
            gift_age = match_age_group(getattr(gift, "age_group", None)) or str(getattr(gift, "age_group", "") or "")
            if gift_age:
                age_match = target_age.lower().split("(")[0].strip() in gift_age.lower()
                weighted_total += 0.9
                weighted_hits += 0.9 if age_match else 0.0
                if not age_match:
                    reasons.append("age_group_mismatch")

        gender_match = None
        if gender:
            gender_kws = _GENDER_KEYWORDS.get(gender.lower(), [])
            if gender_kws:
                gift_text_lower = gift_text.lower()
                gender_match = any(kw in gift_text_lower for kw in gender_kws)
                weighted_total += 0.5
                weighted_hits += 0.5 if gender_match else 0.0
                if gender_match is False:
                    reasons.append("gender_signal_mismatch")

        hobby_overlap = None
        if hobbies:
            hobby_tokens = _tokenize(hobbies)
            if hobby_tokens:
                hobby_overlap = len(hobby_tokens & gift_tokens) / max(len(hobby_tokens), 1)
                weighted_total += 1.0
                weighted_hits += hobby_overlap
                if hobby_overlap <= 0:
                    reasons.append("hobby_mismatch")

        validity_score = (weighted_hits / weighted_total) if weighted_total > 0 else 1.0
        is_valid = (not hard_fail) and (validity_score >= 0.45)
        if is_valid and not reasons:
            reasons = ["all_constraints_satisfied"]

        return {
            "is_valid_recommendation": bool(is_valid),
            "validity_score": _round(validity_score),
            "validity_reasons": reasons[:5],
            "occasion_match": occasion_match,
            "relationship_match": relationship_match,
            "age_match": age_match,
            "gender_match": gender_match,
            "price_match": price_match,
            "hobby_overlap": _round(hobby_overlap),
        }

    def _build_gift_diagnostics(
        self,
        gift: Gift,
        *,
        occasion: str | None = None,
        relationship: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        age: str | None = None,
        gender: str | None = None,
        hobbies: str | None = None,
        query_cosine_map: dict[int, float] | None = None,
        content_score_map: dict[int, float] | None = None,
        collab_score_map: dict[int, float] | None = None,
        knowledge_score_map: dict[int, float] | None = None,
        rag_score_map: dict[int, float] | None = None,
    ) -> dict:
        base = self._build_gift_validity(
            gift,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            age=age,
            gender=gender,
            hobbies=hobbies,
        )
        gid = gift.id

        def _round(v: float | None) -> float | None:
            if v is None:
                return None
            return round(float(v), 4)

        base.update(
            {
                "query_cosine_similarity": _round((query_cosine_map or {}).get(gid)),
                "content_cosine_similarity": _round((content_score_map or {}).get(gid)),
                "collaborative_cosine_similarity": _round((collab_score_map or {}).get(gid)),
                "knowledge_similarity": _round((knowledge_score_map or {}).get(gid)),
                "rag_similarity": _round((rag_score_map or {}).get(gid)),
            }
        )
        return base

    def _augment_metrics_with_gift_quality(
        self,
        metrics: dict,
        gifts: list[RecommendationWithGift],
    ) -> dict:
        if not gifts:
            metrics["validity_rate"] = 0.0
            metrics["invalidity_rate"] = 0.0
            metrics["avg_query_cosine_similarity"] = 0.0
            return metrics

        valid_flags = [bool(g.is_valid_recommendation) for g in gifts if g.is_valid_recommendation is not None]
        validity_scores = [float(g.validity_score) for g in gifts if g.validity_score is not None]
        query_cos = [float(g.query_cosine_similarity) for g in gifts if g.query_cosine_similarity is not None]

        invalid_reason_counts: dict[str, int] = {}
        for g in gifts:
            if not g.validity_reasons:
                continue
            for reason in g.validity_reasons:
                invalid_reason_counts[reason] = invalid_reason_counts.get(reason, 0) + 1

        if valid_flags:
            valid_count = sum(1 for v in valid_flags if v)
            total = len(valid_flags)
            metrics["valid_recommendations"] = valid_count
            metrics["invalid_recommendations"] = total - valid_count
            metrics["validity_rate"] = round(valid_count / max(total, 1), 4)
            metrics["invalidity_rate"] = round(1.0 - metrics["validity_rate"], 4)

        if validity_scores:
            metrics["avg_validity_score"] = round(sum(validity_scores) / len(validity_scores), 4)
        if query_cos:
            metrics["avg_query_cosine_similarity"] = round(sum(query_cos) / len(query_cos), 4)
        if invalid_reason_counts:
            metrics["top_invalid_reasons"] = sorted(
                invalid_reason_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:5]
        return metrics

    def _compute_metrics(
        self,
        scored: list[dict],
        liked_ids: set[int],
        all_gift_ids: set[int],
        top_n: int,
        gift_map: dict | None = None,
        occasion: str | None = None,
        relationship: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        age: str | None = None,
        gender: str | None = None,
        hobbies: str | None = None,
        prefer_context: bool = False,
    ) -> dict:
        """Compute model metrics.

        - interaction mode: classic classification metrics on interaction labels.
        - context mode: top-K ranking metrics against context-valid pool.
        """
        def _clamp(v: float) -> float:
            return max(0.0, min(v, 1.0))

        ranked_ids = [r["id"] for r in scored[:top_n]]
        recommended_ids = set(ranked_ids)
        predicted_score_map = {r["id"]: float(r.get("score", 0.0)) for r in scored[:top_n]}
        coverage = len(recommended_ids) / len(all_gift_ids) if all_gift_ids else 0.0

        mode = "interaction"
        positive_ids: set[int]
        if liked_ids and not prefer_context:
            positive_ids = set(liked_ids)
        else:
            mode = "context"
            pool_ids: set[int] = set()
            if gift_map:
                for gid, g in gift_map.items():
                    validity = self._build_gift_validity(
                        g,
                        occasion=occasion,
                        relationship=relationship,
                        min_price=min_price,
                        max_price=max_price,
                        age=age,
                        gender=gender,
                        hobbies=hobbies,
                    )
                    if validity.get("is_valid_recommendation") is True:
                        pool_ids.add(gid)
            positive_ids = pool_ids or set(all_gift_ids)

        k = max(1, top_n)
        rel_at_k = [1 if gid in positive_ids else 0 for gid in ranked_ids[:k]]
        hits_at_k = int(sum(rel_at_k))
        positive_count = len(positive_ids)

        precision_at_k = hits_at_k / k
        recall_at_k = (hits_at_k / positive_count) if positive_count > 0 else 0.0
        f1_at_k = (
            (2 * precision_at_k * recall_at_k) / (precision_at_k + recall_at_k)
            if (precision_at_k + recall_at_k) > 0
            else 0.0
        )
        hit_rate_at_k = 1.0 if hits_at_k > 0 else 0.0

        dcg = sum(
            (rel / math.log2(idx + 2))
            for idx, rel in enumerate(rel_at_k)
            if rel > 0
        )
        ideal_hits = min(k, positive_count)
        idcg = sum(1.0 / math.log2(idx + 2) for idx in range(ideal_hits))
        ndcg_at_k = (dcg / idcg) if idcg > 0 else 0.0

        running_hits = 0
        precision_sum = 0.0
        first_rel_rank: int | None = None
        for idx, rel in enumerate(rel_at_k, start=1):
            if rel:
                running_hits += 1
                precision_sum += running_hits / idx
                if first_rel_rank is None:
                    first_rel_rank = idx
        ap_denom = min(k, positive_count) if positive_count > 0 else 1
        map_at_k = precision_sum / ap_denom if ap_denom > 0 else 0.0
        mrr_at_k = (1.0 / first_rel_rank) if first_rel_rank else 0.0

        tp = hits_at_k
        fp = len(recommended_ids - positive_ids)
        fn = len(positive_ids - recommended_ids)
        tn = max(len(all_gift_ids) - tp - fp - fn, 0)
        cm = [[int(tn), int(fp)], [int(fn), int(tp)]]

        # Keep legacy keys for frontend compatibility; in context mode they mirror @K metrics.
        precision = precision_at_k
        recall = recall_at_k
        f1 = f1_at_k

        accuracy: float | None = None
        error_rate: float | None = None
        mae: float | None = None
        rmse: float | None = None
        if mode == "interaction":
            eval_ids = sorted(positive_ids | recommended_ids) or sorted(all_gift_ids)
            y_true = [1 if gid in positive_ids else 0 for gid in eval_ids]
            y_pred = [1 if gid in recommended_ids else 0 for gid in eval_ids]
            y_pred_score = [predicted_score_map.get(gid, 0.0) for gid in eval_ids]
            accuracy = float(accuracy_score(y_true, y_pred))
            error_rate = float(1.0 - accuracy)
            mae = float(mean_absolute_error(y_true, y_pred_score))
            rmse = float(mean_squared_error(y_true, y_pred_score) ** 0.5)

        return {
            "precision": round(_clamp(precision), 4),
            "recall": round(_clamp(recall), 4),
            "f1": round(_clamp(f1), 4),
            "f1_score": round(_clamp(f1), 4),
            "precision_at_k": round(_clamp(precision_at_k), 4),
            "recall_at_k": round(_clamp(recall_at_k), 4),
            "f1_at_k": round(_clamp(f1_at_k), 4),
            "hit_rate_at_k": round(_clamp(hit_rate_at_k), 4),
            "ndcg_at_k": round(_clamp(ndcg_at_k), 4),
            "map_at_k": round(_clamp(map_at_k), 4),
            "mrr_at_k": round(_clamp(mrr_at_k), 4),
            "hits_at_k": int(hits_at_k),
            "k": int(k),
            "positive_pool_size": int(positive_count),
            "accuracy": round(_clamp(accuracy), 4) if accuracy is not None else None,
            "error_rate": round(_clamp(error_rate), 4) if error_rate is not None else None,
            "mae": round(max(mae, 0.0), 4) if mae is not None else None,
            "rmse": round(max(rmse, 0.0), 4) if rmse is not None else None,
            "confusion_matrix": cm if mode == "interaction" else None,
            "tp": int(tp) if mode == "interaction" else None,
            "fp": int(fp) if mode == "interaction" else None,
            "tn": int(tn) if mode == "interaction" else None,
            "fn": int(fn) if mode == "interaction" else None,
            "coverage": round(_clamp(coverage), 4),
            "recommended_count": len(recommended_ids),
            "metrics_mode": mode,
        }

    async def compare_all_models(
        self,
        user_id: int,
        top_n: int = 6,
        occasion: str = None,
        relationship: str = None,
        min_price: float = None,
        max_price: float = None,
        query: str = None,
        age: str = None,
        gender: str = None,
        hobbies: str = None,
        age_exact: int | None = None,
        include_rag: bool = True,
    ) -> CompareResponse:
        """
        Run all 5 models and return their results side by side.
        New users (no history) get content + RAG only; collaborative and hybrid
        are marked as cold-start and show popularity-based fallback.
        """
        recommender = get_recommender()
        if not recommender._trained:
            await recommender.train(self.db)

        # --- User history ---
        user_interactions = await self.interaction_repo.get_user_interactions(user_id)
        liked_ids = {
            i.gift_id for i in user_interactions
            if i.interaction_type.value in ("purchase", "rating") and (i.rating is None or i.rating >= 3)
        }
        clicked_ids = {i.gift_id for i in user_interactions}
        user_has_history = len(clicked_ids) > 0

        # --- Gift map ---
        all_gifts = await self.gift_repo.get_all_gifts()
        gift_map = {g.id: g for g in all_gifts}
        all_gift_ids = set(gift_map.keys())

        def _clean_input(value: str | None) -> str | None:
            if value is None:
                return None
            cleaned = str(value).strip()
            if not cleaned:
                return None
            lowered = cleaned.lower()
            if lowered in {"none", "no", "nothing", "n/a", "na", "null", "unknown", "-", "0"}:
                return None
            return cleaned

        query = _clean_input(query)
        age = _clean_input(age)
        gender = _clean_input(gender)
        hobbies = _clean_input(hobbies)
        relationship = _clean_input(relationship)
        occasion = _clean_input(occasion)

        # Derive age_exact from age group label if not explicitly provided
        if age_exact is None and age:
            age_exact = _age_group_to_exact(age)

        # Build a structured natural language query for TF-IDF / vector search.
        # Avoids repeating raw taxonomy labels like "Child (0-12)" which don't match gift text.
        if query:
            # Use the explicit query if passed directly
            profile_query = query
        else:
            nl_parts = []
            if relationship:
                nl_parts.append(f"Gift for {relationship}")
            else:
                nl_parts.append("Gift")
            if occasion:
                nl_parts.append(f"for {occasion}")
            # Human-readable age: extract plain label (e.g. "Child" from "Child (0-12)")
            if age_exact is not None:
                nl_parts.append(f"aged {age_exact}")
            elif age:
                age_plain = age.split("(")[0].strip()  # "Child" from "Child (0-12)"
                nl_parts.append(f"age group {age_plain}")
            if gender:
                nl_parts.append(gender)
            if hobbies:
                # Repeat hobbies twice for TF-IDF signal boost (not 3x to avoid noise)
                nl_parts.append(f"who loves {hobbies}")
                nl_parts.append(hobbies)  # extra weight
            if max_price:
                nl_parts.append(f"under ${max_price:.0f}")
            profile_query = " ".join(nl_parts).strip() or None
        inputs_summary = "; ".join(
            [
                f"query={profile_query or '-'}",
                f"occasion={occasion or '-'}",
                f"relationship={relationship or '-'}",
                f"min_price={min_price if min_price is not None else '-'}",
                f"max_price={max_price if max_price is not None else '-'}",
            ]
        )

        # Query-to-item cosine similarity map for per-gift diagnostics
        query_cosine_map: dict[int, float] = {}
        try:
            if (
                profile_query
                and recommender.content_filter._is_fitted
                and recommender.content_filter.tfidf_matrix is not None
            ):
                q_vec = recommender.content_filter.vectorizer.transform([profile_query.lower().strip()])
                sims = cosine_similarity(q_vec, recommender.content_filter.tfidf_matrix).flatten()
                query_cosine_map = {
                    gid: float(sim)
                    for gid, sim in zip(recommender.content_filter.gift_ids, sims)
                }
        except Exception:
            query_cosine_map = {}

        # ---------- 1. Content-Based ----------
        age_group_label = match_age_group(age) if age else None
        age_groups = [age_group_label] if age_group_label else None

        content_scored = recommender.content_filter.get_scores_for_user_profile(
            liked_gift_ids=list(liked_ids) if liked_ids else [],
            top_n=top_n * 3,
            occasion=occasion,
            relationship=relationship,
            age_groups=age_groups,
            min_price=min_price,
            max_price=max_price,
            query_text=profile_query,
        )
        if not content_scored and profile_query:
            # Relax filters to avoid empty content results
            content_scored = recommender.content_filter.get_scores_for_query(
                query_text=profile_query,
                top_n=top_n * 3,
                occasion=None,
                relationship=None,
                age_groups=age_groups,
                min_price=min_price,
                max_price=max_price,
            )
        content_score_map = {r["id"]: float(r.get("score", 0.0)) for r in content_scored}
        content_meta: dict[int, dict] = {}
        for item in content_scored[:top_n]:
            gift = gift_map.get(item["id"])
            if not gift:
                continue
            content_meta[gift.id] = self._build_gift_diagnostics(
                gift,
                occasion=occasion,
                relationship=relationship,
                min_price=min_price,
                max_price=max_price,
                age=age,
                gender=gender,
                hobbies=hobbies,
                query_cosine_map=query_cosine_map,
                content_score_map=content_score_map,
            )
        content_gifts = self._scored_to_gifts(
            content_scored,
            gift_map,
            ModelType.content_based,
            top_n,
            per_gift_meta=content_meta,
        )
        content_metrics = self._compute_metrics(
            content_scored,
            liked_ids,
            all_gift_ids,
            top_n,
            gift_map=gift_map,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            age=age,
            gender=gender,
            hobbies=hobbies,
            prefer_context=True,
        )
        content_metrics = self._augment_metrics_with_gift_quality(content_metrics, content_gifts)
        content_metrics["inputs"] = inputs_summary

        # ---------- 2. Collaborative ----------
        is_cold_start = user_id not in recommender.collaborative_filter.user_ids
        collab_scored = recommender.collaborative_filter.get_scores_for_user(
            user_id=user_id,
            top_n=top_n * 3,
            exclude_gift_ids=list(clicked_ids),
        )

        # Blend collaborative with query-aware content scores for personalization
        collab_blend_mode = None
        content_for_query: list[dict] = []
        if profile_query:
            content_for_query = recommender.content_filter.get_scores_for_query(
                query_text=profile_query,
                top_n=top_n * 3,
                occasion=occasion,
                relationship=relationship,
                age_groups=age_groups,
                min_price=min_price,
                max_price=max_price,
            )
            content_map_q = {r["id"]: r["score"] for r in content_for_query}

            if is_cold_start:
                # For cold-start users, avoid static popularity-only outputs by heavily
                # weighting context-aware content signals.
                pop_map = {r["id"]: r["score"] for r in collab_scored}
                blended = []
                for gid in set(pop_map.keys()) | set(content_map_q.keys()):
                    blended.append({
                        "id": gid,
                        "score": round(0.25 * pop_map.get(gid, 0.0) + 0.75 * content_map_q.get(gid, 0.0), 6),
                    })
                blended.sort(key=lambda x: x["score"], reverse=True)
                collab_scored = blended[: top_n * 3]
                collab_blend_mode = "cold_pop_content_25_75"
            elif collab_scored:
                blended = []
                for r in collab_scored:
                    blended.append({
                        "id": r["id"],
                        "score": round(0.55 * r["score"] + 0.45 * content_map_q.get(r["id"], 0.0), 6),
                    })
                blended.sort(key=lambda x: x["score"], reverse=True)
                collab_scored = blended
                collab_blend_mode = "history_collab_content_55_45"

        # If collaborative returns nothing, fall back to context-aware content results
        # (avoid empty collaborative tab while still being transparent in metrics)
        collab_fallback = None
        if not collab_scored:
            collab_scored = recommender.content_filter.get_scores_for_query(
                query_text=profile_query,
                top_n=top_n * 3,
                occasion=occasion,
                relationship=relationship,
                age_groups=age_groups,
                min_price=min_price,
                max_price=max_price,
            )
            collab_fallback = "content_fallback"
        collab_scored = self._apply_feature_boosts(
            collab_scored,
            gift_map,
            hobbies=hobbies,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            age=age,
            gender=gender,
        )
        # Enforce validity-aware ranking so collaborative output is not random/popularity-only.
        collab_ranked: list[dict] = []
        for item in collab_scored:
            gift = gift_map.get(item["id"])
            if not gift:
                continue
            v = self._build_gift_validity(
                gift,
                occasion=occasion,
                relationship=relationship,
                min_price=min_price,
                max_price=max_price,
                age=age,
                gender=gender,
                hobbies=hobbies,
            )
            collab_ranked.append(
                {
                    "id": item["id"],
                    "score": float(item.get("score", 0.0)),
                    "_validity_score": float(v.get("validity_score") or 0.0),
                    "_is_valid": bool(v.get("is_valid_recommendation") is True),
                }
            )

        # If collaborative candidates are weak, supplement with highly valid
        # context-matching content candidates to avoid random recommendations.
        collab_supplemented = 0
        current_valid = sum(1 for r in collab_ranked if r["_is_valid"])
        if current_valid < top_n and content_for_query:
            existing_ids = {r["id"] for r in collab_ranked}
            for item in content_for_query:
                gid = item["id"]
                if gid in existing_ids:
                    continue
                gift = gift_map.get(gid)
                if not gift:
                    continue
                v = self._build_gift_validity(
                    gift,
                    occasion=occasion,
                    relationship=relationship,
                    min_price=min_price,
                    max_price=max_price,
                    age=age,
                    gender=gender,
                    hobbies=hobbies,
                )
                if v.get("is_valid_recommendation") is not True:
                    continue
                collab_ranked.append(
                    {
                        "id": gid,
                        "score": float(item.get("score", 0.0)),
                        "_validity_score": float(v.get("validity_score") or 0.0),
                        "_is_valid": True,
                    }
                )
                existing_ids.add(gid)
                collab_supplemented += 1
                current_valid += 1
                if current_valid >= top_n:
                    break

        collab_ranked.sort(
            key=lambda r: (r["_is_valid"], r["_validity_score"], r["score"]),
            reverse=True,
        )
        collab_scored = [{"id": r["id"], "score": r["score"]} for r in collab_ranked]
        collab_score_map = {r["id"]: float(r.get("score", 0.0)) for r in collab_scored}
        collab_meta: dict[int, dict] = {}
        for item in collab_scored[:top_n]:
            gift = gift_map.get(item["id"])
            if not gift:
                continue
            collab_meta[gift.id] = self._build_gift_diagnostics(
                gift,
                occasion=occasion,
                relationship=relationship,
                min_price=min_price,
                max_price=max_price,
                age=age,
                gender=gender,
                hobbies=hobbies,
                query_cosine_map=query_cosine_map,
                content_score_map=content_score_map,
                collab_score_map=collab_score_map,
            )
        collab_gifts = self._scored_to_gifts(
            collab_scored,
            gift_map,
            ModelType.collaborative,
            top_n,
            per_gift_meta=collab_meta,
        )
        collab_metrics = self._compute_metrics(
            collab_scored,
            liked_ids,
            all_gift_ids,
            top_n,
            gift_map=gift_map,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            age=age,
            gender=gender,
            hobbies=hobbies,
            prefer_context=True,
        )
        collab_metrics = self._augment_metrics_with_gift_quality(collab_metrics, collab_gifts)
        collab_metrics["inputs"] = inputs_summary
        collab_metrics["history_used"] = len(clicked_ids)
        if collab_blend_mode:
            collab_metrics["blend_mode"] = collab_blend_mode
        if collab_fallback:
            collab_metrics["fallback"] = collab_fallback
        if collab_supplemented:
            collab_metrics["validity_supplemented"] = collab_supplemented

        # ---------- 3. Knowledge-Based ----------
        knowledge = KnowledgeBasedRecommender()
        def _stringify(value) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            return str(value)

        knowledge_scored = knowledge.score_gifts(
            gifts=[
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description or "",
                    "occasion": g.occasion or "",
                    "relationship": g.relationship or "",
                    "category_name": g.category.name if g.category else "",
                    "tags": _stringify(getattr(g, "tags", "")),
                    "age_group": _stringify(getattr(g, "age_group", "")),
                    "price": g.price,
                }
                for g in all_gifts
            ],
            top_n=top_n * 3,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            query_text=profile_query,
            age=age,
            gender=gender,
            hobbies=hobbies,
            age_exact=age_exact,
        )
        knowledge_score_map = {r["id"]: float(r.get("score", 0.0)) for r in knowledge_scored}
        knowledge_meta: dict[int, dict] = {}
        for item in knowledge_scored[:top_n]:
            gift = gift_map.get(item["id"])
            if not gift:
                continue
            knowledge_meta[gift.id] = self._build_gift_diagnostics(
                gift,
                occasion=occasion,
                relationship=relationship,
                min_price=min_price,
                max_price=max_price,
                age=age,
                gender=gender,
                hobbies=hobbies,
                query_cosine_map=query_cosine_map,
                content_score_map=content_score_map,
                collab_score_map=collab_score_map,
                knowledge_score_map=knowledge_score_map,
            )
        knowledge_gifts_result = self._scored_to_gifts(
            knowledge_scored,
            gift_map,
            ModelType.knowledge_based,
            top_n,
            per_gift_meta=knowledge_meta,
        )
        knowledge_metrics = self._compute_metrics(
            knowledge_scored,
            liked_ids,
            all_gift_ids,
            top_n,
            gift_map=gift_map,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            age=age,
            gender=gender,
            hobbies=hobbies,
            prefer_context=True,
        )
        knowledge_metrics = self._augment_metrics_with_gift_quality(
            knowledge_metrics,
            knowledge_gifts_result,
        )
        knowledge_metrics["inputs"] = inputs_summary

        # ---------- 4. Hybrid (Content + Collaborative + Knowledge) ----------
        hybrid_scored = recommender.recommend(
            user_id=user_id,
            liked_gift_ids=list(liked_ids),
            top_n=top_n * 3,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            age_groups=age_groups,
            query_text=profile_query,
            knowledge_gifts=knowledge_scored,
        )
        hybrid_score_map = {r["id"]: float(r.get("score", 0.0)) for r in hybrid_scored}
        hybrid_meta: dict[int, dict] = {}
        for item in hybrid_scored[:top_n]:
            gift = gift_map.get(item["id"])
            if not gift:
                continue
            hybrid_meta[gift.id] = self._build_gift_diagnostics(
                gift,
                occasion=occasion,
                relationship=relationship,
                min_price=min_price,
                max_price=max_price,
                age=age,
                gender=gender,
                hobbies=hobbies,
                query_cosine_map=query_cosine_map,
                content_score_map=content_score_map,
                collab_score_map=collab_score_map,
                knowledge_score_map=knowledge_score_map,
            )
        hybrid_gifts = self._scored_to_gifts(
            hybrid_scored,
            gift_map,
            ModelType.hybrid,
            top_n,
            per_gift_meta=hybrid_meta,
        )
        hybrid_metrics = self._compute_metrics(
            hybrid_scored,
            liked_ids,
            all_gift_ids,
            top_n,
            gift_map=gift_map,
            occasion=occasion,
            relationship=relationship,
            min_price=min_price,
            max_price=max_price,
            age=age,
            gender=gender,
            hobbies=hobbies,
            prefer_context=True,
        )
        hybrid_metrics = self._augment_metrics_with_gift_quality(hybrid_metrics, hybrid_gifts)
        hybrid_metrics["content_weight"] = recommender.content_weight
        hybrid_metrics["collab_weight"] = recommender.collaborative_weight
        hybrid_metrics["knowledge_weight"] = recommender.knowledge_weight
        hybrid_metrics["inputs"] = inputs_summary

        # ---------- 5. RAG ----------
        rag_scored: list[dict] = []
        rag_score_map: dict[int, float] = {}
        rag_gifts: list[RecommendationWithGift] = []
        rag_explanation: str = ""
        rag_metrics: dict = {}
        if include_rag:
            try:
                from app.services.rag.rag_service import RAGService
                from app.schemas.recommendation import RAGQueryCreate
                rag_svc = RAGService()
                # Build a rich query using ALL form inputs
                if query:
                    rag_query = query
                else:
                    parts = []
                    parts.append(f"Gift for {relationship or 'someone special'}")
                    parts.append(f"for {occasion or 'a special occasion'}")
                    if age:
                        parts.append(f"aged {age}")
                    if gender:
                        parts.append(f"({gender})")
                    if hobbies:
                        parts.append(f"who enjoys {hobbies}")
                    if max_price:
                        parts.append(f"under ${max_price:.0f}")
                    rag_query = " ".join(parts)
                rag_result = await rag_svc.ask(
                    db=self.db,
                    user_id=user_id,
                    request=RAGQueryCreate(
                        query=rag_query,
                        top_k=top_n,
                        occasion=occasion,
                        relationship=relationship,
                        budget_max=max_price,
                        age=age,
                        gender=gender,
                        hobbies=hobbies,
                    ),
                )
                rag_explanation = rag_result.get("response", "")
                rag_candidates: list[tuple[Gift, dict]] = []
                rag_supplemented = 0
                for g_dict in rag_result.get("retrieved_gifts", []):
                    gift = gift_map.get(g_dict["id"])
                    if gift is None:
                        continue
                    provisional_meta = self._build_gift_diagnostics(
                        gift,
                        occasion=occasion,
                        relationship=relationship,
                        min_price=min_price,
                        max_price=max_price,
                        age=age,
                        gender=gender,
                        hobbies=hobbies,
                        query_cosine_map=query_cosine_map,
                        content_score_map=content_score_map,
                        collab_score_map=collab_score_map,
                        knowledge_score_map=knowledge_score_map,
                        rag_score_map={gift.id: 1.0},
                    )
                    rag_candidates.append((gift, provisional_meta))

                # Prefer gifts that satisfy constraints, then rank by validity + similarity.
                valid_candidates = [c for c in rag_candidates if c[1].get("is_valid_recommendation") is True]
                ranked = valid_candidates or rag_candidates
                ranked.sort(
                    key=lambda c: (
                        float(c[1].get("validity_score") or 0.0),
                        float(c[1].get("query_cosine_similarity") or 0.0),
                    ),
                    reverse=True,
                )
                ranked = ranked[:top_n]

                # If RAG retrieval quality is weak for this context, supplement from
                # strong context-aware content candidates to keep results meaningful.
                if len(valid_candidates) < max(2, top_n // 2):
                    existing = {gift.id for gift, _meta in ranked}
                    valid_ranked = sum(
                        1 for _gift, meta in ranked if meta.get("is_valid_recommendation") is True
                    )
                    for item in content_scored:
                        gid = item["id"]
                        if gid in existing:
                            continue
                        gift = gift_map.get(gid)
                        if not gift:
                            continue
                        meta = self._build_gift_diagnostics(
                            gift,
                            occasion=occasion,
                            relationship=relationship,
                            min_price=min_price,
                            max_price=max_price,
                            age=age,
                            gender=gender,
                            hobbies=hobbies,
                            query_cosine_map=query_cosine_map,
                            content_score_map=content_score_map,
                            collab_score_map=collab_score_map,
                            knowledge_score_map=knowledge_score_map,
                        )
                        if meta.get("is_valid_recommendation") is not True:
                            continue
                        ranked.append((gift, meta))
                        existing.add(gid)
                        rag_supplemented += 1
                        valid_ranked += 1
                        if valid_ranked >= top_n:
                            break

                ranked.sort(
                    key=lambda c: (
                        float(c[1].get("is_valid_recommendation") is True),
                        float(c[1].get("validity_score") or 0.0),
                        float(c[1].get("query_cosine_similarity") or 0.0),
                        float(c[1].get("content_cosine_similarity") or 0.0),
                    ),
                    reverse=True,
                )
                ranked = ranked[:top_n]

                for gift, meta in ranked:
                    score = float(meta.get("validity_score") or 0.5)
                    rag_scored.append({"id": gift.id, "score": max(0.01, min(1.0, score))})
                rag_score_map = {r["id"]: float(r.get("score", 0.0)) for r in rag_scored}
                rag_meta: dict[int, dict] = {}
                for item in rag_scored[:top_n]:
                    gift = gift_map.get(item["id"])
                    if not gift:
                        continue
                    rag_meta[gift.id] = self._build_gift_diagnostics(
                        gift,
                        occasion=occasion,
                        relationship=relationship,
                        min_price=min_price,
                        max_price=max_price,
                        age=age,
                        gender=gender,
                        hobbies=hobbies,
                        query_cosine_map=query_cosine_map,
                        content_score_map=content_score_map,
                        collab_score_map=collab_score_map,
                        knowledge_score_map=knowledge_score_map,
                        rag_score_map=rag_score_map,
                    )
                rag_gifts = self._scored_to_gifts(
                    rag_scored,
                    gift_map,
                    ModelType.rag,
                    top_n,
                    per_gift_meta=rag_meta,
                )
                rag_metrics = self._compute_metrics(
                    rag_scored,
                    liked_ids,
                    all_gift_ids,
                    top_n,
                    gift_map=gift_map,
                    occasion=occasion,
                    relationship=relationship,
                    min_price=min_price,
                    max_price=max_price,
                    age=age,
                    gender=gender,
                    hobbies=hobbies,
                    prefer_context=True,
                )
                rag_metrics = self._augment_metrics_with_gift_quality(rag_metrics, rag_gifts)
                rag_metrics.update({
                    "retrieved_count": len(rag_gifts),
                    "query_used": rag_query,
                    "inputs": inputs_summary,
                })
                if rag_supplemented:
                    rag_metrics["validity_supplemented"] = rag_supplemented
            except Exception as e:
                logger.error("compare.rag_failed", error=str(e))
                try:
                    # RAG failures can leave transaction state aborted (asyncpg).
                    await self.db.rollback()
                except Exception:
                    pass
                rag_explanation = "RAG unavailable — check OPENAI_API_KEY."
                rag_metrics = {"error": str(e)}
        else:
            rag_explanation = "RAG skipped for this evaluation pass."
            rag_metrics = {"skipped": True}

        models = [
            ModelResult(
                model="content",
                label="Content-Based (TF-IDF + Cosine)",
                gifts=content_gifts,
                is_cold_start=not bool(liked_ids),
                metrics=content_metrics,
            ),
            ModelResult(
                model="collaborative",
                label="Collaborative (User Similarity)",
                gifts=collab_gifts,
                is_cold_start=is_cold_start,
                metrics=collab_metrics,
            ),
            ModelResult(
                model="hybrid",
                label="Hybrid (Content + Collaborative + Knowledge)",
                gifts=hybrid_gifts,
                is_cold_start=is_cold_start and not bool(liked_ids),
                metrics=hybrid_metrics,
            ),
            ModelResult(
                model="knowledge",
                label="Knowledge-Based (Rules + Keywords)",
                gifts=knowledge_gifts_result,
                is_cold_start=False,
                metrics=knowledge_metrics,
            ),
            ModelResult(
                model="rag",
                label="RAG (OpenAI + Vector Search)",
                gifts=rag_gifts,
                is_cold_start=False,
                metrics=rag_metrics,
                explanation=rag_explanation,
            ),
        ]

        return CompareResponse(user_has_history=user_has_history, models=models)

    async def get_home_recommendations(self, user_id: int, top_n: int = 8) -> list[RecommendationWithGift]:
        """Recommend gifts for the homepage using profile data and past interactions."""
        recommender = get_recommender()
        if not recommender._trained:
            await recommender.train(self.db)

        profile = await self.profile_repo.get_by_user_id(user_id)
        interactions = await self.interaction_repo.get_user_interactions(user_id, limit=100)
        # Treat purchases/high ratings as strong signal; clicks as soft signal.
        # This makes homepage recommendations adapt to past picks even when users don't rate.
        positive_ids: list[int] = []
        clicked_ids: set[int] = set()
        for i in interactions:
            itype = i.interaction_type.value
            clicked_ids.add(i.gift_id)
            if itype == "purchase":
                positive_ids.append(i.gift_id)
            elif itype == "rating" and (i.rating is None or i.rating >= 3):
                positive_ids.append(i.gift_id)
            elif itype == "click":
                positive_ids.append(i.gift_id)

        # Keep order stable and avoid duplicates.
        liked_ids = list(dict.fromkeys(positive_ids))

        # Extract profile data
        resolved_age = profile.age if profile else None
        resolved_gender = profile.gender if profile else None
        resolved_hobbies = profile.hobbies if profile else None
        resolved_occasion = None
        resolved_relationship = profile.relationship if profile else None

        query_parts = []
        category_pref = None
        age_group_pref = None
        tags_pref = None

        if profile:
            if resolved_age:
                query_parts.append(f"age {resolved_age}")
            if resolved_gender:
                query_parts.append(resolved_gender)
            if resolved_hobbies:
                query_parts.append(f"who loves {resolved_hobbies}")
                query_parts.append(resolved_hobbies)  # extra weight
            if resolved_relationship:
                query_parts.append(f"Gift for {resolved_relationship}")
            if profile.occasion:
                query_parts.append(profile.occasion)
            if profile.occasions:
                resolved_occasion = profile.occasions[0]
            if profile.favorite_categories:
                category_pref = profile.favorite_categories
            if profile.gifting_for_ages:
                age_group_pref = profile.gifting_for_ages
            if profile.interests:
                tags_pref = profile.interests
            if profile.budget_max:
                query_parts.append(f"under ${profile.budget_max:.0f}")
        profile_query = " ".join([p for p in query_parts if p]).strip() or None

        def _stringify(value) -> str:
            if value is None:
                return ""
            if isinstance(value, str):
                return value
            return str(value)

        # Content-based scoring
        scored = recommender.content_filter.get_scores_for_user_profile(
            liked_gift_ids=liked_ids,
            top_n=top_n * 3,
            occasion=resolved_occasion or (profile.occasion if profile else None),
            relationship=resolved_relationship,
            category_names=category_pref,
            age_groups=age_group_pref,
            tags=tags_pref,
            min_price=profile.budget_min if profile else None,
            max_price=profile.budget_max if profile else None,
            query_text=profile_query,
        )

        # Fallback to query-based ranking if profile/filters are too strict
        if not scored:
            scored = recommender.content_filter.get_scores_for_query(
                query_text=profile_query,
                top_n=top_n * 3,
                occasion=resolved_occasion or (profile.occasion if profile else None),
                relationship=resolved_relationship,
                category_names=category_pref,
                age_groups=age_group_pref,
                tags=tags_pref,
                min_price=profile.budget_min if profile else None,
                max_price=profile.budget_max if profile else None,
            )

        # Relax constraints if strict profile filters still return nothing.
        if not scored:
            scored = recommender.content_filter.get_scores_for_query(
                query_text=profile_query,
                top_n=top_n * 3,
                occasion=None,
                relationship=None,
                category_names=None,
                age_groups=None,
                tags=None,
                min_price=profile.budget_min if profile else None,
                max_price=profile.budget_max if profile else None,
            )

        # Last-resort catalog fallback (works for brand-new users).
        if not scored:
            scored = recommender.content_filter.get_scores_for_query(
                query_text=None,
                top_n=top_n * 3,
                occasion=None,
                relationship=None,
                category_names=None,
                age_groups=None,
                tags=None,
                min_price=None,
                max_price=None,
            )
        if not scored:
            return []

        # Resolve only shortlisted gifts from DB instead of loading entire catalog.
        # This keeps homepage recommendations responsive on large datasets.
        candidate_ids = list(dict.fromkeys(item["id"] for item in scored))
        gifts_result = await self.db.execute(
            select(Gift)
            .options(selectinload(Gift.category))
            .where(Gift.id.in_(candidate_ids))
        )
        gift_map = {g.id: g for g in gifts_result.scalars().all()}
        if not gift_map:
            return []

        # Keep only items that still exist in the catalog.
        scored = [item for item in scored if item["id"] in gift_map]
        if not scored:
            return []

        # Knowledge-based scoring using only shortlisted candidates.
        candidate_gifts = [gift_map[item["id"]] for item in scored]
        knowledge_scored = KnowledgeBasedRecommender().score_gifts(
            gifts=[
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description or "",
                    "occasion": g.occasion or "",
                    "relationship": g.relationship or "",
                    "category_name": g.category.name if g.category else "",
                    "tags": _stringify(getattr(g, "tags", "")),
                    "age_group": _stringify(getattr(g, "age_group", "")),
                    "price": g.price,
                }
                for g in candidate_gifts
            ],
            top_n=max(len(candidate_gifts), top_n * 3),
            occasion=resolved_occasion or (profile.occasion if profile else None),
            relationship=resolved_relationship,
            min_price=profile.budget_min if profile else None,
            max_price=profile.budget_max if profile else None,
            query_text=profile_query,
            age=resolved_age,
            gender=resolved_gender,
            hobbies=resolved_hobbies,
        )

        # Blend knowledge scores into content scores
        know_map = {r["id"]: r["score"] for r in knowledge_scored}
        for item in scored:
            k_score = know_map.get(item["id"], 0.0)
            # Blend: 80% content + 20% knowledge
            item["score"] = round(0.80 * item["score"] + 0.20 * k_score, 6)
        scored.sort(key=lambda x: x["score"], reverse=True)

        # Apply feature boosts with all profile signals
        scored = self._apply_feature_boosts(
            scored,
            gift_map,
            hobbies=resolved_hobbies,
            occasion=resolved_occasion or (profile.occasion if profile else None),
            relationship=resolved_relationship,
            min_price=profile.budget_min if profile else None,
            max_price=profile.budget_max if profile else None,
            age=resolved_age,
            gender=resolved_gender,
        )

        return self._scored_to_gifts(scored, gift_map, ModelType.content_based, top_n)
