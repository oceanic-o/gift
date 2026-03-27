import asyncio
import os
import sys
from pathlib import Path

# Add backend to path (prefer local repo; /app for container runtime)
repo_backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_backend))
if "/app" not in sys.path:
    sys.path.append("/app")

from app.core.database import AsyncSessionLocal as SessionLocal
from app.services.recommendation_service import RecommendationService
from app.services.recommendation.hybrid import get_recommender
from app.core.config import settings
from app.core.taxonomy import match_age_group
from app.repositories.gift_repository import GiftRepository
from app.services.recommendation.knowledge_based import KnowledgeBasedRecommender
from app.services.rag.rag_service import RAGService
from app.schemas.recommendation import RAGQueryCreate

RELEVANCE_RULES = {
    "min_signal_hits": 2,
    "min_hobby_overlap": 0.2,
    "min_hybrid_score": 0.1,
    "min_confidence": 0.25,
    "min_content_score": 0.1,
    "min_knowledge_score": 0.3,
    "strong_signal_hits": 3,
}


def _bool(v):
    return bool(v) if v is not None else False


def evaluate_relevance(metrics, gift=None, age_match_override=None):
    gift_occasion = getattr(gift, "occasion", None) if gift is not None else None
    gift_relationship = getattr(gift, "relationship", None) if gift is not None else None
    gift_age_group = getattr(gift, "age_group", None) if gift is not None else None
    signals = {}
    signals["occasion"] = None if not gift_occasion else _bool(metrics.occasion_match)
    signals["relationship"] = None if not gift_relationship else _bool(metrics.relationship_match)
    signals["age"] = None if not gift_age_group else _bool(age_match_override if age_match_override is not None else metrics.age_group_match)
    signals["price"] = _bool(metrics.price_fit)
    signals["hobby"] = (metrics.hobby_overlap or 0.0) >= RELEVANCE_RULES["min_hobby_overlap"]

    signal_hits = sum(1 for v in signals.values() if v)
    signal_known = sum(1 for v in signals.values() if v is not None)
    effective_min_hits = min(RELEVANCE_RULES["min_signal_hits"], signal_known)
    effective_strong_hits = min(RELEVANCE_RULES["strong_signal_hits"], signal_known)
    score_ok = (metrics.hybrid_score or 0.0) >= RELEVANCE_RULES["min_hybrid_score"]
    confidence_ok = (metrics.confidence or 0.0) >= RELEVANCE_RULES["min_confidence"]
    content_ok = (metrics.content_score or 0.0) >= RELEVANCE_RULES["min_content_score"]
    knowledge_ok = (metrics.knowledge_score or 0.0) >= RELEVANCE_RULES["min_knowledge_score"]

    strong_signals = signal_hits >= effective_strong_hits if signal_known else False
    is_relevant = (
        (signal_hits >= effective_min_hits and (score_ok or confidence_ok))
        or (strong_signals and (content_ok or knowledge_ok))
    )

    reasons = []
    if signal_hits < effective_min_hits:
        reasons.append(f"signals({signal_hits}/{signal_known})")
    if not (score_ok or confidence_ok):
        reasons.append("low_hybrid/conf")
    if strong_signals and not (content_ok or knowledge_ok):
        reasons.append("weak_content/knowledge")

    return is_relevant, signals, signal_hits, score_ok, confidence_ok, content_ok, knowledge_ok, reasons

