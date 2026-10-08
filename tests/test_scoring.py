import pytest

from kcdice.scoring import is_bust, score


@pytest.mark.parametrize(
    ("dice", "expected"),
    [
        ([1], 100),
        ([5], 50),
        ([1, 5], 150),
        ([1, 1], 200),
        ([1, 2, 3, 4, 5], 500),
        ([2, 3, 4, 5, 6], 750),
        ([1, 2, 3, 4, 5, 6], 1500),
        ([6, 1, 3, 5, 2, 4], 1500),
        ([1, 1, 1], 1000),
        ([2, 2, 2], 200),
        ([3, 3, 3], 300),
        ([4, 4, 4], 400),
        ([5, 5, 5], 500),
        ([6, 6, 6], 600),
        ([2, 2, 2, 2], 400),
        ([2, 2, 2, 2, 2], 800),
        ([2, 2, 2, 2, 2, 2], 1600),
        ([1, 1, 1, 1], 2000),
        ([2, 2, 2, 1], 300),
        ([5, 5, 5, 1, 1], 700),
        ([1, 2, 3, 4, 5, 1], 600),
        ([2, 3, 4, 5, 6, 5], 800),
    ],
)
def test_score(dice, expected):
    assert score(dice) == expected


@pytest.mark.parametrize(
    "dice",
    [[], [2], [2, 3], [2, 2], [2, 2, 3], [1, 2], [2, 2, 2, 3], [1, 2, 3, 4]],
)
def test_score_is_zero_when_a_die_does_not_contribute(dice):
    assert score(dice) == 0


def test_score_does_not_mutate_input():
    dice = [5, 1, 3, 2, 4]
    score(dice)
    assert dice == [5, 1, 3, 2, 4]


@pytest.mark.parametrize(
    "dice",
    [[1], [5], [2, 3, 1], [2, 2, 2], [3, 3, 3, 4], [6, 6, 6, 6, 2, 3]],
)
def test_not_bust(dice):
    assert not is_bust(dice)


@pytest.mark.parametrize(
    "dice",
    [[2], [2, 3, 4, 6], [2, 2, 3, 3, 4, 4], [2, 2, 6, 6]],
)
def test_bust(dice):
    assert is_bust(dice)
