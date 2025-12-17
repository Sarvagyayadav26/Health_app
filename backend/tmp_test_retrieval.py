import json
from src.rag.embeddings import Embedder
from src.storage.vector_store import InMemoryVectorStore
from src.rag.retriever import Retriever

print('Loading vector store...')
store = InMemoryVectorStore()
store.load()
print('Loaded', len(store.ids), 'documents')

embedder = Embedder()
retriever = Retriever(embedder, store)

q = 'career advice for recent grads'
print('Query:', q)
results = retriever.retrieve(q, top_k=5)
print('Results count:', len(results))
print(json.dumps(results, indent=2))