async def audit():
    async with SessionLocal() as db:
        service = RecommendationService(db)
        recommender = get_recommender()
        gift_repo = GiftRepository(db)
        kb = KnowledgeBasedRecommender()
        rag_service = RAGService()
        
        print("--- Training Recommender ---")
        await recommender.train(db)

        all_gifts = await gift_repo.get_all_gifts()
        gift_map = {g.id: g for g in all_gifts}
        gift_dicts = [
            {
                "id": g.id,
                "title": g.title,
                "description": g.description or "",
                "occasion": g.occasion or "",
                "relationship": g.relationship or "",
                "category_name": g.category.name if g.category else "",
                "tags": getattr(g, "tags", "") or "",
                "age_group": getattr(g, "age_group", "") or "",
                "price": g.price,
            }
            for g in all_gifts
        ]
        
        test_cases = [
            {
                "name": "Teen Boy - Birthday - Video Games",
                "age": "Teen (13-17)",
                "gender": "Male",
                "occasion": "Birthday",
                "hobbies": "Video Games, Esports",
                "budget": "$25–$50"
            },
            {
                "name": "Adult Woman - Anniversary - Cooking",
                "age": "Adult (26-40)",
                "gender": "Female",
                "occasion": "Anniversary",
                "hobbies": "Cooking, Baking, Wine",
                "budget": "$100–$200"
            },
            {
                "name": "Young Child - Birthday - Puzzles/Learning",
                "age": "Child (0-12)",
                "gender": "Non-binary",
                "occasion": "Birthday",
                "hobbies": "Puzzles, Science Kits",
                "budget": "Under $25"
            },
            {
                "name": "Senior Woman - Retirement - Gardening",
                "age": "Senior (60+)",
                "gender": "Female",
                "occasion": "Retirement",
                "hobbies": "Gardening, House Plants, Tea",
                "budget": "$50–$100"
            }
        ]

        print(f"\n{'User Profile':<40} | {'Top Recommended Gifts'}")
        for tc in test_cases:
            from app.services.recommendation_service import _parse_budget
            min_p, max_p = _parse_budget(tc["budget"])
            
            # Use get_minimal_recommendations for the user-facing list
            recs = await service.get_minimal_recommendations(
                user_id=1,
                top_n=3,
                occasion=tc["occasion"],
                age=tc["age"],
                gender=tc["gender"],
                hobbies=tc["hobbies"],
                min_price=min_p,
                max_price=max_p
            )
            
            print(f"\nProfile: {tc['name']}")
            print(f"Inputs: {tc['age']}, {tc['gender']}, {tc['hobbies']}, {tc['budget']}")
            
            for rank, r in enumerate(recs):
                # Get details + full metrics for this gift
                details = await service.get_gift_details_with_metrics(
                    user_id=1,
                    gift_id=r.gift_id,
                    occasion=tc["occasion"],
                    age=tc["age"],
                    gender=tc["gender"],
                    hobbies=tc["hobbies"],
                    min_price=min_p,
                    max_price=max_p
                )
                m = details.metrics
                # Determine "Target" label for reporting
                target_label = match_age_group(tc["age"])
                gift_age_label = match_age_group(details.gift.age_group)
                age_match = (target_label == gift_age_label) if target_label and gift_age_label else m.age_group_match

                relevant, signals, signal_hits, score_ok, confidence_ok, content_ok, knowledge_ok, reasons = evaluate_relevance(
                    m, gift=details.gift, age_match_override=age_match
                )
                signal_summary = ", ".join([
                    f"{k}={'-' if v is None else ('Y' if v else 'N')}" for k, v in signals.items()
                ])
                verdict = "RELEVANT" if relevant else "CHECK"
                reason_text = " | Reasons: " + ", ".join(reasons) if reasons else ""

                print(f"  {rank+1}. {r.title} (${r.price})")
                print(f"     Score: {r.score:.4f} | Content: {m.content_score:.2f} | Collab: {m.collab_score:.2f} | KB: {m.knowledge_score:.2f}")
                print(f"     Matches: Occasion={m.occasion_match}, Age={age_match}, HobbyOverlap={m.hobby_overlap}, PriceFit={m.price_fit}")
                print(
                    "     Audit: {verdict} | Signals({hits}/5): {signals} | ScoreOK={score_ok} | ConfOK={conf_ok} | ContentOK={content_ok} | KBOK={kb_ok}{reasons}".format(
                        verdict=verdict,
                        hits=signal_hits,
                        signals=signal_summary,
                        score_ok="Y" if score_ok else "N",
                        conf_ok="Y" if confidence_ok else "N",
                        content_ok="Y" if content_ok else "N",
                        kb_ok="Y" if knowledge_ok else "N",
                        reasons=reason_text,
                    )
                )

            print("\n  Knowledge-Based Recommendations")
            kb_query = f"{tc['hobbies']} {tc['occasion']} {tc['age']} {tc['gender']}"
            kb_results = kb.score_gifts(
                gift_dicts,
                top_n=3,
                occasion=tc["occasion"],
                min_price=min_p,
                max_price=max_p,
                age=tc["age"],
                gender=tc["gender"],
                hobbies=tc["hobbies"],
                query_text=kb_query,
            )
            for rank, r in enumerate(kb_results):
                gift = gift_map.get(r["id"])
                if not gift:
                    continue
                details = await service.get_gift_details_with_metrics(
                    user_id=1,
                    gift_id=gift.id,
                    occasion=tc["occasion"],
                    age=tc["age"],
                    gender=tc["gender"],
                    hobbies=tc["hobbies"],
                    min_price=min_p,
                    max_price=max_p,
                )
                m = details.metrics
                target_label = match_age_group(tc["age"])
                gift_age_label = match_age_group(details.gift.age_group)
                age_match = (target_label == gift_age_label) if target_label and gift_age_label else m.age_group_match
                relevant, signals, signal_hits, score_ok, confidence_ok, content_ok, knowledge_ok, reasons = evaluate_relevance(
                    m, gift=details.gift, age_match_override=age_match
                )
                signal_summary = ", ".join([
                    f"{k}={'-' if v is None else ('Y' if v else 'N')}" for k, v in signals.items()
                ])
                verdict = "RELEVANT" if relevant else "CHECK"
                reason_text = " | Reasons: " + ", ".join(reasons) if reasons else ""
                print(f"    {rank+1}. {gift.title} (${gift.price}) | KB Score: {r['score']:.2f}")
                print(
                    "       Audit: {verdict} | Signals({hits}/5): {signals} | ScoreOK={score_ok} | ConfOK={conf_ok} | ContentOK={content_ok} | KBOK={kb_ok}{reasons}".format(
                        verdict=verdict,
                        hits=signal_hits,
                        signals=signal_summary,
                        score_ok="Y" if score_ok else "N",
                        conf_ok="Y" if confidence_ok else "N",
                        content_ok="Y" if content_ok else "N",
                        kb_ok="Y" if knowledge_ok else "N",
                        reasons=reason_text,
                    )
                )

            print("\n  RAG Recommendations")
            try:
                rag_query = (
                    f"{tc['occasion']} gift for a {tc['age']} {tc['gender']} who likes {tc['hobbies']} under {tc['budget']}"
                )
                rag_payload = RAGQueryCreate(
                    query=rag_query,
                    top_k=3,
                    budget_max=max_p,
                    occasion=tc["occasion"],
                    age=tc["age"],
                    gender=tc["gender"],
                    hobbies=tc["hobbies"],
                )
                rag_result = await rag_service.ask(db, user_id=1, request=rag_payload)
                rag_gifts = rag_result.get("retrieved_gifts", [])
                print(f"    Response: {rag_result.get('response')}")
                for rank, g in enumerate(rag_gifts):
                    gid = g.get("id")
                    title = g.get("title")
                    price = g.get("price")
                    if gid is None:
                        print(f"    {rank+1}. {title} (${price})")
                        continue
                    details = await service.get_gift_details_with_metrics(
                        user_id=1,
                        gift_id=gid,
                        occasion=tc["occasion"],
                        age=tc["age"],
                        gender=tc["gender"],
                        hobbies=tc["hobbies"],
                        min_price=min_p,
                        max_price=max_p,
                    )
                    m = details.metrics
                    target_label = match_age_group(tc["age"])
                    gift_age_label = match_age_group(details.gift.age_group)
                    age_match = (target_label == gift_age_label) if target_label and gift_age_label else m.age_group_match
                    relevant, signals, signal_hits, score_ok, confidence_ok, content_ok, knowledge_ok, reasons = evaluate_relevance(
                        m, gift=details.gift, age_match_override=age_match
                    )
                    signal_summary = ", ".join([
                        f"{k}={'-' if v is None else ('Y' if v else 'N')}" for k, v in signals.items()
                    ])
                    verdict = "RELEVANT" if relevant else "CHECK"
                    reason_text = " | Reasons: " + ", ".join(reasons) if reasons else ""
                    print(f"    {rank+1}. {title} (${price})")
                    print(
                        "       Audit: {verdict} | Signals({hits}/5): {signals} | ScoreOK={score_ok} | ConfOK={conf_ok} | ContentOK={content_ok} | KBOK={kb_ok}{reasons}".format(
                            verdict=verdict,
                            hits=signal_hits,
                            signals=signal_summary,
                            score_ok="Y" if score_ok else "N",
                            conf_ok="Y" if confidence_ok else "N",
                            content_ok="Y" if content_ok else "N",
                            kb_ok="Y" if knowledge_ok else "N",
                            reasons=reason_text,
                        )
                    )
            except Exception as exc:
                print(f"    RAG test failed: {exc}")

if __name__ == "__main__":
    asyncio.run(audit())
