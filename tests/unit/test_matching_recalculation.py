from app.services.matching_recalculation import MatchingRecalculationService


def test_score_distribution_uses_expected_ranges() -> None:
    distribution = MatchingRecalculationService._distribution([100, 90, 89, 80, 79, 70, 69, 0])

    assert distribution.excellent == 2
    assert distribution.strong == 2
    assert distribution.possible == 2
    assert distribution.low == 2
    assert distribution.total == 8
