
from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)


@lru_cache(maxsize=1)
def get_semantic_model() -> SentenceTransformer:
    """Load the local embedding model once per application process."""
    return SentenceTransformer(MODEL_NAME)
