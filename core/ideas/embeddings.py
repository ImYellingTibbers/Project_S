from typing import List
import os
import openai


openai.api_key = os.getenv("OPENAI_API_KEY")


def embed_text(text: str) -> List[float]:
    """
    Returns an embedding vector suitable for JSON storage.
    """
    resp = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return resp.data[0].embedding
