import uuid

class Indexer:
    def __init__(self, embedder, vector_store):
        self.embedder = embedder
        self.vector_store = vector_store

    def index_documents(self, docs):
        """
        docs: iterable of dicts with keys: 'text' and optional 'metadata'
        """
        for doc in docs:
            doc_id = doc.get("id") or str(uuid.uuid4())
            text = doc["text"]
            embedding = self.embedder.embed(text)[0]
            self.vector_store.add(doc_id, text, embedding, doc.get("metadata", {}))
        self.vector_store.save()