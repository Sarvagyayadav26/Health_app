import os
import numpy as np
from sklearn.neighbors import NearestNeighbors
import json
import src.utils.config as config

class InMemoryVectorStore:
    def __init__(self):
        self.ids = []
        self.texts = []
        self.metadatas = []
        self.embeddings = None
        self._nn = None

    def add(self, doc_id: str, text: str, embedding: np.ndarray, metadata: dict = None):
        self.ids.append(doc_id)
        self.texts.append(text)
        self.metadatas.append(metadata or {})

        embedding = embedding.reshape(1, -1)

        if self.embeddings is None:
            self.embeddings = embedding
        else:
            self.embeddings = np.vstack([self.embeddings, embedding])

        self._nn = None  # reset index

    def _ensure_index(self):
        if self._nn is None and self.embeddings is not None and len(self.embeddings) > 0:
            n_neighbors = min(10, len(self.embeddings))
            self._nn = NearestNeighbors(n_neighbors=n_neighbors, metric="cosine")
            self._nn.fit(self.embeddings)

    def query(self, query_embedding, top_k=3):
        self._ensure_index()

        if self._nn is None:
            return []

        distances, indices = self._nn.kneighbors(
            query_embedding.reshape(1, -1),
            n_neighbors=min(top_k, len(self.embeddings))
        )

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            results.append({
                "id": self.ids[idx],
                "text": self.texts[idx],
                "metadata": self.metadatas[idx],
                "score": float(dist),  # cosine distance
            })

        return results

    def save(self, path=None):
        path = path or config.VECTOR_STORE_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)

        np.savez(
            path,
            embeddings=self.embeddings.astype("float32") if self.embeddings is not None else np.empty((0,)),
            ids=np.array(self.ids, dtype=object),
            texts=np.array(self.texts, dtype=object),
            metadatas=np.array(self.metadatas, dtype=object)
        )

    def load(self, path=None):
        path = path or config.VECTOR_STORE_PATH
        if not os.path.exists(path):
            return

        data = np.load(path, allow_pickle=True)

        self.embeddings = data["embeddings"]
        self.ids = data["ids"].tolist()
        self.texts = data["texts"].tolist()
        self.metadatas = data["metadatas"].tolist()
        self._nn = None
