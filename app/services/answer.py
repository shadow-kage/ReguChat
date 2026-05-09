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
        # Redis unavailable — degrade gracefully rather than returning 500.
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


async def stream_query(domain_id: str, query: str) -> AsyncIterator[str]:
    """
    Yields text chunks for SSE streaming.
    Bypasses the cache — streaming responses are not stored.
    """
    domain = DomainRegistry.get_instance().get(domain_id)
    if domain is None:
        yield f"Unknown domain: '{domain_id}'."
        return

    chunks = retrieve_top_k(query, domain)
    if not chunks:
        yield "No relevant information found in the knowledge base for this question."
        return

    async for chunk in stream_answer(
        rag_context=_build_rag_context(chunks),
        user_query=query,
        system_prompt=domain.system_prompt,
        noise_filters=domain.noise_filters,
    ):
        yield chunk
