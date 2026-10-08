import random

from kcdice.game import DEFAULT_TARGET, Game
from kcdice.player import Player


def make_game(n=2, **kwargs):
    return Game([Player(f"P{i}") for i in range(n)], **kwargs)


def test_default_target():
    assert make_game().max_score == DEFAULT_TARGET == 4000


def test_turn_order_cycles():
    game = make_game(3)
    names = []
    for _ in range(4):
        names.append(game.current_player.name)
        game.next_turn()
    assert names == ["P0", "P1", "P2", "P0"]


def test_no_winner_below_target():
    game = make_game(max_score=1000)
    game.players[0].current_score = 999
    assert game.winner is None


def test_winner_at_or_above_target():
    game = make_game(max_score=1000)
    game.players[1].current_score = 1000
    assert game.winner is game.players[1]


def test_roll_uses_current_player_dice_and_seeded_rng():
    game = make_game(rng=random.Random(3))
    game.current_player.available_dice = 4
    dice = game.roll()
    assert len(dice) == 4
    expected = make_game(rng=random.Random(3)).players[0]
    expected.available_dice = 4
    assert dice == expected.roll(random.Random(3))
