from sentence_transformers import SentenceTransformer
import src.utils.config as config

class Embedder:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.EMBEDDING_MODEL
        self.model = SentenceTransformer(self.model_name)

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )
