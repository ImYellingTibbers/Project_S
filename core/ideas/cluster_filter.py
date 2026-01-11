import numpy as np
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity
import hdbscan


CLUSTER_SIMILARITY_THRESHOLD = 0.90
CLUSTER_SATURATION_LIMIT = 25


def cluster_embeddings(embeddings: List[List[float]]):
    """
    Returns cluster labels (-1 = noise).
    """
    if len(embeddings) < 5:
        return [-1] * len(embeddings)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=5,
        metric="euclidean"
    )
    return clusterer.fit_predict(embeddings)


def should_reject_candidate(
    candidate_embedding: List[float],
    past_embeddings: List[List[float]],
    cluster_labels: List[int],
) -> bool:
    if not past_embeddings:
        return False

    sims = cosine_similarity(
        [candidate_embedding],
        past_embeddings
    )[0]

    best_idx = int(np.argmax(sims))
    best_sim = sims[best_idx]

    if best_sim < CLUSTER_SIMILARITY_THRESHOLD:
        return False

    cluster_id = cluster_labels[best_idx]
    if cluster_id == -1:
        return False

    cluster_size = sum(1 for c in cluster_labels if c == cluster_id)

    return cluster_size >= CLUSTER_SATURATION_LIMIT
