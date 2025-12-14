import numpy as np
from src.storage.vector_store import InMemoryVectorStore

def test_add_and_query():
    vs = InMemoryVectorStore()
    emb1 = np.array([1.0, 0.0, 0.0])
    emb2 = np.array([0.9, 0.1, 0.0])
    vs.add("a", "text a", emb1)
    vs.add("b", "text b", emb2)
    q = np.array([0.95, 0.05, 0.0])
    res = vs.query(q, top_k=2)
    assert len(res) == 2
    assert res[0]["id"] in {"a","b"}