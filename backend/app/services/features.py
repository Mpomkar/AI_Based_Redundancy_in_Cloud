from dataclasses import dataclass


@dataclass
class FeatureVector:
    max_similarity: float
    size_ratio: float
    neighbor_frequency: float


def build_features(
    max_similarity: float,
    new_size: int,
    best_match_size: int | None,
    similar_count: int,
) -> FeatureVector:
    if best_match_size and best_match_size > 0 and new_size >= 0:
        s1, s2 = sorted([new_size, best_match_size])
        size_ratio = s1 / s2 if s2 else 0.0
    else:
        size_ratio = 0.0
    size_ratio = max(0.0, min(1.0, size_ratio))
    freq = min(1.0, similar_count / 5.0)
    return FeatureVector(
        max_similarity=max(0.0, min(1.0, max_similarity)),
        size_ratio=size_ratio,
        neighbor_frequency=freq,
    )


def to_matrix(f: FeatureVector) -> list[list[float]]:
    return [[f.max_similarity, f.size_ratio, f.neighbor_frequency]]
