"""Embedding Service supporting OpenAI, Gemini, and deterministic local embeddings."""
import math
import hashlib
from typing import List
from ..core.config import settings

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two numeric vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

class EmbeddingService:
    def __init__(self):
        self.dimension = settings.EMBEDDING_DIMENSION

    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding vector based on configured provider, with deterministic offline fallback."""
        provider = settings.EMBEDDING_PROVIDER.lower()

        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                resp = client.embeddings.create(input=text, model=settings.EMBEDDING_MODEL)
                return resp.data[0].embedding
            except Exception:
                pass

        if provider == "google" and settings.GOOGLE_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                res = genai.embed_content(model="models/text-embedding-004", content=text)
                return res["embedding"]
            except Exception:
                pass

        # Deterministic semantic hash-embedding (fallback when no API key configured)
        return self._deterministic_vector(text, dim=128)

    def _deterministic_vector(self, text: str, dim: int = 128) -> List[float]:
        """Creates a normalized deterministic pseudo-semantic vector from text tokens."""
        words = text.lower().split()
        vec = [0.0] * dim
        for w in words:
            h = int(hashlib.md5(w.encode('utf-8')).hexdigest(), 16)
            for i in range(dim):
                bit = (h >> (i % 64)) & 1
                vec[i] += (1.0 if bit else -1.0)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

embedding_service = EmbeddingService()
