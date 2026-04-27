import faiss
import numpy as np
import pickle

class FAISSVectorDB:

    def __init__(self, dim):

        self.index = faiss.IndexFlatL2(dim)
        self.texts = []

    def add(self, embeddings, texts):

        self.index.add(np.array(embeddings))
        self.texts.extend(texts)

    def search(self, query_embedding, k=5):

        D, I = self.index.search(np.array([query_embedding]), k)

        # Return (text, distance) pairs so callers can
        # decide if a match is relevant enough.
        results = []
        for rank, idx in enumerate(I[0]):
            # Distance is squared L2 from IndexFlatL2
            dist = float(D[0][rank])
            results.append((self.texts[idx], dist))

        return results

    def save(self, path):

        faiss.write_index(self.index, f"{path}/index.faiss")

        with open(f"{path}/texts.pkl", "wb") as f:
            pickle.dump(self.texts, f)

    def load(self, path):

        self.index = faiss.read_index(f"{path}/index.faiss")

        with open(f"{path}/texts.pkl", "rb") as f:
            self.texts = pickle.load(f)