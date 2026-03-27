"""
Admin Service Layer.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, inspect, text
from sqlalchemy.exc import SQLAlchemyError
import json
from fastapi import HTTPException, status
from pathlib import Path

from app.core.logging import logger
from app.models.models import User, Gift, Interaction, Recommendation, Category, UserRole, ModelMetric
from app.repositories.user_repository import UserRepository
from app.repositories.gift_repository import GiftRepository
from app.repositories.interaction_repository import (
    InteractionRepository, RecommendationRepository, ModelMetricRepository
)
from app.repositories.gift_repository import CategoryRepository
import os
from dotenv import dotenv_values
from app.schemas.recommendation import AdminStats, EnvSettingsResponse, EnvSettingsUpdate
from app.core.config import settings
from app.services.recommendation.hybrid import get_recommender
from app.services.evaluation.evaluator import RecommendationEvaluator
from app.services.rag.rag_service import RAGService
from app.services.recommendation_service import RecommendationService

RUNTIME_BACKEND_OVERRIDES: dict[str, str] = {}
RUNTIME_FRONTEND_OVERRIDES: dict[str, str] = {}


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.gift_repo = GiftRepository(db)
        self.interaction_repo = InteractionRepository(db)
        self.rec_repo = RecommendationRepository(db)
        self.metric_repo = ModelMetricRepository(db)
        self.category_repo = CategoryRepository(db)

    async def get_stats(self) -> AdminStats:
        total_users = await self.user_repo.count()
        total_gifts = await self.gift_repo.count()
        total_interactions = await self.interaction_repo.get_total_count()
        total_recommendations = await self.rec_repo.get_total_count()
        interaction_breakdown = await self.interaction_repo.get_interaction_counts_by_type()

        # Popular categories by gift count
        result = await self.db.execute(
            select(Category.name, func.count(Gift.id).label("gift_count"))
            .join(Gift, Gift.category_id == Category.id)
            .group_by(Category.name)
            .order_by(func.count(Gift.id).desc())
            .limit(5)
        )
        popular_categories = [
            {"name": row[0], "count": row[1]} for row in result.all()
        ]

        # Best model
        best = await self.metric_repo.get_best_model()
        best_model = None
        if best:
            best_model = {
                "model_name": best.model_name,
                "f1_score": best.f1_score,
                "precision": best.precision,
                "recall": best.recall,
                "accuracy": best.accuracy,
                "evaluated_at": best.evaluated_at.isoformat(),
            }

        return AdminStats(
            total_users=total_users,
            total_gifts=total_gifts,
            total_interactions=total_interactions,
            total_recommendations=total_recommendations,
            popular_categories=popular_categories,
            best_model=best_model,
            interaction_breakdown=interaction_breakdown,
        )

    async def get_all_metrics(self):
        return await self.metric_repo.get_all_metrics()

    async def get_all_users(self, skip: int = 0, limit: int = 100):
        return await self.user_repo.get_all_users(skip=skip, limit=limit)

    async def get_all_interactions(self, skip: int = 0, limit: int = 100):
        return await self.interaction_repo.get_all_paginated(skip=skip, limit=limit)

    async def delete_user(self, user_id: int) -> dict:
        deleted = await self.user_repo.delete(user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {"message": "User deleted"}

    async def update_user_role(self, user_id: int, role: UserRole) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.role = role
        await self.db.flush()
        return user

    async def delete_interaction(self, interaction_id: int) -> dict:
        deleted = await self.interaction_repo.delete(interaction_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
        return {"message": "Interaction deleted"}

    async def import_gifts_from_json(
        self,
        json_path: str,
        limit: int | None = None,
        force: bool = False,
    ) -> dict:
        if force:
            await self.db.execute(delete(Recommendation))
            await self.db.execute(delete(Interaction))
            await self.db.execute(delete(Gift))
            await self.db.execute(delete(Category))

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JSON file not found: {json_path}",
            ) from exc
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for gift data.",
            ) from exc

        items = payload if isinstance(payload, list) else payload.get("gifts") or payload.get("products", [])
        if limit:
            items = items[:limit]

        created = 0
        skipped = 0

        for row in items:
            gift_metadata = row.get("gift_metadata") or {}
            image_info = row.get("image") if isinstance(row.get("image"), dict) else {}

            title = str(row.get("gift_name") or row.get("title") or row.get("name") or "").strip()
            if not title:
                skipped += 1
                continue

            description = str(row.get("description") or "").strip() or None

            category_name = str(row.get("primary_category") or "").strip().title() or None
            categories = row.get("categories")
            if not category_name and isinstance(categories, list) and categories:
                category_name = str(categories[-1]).strip().title()
            if not category_name:
                category_name = str(row.get("category") or "General").strip().title()
            category, _ = await self.category_repo.get_or_create(category_name or "General")

            price_value = row.get("sale_price") if row.get("sale_price") is not None else row.get("price")
            if isinstance(price_value, (int, float)):
                price = float(price_value)
            else:
                price_raw = str(price_value or "0").replace("$", "").replace(",", "").strip()
                try:
                    price = float(price_raw)
                except ValueError:
                    skipped += 1
                    continue

            occasion = str(row.get("occasion") or "").strip() or None
            if not occasion and isinstance(gift_metadata, dict):
                occasions = gift_metadata.get("best_for_occasions")
                if isinstance(occasions, list) and occasions:
                    occasion = str(occasions[0]).strip() or None

            relationship = str(row.get("relationship") or "").strip() or None
            if not relationship and isinstance(gift_metadata, dict):
                relationships = gift_metadata.get("suitable_for_relationships")
                if isinstance(relationships, list) and relationships:
                    relationship = str(relationships[0]).strip() or None

            age_group = str(row.get("age_group") or "").strip() or None
            if not age_group and isinstance(gift_metadata, dict):
                ages = gift_metadata.get("best_for_age_ranges")
                if isinstance(ages, list) and ages:
                    age_group = str(ages[0]).strip() or None

            tags_value = row.get("tags")
            if isinstance(tags_value, list):
                tags = ", ".join([str(t).strip() for t in tags_value if str(t).strip()]) or None
            else:
                tags = str(tags_value or "").strip() or None

            brand = str(row.get("brand") or "").strip()
            extra_tags = []
            if brand:
                extra_tags.append(brand)
            if isinstance(categories, list):
                extra_tags.extend([str(c).strip() for c in categories if str(c).strip()])
            if isinstance(gift_metadata, dict):
                interests = gift_metadata.get("recipient_interests")
                if isinstance(interests, list):
                    extra_tags.extend([str(i).strip() for i in interests if str(i).strip()])
            if extra_tags:
                joined_extra = ", ".join([t for t in extra_tags if t])
                tags = f"{tags}, {joined_extra}" if tags else joined_extra

            image_url = str(
                row.get("image_url")
                or (image_info.get("url") if isinstance(image_info, dict) else None)
                or row.get("image")
                or ""
            ).strip() or None
            product_url = str(
                row.get("product_url")
                or row.get("product_link")
                or row.get("url")
                or row.get("link")
                or ""
            ).strip() or None

            gift = Gift(
                title=title,
                description=description,
                category_id=category.id,
                price=price,
                occasion=occasion,
                relationship=relationship,
                age_group=age_group,
                tags=tags,
                image_url=image_url,
                product_url=product_url,
            )
            await self.gift_repo.create(gift)
            created += 1

        return {
            "message": "JSON import complete",
            "created": created,
            "skipped": skipped,
        }

    async def reset_and_populate_catalog(
        self,
    json_path: str = "../data/gifts_50k.json",
        limit: int | None = None,
        embed_batch_size: int = 100,
    ) -> dict:
        """Hard reset gift + vector catalog and re-import from data folder.

        This deletes dependent tables that reference gifts to keep FK constraints happy.
        Afterwards it imports the JSON catalog and generates embeddings so pgvector index is usable.
        """
        # Cleanup (order matters with FK constraints)
        await self.db.execute(delete(Recommendation))
        await self.db.execute(delete(Interaction))
        await self.db.execute(delete(Gift))
        await self.db.execute(delete(Category))
        # RAG queries are unrelated to gifts; keep them.
        await self.db.commit()

        imported = await self.import_gifts_from_json(
            json_path=json_path,
            limit=limit,
            force=False,
        )
        await self.db.commit()

        embedded = await self.embed_gifts(batch_size=embed_batch_size)
        # embed_gifts commits internally per batch; still safe to commit here
        await self.db.commit()

        # Retrain model to pick up new catalog
        try:
            await self.retrain_model()
        except Exception as e:
            logger.warning("admin.retrain_after_reset_failed", error=str(e))

        return {
            "message": "Catalog reset and populated",
            "import": imported,
            "embeddings": embedded,
        }

    async def get_dataset_metadata(self, json_path: str = "../data/gifts_50k.json") -> dict:
        file_path = Path(json_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset file not found: {json_path}",
            )
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for dataset metadata.",
            ) from exc

        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        products = payload.get("products") if isinstance(payload, dict) else payload
        products = products or []
        sample = products[0] if products else {}

        return {
            "file_path": str(file_path),
            "schema_version": metadata.get("schema_version"),
            "generator_version": metadata.get("generator_version"),
            "image_source": metadata.get("image_source"),
            "image_license": metadata.get("image_license"),
            "total_products": metadata.get("total_products", len(products)),
            "total_users": metadata.get("total_users"),
            "categories": metadata.get("categories", []),
            "occasions": metadata.get("occasions", []),
            "age_ranges": metadata.get("age_ranges", []),
            "product_fields": list(sample.keys()) if isinstance(sample, dict) else [],
        }

    async def get_database_schema(self) -> dict:
        def _inspect(connection):
            bind = connection
            if hasattr(connection, "get_bind"):
                bind = connection.get_bind()
            inspector = inspect(bind)
            tables = []
            for table_name in inspector.get_table_names():
                columns = []
                for column in inspector.get_columns(table_name):
                    columns.append(
                        {
                            "name": column.get("name"),
                            "type": str(column.get("type")),
                            "nullable": bool(column.get("nullable")),
                            "default": str(column.get("default")) if column.get("default") is not None else None,
                        }
                    )
                foreign_keys = []
                for fk in inspector.get_foreign_keys(table_name):
                    foreign_keys.append(
                        {
                            "constrained_columns": fk.get("constrained_columns", []),
                            "referred_table": fk.get("referred_table"),
                            "referred_columns": fk.get("referred_columns", []),
                        }
                    )
                tables.append(
                    {
                        "name": table_name,
                        "columns": columns,
                        "foreign_keys": foreign_keys,
                    }
                )
            return {"tables": tables}

        try:
            return await self.db.run_sync(_inspect)
        except SQLAlchemyError as exc:
            logger.error("admin.schema_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Schema inspection failed: {exc}",
            ) from exc

    async def run_readonly_query(self, sql: str, max_rows: int = 200) -> dict:
        cleaned = sql.strip().rstrip(";")
        lowered = cleaned.lower()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only SELECT/CTE queries are allowed.",
            )
        forbidden = [";", "insert ", "update ", "delete ", "drop ", "alter ", "create "]
        if any(token in lowered for token in forbidden):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only single read-only queries are allowed.",
            )

        stmt = text(cleaned)
        try:
            result = await self.db.execute(stmt)
        except SQLAlchemyError as exc:
            logger.error("admin.query_failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query failed: {exc}",
            ) from exc

        rows = result.fetchmany(size=max_rows)
        columns = list(result.keys()) if result.returns_rows else []
        return {
            "columns": columns,
            "rows": [list(row) for row in rows],
            "row_count": len(rows),
        }

    async def embed_gifts(self, batch_size: int = 100) -> dict:
        rag = RAGService()
        return await rag.embed_and_store_gifts(self.db, batch_size=batch_size)

    async def ingest_web_gifts(
        self,
        query: str,
        limit: int | None = None,
        occasion: str | None = None,
        relationship: str | None = None,
    ) -> dict:
        if not query:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query is required")
        rag = RAGService()
        result = await rag.ingest_web_gifts(
            db=self.db,
            query=query,
            limit=limit,
            occasion=occasion,
            relationship=relationship,
        )
        await self.db.commit()
        return result

    async def retrain_model(self) -> dict:
        """Retrain the hybrid recommender with latest data."""
        recommender = get_recommender()
        await recommender.train(self.db)
        logger.info("admin.retrain_complete")
        return {"message": "Model retrained successfully."}

    async def _evaluate_all_models_contextual(
        self,
        max_users: int = 1,
        top_n: int = 6,
    ) -> dict:
        """Evaluate all 5 models using stored user profile context + interactions.

        This is a context-aware offline batch evaluation meant for admin comparison.
        """
        interactions = await self.interaction_repo.get_all_interactions_for_matrix()
        user_ids = sorted({i.user_id for i in interactions})
        if not user_ids:
            return {
                "message": "No interactions found for evaluation.",
                "mode": "profile_context_batch",
                "users_evaluated": 0,
                "results": [],
            }

        sampled_users = user_ids[:max_users]
        rec_service = RecommendationService(self.db)

        metric_keys = [
            "precision",
            "recall",
            "f1",
            "accuracy",
            "error_rate",
            "mae",
            "rmse",
            "coverage",
            "precision_at_k",
            "recall_at_k",
            "f1_at_k",
            "hit_rate_at_k",
            "ndcg_at_k",
            "map_at_k",
            "mrr_at_k",
            "validity_rate",
            "invalidity_rate",
            "avg_validity_score",
        ]

        aggregates: dict[str, dict] = {}
        for idx, uid in enumerate(sampled_users):
            profile = await rec_service.profile_repo.get_by_user_id(uid)
            age = getattr(profile, "age", None) if profile else None
            gender = getattr(profile, "gender", None) if profile else None
            hobbies = getattr(profile, "hobbies", None) if profile else None
            relationship = getattr(profile, "relationship", None) if profile else None
            occasion = getattr(profile, "occasion", None) if profile else None
            min_price = getattr(profile, "budget_min", None) if profile else None
            max_price = getattr(profile, "budget_max", None) if profile else None

            try:
                compared = await rec_service.compare_all_models(
                    user_id=uid,
                    top_n=top_n,
                    occasion=occasion,
                    relationship=relationship,
                    min_price=min_price,
                    max_price=max_price,
                    age=age,
                    gender=gender,
                    hobbies=hobbies,
                    include_rag=(idx == 0),
                )
            except Exception as exc:
                logger.warning("admin.evaluate_all_models.user_failed", user_id=uid, error=str(exc))
                continue

            for model in compared.models:
                bucket = aggregates.setdefault(
                    model.model,
                    {
                        "count": 0,
                        "sums": {k: 0.0 for k in metric_keys},
                        "valid_counts": {k: 0 for k in metric_keys},
                    },
                )
                metrics = model.metrics or {}
                bucket["count"] += 1
                for key in metric_keys:
                    raw = metrics.get(key)
                    if key == "f1" and raw is None:
                        raw = metrics.get("f1_score")
                    if isinstance(raw, (int, float)):
                        bucket["sums"][key] += float(raw)
                        bucket["valid_counts"][key] += 1

        model_results: list[dict] = []
        for model_name, data in sorted(aggregates.items()):
            row: dict[str, float | int | str | None] = {
                "model_name": model_name,
                "users_evaluated": int(data["count"]),
            }
            for key in metric_keys:
                cnt = int(data["valid_counts"][key])
                row[key] = round(data["sums"][key] / cnt, 4) if cnt > 0 else None

            # Keep compatibility aliases for frontend cards/messages.
            row["f1_score"] = row.get("f1")

            # Persist core summary for model history table.
            persisted = ModelMetric(
                model_name=model_name,
                precision=float(row["precision"] or 0.0),
                recall=float(row["recall"] or 0.0),
                f1_score=float(row["f1"] or 0.0),
                accuracy=float(row["accuracy"] or 0.0),
            )
            await self.metric_repo.create(persisted)
            model_results.append(row)

        return {
            "message": "All model evaluations completed.",
            "mode": "profile_context_batch",
            "users_evaluated": len(sampled_users),
            "results": model_results,
        }

    async def evaluate_model(self, cross_validate: bool = False) -> dict:
        """Run evaluation for all available models and store summary metrics."""
        _ = cross_validate  # preserved for API compatibility
        return await self._evaluate_all_models_contextual(max_users=1, top_n=6)

    async def tune_and_evaluate(self) -> dict:
        """Grid search simple weight combos and return metrics series for plotting."""
        # Prepare gifts for evaluator
        all_gifts = await self.gift_repo.get_all_gifts()
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

        # Interactions for splitting
        interaction_repo = self.interaction_repo
        all_interactions = await interaction_repo.get_all_interactions_for_matrix()
        if len(all_interactions) < 10:
            return {"message": "Insufficient interactions for tuning", "count": len(all_interactions)}

        combos = []
        for cw in (0.7, 0.8, 0.9):
            for tw in (0.5, 0.6, 0.7):
                ew = 1.0 - tw
                from app.services.evaluation.evaluator import RecommendationEvaluator
                evaluator = RecommendationEvaluator(
                    content_weight=cw, collaborative_weight=1.0 - cw,
                    tfidf_weight=tw, embed_weight=ew,
                )
                result = await evaluator.evaluate(self.db, gift_dicts, model_name=f"hybrid_c{cw:.1f}_t{tw:.1f}")
                combos.append({
                    "content_weight": cw,
                    "collaborative_weight": 1.0 - cw,
                    "tfidf_weight": tw,
                    "embed_weight": ew,
                    "precision": result.precision,
                    "recall": result.recall,
                    "f1": result.f1_score,
                    "accuracy": result.accuracy,
                })
        # Sort by F1 desc
        combos.sort(key=lambda x: x["f1"], reverse=True)
        return {
            "results": combos,
            "best": combos[0] if combos else None,
        }

    async def get_env_settings(self) -> EnvSettingsResponse:
        """Read backend and frontend .env files."""
        backend_path = "/app/.env"
        frontend_path = "/app/frontend.env"

        backend_env = {}
        if os.path.exists(backend_path):
            backend_env = dotenv_values(backend_path)

        frontend_env = {}
        if os.path.exists(frontend_path):
            frontend_env = dotenv_values(frontend_path)

        # Overlay any runtime-only updates (when bind-mounted env file cannot be rewritten).
        backend_env.update(RUNTIME_BACKEND_OVERRIDES)
        frontend_env.update(RUNTIME_FRONTEND_OVERRIDES)

        return EnvSettingsResponse(
            backend={k: v or "" for k, v in backend_env.items()},
            frontend={k: v or "" for k, v in frontend_env.items()},
        )

    def _upsert_env_values_in_place(self, path: str, updates: dict[str, str]) -> None:
        """Update KEY=VALUE entries in place without atomic rename.

        `python-dotenv.set_key` uses temp-file + os.replace, which fails on bind-mounted
        single-file volumes in Docker with: [Errno 16] Device or resource busy.
        """
        lines: list[str] = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        remaining = {k: str(v) for k, v in updates.items()}
        out: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                out.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}\n")
            else:
                out.append(line)

        for key, value in remaining.items():
            out.append(f"{key}={value}\n")

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(out)

    def _apply_backend_runtime_settings(self, updates: dict[str, str]) -> None:
        """Apply backend updates immediately to the live settings object."""
        for key, raw_val in updates.items():
            value = str(raw_val)
            current = getattr(settings, key, None)
            try:
                if isinstance(current, bool):
                    parsed = value.strip().lower() in {"1", "true", "yes", "on"}
                elif isinstance(current, int) and not isinstance(current, bool):
                    parsed = int(float(value))
                elif isinstance(current, float):
                    parsed = float(value)
                else:
                    parsed = value
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid value for {key}: {value}",
                ) from exc

            if hasattr(settings, key):
                setattr(settings, key, parsed)
            os.environ[key] = str(parsed)
            RUNTIME_BACKEND_OVERRIDES[key] = str(parsed)

    async def update_env_settings(self, data: EnvSettingsUpdate) -> dict:
        """Update backend and/or frontend .env files."""
        backend_path = "/app/.env"
        frontend_path = "/app/frontend.env"
        warnings: list[str] = []

        if data.backend:
            self._apply_backend_runtime_settings(data.backend)
            try:
                self._upsert_env_values_in_place(backend_path, data.backend)
            except OSError as exc:
                warnings.append(
                    f"Backend values applied at runtime but could not persist to .env: {exc}"
                )
                logger.warning("admin.settings_backend_persist_failed", error=str(exc))

        if data.frontend:
            for key, value in data.frontend.items():
                RUNTIME_FRONTEND_OVERRIDES[key] = str(value)
            try:
                self._upsert_env_values_in_place(frontend_path, data.frontend)
            except OSError as exc:
                warnings.append(
                    f"Frontend values updated in memory but could not persist to .env: {exc}"
                )
                logger.warning("admin.settings_frontend_persist_failed", error=str(exc))

        if warnings:
            return {
                "message": "Settings applied with warnings.",
                "warnings": warnings,
            }
        return {"message": "Environment settings updated successfully."}
