"""
Similarity graph construction for semantic reduction pipeline.

Builds pairwise similarity matrices from WitnessSenseUnit lists
using lemmatized token-based similarity functions.
"""

import numpy as np
from langnet.semantic_reducer.normalizer import get_similarity_function, lemmatize_gloss
from langnet.semantic_reducer.types import WitnessSenseUnit


def build_similarity_matrix(
    wsus: list[WitnessSenseUnit],
    similarity_func: str = "jaccard",
) -> np.ndarray:
    """
    Build pairwise similarity matrix from WSU list.

    Args:
        wsus: List of WitnessSenseUnit objects
        similarity_func: Name of similarity function ("jaccard", "dice", "cosine")

    Returns:
        NxN numpy array where matrix[i][j] = similarity(wsus[i], wsus[j])
    """
    sim_fn = get_similarity_function(similarity_func)
    n = len(wsus)
    matrix = np.eye(n, dtype=np.float64)

    token_sets = [lemmatize_gloss(wsu.gloss_normalized) for wsu in wsus]

    for i in range(n):
        for j in range(i + 1, n):
            sim = sim_fn(token_sets[i], token_sets[j])
            matrix[i, j] = sim
            matrix[j, i] = sim

    return matrix


def get_similar_pairs(
    matrix: np.ndarray,
    threshold: float,
) -> list[tuple[int, int, float]]:
    """
    Get all pairs with similarity >= threshold.

    Args:
        matrix: Similarity matrix from build_similarity_matrix
        threshold: Minimum similarity score

    Returns:
        List of (i, j, similarity) tuples sorted by similarity desc
    """
    n = matrix.shape[0]
    pairs: list[tuple[int, int, float]] = []

    i_indices, j_indices = np.triu_indices(n, k=1)
    mask = matrix[i_indices, j_indices] >= threshold

    for i, j, sim in zip(
        i_indices[mask], j_indices[mask], matrix[i_indices[mask], j_indices[mask]]
    ):
        pairs.append((int(i), int(j), float(sim)))

    pairs.sort(key=lambda p: (-p[2], p[0], p[1]))
    return pairs


def get_neighbors(
    matrix: np.ndarray,
    index: int,
    threshold: float,
) -> list[tuple[int, float]]:
    """
    Get all neighbors of a WSU with similarity >= threshold.

    Args:
        matrix: Similarity matrix
        index: Index of the WSU
        threshold: Minimum similarity score

    Returns:
        List of (neighbor_index, similarity) tuples sorted by similarity desc
    """
    row = matrix[index]
    mask = (row >= threshold) & (np.arange(len(row)) != index)
    indices = np.where(mask)[0]

    neighbors = [(int(i), float(row[i])) for i in indices]
    neighbors.sort(key=lambda p: (-p[1], p[0]))
    return neighbors
