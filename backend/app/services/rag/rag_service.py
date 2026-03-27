"""
Retrieval-Augmented Generation (RAG) Service.

Pipeline:
1. Embed the user's natural-language query using OpenAI Embeddings API
2. Perform vector similarity search in pgvector to retrieve top-K relevant gifts
3. Build a context string from retrieved gifts
4. Send context + query to OpenAI Chat Completions API
5. Return the generated explanation and the retrieved gifts
6. Persist the query and response to rag_queries table

Uses:
- openai.AsyncOpenAI for async API calls
- pgvector for similarity search
- tenacity for retry logic on transient API errors
"""

import json
import asyncio
import re
from typing import Optional
import httpx
from openai import AsyncOpenAI, APIError, RateLimitError, BadRequestError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.models import RAGQuery
from app.repositories.gift_repository import GiftRepository, CategoryRepository
from app.repositories.web_gift_repository import WebGiftRepository
from app.models.models import WebGift
from app.repositories.interaction_repository import RAGQueryRepository
from app.schemas.recommendation import RAGQueryCreate, RAGQueryResponse


class RAGService:
    SYSTEM_PROMPT = """You are GiftGenius, an expert AI gift advisor.
You will be given a user's gift request and a list of relevant gift options retrieved from a database.
Your job is to:
1. Analyze the user's needs, occasion, relationship, and budget (if mentioned)
2. Recommend the most suitable gifts from the provided options
3. Explain WHY each gift is suitable in a warm, helpful tone
4. Give practical tips for personalizing or presenting the gift

Only recommend gifts from the provided context. Do NOT make up gifts.
Format your response clearly with numbered recommendations."""

    IDEA_SYSTEM_PROMPT = """You are a gift recommendation engine that outputs JSON.
Given a user request, generate a diverse list of gift ideas that could plausibly exist in a catalog.

Rules:
- Output MUST be valid JSON only (no Markdown)
- Output shape: {"gifts": [ ... ]}
- Each gift must have: title, description, category, price, occasion, relationship, tags
- price must be a number (float)
- Keep titles short and non-duplicative
- Prefer practical real-world products; do not include brand names unless necessary
- If the user mentions a budget, keep prices within it
"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=60.0)
        self.chat_model = self._resolve_chat_model()
        self.embedding_model = self._resolve_embedding_model()
        # DB column is Vector(1536) in app.models.models.Gift.embedding
        self.vector_dim = 1536

    def _coerce_embedding_dim(self, vector: list[float]) -> list[float]:
        """Force embedding dimensionality to match pgvector column width.

        If model output is longer, truncate. If shorter, zero-pad.
        This avoids runtime DB errors when embedding model and DB schema differ.
        """
        if vector is None:
            return []
        dim = self.vector_dim
        if len(vector) == dim:
            return vector
        if len(vector) > dim:
            logger.warning(
                "rag.embedding_truncated",
                current_dim=len(vector),
                target_dim=dim,
                model=self.embedding_model,
            )
            return vector[:dim]
        logger.warning(
            "rag.embedding_padded",
            current_dim=len(vector),
            target_dim=dim,
            model=self.embedding_model,
        )
        return vector + ([0.0] * (dim - len(vector)))

    def _resolve_chat_model(self) -> str:
        configured = (settings.OPENAI_RAG_CHAT_MODEL or settings.OPENAI_CHAT_MODEL or "gpt-4o").strip()
        lowered = configured.lower()
        if lowered in {"gpt-40", "gpt4o", "gpt_4o"}:
            return "gpt-4o"
        return configured

    def _resolve_embedding_model(self) -> str:
        configured = (settings.OPENAI_RAG_EMBEDDING_MODEL or settings.OPENAI_EMBEDDING_MODEL or "text-embedding-3-small").strip()
        lowered = configured.lower()
        aliases = {
            "embedding-3-small": "text-embedding-3-small",
            "embedding-3-large": "text-embedding-3-large",
        }
        return aliases.get(lowered, configured)

    async def _create_embedding_with_fallback(self, text_input: str | list[str]):
        preferred = self.embedding_model
        candidates = [
            preferred,
            settings.OPENAI_EMBEDDING_MODEL,
            "text-embedding-3-large",
            "text-embedding-3-small",
        ]
        tried: set[str] = set()
        last_error: Exception | None = None

        for model in candidates:
            if not model:
                continue
            model = str(model).strip()
            if not model or model in tried:
                continue
            tried.add(model)
            try:
                return await self.client.embeddings.create(
                    model=model,
                    input=text_input,
                )
            except BadRequestError as e:
                last_error = e
                msg = str(e).lower()
                if "model" in msg or "not found" in msg or "unsupported" in msg:
                    logger.warning("rag.embedding_model_fallback", tried_model=model, error=str(e))
                    continue
                raise
            except Exception as e:
                last_error = e
                raise

        if last_error:
            raise last_error
        raise RuntimeError("No embedding model candidates available")

    async def _create_chat_completion_with_fallback(self, *, messages: list[dict], temperature: float, max_tokens: int, response_format: Optional[dict] = None):
        preferred = self.chat_model
        candidates = [
            preferred,
            settings.OPENAI_CHAT_MODEL,
            "gpt-4o",
            "gpt-4o-mini",
        ]
        tried: set[str] = set()
        last_error: Exception | None = None

        for model in candidates:
            if not model:
                continue
            model = str(model).strip()
            if not model or model in tried:
                continue
            tried.add(model)
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format is not None:
                    payload["response_format"] = response_format
                return await self.client.chat.completions.create(**payload)
            except BadRequestError as e:
                last_error = e
                msg = str(e).lower()
                if "model" in msg or "not found" in msg or "unsupported" in msg or "permission" in msg:
                    logger.warning("rag.chat_model_fallback", tried_model=model, error=str(e))
                    continue
                raise
            except Exception as e:
                last_error = e
                raise

        if last_error:
            raise last_error
        raise RuntimeError("No chat model candidates available")

    def _parse_price(self, raw: str | None) -> Optional[float]:
        if not raw:
            return None
        m = re.search(r"([0-9]+(?:\.[0-9]+)?)", raw.replace(",", ""))
        return float(m.group(1)) if m else None

    async def _fetch_web_gifts(self, query: str) -> list[dict]:
        """Fetch external gift ideas from a web search provider (optional)."""
        if not (settings.WEB_SEARCH_API_KEY and settings.WEB_SEARCH_ENDPOINT):
            return []

        provider = (settings.WEB_SEARCH_PROVIDER or "").lower()
        params = {}
        headers = {}

        if provider == "serpapi":
            params = {
                "engine": "google_shopping",
                "q": query,
                "api_key": settings.WEB_SEARCH_API_KEY,
                "num": settings.WEB_SEARCH_LIMIT,
            }
        elif provider == "brave":
            headers = {"X-Subscription-Token": settings.WEB_SEARCH_API_KEY}
            params = {
                "q": query,
                "count": settings.WEB_SEARCH_LIMIT,
            }
        else:
            return []

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(settings.WEB_SEARCH_ENDPOINT, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        items: list[dict] = []
        if provider == "serpapi":
            for r in data.get("shopping_results", [])[: settings.WEB_SEARCH_LIMIT]:
                items.append(
                    {
                        "title": r.get("title"),
                        "description": r.get("snippet"),
                        "price": self._parse_price(r.get("price")),
                        "product_url": r.get("link"),
                        "image_url": r.get("thumbnail"),
                        "source": "web",
                    }
                )
        elif provider == "brave":
            for r in data.get("web", {}).get("results", [])[: settings.WEB_SEARCH_LIMIT]:
                items.append(
                    {
                        "title": r.get("title"),
                        "description": r.get("description"),
                        "price": None,
                        "product_url": r.get("url"),
                        "image_url": None,
                        "source": "web",
                    }
                )

        return [i for i in items if i.get("title")]

    async def _ingest_web_gifts(
        self,
        db: AsyncSession,
        gifts: list[dict],
        occasion: Optional[str],
        relationship: Optional[str],
    ) -> list[int]:
        gift_repo = GiftRepository(db)
        category_repo = CategoryRepository(db)
        web_repo = WebGiftRepository(db)
        category, _ = await category_repo.get_or_create("Web")

        created_ids: list[int] = []
        for g in gifts:
            existing = None
            source_url = g.get("product_url")
            if source_url:
                existing = await gift_repo.get_by_product_url(source_url)
                existing_web = await web_repo.get_by_source_url(source_url)
                if existing_web:
                    continue
            if existing is None:
                existing = await gift_repo.get_by_title(g.get("title", ""))

            if existing:
                if await web_repo.get_by_gift_id(existing.id):
                    continue
                web_entry = WebGift(
                    gift_id=existing.id,
                    source="web",
                    source_url=source_url,
                    query=None,
                    provider=settings.WEB_SEARCH_PROVIDER or None,
                    raw_payload=json.dumps(g) if g else None,
                )
                db.add(web_entry)
                created_ids.append(existing.id)
                continue

            price = g.get("price")
            if price is None:
                price = 25.0  # default placeholder if price missing

            new_gift = gift_repo.model(
                title=g.get("title"),
                description=g.get("description") or "Imported from web search.",
                category_id=category.id,
                price=price,
                occasion=occasion,
                relationship=relationship,
                image_url=g.get("image_url"),
                product_url=g.get("product_url"),
            )
            await gift_repo.create(new_gift)

            web_entry = WebGift(
                gift_id=new_gift.id,
                source="web",
                source_url=source_url,
                query=None,
                provider=settings.WEB_SEARCH_PROVIDER or None,
                raw_payload=json.dumps(g) if g else None,
            )
            db.add(web_entry)

            # embed immediately if OpenAI key is available
            if settings.OPENAI_API_KEY:
                try:
                    emb = await self.embed_text(
                        f"{new_gift.title}. {new_gift.description or ''}."
                    )
                    await gift_repo.update_embedding(new_gift.id, emb)
                except Exception as e:
                    logger.error("rag.web_embed_failed", gift_id=new_gift.id, error=str(e))

            created_ids.append(new_gift.id)

        return created_ids

    async def ingest_web_gifts(
        self,
        db: AsyncSession,
        query: str,
        limit: Optional[int] = None,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
    ) -> dict:
        web_candidates = await self._fetch_web_gifts(query)
        if limit:
            web_candidates = web_candidates[:limit]
        created_ids = await self._ingest_web_gifts(db, web_candidates, occasion, relationship)
        return {
            "message": "Web gifts ingested",
            "created": len(created_ids),
            "skipped": max(len(web_candidates) - len(created_ids), 0),
        }

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding vector for a given text string."""
        response = await self._create_embedding_with_fallback(text.replace("\n", " "))
        return self._coerce_embedding_dim(response.data[0].embedding)

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_response(
        self,
        user_query: str,
        gift_context: str,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        age: Optional[str] = None,
        gender: Optional[str] = None,
        hobbies: Optional[str] = None,
    ) -> str:
        """Call OpenAI Chat API with retrieved context to generate recommendation explanation."""
        user_message = f"""User Request: {user_query}

Context Details:
Occasion: {occasion or 'Not specified'}
Relationship: {relationship or 'Not specified'}
Recipient Age: {age or 'Not specified'}
Recipient Gender: {gender or 'Not specified'}
Recipient Hobbies/Interests: {hobbies or 'Not specified'}

Available Gift Options:
{gift_context}

Please provide personalized gift recommendations based on the options above."""

        response = await self._create_chat_completion_with_fallback(
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content or ""

    @retry(
        retry=retry_if_exception_type((RateLimitError, APIError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_gift_ideas_json(
        self,
        user_query: str,
        top_n: int = 6,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        age: Optional[str] = None,
        gender: Optional[str] = None,
        hobbies: Optional[str] = None,
    ) -> dict:
        """Generate new gift ideas as structured JSON suitable for DB ingestion."""
        constraints = {
            "top_n": top_n,
            "occasion": occasion,
            "relationship": relationship,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "age": age,
            "gender": gender,
            "hobbies": hobbies,
        }
        prompt = (
            "User request: " + (user_query or "") + "\n" +
            "Constraints: " + json.dumps(constraints) + "\n" +
            f"Return {top_n} gifts."
        )
        resp = await self._create_chat_completion_with_fallback(
            messages=[
                {"role": "system", "content": self.IDEA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=900,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Last-ditch: try to extract JSON substring
            m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if m:
                return json.loads(m.group(0))
            raise

    async def _upsert_generated_gifts(
        self,
        db: AsyncSession,
        gifts_payload: dict,
        occasion: Optional[str],
        relationship: Optional[str],
    ) -> list[int]:
        """Insert generated gifts into main DB and embed them to populate vector index."""
        gift_repo = GiftRepository(db)
        category_repo = CategoryRepository(db)

        items = gifts_payload.get("gifts") if isinstance(gifts_payload, dict) else None
        if not isinstance(items, list):
            return []

        created_ids: list[int] = []
        for g in items:
            title = str((g or {}).get("title") or "").strip()
            if not title:
                continue

            existing = await gift_repo.get_by_title(title)
            if existing:
                created_ids.append(existing.id)
                continue

            category_name = str((g or {}).get("category") or "General").strip() or "General"
            category, _ = await category_repo.get_or_create(category_name)

            price = (g or {}).get("price")
            try:
                price_f = float(price)
            except Exception:
                price_f = 25.0

            new_gift = gift_repo.model(
                title=title,
                description=str((g or {}).get("description") or "").strip() or "Suggested by AI.",
                category_id=category.id,
                price=price_f,
                occasion=str((g or {}).get("occasion") or occasion or "").strip() or None,
                relationship=str((g or {}).get("relationship") or relationship or "").strip() or None,
                tags=str((g or {}).get("tags") or "").strip() or None,
                image_url=None,
                product_url=None,
            )
            await gift_repo.create(new_gift)

            if settings.OPENAI_API_KEY:
                try:
                    emb = await self.embed_text(
                        f"{new_gift.title}. {new_gift.description or ''}. "
                        f"Occasion: {new_gift.occasion or ''}. Relationship: {new_gift.relationship or ''}. "
                        f"Category: {category_name}. Tags: {new_gift.tags or ''}."
                    )
                    await gift_repo.update_embedding(new_gift.id, emb)
                except Exception as e:
                    logger.error("rag.generated_embed_failed", gift_id=new_gift.id, error=str(e))

            created_ids.append(new_gift.id)

        return created_ids

    def _build_gift_context(self, gifts: list) -> str:
        """Format retrieved gifts into a structured context string for the LLM."""
        lines = []
        for i, gift in enumerate(gifts, 1):
            category_name = gift.category.name if gift.category else "General"
            line = (
                f"{i}. **{gift.title}** (${gift.price:.2f})\n"
                f"   Category: {category_name}\n"
                f"   Occasion: {gift.occasion or 'Any'} | Relationship: {gift.relationship or 'Any'}\n"
                f"   Description: {gift.description or 'No description available.'}"
            )
            lines.append(line)
        return "\n\n".join(lines)

    async def ask(
        self,
        db: AsyncSession,
        user_id: int,
        request: RAGQueryCreate,
    ) -> dict:
        """
        Full RAG pipeline: embed → retrieve → generate → persist.

        Returns:
            dict with keys: query, response, retrieved_gifts (list of gift dicts)
        """
        rag_repo = RAGQueryRepository(db)
        gift_repo = GiftRepository(db)

        logger.info("rag.query_received", user_id=user_id, query=request.query[:100])

        if not settings.OPENAI_API_KEY:
            logger.warning("rag.no_openai_key_fallback")
            web_candidates = await self._fetch_web_gifts(request.query)
            if web_candidates:
                await self._ingest_web_gifts(
                    db,
                    web_candidates,
                    request.occasion,
                    request.relationship,
                )
            all_gifts = await gift_repo.get_all_gifts()
            query_tokens = set(re.findall(r"[a-zA-Z0-9']+", request.query.lower()))
            filter_tokens = set(
                re.findall(
                    r"[a-zA-Z0-9']+",
                    " ".join([
                        request.age or "",
                        request.gender or "",
                        request.hobbies or "",
                    ]).lower(),
                )
            )
            scored = []
            for g in all_gifts:
                if request.budget_max is not None and g.price is not None and g.price > request.budget_max:
                    continue
                if request.occasion and g.occasion:
                    if request.occasion.lower() not in g.occasion.lower():
                        continue
                if request.relationship and g.relationship:
                    if request.relationship.lower() not in g.relationship.lower():
                        continue
                text = " ".join(
                    [
                        g.title or "",
                        g.description or "",
                        g.category.name if g.category else "",
                        g.occasion or "",
                        g.relationship or "",
                    ]
                ).lower()
                gift_tokens = set(re.findall(r"[a-zA-Z0-9']+", text))
                if filter_tokens and not (filter_tokens & gift_tokens):
                    continue
                overlap = len(query_tokens & gift_tokens) / max(len(query_tokens), 1)
                if overlap > 0:
                    scored.append((overlap, g))
            scored.sort(key=lambda x: x[0], reverse=True)
            retrieved_gifts = [g for _, g in scored[: request.top_k]]
            return {
                "query": request.query,
                "response": "RAG fallback used (no OpenAI key). Showing keyword matches.",
                "retrieved_gifts": [
                    {
                        "id": g.id,
                        "title": g.title,
                        "description": g.description,
                        "price": g.price,
                        "occasion": g.occasion,
                        "relationship": g.relationship,
                        "image_url": g.image_url,
                        "product_url": g.product_url,
                        "category_name": g.category.name if g.category else None,
                    }
                    for g in retrieved_gifts
                ],
            }

        # Step 1: Embed the user query
        try:
            query_embedding = await self.embed_text(request.query)
        except Exception as e:
            logger.error("rag.embedding_failed", error=str(e))
            raise

        # Step 2: Vector similarity search
        retrieved_gifts = await gift_repo.similarity_search(
            query_embedding=query_embedding,
            top_k=request.top_k,
            occasion=request.occasion,
            relationship=request.relationship,
            max_price=request.budget_max,
        )

        # Heuristic: treat very-far matches as "no result".
        # similarity_search currently returns only Gift objects, so we approximate by requiring
        # at least a minimal count; the optional soft fallback below will build new candidates.

        # If filters are too strict (occasion/relationship missing in data), retry without them
        if not retrieved_gifts and (request.occasion or request.relationship):
            retrieved_gifts = await gift_repo.similarity_search(
                query_embedding=query_embedding,
                top_k=request.top_k,
                occasion=None,
                relationship=None,
                max_price=request.budget_max,
            )

    # If vector search returns nothing, pull web gifts even when OpenAI key exists
        if not retrieved_gifts:
            web_candidates = await self._fetch_web_gifts(request.query)
            if web_candidates:
                await self._ingest_web_gifts(
                    db,
                    web_candidates,
                    request.occasion,
                    request.relationship,
                )
                # Re-run similarity search after ingesting web gifts
                retrieved_gifts = await gift_repo.similarity_search(
                    query_embedding=query_embedding,
                    top_k=request.top_k,
                    occasion=request.occasion,
                    relationship=request.relationship,
                    max_price=request.budget_max,
                )

        # If still nothing, generate brand-new gift ideas via OpenAI and ingest them.
        if not retrieved_gifts:
            try:
                ideas = await self.generate_gift_ideas_json(
                    user_query=request.query,
                    top_n=max(5, min(10, request.top_k)),
                    occasion=request.occasion,
                    relationship=request.relationship,
                    budget_min=request.budget_min if hasattr(request, "budget_min") else None,
                    budget_max=request.budget_max,
                    age=request.age,
                    gender=request.gender,
                    hobbies=request.hobbies,
                )
                created_ids = await self._upsert_generated_gifts(
                    db=db,
                    gifts_payload=ideas,
                    occasion=request.occasion,
                    relationship=request.relationship,
                )
                await db.commit()
                if created_ids:
                    # Re-run similarity search now that we have fresh vectors
                    retrieved_gifts = await gift_repo.similarity_search(
                        query_embedding=query_embedding,
                        top_k=request.top_k,
                        occasion=request.occasion,
                        relationship=request.relationship,
                        max_price=request.budget_max,
                    )
            except Exception as e:
                logger.error("rag.idea_fallback_failed", error=str(e))

        # Re-rank retrieved gifts with hobby/interest keyword overlap when present
        if retrieved_gifts:
            def _tokenize(text: str) -> set[str]:
                return {t.lower() for t in re.findall(r"[a-zA-Z0-9']+", text or "") if len(t) > 1}

            # Extract hobby-like tokens from the query
            query_text = request.query or ""
            hobby_tokens: set[str] = set()
            for m in re.finditer(r"(?:enjoys|likes|interested in|hobby is)\s+([a-zA-Z0-9\s,&-]{3,})", query_text, flags=re.IGNORECASE):
                hobby_tokens |= _tokenize(m.group(1))
            # If no explicit hobbies found, use a lightweight keyword set from the whole query
            if not hobby_tokens:
                hobby_tokens = _tokenize(query_text)

            def _score_gift(g) -> float:
                text = " ".join([
                    g.title or "",
                    g.description or "",
                    g.category.name if g.category else "",
                    g.occasion or "",
                    g.relationship or "",
                ])
                gift_tokens = _tokenize(text)
                if not hobby_tokens:
                    return 0.0
                overlap = len(hobby_tokens & gift_tokens) / max(len(hobby_tokens), 1)
                return overlap

            # Prefer gifts with any hobby overlap when such tokens exist
            if hobby_tokens:
                overlap_candidates = [g for g in retrieved_gifts if _score_gift(g) > 0]
                if overlap_candidates:
                    retrieved_gifts = overlap_candidates

            retrieved_gifts = sorted(
                retrieved_gifts,
                key=lambda g: _score_gift(g),
                reverse=True,
            )

        if not retrieved_gifts:
            all_gifts = await gift_repo.get_all_gifts()
            filtered = []
            for g in all_gifts:
                if request.occasion and g.occasion and request.occasion.lower() not in g.occasion.lower():
                    continue
                if request.relationship and g.relationship and request.relationship.lower() not in g.relationship.lower():
                    continue
                if request.budget_max is not None and g.price > request.budget_max:
                    continue
                filtered.append(g)
            retrieved_gifts = filtered[: request.top_k]

            if not retrieved_gifts:
                response_text = (
                    "I couldn't find gifts matching your exact criteria in our database. "
                    "Try broadening your search or adjusting the budget and filters."
                )
                rag_entry = RAGQuery(
                    user_id=user_id,
                    query=request.query,
                    response=response_text,
                )
                await rag_repo.create(rag_entry)
                return {
                    "id": rag_entry.id,
                    "query": request.query,
                    "response": response_text,
                    "retrieved_gifts": [],
                }

        # Step 3: Build context
        gift_context = self._build_gift_context(retrieved_gifts)

        # Step 4: Generate LLM response
        try:
            response_text = await self.generate_response(
                user_query=request.query,
                gift_context=gift_context,
                occasion=request.occasion,
                relationship=request.relationship,
                age=request.age,
                gender=request.gender,
                hobbies=request.hobbies,
            )
        except Exception as e:
            logger.error("rag.generation_failed", error=str(e))
            response_text = (
                f"I found {len(retrieved_gifts)} relevant gifts for you, "
                "but I'm having trouble generating a detailed explanation right now. "
                "Please try again shortly."
            )

        # Step 5: Persist query + response
        rag_entry = RAGQuery(
            user_id=user_id,
            query=request.query,
            response=response_text,
        )
        await rag_repo.create(rag_entry)

        retrieved_gift_dicts = [
            {
                "id": g.id,
                "title": g.title,
                "price": g.price,
                "occasion": g.occasion,
                "relationship": g.relationship,
                "description": g.description,
                "category": g.category.name if g.category else None,
            }
            for g in retrieved_gifts
        ]

        logger.info(
            "rag.query_complete",
            user_id=user_id,
            n_retrieved=len(retrieved_gifts),
            rag_query_id=rag_entry.id,
        )

        return {
            "id": rag_entry.id,
            "query": request.query,
            "response": response_text,
            "retrieved_gifts": retrieved_gift_dicts,
        }

    async def embed_and_store_gifts(self, db: AsyncSession, batch_size: int = 100) -> dict:
        """
        Batch-embed all gifts that don't yet have an embedding vector.
        Uses OpenAI batch embedding API for efficiency.
        Called at startup or on demand via admin endpoint.
        """
        gift_repo = GiftRepository(db)
        gifts_without_embeddings = await gift_repo.get_gifts_without_embeddings()

        if not gifts_without_embeddings:
            return {"message": "All gifts already have embeddings.", "updated": 0}

        total = len(gifts_without_embeddings)
        updated = 0
        failed = 0

        # Process in batches
        for i in range(0, total, batch_size):
            batch = gifts_without_embeddings[i:i + batch_size]
            texts = [
                (
                    f"{g.title}. {g.description or ''} "
                    f"Occasion: {g.occasion or ''}. Relationship: {g.relationship or ''}. "
                    f"Category: {g.category.name if g.category else ''}. "
                    f"Tags: {g.tags or ''}. Age group: {g.age_group or ''}."
                )
                for g in batch
            ]

            try:
                response = None
                for attempt in range(3):
                    try:
                        response = await self._create_embedding_with_fallback(
                            [t.replace("\n", " ") for t in texts]
                        )
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise
                        logger.warning("rag.batch_retry", batch_start=i, attempt=attempt + 1, error=str(e))
                        await asyncio.sleep(2 + attempt * 2)
                for j, emb_data in enumerate(response.data):
                    try:
                        await gift_repo.update_embedding(batch[j].id, emb_data.embedding)
                        updated += 1
                    except Exception as e:
                        logger.error("rag.embed_store_failed", gift_id=batch[j].id, error=str(e))
                        failed += 1

                # Commit each batch
                await db.commit()
                logger.info("rag.batch_embedded", batch=i // batch_size + 1, updated=updated, total=total)
                await asyncio.sleep(0.6)
            except Exception as e:
                logger.error("rag.batch_embed_failed", batch_start=i, error=str(e))
                failed += len(batch)

        logger.info("rag.embeddings_complete", updated=updated, failed=failed, total=total)
        return {
            "message": f"Embeddings updated for {updated}/{total} gifts. Failed: {failed}.",
            "updated": updated,
            "failed": failed,
            "total": total,
        }
