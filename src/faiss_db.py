import os
import faiss
import numpy as np
import pickle


class FAISSVectorDB:
    """
    Wraps a FAISS flat-L2 index with a parallel list of chunk metadata dicts.
    Each stored item is expected to be {"text": str, "source": str}, though
    the class is agnostic to the dict shape — it stores and returns whatever
    is passed in.
    """

    def __init__(self, dim: int):
        self.index = faiss.IndexFlatL2(dim)
        self.chunks: list[dict] = []

    def add(self, embeddings, chunks: list[dict]) -> None:
        # FAISS requires float32; enforce it regardless of upstream dtype.
        self.index.add(np.array(embeddings, dtype=np.float32))
        self.chunks.extend(chunks)

    def search(self, query_embedding, k: int = 5) -> list[tuple[dict, float]]:
        query = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query, k)

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            # FAISS returns -1 for slots when k > number of stored vectors.
            if idx == -1:
                continue
            results.append((self.chunks[idx], float(dist)))
        return results

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "chunks.pkl"), "wb") as f:
            pickle.dump(self.chunks, f)

    def load(self, path: str) -> None:
        self.index = faiss.read_index(os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "chunks.pkl"), "rb") as f:
            self.chunks = pickle.load(f)
