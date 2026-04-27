from embeddings import model
from faiss_db import FAISSVectorDB
from cache_store import get_cache, store_cache
from orchestrator import generate_filtered_answer

VECTOR_DB_PATH = "vector_db"

# Global FAISS DB instance used by `ask()`.
# The index + texts are loaded from disk (built by `pipeline.py`).
try:
    _dim = int(getattr(model, "get_sentence_embedding_dimension", lambda: 384)())
except Exception:
    _dim = 384

db = FAISSVectorDB(_dim)
try:
    db.load(VECTOR_DB_PATH)
except Exception as e:
    raise RuntimeError(
        f"Failed to load FAISS vector DB from '{VECTOR_DB_PATH}'. "
        "Build it first by running: uv run src/pipeline.py"
    ) from e


def ask(query):
    cached = get_cache(query)

    if cached:
        print("CACHE HIT")
        return cached

    print("CACHE MISS → Searching FAISS")

    q_embed = model.encode(query)

    # Each result is (text, distance)
    results = db.search(q_embed)

    if not results:
        return "No information found in the database."

    best_text, best_distance = results[0]

    # Distance is squared L2 between normalized embeddings.
    # Larger distance => less similar. Threshold is tunable.
    if best_distance > 1.2:
        return "No relevant information found in the database for this question."

    store_cache(query, best_text)

    return best_text


def answer_with_orchestrator(query: str) -> str:
    """
    Full pipeline:
    - Runs FAISS/RAG to get the best matching context.
    - Uses the orchestrator to build a hidden system prompt from that context.
    - Calls Gemini with that system prompt + user query to produce a
      filtered, human‑readable answer.

    Returns only the final answer string (no raw context or system prompt).
    """
    rag_context = ask(query)
    return generate_filtered_answer(rag_context, user_query=query)


if __name__ == "__main__":
    while True:
        print("Ask a question or type 'exit' to quit")
        q = input()
        if q == "exit":
            break
        final_answer = answer_with_orchestrator(q)
        print(final_answer)
        print("\n==============================================================\n")