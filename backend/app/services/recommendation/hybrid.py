"""
Hybrid Recommendation Engine.

Combines:
- Content-Based Filtering (TF-IDF + Cosine Similarity)
- Collaborative Filtering (User-Item Matrix + Cosine Similarity)
- Knowledge-Based scoring (rules + keyword overlap)

Final Score Formula:
    final = content_w * content + collab_w * collab + knowledge_w * knowledge

Defaults: content_w=0.55, collab_w=0.35, knowledge_w=0.10

Includes:
- Automatic retraining on interaction data
- Cold start fallback
- Configurable weights
"""

import asyncio
from typing import Optional
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.core.taxonomy import match_age_group
from app.models.models import Gift, Interaction
from app.repositories.gift_repository import GiftRepository
from app.repositories.interaction_repository import InteractionRepository
from app.services.recommendation.content_based import ContentBasedFilter
from app.services.recommendation.collaborative import CollaborativeFilter


class HybridRecommender:
    def __init__(
        self,
        content_weight: float = 0.55,
        collaborative_weight: float = 0.35,
        knowledge_weight: float = 0.10,
    ):
        self.content_weight = content_weight
        self.collaborative_weight = collaborative_weight
        self.knowledge_weight = knowledge_weight
        # Blend defaults for content (can be tuned)
        self.content_filter = ContentBasedFilter(tfidf_weight=0.6, embed_weight=0.4)
        self.collaborative_filter = CollaborativeFilter()
        self._trained = False

    def set_weights(self, content: float, collaborative: float, knowledge: float = 0.0) -> None:
        if abs(content + collaborative + knowledge - 1.0) > 1e-6:
            raise ValueError("Weights must sum to 1.0")
        self.content_weight = content
        self.collaborative_weight = collaborative
        self.knowledge_weight = knowledge

    async def train(self, db: AsyncSession) -> None:
        """
        Load all gifts, interactions, and user profiles from DB, fit both models.
        User profiles are encoded as feature vectors and blended into collaborative
        filtering similarity (70% interaction-based + 30% profile-based).
        """
        from app.repositories.user_profile_repository import UserProfileRepository
        from app.core.taxonomy import HOBBIES, AGE_GROUPS, RELATIONSHIPS, OCCASIONS

        gift_repo = GiftRepository(db)
        interaction_repo = InteractionRepository(db)
        profile_repo = UserProfileRepository(db)

        all_gifts = await gift_repo.get_all_gifts()
        all_interactions = await interaction_repo.get_all_interactions_for_matrix()

        if not all_gifts:
            logger.warning("hybrid_recommender.no_gifts_to_train")
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
                "age_group": g.age_group or "",
                "price": g.price,
                "embedding": (list(g.embedding) if getattr(g, "embedding", None) is not None else None),
            }
            for g in all_gifts
        ]

        interaction_dicts = [
            {
                "user_id": i.user_id,
                "gift_id": i.gift_id,
                "interaction_type": i.interaction_type.value,
                "rating": i.rating,
            }
            for i in all_interactions
        ]

        self.content_filter.fit(gift_dicts)

        # Build profile feature vectors for blended collaborative similarity
        profile_vectors = None
        try:
            all_profiles = await profile_repo.get_all()
            if all_profiles:
                # Determine user_ids that will appear in the interaction matrix
                interaction_user_ids = sorted({d["user_id"] for d in interaction_dicts})
                profiles_by_user = {p.user_id: p for p in all_profiles}

                # Encode features: age_group (6) + gender (4) + hobbies (multi-hot, top 40) + occasion (14) + relationship (23)
                hobby_index = {h: i for i, h in enumerate(HOBBIES[:40])}  # top 40 hobbies
                age_index = {a: i for i, a in enumerate(AGE_GROUPS)}
                gender_index = {"Male": 0, "Female": 1, "Non-binary": 2, "Prefer not to say": 3}
                occ_index = {o: i for i, o in enumerate(OCCASIONS)}
                rel_index = {r: i for i, r in enumerate(RELATIONSHIPS)}

                n_features = len(AGE_GROUPS) + 4 + len(HOBBIES[:40]) + len(OCCASIONS) + len(RELATIONSHIPS)
                vectors = []

                for uid in interaction_user_ids:
                    vec = np.zeros(n_features, dtype=np.float32)
                    p = profiles_by_user.get(uid)
                    if p:
                        # Age group one-hot
                        if p.age and p.age in age_index:
                            vec[age_index[p.age]] = 1.0
                        age_off = len(AGE_GROUPS)
                        # Gender one-hot
                        if p.gender and p.gender in gender_index:
                            vec[age_off + gender_index[p.gender]] = 1.0
                        hobby_off = age_off + 4
                        # Hobbies multi-hot (from comma-separated string or list)
                        raw_hobbies = p.hobbies or ""
                        if isinstance(raw_hobbies, list):
                            hobby_list = raw_hobbies
                        else:
                            hobby_list = [h.strip() for h in raw_hobbies.split(",") if h.strip()]
                        for h in hobby_list:
                            if h in hobby_index:
                                vec[hobby_off + hobby_index[h]] = 1.0
                        occ_off = hobby_off + len(HOBBIES[:40])
                        # Occasion one-hot
                        if p.occasion and p.occasion in occ_index:
                            vec[occ_off + occ_index[p.occasion]] = 1.0
                        rel_off = occ_off + len(OCCASIONS)
                        # Relationship one-hot
                        if p.relationship and p.relationship in rel_index:
                            vec[rel_off + rel_index[p.relationship]] = 1.0
                    vectors.append(vec)

                if vectors:
                    profile_vectors = np.stack(vectors, axis=0)
                    logger.info(
                        "hybrid_recommender.profile_vectors_built",
                        n_users=len(vectors),
                        n_features=n_features,
                    )
        except Exception as e:
            logger.warning("hybrid_recommender.profile_vector_build_failed", error=str(e))
            profile_vectors = None

        self.collaborative_filter.fit(interaction_dicts, profile_vectors=profile_vectors)
        self._trained = True
        logger.info(
            "hybrid_recommender.trained",
            n_gifts=len(all_gifts),
            n_interactions=len(all_interactions),
            profile_blending=profile_vectors is not None,
        )


    def recommend(
        self,
        user_id: int,
        liked_gift_ids: list[int],
        top_n: int = settings.TOP_N_RECOMMENDATIONS,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        category_names: Optional[list[str]] = None,
        age_groups: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        gender: Optional[str] = None,
        query_text: Optional[str] = None,
        knowledge_gifts: Optional[list[dict]] = None,
    ) -> list[dict]:
        """
        Generate hybrid recommendations.

        Returns:
            List of dicts: [{"id": gift_id, "score": float, "content_score": float,
                             "collab_score": float, "knowledge_score": float}]
        """
        if not self._trained:
            logger.warning("hybrid_recommender.not_trained")
            return []

        # --- Content scores ---
        content_results = self.content_filter.get_scores_for_user_profile(
            liked_gift_ids=liked_gift_ids,
            top_n=max(top_n * 6, 60),
            occasion=occasion,
            relationship=relationship,
            category_names=category_names,
            age_groups=age_groups,
            tags=tags,
            min_price=min_price,
            max_price=max_price,
            query_text=query_text,
        )
        # If profile-based ranking over-constrains candidates, fall back to query ranking.
        if not content_results and query_text:
            content_results = self.content_filter.get_scores_for_query(
                query_text=query_text,
                top_n=max(top_n * 6, 60),
                occasion=occasion,
                relationship=relationship,
                category_names=category_names,
                age_groups=age_groups,
                tags=tags,
                min_price=min_price,
                max_price=max_price,
            )
        # Last-resort relaxed query fallback to avoid empty hybrid output for heavy-history users.
        if not content_results and query_text:
            content_results = self.content_filter.get_scores_for_query(
                query_text=query_text,
                top_n=max(top_n * 6, 60),
                occasion=None,
                relationship=None,
                category_names=None,
                age_groups=age_groups,
                tags=None,
                min_price=min_price,
                max_price=max_price,
            )
        content_map = {r["id"]: r["score"] for r in content_results}

        # --- Collaborative scores ---
        collab_results = self.collaborative_filter.get_scores_for_user(
            user_id=user_id,
            top_n=max(top_n * 10, 100),  # Fetch a larger pool for filtering
            exclude_gift_ids=liked_gift_ids,
            diversity_lambda=0.78,
            candidate_pool=max(top_n * 15, 200),
        )
        collab_ids = [r["id"] for r in collab_results]
        
        # Filter collaborative results using master gift_df
        if collab_ids and self.content_filter.gift_df is not None:
            if "id" not in self.content_filter.gift_df.columns:
                logger.warning("hybrid_recommender.gift_df_missing_id_for_collab_filter")
                collab_map = {}
            else:
                df = self.content_filter.gift_df[
                    self.content_filter.gift_df["id"].isin(collab_ids)
                ].copy()
                filtered_df = self.content_filter._apply_filters(
                    df,
                    occasion,
                    relationship,
                    category_names,
                    age_groups,
                    tags,
                    min_price,
                    max_price,
                )
                if "id" not in filtered_df.columns:
                    logger.warning("hybrid_recommender.filtered_collab_missing_id")
                    collab_map = {}
                else:
                    allowed_collab_ids = set(filtered_df["id"])
                    collab_map = {
                        r["id"]: r["score"]
                        for r in collab_results
                        if r["id"] in allowed_collab_ids
                    }
        else:
            collab_map = {}

        # --- Knowledge map (optional) ---
        know_map = {r["id"]: r["score"] for r in (knowledge_gifts or [])}
        # Ensure knowledge gifts also satisfy global filters (redundancy check)
        if know_map and self.content_filter.gift_df is not None:
            if "id" not in self.content_filter.gift_df.columns:
                logger.warning("hybrid_recommender.gift_df_missing_id_for_knowledge_filter")
                know_map = {}
            else:
                df = self.content_filter.gift_df[
                    self.content_filter.gift_df["id"].isin(know_map.keys())
                ].copy()
                filtered_df = self.content_filter._apply_filters(
                    df,
                    occasion,
                    relationship,
                    category_names,
                    age_groups,
                    tags,
                    min_price,
                    max_price,
                )
                if "id" not in filtered_df.columns:
                    logger.warning("hybrid_recommender.filtered_knowledge_missing_id")
                    know_map = {}
                else:
                    allowed_know_ids = set(filtered_df["id"])
                    know_map = {
                        gid: score
                        for gid, score in know_map.items()
                        if gid in allowed_know_ids
                    }

        # Adjust weights if collaborative has no signal or for Cold Start
        content_weight = self.content_weight
        collaborative_weight = self.collaborative_weight
        knowledge_weight = self.knowledge_weight
        
        # Cold Start check: If user has < 3 likes, dampen popularity influence
        if not liked_gift_ids or len(liked_gift_ids) < 3:
            # Shift 70% of collab weight to knowledge/content to favor specific inputs
            shift = collaborative_weight * 0.7
            collaborative_weight -= shift
            knowledge_weight += shift * 0.4
            content_weight += shift * 0.6
            logger.info("hybrid_recommender.cold_start_dampening", user_id=user_id, collab_w=collaborative_weight)

        if not collab_results:
            # redistribute collab share to content + knowledge
            extra = collaborative_weight
            content_weight = min(0.85, content_weight + extra * 0.75)
            knowledge_weight = min(0.25, knowledge_weight + extra * 0.25)
            collaborative_weight = 0.0

        # --- Merge all candidate gift IDs ---
        all_gift_ids = set(content_map.keys()) | set(collab_map.keys()) | set(know_map.keys())

        # Prepare for demographic penalties
        target_age_group = age_groups[0] if age_groups and len(age_groups) > 0 else None
        
        results = []
        for gid in all_gift_ids:
            c_score = content_map.get(gid, 0.0)
            cf_score = collab_map.get(gid, 0.0)
            k_score = know_map.get(gid, 0.0)
            
            final = content_weight * c_score + collaborative_weight * cf_score + knowledge_weight * k_score
            
            # --- Demographic Penalty ---
            penalty = 1.0
            if (
                (target_age_group or gender)
                and self.content_filter.gift_df is not None
                and "id" in self.content_filter.gift_df.columns
            ):
                gift_data = self.content_filter.gift_df[
                    self.content_filter.gift_df["id"] == gid
                ]
                if not gift_data.empty:
                    row = gift_data.iloc[0]
                    # Normalize gift age
                    raw_gift_age = str(row.get("age_group", "") or "")
                    gift_age_label = match_age_group(raw_gift_age) or ""
                    gift_age_lower = gift_age_label.lower()
                    
                    target_age_lower = target_age_group.lower() if target_age_group else ""
                    
                    # Age Mismatch Penalties
                    if target_age_lower:
                        if "child" in target_age_lower:
                            if "adult" in gift_age_lower or "middle" in gift_age_lower or "senior" in gift_age_lower:
                                penalty *= 0.1
                            elif "teen" in gift_age_lower:
                                penalty *= 0.4
                        elif "teen" in target_age_lower:
                            if "child" in gift_age_lower:
                                penalty *= 0.3
                            elif "senior" in gift_age_lower:
                                penalty *= 0.1
                        elif "senior" in target_age_lower:
                            if "child" in gift_age_lower:
                                penalty *= 0.1
                            elif "teen" in gift_age_lower:
                                penalty *= 0.5
                    
                    # --- Gender Penalty ---
                    # If target is Male, penalize gifts that are exclusively Female-coded
                    # This helps avoid 'Flower Bouquet' or 'Jewelry' takeover for boys
                    if gender:
                        g_lower = gender.lower()
                        title = str(row.get("title", "")).lower()
                        tags = str(row.get("tags", "")).lower()
                        combined = title + " " + tags
                        
                        if "male" in g_lower or "boy" in g_lower or "man" in g_lower:
                            female_signals = ["flower", "women", "lady", "female", "jewelry", "necklace", "bracelet", "skincare", "makeup"]
                            if any(sig in combined for sig in female_signals):
                                # Only penalize if it's NOT also matching male signals or hobby tags
                                if not any(sig in combined for sig in ["men", "male", "guy", "unisex"]):
                                    penalty *= 0.25 # Substantial penalty for gender-mismatch signals
                        elif "female" in g_lower or "girl" in g_lower or "woman" in g_lower:
                            male_signals = ["men", "male", "guy", "masculine", "beard", "shaving"]
                            if any(sig in combined for sig in male_signals):
                                if not any(sig in combined for sig in ["women", "female", "lady", "unisex"]):
                                    penalty *= 0.25
            
            final *= penalty

            results.append(
                {
                    "id": gid,
                    "score": round(final, 6),
                    "content_score": round(c_score, 6),
                    "collab_score": round(cf_score, 6),
                    "knowledge_score": round(k_score, 6),
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        if not results:
            return []

        # Exploration: slightly boost items that only one model surfaced.
        # This helps avoid the same gifts repeating when one model dominates.
        content_only = set(content_map.keys()) - set(collab_map.keys())
        collab_only = set(collab_map.keys()) - set(content_map.keys())
        for r in results:
            gid = r["id"]
            if gid in content_only or gid in collab_only:
                r["score"] = round(min(1.0, float(r["score"]) + 0.03), 6)

        results.sort(key=lambda x: x["score"], reverse=True)

        # Diversity re-ranking across the final list.
        results = self._mmr_diversify(results, k=top_n, diversity_lambda=0.80)
        # Keep contract: sorted by final score desc.
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_n]

    def _mmr_diversify(self, scored_items: list[dict], k: int, diversity_lambda: float = 0.8) -> list[dict]:
        """MMR diversify using content TF-IDF space when available.

        We use precomputed TF-IDF matrix inside ContentBasedFilter, which correlates with semantic similarity.
        """
        if not scored_items or not getattr(self.content_filter, "_is_fitted", False):
            return scored_items[:k]
        if self.content_filter.tfidf_matrix is None or not self.content_filter.gift_ids:
            return scored_items[:k]

        id_to_idx = {gid: i for i, gid in enumerate(self.content_filter.gift_ids)}
        candidates = [it for it in scored_items if it["id"] in id_to_idx]
        if len(candidates) <= 1:
            return scored_items[:k]

        # Build dense vectors for similarity for candidates (OK for small candidate pools)
        X = self.content_filter.tfidf_matrix[[id_to_idx[it["id"]] for it in candidates]]
        # Convert to dense float32 for fast cosine via dot after row-normalization
        X = X.astype(np.float32).toarray()
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
        X = X / norms
        sim = X @ X.T

        diversity_lambda = float(np.clip(diversity_lambda, 0.0, 1.0))

        selected: list[int] = []
        remaining = list(range(len(candidates)))
        selected.append(remaining.pop(0))
        while remaining and len(selected) < k:
            best = None
            best_score = -1e9
            for i in remaining:
                rel = float(candidates[i]["score"])
                red = max((float(sim[i, j]) for j in selected), default=0.0)
                mmr = diversity_lambda * rel - (1.0 - diversity_lambda) * red
                if mmr > best_score:
                    best_score = mmr
                    best = i
            selected.append(best)
            remaining.remove(best)

        reranked = [candidates[i] for i in selected]
        # Append any items not included (keeps deterministic behavior)
        selected_ids = {it["id"] for it in reranked}
        tail = [it for it in scored_items if it["id"] not in selected_ids]
        return (reranked + tail)[:k]


# Singleton instance – loaded once at startup, retrained on demand
_recommender_instance: Optional[HybridRecommender] = None


def get_recommender() -> HybridRecommender:
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = HybridRecommender()
    return _recommender_instance
