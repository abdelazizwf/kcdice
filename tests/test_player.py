import random

import pytest

from kcdice.player import InvalidSelection, Player


def test_roll_returns_available_dice():
    player = Player()
    dice = player.roll(random.Random(0))
    assert len(dice) == 6
    assert all(1 <= d <= 6 for d in dice)

    player.available_dice = 2
    assert len(player.roll(random.Random(0))) == 2


def test_roll_is_reproducible_with_seed():
    assert Player().roll(random.Random(7)) == Player().roll(random.Random(7))


def test_apply_selection_updates_state():
    player = Player()
    result = player.apply_selection([1, 2, 5, 3, 4, 6], [1, 3])
    assert result.score == 150
    assert not result.hot_dice
    assert player.temp_score == 150
    assert player.available_dice == 4


def test_temp_score_accumulates():
    player = Player()
    player.apply_selection([1, 2, 3, 4, 6, 6], [1])
    player.apply_selection([5, 2, 3, 4, 6], [1])
    assert player.temp_score == 150
    assert player.available_dice == 4


def test_hot_dice_resets_available_dice_and_keeps_score():
    player = Player()
    result = player.apply_selection([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6])
    assert result.hot_dice
    assert result.score == 1500
    assert player.temp_score == 1500
    assert player.available_dice == 6


@pytest.mark.parametrize(
    ("positions", "message"),
    [
        ([], "at least one"),
        ([0], "between 1 and 3"),
        ([4], "between 1 and 3"),
        ([-1], "between 1 and 3"),
        ([1, 1], "only be selected once"),
        ([2], "Invalid selection"),
        ([1, 2], "Invalid selection"),
    ],
)
def test_invalid_selection_raises_and_leaves_state_untouched(positions, message):
    player = Player()
    with pytest.raises(InvalidSelection, match=message):
        player.apply_selection([1, 2, 3], positions)
    assert player.temp_score == 0
    assert player.available_dice == 6


def test_bank_adds_temp_score_and_resets():
    player = Player()
    player.apply_selection([1, 2, 3], [1])
    player.bank()
    assert player.current_score == 100
    assert player.temp_score == 0
    assert player.available_dice == 6


def test_bust_discards_temp_score_and_resets():
    player = Player()
    player.current_score = 300
    player.apply_selection([1, 2, 3], [1])
    player.bust()
    assert player.current_score == 300
    assert player.temp_score == 0
    assert player.available_dice == 6
