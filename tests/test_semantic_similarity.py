from langnet.reduction import (
    SimilarityMode,
    WitnessSenseUnit,
    build_similarity_matrix,
    cluster_similar_witnesses,
    dice_similarity,
    get_similar_pairs,
    jaccard_similarity,
    sort_witnesses_by_priority,
    tokenize_similarity_text,
)

OPEN_CLUSTER_COUNT = 2
SKEPTIC_CLUSTER_COUNT = 3


def _wsu(
    gloss: str,
    source: str,
    ref: str,
) -> WitnessSenseUnit:
    normalized = " ".join(gloss.lower().split())
    return WitnessSenseUnit(
        wsu_id=f"wsu:{source}:{ref}",
        lexeme_anchor="lex:agni",
        sense_anchor=f"sense:{source}:{ref}",
        gloss=gloss,
        normalized_gloss=normalized,
        source_tool=source,
        claim_id=f"claim:{source}",
        source_triple_subject="lex:agni",
        evidence={"source_tool": source, "source_ref": ref},
    )


def test_similarity_tokenization_is_deterministic_and_conservative() -> None:
    assert tokenize_similarity_text("A sacrificial fire, in the ritual.") == (
        "sacrificial",
        "fire",
        "ritual",
    )


def test_similarity_scores_cover_overlap_without_embeddings() -> None:
    fire_flame = tokenize_similarity_text("fire flame")
    fire_blaze = tokenize_similarity_text("fire blaze")
    water = tokenize_similarity_text("water")

    assert jaccard_similarity(fire_flame, fire_flame) == 1.0
    assert 0.0 < jaccard_similarity(fire_flame, fire_blaze) < 1.0
    assert dice_similarity(fire_flame, fire_blaze) > jaccard_similarity(fire_flame, fire_blaze)
    assert jaccard_similarity(fire_flame, water) == 0.0


def test_similarity_matrix_and_pairs_are_stable() -> None:
    witnesses = [
        _wsu("fire flame", "cdsl", "mw:1"),
        _wsu("fire blaze", "dico", "dico:1"),
        _wsu("water", "cdsl", "mw:2"),
    ]

    matrix = build_similarity_matrix(witnesses)
    assert matrix[0][0] == 1.0
    assert matrix[0][1] == matrix[1][0]
    assert matrix[0][2] == 0.0

    pairs = get_similar_pairs(matrix, threshold=0.25)
    assert [(pair.left, pair.right) for pair in pairs] == [(0, 1)]


def test_similarity_clustering_is_opt_in_and_preserves_witness_uniqueness() -> None:
    witnesses = [
        _wsu("fire flame", "cdsl", "mw:1"),
        _wsu("fire blaze", "dico", "dico:1"),
        _wsu("water", "cdsl", "mw:2"),
    ]

    open_buckets = cluster_similar_witnesses(
        witnesses,
        language="san",
        mode=SimilarityMode.OPEN,
    )
    skeptic_buckets = cluster_similar_witnesses(
        witnesses,
        language="san",
        mode=SimilarityMode.SKEPTIC,
    )

    assert len(open_buckets) == OPEN_CLUSTER_COUNT
    assert len(skeptic_buckets) == SKEPTIC_CLUSTER_COUNT
    assert len({w.wsu_id for bucket in open_buckets for w in bucket.witnesses}) == len(witnesses)
    assert all(bucket.bucket_id.startswith("bucket:sim:") for bucket in open_buckets)


def test_similarity_clustering_uses_transitive_components() -> None:
    witnesses = [
        _wsu("bright flame", "cdsl", "mw:1"),
        _wsu("flame smoke", "dico", "dico:1"),
        _wsu("smoke ritual", "cdsl", "mw:2"),
    ]

    buckets = cluster_similar_witnesses(
        witnesses,
        language="san",
        mode=SimilarityMode.OPEN,
    )

    assert len(buckets) == 1
    assert [w.source_tool for w in buckets[0].witnesses] == ["dico", "cdsl", "cdsl"]


def test_similarity_clustering_uses_source_priority_for_bucket_display() -> None:
    witnesses = [
        _wsu("fire", "cltk", "cltk:1"),
        _wsu("fire", "dico", "dico:1"),
        _wsu("fire", "cdsl", "mw:1"),
    ]

    ordered = sort_witnesses_by_priority(witnesses)
    assert [w.source_tool for w in ordered] == ["dico", "cdsl", "cltk"]

    buckets = cluster_similar_witnesses(witnesses, language="san", mode=SimilarityMode.SKEPTIC)
    assert len(buckets) == 1
    assert buckets[0].witnesses[0].source_tool == "dico"
    assert buckets[0].confidence_label == "similarity-multi-witness"
