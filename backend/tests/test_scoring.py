"""Unit tests for scoring logic (pure functions, no DB)."""

from app.services.scoring_service import (
    BASE_POINTS,
    CONSENSUS_BONUS,
    MAX_DISTANCE_BONUS,
    compute_score,
    distance_bonus,
)


def test_distance_bonus_tiers() -> None:
    assert distance_bonus(0) == 5
    assert distance_bonus(50) == 5
    assert distance_bonus(51) == 4
    assert distance_bonus(100) == 4
    assert distance_bonus(200) == 3
    assert distance_bonus(350) == 2
    assert distance_bonus(351) == 1
    assert distance_bonus(10_000) == 1


def test_compute_score_is_base_plus_distance_bonus() -> None:
    assert compute_score(0) == BASE_POINTS + 5
    assert compute_score(500) == BASE_POINTS + 1


def test_score_ranges_do_not_overlap() -> None:
    # retroactive_score_update decodes the consensus bonus from the score
    # magnitude; that only works while these ranges stay disjoint.
    max_without_consensus = BASE_POINTS + MAX_DISTANCE_BONUS
    min_with_consensus = BASE_POINTS + 1 + CONSENSUS_BONUS
    assert min_with_consensus > max_without_consensus
