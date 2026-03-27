"""
Content-Based Filtering using TF-IDF and Cosine Similarity.

Steps:
1. Build a TF-IDF matrix from gift descriptions + metadata
2. Compute cosine similarity between a target gift or query
3. Filter by occasion, relationship, and budget
4. Handle cold start (new users) by using context/popularity
"""

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional

from app.core.logging import logger


class ContentBasedFilter:
    def __init__(self, tfidf_weight: float = 0.6, embed_weight: float = 0.4):
        # Blend weights for TF-IDF vs dense embedding similarity
        if tfidf_weight + embed_weight <= 0:
            raise ValueError("At least one of tfidf_weight or embed_weight must be > 0")
        self.tfidf_weight = float(tfidf_weight)
        self.embed_weight = float(embed_weight)

        self.vectorizer = TfidfVectorizer(
            max_features=8000,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
            min_df=2,
            max_df=0.9,
        )
        self.tfidf_matrix: Optional[np.ndarray] = None
        self.embed_matrix: Optional[np.ndarray] = None  # shape: (n_gifts, d)
        self.gift_ids: list[int] = []
        self.gift_df: Optional[pd.DataFrame] = None
        self._is_fitted = False

    def _build_corpus(self, gifts: list[dict]) -> list[str]:
        """
        Combine multiple gift fields into a single weighted text corpus.
        Repeating important fields increases their TF-IDF weight.
        """
        corpus = []
        for g in gifts:
            title = (g.get("title", "") or "").strip()
            description = (g.get("description", "") or "").strip()
            occasion = (g.get("occasion", "") or "").strip()
            relationship = (g.get("relationship", "") or "").strip()
            category_name = (g.get("category_name", "") or "").strip()
            tags = (g.get("tags", "") or "").strip()
            age_group = (g.get("age_group", "") or "").strip()

            parts = [
                f"{title} {title}",             # weight title more (x2)
                description,
                f"{occasion} {occasion}",       # emphasize occasion (x2)
                f"{relationship} {relationship}",  # emphasize relationship (x2)
                category_name,
                f"{tags} {tags} {tags}",        # strongly weight hobbies/tags (x3)
                age_group,
            ]
            text = " ".join([p for p in parts if p]).lower().strip()
            corpus.append(text if text else "unknown")
        return corpus

    def _normalize_embeddings(self, gifts: list[dict]) -> Optional[np.ndarray]:
        # Build matrix from optional 'embedding' vectors present in gifts
        vecs = []
        has_any = False
        for g in gifts:
            emb = g.get("embedding")
            if isinstance(emb, list) and len(emb) > 0:
                has_any = True
                vecs.append(np.asarray(emb, dtype=np.float32))
            else:
                vecs.append(None)
        if not has_any:
            return None
        # Pad missing as zeros to consistent shape
        dim = max((v.shape[0] for v in vecs if v is not None), default=0)
        if dim == 0:
            return None
        mat = np.zeros((len(vecs), dim), dtype=np.float32)
        for i, v in enumerate(vecs):
            if v is not None and v.shape[0] == dim:
                mat[i] = v
        # Normalize rows for cosine
        norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        mat = mat / norms
        return mat

    def fit(self, gifts: list[dict]) -> None:
        """
        Fit the TF-IDF vectorizer on the gift corpus.

        Args:
            gifts: List of dicts with keys: id, title, description,
                   occasion, relationship, category_name, price, embedding (optional)
        """
        if not gifts:
            logger.warning("content_filter.fit called with empty gift list")
            return

        self.gift_df = pd.DataFrame(gifts)
        self.gift_ids = self.gift_df["id"].tolist()

        corpus = self._build_corpus(gifts)
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

        # Optional dense embedding matrix
        self.embed_matrix = self._normalize_embeddings(gifts)

        self._is_fitted = True
        logger.info("content_filter.fitted", num_gifts=len(gifts), has_embeddings=bool(self.embed_matrix is not None))

    def get_similar_gifts(
        self,
        gift_id: int,
        top_n: int = 10,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        category_names: Optional[list[str]] = None,
        age_groups: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> list[dict]:
        """
        Get top-N similar gifts by cosine similarity to a given gift.
        Applies context filters (occasion, relationship, budget).
        """
        if not self._is_fitted or self.gift_df is None:
            logger.warning("content_filter.not_fitted")
            return []

        if gift_id not in self.gift_ids:
            logger.warning("content_filter.gift_not_found", gift_id=gift_id)
            return self._cold_start(
                top_n,
                occasion,
                relationship,
                category_names,
                age_groups,
                tags,
                min_price,
                max_price,
            )

        idx = self.gift_ids.index(gift_id)
        gift_vector = self.tfidf_matrix[idx]
        similarities = cosine_similarity(gift_vector, self.tfidf_matrix).flatten()

        # Build candidate DataFrame
        df = self.gift_df.copy()
        df["content_score"] = similarities
        df = df[df["id"] != gift_id]

        # Apply filters
        df = self._apply_filters(
            df,
            occasion,
            relationship,
            category_names,
            age_groups,
            tags,
            min_price,
            max_price,
        )
        if "content_score" not in df.columns:
            return []
        df = df.sort_values("content_score", ascending=False).head(top_n)

        return df[["id", "content_score"]].rename(columns={"content_score": "score"}).to_dict("records")

    def get_scores_for_user_profile(
        self,
        liked_gift_ids: list[int],
        top_n: int = 10,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        category_names: Optional[list[str]] = None,
        age_groups: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        query_text: Optional[str] = None,
    ) -> list[dict]:
        """
        Build a user profile vector as the mean TF-IDF of liked gifts,
        then rank all gifts by similarity to that profile vector.
        Also blends dense-embedding similarity when embeddings are available.
        """
        if not self._is_fitted or self.gift_df is None:
            return []

        valid_indices = [
            self.gift_ids.index(gid)
            for gid in liked_gift_ids
            if gid in self.gift_ids
        ]

        # If no liked items, fall back to query-based ranking or cold start
        if not valid_indices:
            return self.get_scores_for_query(
                query_text=query_text,
                top_n=top_n,
                occasion=occasion,
                relationship=relationship,
                category_names=category_names,
                age_groups=age_groups,
                tags=tags,
                min_price=min_price,
                max_price=max_price,
            )

        # TF-IDF profile
        profile_matrix = self.tfidf_matrix[valid_indices]
        profile_vector = np.asarray(profile_matrix.mean(axis=0))
        tfidf_sim = cosine_similarity(profile_vector, self.tfidf_matrix).flatten()

        # Optional dense-embedding profile
        emb_sim = None
        if self.embed_matrix is not None:
            # mean and normalize
            user_vec = self.embed_matrix[valid_indices].mean(axis=0)
            norm = np.linalg.norm(user_vec) + 1e-9
            user_vec = user_vec / norm
            # cosine via dot since rows are normalized
            emb_sim = (self.embed_matrix @ user_vec).astype(np.float32)

        # Optional query blending (helps use form inputs even with history)
        if query_text:
            query_vec = self.vectorizer.transform([query_text.lower().strip()])
            query_sim = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            tfidf_sim = 0.7 * tfidf_sim + 0.3 * query_sim

        # Combine tfidf and embedding similarities
        if emb_sim is not None and self.embed_weight > 0:
            total_w = (self.tfidf_weight if tfidf_sim is not None else 0) + self.embed_weight
            if total_w == 0:
                combined = emb_sim
            else:
                tfidf_part = (self.tfidf_weight / total_w) * (tfidf_sim if tfidf_sim is not None else 0)
                embed_part = (self.embed_weight / total_w) * emb_sim
                combined = tfidf_part + embed_part
            similarities = combined
        else:
            similarities = tfidf_sim

        df = self.gift_df.copy()
        df["content_score"] = similarities
        df = df[~df["id"].isin(liked_gift_ids)]  # exclude already seen
        df = self._apply_filters(
            df,
            occasion,
            relationship,
            category_names,
            age_groups,
            tags,
            min_price,
            max_price,
        )
        if "content_score" not in df.columns:
            logger.warning("content_filter.filtered_missing_content_score")
            return []
        if "id" not in df.columns:
            logger.warning("content_filter.filtered_missing_id")
            return []
        df = df.sort_values("content_score", ascending=False).head(top_n)

        return df[["id", "content_score"]].rename(columns={"content_score": "score"}).to_dict("records")

    def get_scores_for_query(
        self,
        query_text: Optional[str],
        top_n: int = 10,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        category_names: Optional[list[str]] = None,
        age_groups: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> list[dict]:
        """
        Score gifts directly against a free-text query (e.g., age, hobbies, gender).
        Falls back to cold start if no query is provided.
        """
        if not self._is_fitted or self.gift_df is None:
            return []

        if not query_text:
            return self._cold_start(
                top_n,
                occasion,
                relationship,
                category_names,
                age_groups,
                tags,
                min_price,
                max_price,
            )

        query_vec = self.vectorizer.transform([query_text.lower().strip()])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        df = self.gift_df.copy()
        df["content_score"] = similarities
        filtered = self._apply_filters(
            df,
            occasion,
            relationship,
            category_names,
            age_groups,
            tags,
            min_price,
            max_price,
        )
        if filtered.empty:
            # Relax to price-only filtering if strict filters over-constrain
            filtered = self._apply_filters(
                df,
                occasion=None,
                relationship=None,
                category_names=None,
                age_groups=None,
                tags=None,
                min_price=min_price,
                max_price=max_price,
            )
            if filtered.empty:
                filtered = df
        if "content_score" not in filtered.columns:
            return []
        df = filtered.sort_values("content_score", ascending=False).head(top_n)

        return df[["id", "content_score"]].rename(columns={"content_score": "score"}).to_dict("records")

    def _cold_start(
        self,
        top_n: int,
        occasion: Optional[str],
        relationship: Optional[str],
        category_names: Optional[list[str]],
        age_groups: Optional[list[str]],
        tags: Optional[list[str]],
        min_price: Optional[float],
        max_price: Optional[float],
    ) -> list[dict]:
        """
        Cold start: return top gifts filtered by context, scored equally (1.0).
        Used when we have no user history.
        """
        if self.gift_df is None:
            return []
        df = self.gift_df.copy()
        df = self._apply_filters(
            df,
            occasion,
            relationship,
            category_names,
            age_groups,
            tags,
            min_price,
            max_price,
        )
        if "id" not in df.columns:
            logger.warning("content_filter.cold_start_missing_id")
            return []
        df["score"] = 1.0
        return df.head(top_n)[["id", "score"]].to_dict("records")

    def _apply_filters(
        self,
        df: pd.DataFrame,
        occasion: Optional[str],
        relationship: Optional[str],
        category_names: Optional[list[str]],
        age_groups: Optional[list[str]],
        tags: Optional[list[str]],
        min_price: Optional[float],
        max_price: Optional[float],
    ) -> pd.DataFrame:
        def _has(col: str) -> bool:
            return col in df.columns

        # Inclusive filters: keep rows where the field matches OR is unknown (NaN)
        if occasion and _has("occasion"):
            occ_mask = df["occasion"].isna() | df["occasion"].str.contains(occasion, case=False, na=False)
            df = df[occ_mask]
        if relationship and _has("relationship"):
            rel_mask = df["relationship"].isna() | df["relationship"].str.contains(relationship, case=False, na=False)
            df = df[rel_mask]
        if category_names and _has("category_name"):
            lowered = [c.lower() for c in category_names]
            df = df[df["category_name"].fillna("").str.lower().isin(lowered)]
        if age_groups and _has("age_group"):
            lowered = [a.lower() for a in age_groups]
            df = df[df["age_group"].fillna("").str.lower().isin(lowered)]
        if tags and _has("tags"):
            tag_tokens = [t.lower() for t in tags]
            df = df[df["tags"].fillna("").str.lower().apply(
                lambda v: any(t in v for t in tag_tokens)
            )]
        if min_price is not None and _has("price"):
            df = df[df["price"] >= min_price]
        if max_price is not None and _has("price"):
            df = df[df["price"] <= max_price]
        return df
