"""
Evaluation Module for the Recommendation Engine.

Implements:
- 80/20 train-test split
- Precision, Recall, F1, Accuracy
- Confusion matrix
- Optional 5-fold cross-validation
- Stores results to model_metrics table

Approach:
- We frame evaluation as a binary relevance classification task.
- A gift is "relevant" (positive) for a user if they rated it >= 3 or purchased it.
- We run the hybrid model on the training set, predict top-N for test users,
  then compare with their actual test interactions.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from sklearn.model_selection import KFold
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    confusion_matrix,
)
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import ModelMetric
from app.repositories.interaction_repository import InteractionRepository, ModelMetricRepository
from app.services.recommendation.content_based import ContentBasedFilter
from app.services.recommendation.collaborative import CollaborativeFilter
from app.services.recommendation.hybrid import HybridRecommender
from app.schemas.recommendation import EvaluationResult


class RecommendationEvaluator:
    def __init__(self, top_n: int = 10, cross_validate: bool = False, n_folds: int = 5,
                 content_weight: float = 0.6, collaborative_weight: float = 0.4,
                 tfidf_weight: float = 0.6, embed_weight: float = 0.4):
        self.top_n = top_n
        self.cross_validate = cross_validate
        self.n_folds = n_folds
        self.content_weight = content_weight
        self.collaborative_weight = collaborative_weight
        self.tfidf_weight = tfidf_weight
        self.embed_weight = embed_weight

    def _build_relevance(self, interactions: list[dict]) -> pd.DataFrame:
        """
        Build binary relevance: 1 if rating >= 3 or purchase, 0 for click-only.
        """
        rows = []
        for item in interactions:
            itype = item["interaction_type"]
            rating = item.get("rating")
            if itype == "purchase":
                relevant = 1
            elif itype == "rating" and rating is not None and rating >= 3.0:
                relevant = 1
            else:
                relevant = 0
            rows.append(
                {
                    "user_id": item["user_id"],
                    "gift_id": item["gift_id"],
                    "relevant": relevant,
                }
            )
        return pd.DataFrame(rows)

    def _evaluate_split(
        self,
        train_interactions: list[dict],
        test_interactions: list[dict],
        gift_dicts: list[dict],
    ) -> tuple[list[int], list[int]]:
        """
        Train models on train set, evaluate on test set.
        Returns (y_true, y_pred) binary arrays.
        """
        # Fit models on train split
        content = ContentBasedFilter(tfidf_weight=self.tfidf_weight, embed_weight=self.embed_weight)
        collab = CollaborativeFilter()
        content.fit(gift_dicts)
        collab.fit(train_interactions)

        train_df = self._build_relevance(train_interactions)
        test_df = self._build_relevance(test_interactions)

        if test_df.empty:
            return [], []

        y_true_list = []
        y_pred_list = []

        test_users = test_df["user_id"].unique()

        for uid in test_users:
            user_train = train_df[train_df["user_id"] == uid]
            liked_ids = user_train[user_train["relevant"] == 1]["gift_id"].tolist()

            # Get collaborative scores
            collab_scores = collab.get_scores_for_user(uid, top_n=self.top_n)
            collab_map = {r["id"]: r["score"] for r in collab_scores}

            # Get content scores
            content_scores = content.get_scores_for_user_profile(liked_ids, top_n=self.top_n)
            content_map = {r["id"]: r["score"] for r in content_scores}

            all_gids = set(collab_map.keys()) | set(content_map.keys())
            scored = []
            for gid in all_gids:
                final = self.content_weight * content_map.get(gid, 0.0) + self.collaborative_weight * collab_map.get(gid, 0.0)
                scored.append((gid, final))

            top_recommended = set(
                gid for gid, _ in sorted(scored, key=lambda x: x[1], reverse=True)[: self.top_n]
            )

            # Ground truth: test user's relevant gifts
            user_test = test_df[test_df["user_id"] == uid]
            for _, row in user_test.iterrows():
                y_true_list.append(int(row["relevant"]))
                y_pred_list.append(1 if row["gift_id"] in top_recommended else 0)

        return y_true_list, y_pred_list

    async def evaluate(
        self,
        db: AsyncSession,
        gift_dicts: list[dict],
        model_name: str = "hybrid",
    ) -> EvaluationResult:
        """
        Full evaluation pipeline: load interactions, split, evaluate, store metrics.
        """
        interaction_repo = InteractionRepository(db)
        metric_repo = ModelMetricRepository(db)

        all_interactions = await interaction_repo.get_all_interactions_for_matrix()
        interaction_dicts = [
            {
                "user_id": i.user_id,
                "gift_id": i.gift_id,
                "interaction_type": i.interaction_type.value,
                "rating": i.rating,
            }
            for i in all_interactions
        ]

        if len(interaction_dicts) < 10:
            logger.warning("evaluation.insufficient_data", count=len(interaction_dicts))
            # Return baseline metrics
            result = EvaluationResult(
                model_name=model_name,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                accuracy=0.0,
                confusion_matrix=[[0, 0], [0, 0]],
            )
            await self._save_metric(db, metric_repo, result)
            return result

        # --- 80/20 split ---
        df = pd.DataFrame(interaction_dicts)
        split_idx = int(len(df) * 0.8)
        train_data = df.iloc[:split_idx].to_dict("records")
        test_data = df.iloc[split_idx:].to_dict("records")

        y_true, y_pred = self._evaluate_split(train_data, test_data, gift_dicts)

        if not y_true:
            logger.warning("evaluation.no_predictions_generated")
            result = EvaluationResult(
                model_name=model_name,
                precision=0.0, recall=0.0, f1_score=0.0, accuracy=0.0,
                confusion_matrix=[[0, 0], [0, 0]],
            )
            await self._save_metric(db, metric_repo, result)
            return result

        prec = float(precision_score(y_true, y_pred, zero_division=0))
        rec = float(recall_score(y_true, y_pred, zero_division=0))
        f1 = float(f1_score(y_true, y_pred, zero_division=0))
        acc = float(accuracy_score(y_true, y_pred))
        cm = confusion_matrix(y_true, y_pred).tolist()

        cross_val_scores = None
        if self.cross_validate and len(interaction_dicts) >= 50:
            cross_val_scores = self._cross_validate(interaction_dicts, gift_dicts)

        result = EvaluationResult(
            model_name=model_name,
            precision=round(prec, 4),
            recall=round(rec, 4),
            f1_score=round(f1, 4),
            accuracy=round(acc, 4),
            confusion_matrix=cm,
            cross_val_scores=[round(s, 4) for s in cross_val_scores] if cross_val_scores else None,
        )

        await self._save_metric(db, metric_repo, result)
        logger.info("evaluation.complete", model=model_name, f1=f1, precision=prec, recall=rec)
        return result

    def _cross_validate(self, interaction_dicts: list[dict], gift_dicts: list[dict]) -> list[float]:
        """5-fold cross-validation returning per-fold F1 scores."""
        df = pd.DataFrame(interaction_dicts)
        kf = KFold(n_splits=self.n_folds, shuffle=True, random_state=42)
        fold_scores = []

        for train_idx, test_idx in kf.split(df):
            train_data = df.iloc[train_idx].to_dict("records")
            test_data = df.iloc[test_idx].to_dict("records")
            y_true, y_pred = self._evaluate_split(train_data, test_data, gift_dicts)
            if y_true:
                score = float(f1_score(y_true, y_pred, zero_division=0))
                fold_scores.append(score)

        return fold_scores

    async def _save_metric(
        self,
        db: AsyncSession,
        metric_repo: ModelMetricRepository,
        result: EvaluationResult,
    ) -> None:
        metric = ModelMetric(
            model_name=result.model_name,
            precision=result.precision,
            recall=result.recall,
            f1_score=result.f1_score,
            accuracy=result.accuracy,
            evaluated_at=datetime.now(timezone.utc),
        )
        await metric_repo.create(metric)
