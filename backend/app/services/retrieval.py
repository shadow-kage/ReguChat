from app.core.embeddings import model
from app.domain import DomainPack


def retrieve_top_k(query: str, domain: DomainPack) -> list[dict]:
    q_embed = model.encode(query)
    results = domain.db.search(q_embed, k=domain.top_k)
    return [chunk for chunk, dist in results if dist <= domain.relevance_threshold]
