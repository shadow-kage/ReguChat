import asyncio
import re
from embeddings import model, EMBEDDING_DIM
from faiss_db import FAISSVectorDB
from cache_store import get_cache, store_cache
from orchestrator import generate_answer
from _markers import Marker

VECTOR_DB_PATH = "vector_db"

# Squared L2 distance threshold between normalized embeddings.
# With unit-norm vectors the range is [0, 2]; cosine similarity = 1 - dist/2.
# 1.2 corresponds to cosine similarity ≈ 0.4 — below this the match is too
# weak to be a reliable source for a medical answer.
_RELEVANCE_THRESHOLD = 1.2

_SEPARATOR = "─" * 60

_db = FAISSVectorDB(EMBEDDING_DIM)
try:
    _db.load(VECTOR_DB_PATH)
except Exception as e:
    raise RuntimeError(
        f"Failed to load FAISS vector DB from '{VECTOR_DB_PATH}'. "
        "Build it first by running: python src/pipeline.py"
    ) from e


def _normalize_query(query: str) -> str:
    """
    Produces a stable cache key from a raw query string.
    Lowercases, collapses whitespace, and strips trailing punctuation so that
    trivial variations ("What is diabetes?" / "what is diabetes") resolve to
    the same key without altering the query sent to the LLM or FAISS.
    """
    key = query.lower().strip()
    key = re.sub(r"\s+", " ", key)
    key = key.rstrip("?.!")
    return key


def _retrieve_top_k(query: str, k: int = 3) -> list[dict]:
    """
    Returns up to k chunks that pass the relevance threshold, ordered by
    similarity. Returns an empty list if no match is close enough.
    """
    q_embed = model.encode(query)
    results = _db.search(q_embed, k=k)
    return [chunk for chunk, dist in results if dist <= _RELEVANCE_THRESHOLD]


async def answer(query: str) -> str:
    """
    Full retrieval-augmented generation pipeline.

    Checks Redis cache first. On a miss, retrieves the top-3 matching chunks
    from FAISS and passes them to Gemini (with Claude as fallback) for a
    filtered, human-readable answer. Only LLM-generated answers are cached;
    rule-based fallbacks are not, so repeated queries can still get a real
    answer once the LLM recovers.
    """
    cache_key = _normalize_query(query)

    cached = await get_cache(cache_key)
    if cached:
        print(f"  {Marker.HEAVY_CHECK} Cache hit\n")
        return cached

    print(f"  {Marker.SKIP} Searching knowledge base...\n")

    chunks = _retrieve_top_k(query)
    if not chunks:
        return "No relevant information found in the knowledge base for this question."

    rag_context = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in chunks
    )

    result = await generate_answer(rag_context, user_query=query)

    if not result.is_fallback:
        await store_cache(cache_key, result.text)

    return result.text


async def _repl() -> None:
    print("\nReguChat — Medical Q&A")
    print(_SEPARATOR)
    print("Type a question and press Enter. Type 'exit' to quit.\n")
    while True:
        query = input("Question: ").strip()
        if query.lower() == "exit":
            break
        if not query:
            continue
        print()
        print(await answer(query))
        print(f"\n{_SEPARATOR}\n")


if __name__ == "__main__":
    asyncio.run(_repl())
