import re
from typing import AsyncIterator

from app.core.markers import Marker
from app.domain import DomainRegistry
from app.services.cache import get_cache, store_cache
from app.services.llm import AnswerResult, generate_answer, stream_answer
from app.services.retrieval import retrieve_top_k


def normalize_query(query: str) -> str:
    """Stable cache key: lowercase, collapsed whitespace, stripped punctuation."""
    key = query.lower().strip()
    key = re.sub(r"\s+", " ", key)
    key = key.rstrip("?.!")
    return key


def _build_rag_context(chunks: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    )


async def run_query(domain_id: str, query: str) -> tuple[AnswerResult, bool]:
    """
    Returns (AnswerResult, was_cached).
    Checks Redis before hitting FAISS + LLM; caches LLM answers on success.
    """
    domain = DomainRegistry.get_instance().get(domain_id)
    if domain is None:
        return AnswerResult(text=f"Unknown domain: '{domain_id}'.", is_fallback=True), False

    cache_key = normalize_query(query)

    try:
        cached = await get_cache(domain_id, cache_key)
        if cached:
            return AnswerResult(text=cached, is_fallback=False), True
    except Exception as e:
        print(f"  {Marker.CROSS} Cache read failed ({type(e).__name__}) — proceeding without cache")

    chunks = retrieve_top_k(query, domain)
    if not chunks:
        return (
            AnswerResult(
                text="No relevant information found in the knowledge base for this question.",
                is_fallback=False,
            ),
            False,
        )

    result = await generate_answer(
        rag_context=_build_rag_context(chunks),
        user_query=query,
        system_prompt=domain.system_prompt,
        noise_filters=domain.noise_filters,
    )

    if not result.is_fallback:
        try:
            await store_cache(domain_id, cache_key, result.text)
        except Exception as e:
            print(f"  {Marker.CROSS} Cache write failed ({type(e).__name__}) — answer returned without caching")

    return result, False


# Prefixes produced by _build_fallback in llm.py — these must not be cached.
_FALLBACK_PREFIXES = (
    "Concise summary couldn't be generated.",
    "Unable to generate an answer from the available information.",
)


async def stream_query(domain_id: str, query: str) -> AsyncIterator[dict]:
    """
    Yields SSE event dicts for the streaming endpoint.

    Event shapes:
      {"event": "status", "cache": "hit" | "miss"}
      {"event": "text",   "text": "<chunk>"}
      {"event": "done"}

    Writes to cache after streaming if the answer is not a rule-based fallback.
    """
    domain = DomainRegistry.get_instance().get(domain_id)
    if domain is None:
        yield {"event": "text", "text": f"Unknown domain: '{domain_id}'."}
        yield {"event": "done"}
        return

    cache_key = normalize_query(query)

    try:
        cached = await get_cache(domain_id, cache_key)
    except Exception as e:
        print(f"  {Marker.CROSS} Cache read failed ({type(e).__name__}) — proceeding without cache")
        cached = None

    if cached:
        yield {"event": "status", "cache": "hit"}
        yield {"event": "text", "text": cached}
        yield {"event": "done"}
        return

    yield {"event": "status", "cache": "miss"}

    chunks = retrieve_top_k(query, domain)
    if not chunks:
        yield {"event": "text", "text": "No relevant information found in the knowledge base for this question."}
        yield {"event": "done"}
        return

    collected: list[str] = []
    async for chunk in stream_answer(
        rag_context=_build_rag_context(chunks),
        user_query=query,
        system_prompt=domain.system_prompt,
        noise_filters=domain.noise_filters,
    ):
        collected.append(chunk)
        yield {"event": "text", "text": chunk}

    yield {"event": "done"}

    full_text = "".join(collected)
    if full_text and not full_text.startswith(_FALLBACK_PREFIXES):
        try:
            await store_cache(domain_id, cache_key, full_text)
        except Exception as e:
            print(f"  {Marker.CROSS} Cache write failed ({type(e).__name__}) — answer returned without caching")
