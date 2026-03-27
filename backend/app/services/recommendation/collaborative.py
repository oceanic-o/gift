"""
Collaborative Filtering using User-Item Interaction Matrix and Cosine Similarity.

Steps:
1. Build sparse user-item matrix from interactions
2. Assign weights: purchase=3, rating=2, click=1 (scaled by rating value if available)
3. Compute user-user cosine similarity
4. For a target user, find similar users and aggregate their interactions
5. Return ranked gift scores
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional

from app.core.logging import logger


class CollaborativeFilter:
    INTERACTION_WEIGHTS = {
        "purchase": 3.0,
        "rating": 2.0,
        "click": 1.0,
    }

    def __init__(self):
        self.user_item_matrix: Optional[np.ndarray] = None
        self.user_ids: list[int] = []
        self.gift_ids: list[int] = []
        self.user_similarity: Optional[np.ndarray] = None
        self._is_fitted = False

    def _compute_interaction_score(self, interaction_type: str, rating: Optional[float]) -> float:
        base = self.INTERACTION_WEIGHTS.get(interaction_type, 1.0)
        if interaction_type == "rating" and rating is not None:
            # Scale: rating 1-5 → 0.4 to 2.0 (normalized weight)
            return base * (rating / 5.0) * 2
        return base

    def fit(self, interactions: list[dict], profile_vectors: "np.ndarray | None" = None) -> None:
        """
        Build user-item interaction matrix and compute user-user similarity.

        Args:
            interactions: List of dicts with keys:
                user_id, gift_id, interaction_type, rating (optional)
            profile_vectors: Optional ndarray of shape (n_users, n_features).
                When provided, user-user similarity is blended:
                  70% interaction-based + 30% profile-based.
                Rows must be ordered to match self.user_ids after fit.
        """
        if not interactions:
            logger.warning("collaborative_filter.fit called with empty interactions")
            return

        df = pd.DataFrame(interactions)
        df["score"] = df.apply(
            lambda row: self._compute_interaction_score(
                row["interaction_type"], row.get("rating")
            ),
            axis=1,
        )

        # Aggregate multiple interactions between same user-gift pair
        df = df.groupby(["user_id", "gift_id"], as_index=False)["score"].sum()

        self.user_ids = sorted(df["user_id"].unique().tolist())
        self.gift_ids = sorted(df["gift_id"].unique().tolist())

        user_idx = {uid: i for i, uid in enumerate(self.user_ids)}
        gift_idx = {gid: i for i, gid in enumerate(self.gift_ids)}

        n_users = len(self.user_ids)
        n_gifts = len(self.gift_ids)

        rows = df["user_id"].map(user_idx).values
        cols = df["gift_id"].map(gift_idx).values
        data = df["score"].values

        sparse_matrix = csr_matrix((data, (rows, cols)), shape=(n_users, n_gifts))
        self.user_item_matrix = sparse_matrix.toarray()

        # Compute interaction-based user-user cosine similarity
        interaction_sim = cosine_similarity(self.user_item_matrix)

        # Blend with profile similarity if provided
        if profile_vectors is not None and profile_vectors.shape[0] == n_users:
            try:
                profile_sim = cosine_similarity(profile_vectors.astype(np.float32))
                self.user_similarity = 0.70 * interaction_sim + 0.30 * profile_sim
                logger.info("collaborative_filter.profile_blending_applied", n_users=n_users)
            except Exception as e:
                logger.warning("collaborative_filter.profile_blend_failed", error=str(e))
                self.user_similarity = interaction_sim
        else:
            self.user_similarity = interaction_sim

        self._is_fitted = True
        logger.info(
            "collaborative_filter.fitted",
            n_users=n_users,
            n_gifts=n_gifts,
            n_interactions=len(interactions),
        )


    def get_scores_for_user(
        self,
        user_id: int,
        top_n: int = 10,
        exclude_gift_ids: Optional[list[int]] = None,
        top_neighbors: int = 25,
        diversity_lambda: float = 0.50,
        candidate_pool: int = 120,
    ) -> list[dict]:
        """
        Predict gift scores for a user using weighted user-user collaborative filtering.
        """
        if not self._is_fitted:
            return []

        if user_id not in self.user_ids:
            logger.info("collaborative_filter.user_not_found_using_popularity", user_id=user_id)
            return self._popularity_fallback(top_n, exclude_gift_ids)

        user_idx = self.user_ids.index(user_id)
        user_sims = self.user_similarity[user_idx]  # shape: (n_users,)

        # Exclude the target user itself
        user_sims_copy = user_sims.copy()
        user_sims_copy[user_idx] = 0.0

        # Focus on top similar neighbors with positive similarity
        neighbor_idx = np.argsort(user_sims_copy)[::-1]
        neighbor_idx = [i for i in neighbor_idx if user_sims_copy[i] > 0][:top_neighbors]
        if not neighbor_idx:
            return self._popularity_fallback(top_n, exclude_gift_ids)

        neighbor_sims = user_sims_copy[neighbor_idx]
        neighbor_matrix = self.user_item_matrix[neighbor_idx]

        # Weighted sum of other users' ratings
        # shape: (n_gifts,)
        sim_sum = np.sum(np.abs(neighbor_sims))
        if sim_sum == 0:
            return self._popularity_fallback(top_n, exclude_gift_ids)

        weighted_scores = neighbor_sims @ neighbor_matrix
        predicted_scores = weighted_scores / (sim_sum + 1e-10)

        # Determine gifts the user has already interacted with
        user_row = self.user_item_matrix[user_idx]
        already_seen_gift_ids = {
            self.gift_ids[i] for i, v in enumerate(user_row) if v > 0
        }

        # Normalize to [0, 1]
        max_score = predicted_scores.max() if predicted_scores.size else 0
        if max_score > 0:
            predicted_scores = predicted_scores / max_score

        # Build result, excluding seen gifts
        results = []
        for i, score in enumerate(predicted_scores):
            gift_id = self.gift_ids[i]
            if gift_id in already_seen_gift_ids:
                continue
            if exclude_gift_ids and gift_id in exclude_gift_ids:
                continue
            results.append({"id": gift_id, "score": float(score)})

        results = sorted(results, key=lambda x: x["score"], reverse=True)
        if not results:
            return []

        # Diversity-aware re-ranking.
        # Repetition often comes from popularity-heavy neighborhoods; we diversify the top list
        # by downweighting items that are very similar in the user-item space.
        pool = results[: max(top_n, min(candidate_pool, len(results)))]
        reranked = self._mmr_rerank(
            pool,
            k=top_n,
            diversity_lambda=diversity_lambda,
        )
        return reranked

    def _mmr_rerank(
        self,
        scored_items: list[dict],
        k: int,
        diversity_lambda: float = 0.50,
    ) -> list[dict]:
        """MMR re-ranking to improve diversity while preserving relevance.

        Uses cosine similarity between gift vectors (columns) in the user-item matrix.

        Args:
            scored_items: list of {"id": gift_id, "score": float} sorted desc by score.
            k: how many items to select.
            diversity_lambda: 1.0 => pure relevance, 0.0 => pure diversity.
        """
        if not scored_items or self.user_item_matrix is None:
            return scored_items[:k]

        diversity_lambda = float(np.clip(diversity_lambda, 0.0, 1.0))
        # Build gift vectors for similarity computation
        id_to_col = {gid: idx for idx, gid in enumerate(self.gift_ids)}
        gift_cols = []
        valid_items: list[dict] = []
        for it in scored_items:
            col_idx = id_to_col.get(it["id"])
            if col_idx is None:
                continue
            gift_cols.append(self.user_item_matrix[:, col_idx])
            valid_items.append(it)

        if len(valid_items) <= 1:
            return valid_items[:k]

        mat = np.stack(gift_cols, axis=0).astype(np.float32)
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        mat = mat / norms
        sim = mat @ mat.T  # cosine similarity

        selected: list[int] = []
        remaining = list(range(len(valid_items)))

        # Always start with the most relevant item
        selected.append(remaining.pop(0))

        while remaining and len(selected) < k:
            best_idx = None
            best_mmr = -1e9
            for i in remaining:
                relevance = float(valid_items[i]["score"])
                redundancy = max((float(sim[i, j]) for j in selected), default=0.0)
                mmr = diversity_lambda * relevance - (1.0 - diversity_lambda) * redundancy
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_idx = i
            selected.append(best_idx)
            remaining.remove(best_idx)

        # Preserve original score values, only reorder.
        reranked = [valid_items[i] for i in selected]
        return reranked[:k]

    def _popularity_fallback(
        self,
        top_n: int,
        exclude_gift_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """Return globally popular gifts when no user history exists."""
        if self.user_item_matrix is None:
            return []

        popularity = self.user_item_matrix.sum(axis=0)
        max_pop = popularity.max()
        if max_pop > 0:
            popularity = popularity / max_pop

        results = []
        for i, score in enumerate(popularity):
            gift_id = self.gift_ids[i]
            if exclude_gift_ids and gift_id in exclude_gift_ids:
                continue
            results.append({"id": gift_id, "score": float(score)})

        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]
