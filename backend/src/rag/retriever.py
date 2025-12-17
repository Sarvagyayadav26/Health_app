import re


class Retriever:
    def __init__(self, embedder, vector_store):
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 3):
        query_lower = query.lower()
        query_words = set(query_lower.split())  # Split query into words

        # ================================
        # 1️⃣ TOPIC FILTERING (very important)
        # ================================
        valid_indices = []
        for i, metadata in enumerate(self.vector_store.metadatas):
            topics = metadata.get("topics", [])
            # Check if ANY topic matches:
            # - Topic phrase is in query (e.g., "love stress" in "love stress")
            # - OR any word from topic is in query (e.g., "love" or "stress" in "love stress")
            matches = False
            for topic in topics:
                topic_lower = topic.lower()
                # Check if full topic phrase is in query
                if topic_lower in query_lower:
                    matches = True
                    break

                # Break topic into alphanumeric tokens (handles hyphens, underscores, punctuation)
                topic_words = set(re.findall(r"\w+", topic_lower))
                if topic_words & query_words:  # Intersection of sets
                    matches = True
                    break
            
            if matches:
                valid_indices.append(i)

        # If NO matching topical docs → return empty
        if len(valid_indices) == 0:
            return []

        # ================================
        # 2️⃣ Filter embeddings & docs by topic
        # ================================
        filtered_embeddings = self.vector_store.embeddings[valid_indices]
        filtered_ids = [self.vector_store.ids[i] for i in valid_indices]
        filtered_texts = [self.vector_store.texts[i] for i in valid_indices]
        filtered_metadatas = [self.vector_store.metadatas[i] for i in valid_indices]

        # ================================
        # 3️⃣ Semantic similarity (only on topic-matched docs)
        # ================================
        q_emb = self.embedder.embed(query)[0]

        # Use temporary vector_store-like search
        from sklearn.neighbors import NearestNeighbors
        nn = NearestNeighbors(
            n_neighbors=min(top_k, len(filtered_embeddings)),
            metric="cosine"
        )
        nn.fit(filtered_embeddings)

        distances, indices = nn.kneighbors(q_emb.reshape(1, -1))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            results.append({
                "id": filtered_ids[idx],
                "text": filtered_texts[idx],
                "metadata": filtered_metadatas[idx],
                "score": float(dist)
            })

        return results
