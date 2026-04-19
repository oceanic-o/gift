import os
import sys
print("Script started, checking env and path...", flush=True)

import asyncio
from pathlib import Path

repo_backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_backend))

print("Loading slow imports (app.core)...", flush=True)
from app.core.database import AsyncSessionLocal
from app.services.admin_service import AdminService
from app.services.recommendation_service import RecommendationService

print("Imports complete.", flush=True)

async def run_eval():
    async with AsyncSessionLocal() as db:
        admin = AdminService(db)
        print("Fetching interactions to determine users...", flush=True)
        interactions = await admin.interaction_repo.get_all_interactions_for_matrix()
        user_ids = sorted({i.user_id for i in interactions})
        
        max_users = 25 
        sampled = user_ids[:max_users] if max_users and max_users > 0 else user_ids
            
        print(f"Starting evaluation across {len(sampled)} users... (Limited to {max_users} for performance)", flush=True)
        
        rec_service = RecommendationService(db)
        metric_keys = ["precision", "recall", "f1", "accuracy"]
        aggregates = {}
        
        for idx, uid in enumerate(sampled):
            print(f"Evaluating user {idx+1}/{len(sampled)} (ID: {uid})...", flush=True)
            try:
                profile = await rec_service.profile_repo.get_by_user_id(uid)
                compared = await rec_service.compare_all_models(
                    user_id=uid,
                    top_n=6,
                    occasion=getattr(profile, "occasion", None) if profile else None,
                    relationship=getattr(profile, "relationship", None) if profile else None,
                    min_price=getattr(profile, "budget_min", None) if profile else None,
                    max_price=getattr(profile, "budget_max", None) if profile else None,
                    age=getattr(profile, "age", None) if profile else None,
                    gender=getattr(profile, "gender", None) if profile else None,
                    hobbies=getattr(profile, "hobbies", None) if profile else None,
                    include_rag=(idx == 0)
                )
                
                for model in compared.models:
                    bucket = aggregates.setdefault(model.model, {"count": 0, "sums": {k: 0.0 for k in metric_keys}})
                    metrics = model.metrics or {}
                    has_val = False
                    for key in metric_keys:
                        raw = metrics.get(key)
                        if key == 'f1' and raw is None:
                            raw = metrics.get('f1_score')
                        if isinstance(raw, (int, float)):
                            bucket["sums"][key] += float(raw)
                            has_val = True
                    if has_val:
                        bucket["count"] += 1
            except Exception as e:
                print(f"Error evaluating user {uid}: {e}", flush=True)
                
        print("--- Final Metrics ---", flush=True)
        for m, data in sorted(aggregates.items()):
            cnt = int(data["count"])
            if cnt > 0:
                print(f"Model: {m}")
                for key in metric_keys:
                    val = data["sums"][key] / cnt
                    print(f"  {key}: {val:.4f}")

if __name__ == "__main__":
    asyncio.run(run_eval())
