import random

from kcdice.bot import (
    Banked,
    Busted,
    Kept,
    Rolled,
    ThresholdStrategy,
    play_bot_turn,
)
from kcdice.game import Game
from kcdice.player import Player


def make_game(rolls, strategy=None, n_players=1, max_score=4000):
    players = [
        Player("Bot", strategy=strategy or ThresholdStrategy()),
        *[Player(f"P{i}") for i in range(n_players - 1)],
    ]
    game = Game(players, max_score)
    queue = iter(rolls)
    game.roll = lambda: next(queue)
    return game


def test_player_is_bot_only_with_a_strategy():
    assert not Player().is_bot
    assert Player(strategy=ThresholdStrategy()).is_bot


def test_choose_keeps_the_best_selection():
    game = make_game([])
    assert game.players[0].strategy.choose(
        [2, 2, 2, 5, 3, 4], game.players[0], game
    ) == [
        1,
        2,
        3,
        4,
    ]


def test_bank_when_it_would_win():
    game = make_game([], max_score=500)
    player = game.players[0]
    player.current_score, player.temp_score, player.available_dice = 300, 200, 5
    assert player.strategy.should_bank(player, game)


def test_bank_when_few_dice_remain():
    game = make_game([])
    player = game.players[0]
    player.temp_score, player.available_dice = 100, 2
    assert player.strategy.should_bank(player, game)


def test_roll_again_below_threshold_with_enough_dice():
    game = make_game([])
    player = game.players[0]
    player.temp_score, player.available_dice = 350, 4
    assert not player.strategy.should_bank(player, game)
    player.temp_score = 400
    assert player.strategy.should_bank(player, game)


def test_threshold_adapts_to_the_score_difference():
    strategy = ThresholdStrategy(threshold=400)
    game = make_game([], strategy=strategy, n_players=2)
    bot, other = game.players
    assert strategy.adjusted_threshold(bot, game) == 400
    other.current_score = 1500
    assert strategy.adjusted_threshold(bot, game) == 600
    bot.current_score, other.current_score = 2500, 1000
    assert strategy.adjusted_threshold(bot, game) == 300


def test_turn_that_banks():
    game = make_game([[1, 2, 3, 4, 6, 6], [5, 5, 5, 3, 4]])
    events = list(play_bot_turn(game))
    assert events == [
        Rolled([1, 2, 3, 4, 6, 6]),
        Kept([1, 2, 3, 4, 6, 6], [1], 100, False),
        Rolled([5, 5, 5, 3, 4]),
        Kept([5, 5, 5, 3, 4], [1, 2, 3], 500, False),
        Banked(600),
    ]
    assert game.players[0].current_score == 600
    assert game.players[0].temp_score == 0


def test_turn_that_busts_loses_the_turn_score():
    game = make_game([[1, 2, 3, 4, 6, 6], [2, 3, 4, 6, 2]])
    events = list(play_bot_turn(game))
    assert events[-1] == Busted([2, 3, 4, 6, 2], 100)
    assert game.players[0].current_score == 0
    assert game.players[0].temp_score == 0


def test_bot_banks_after_hot_dice():
    game = make_game([[1, 2, 3, 4, 5, 6], [1, 5, 5, 3, 4, 6]])
    events = list(play_bot_turn(game))
    assert events[1] == Kept([1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6], 1500, True)
    assert events[-1] == Banked(1500)
    assert game.players[0].current_score == 1500


def test_events_are_lazy():
    game = make_game([[1, 2, 3, 4, 6, 6]])
    turn = play_bot_turn(game)
    assert game.players[0].temp_score == 0
    assert next(turn) == Rolled([1, 2, 3, 4, 6, 6])
    assert game.players[0].temp_score == 0
    assert isinstance(next(turn), Kept)
    assert game.players[0].temp_score == 100


def test_random_games_always_terminate():
    for seed in range(30):
        game = Game(
            [Player(f"B{i}", strategy=ThresholdStrategy()) for i in range(2)],
            1000,
            random.Random(seed),
        )
        for _ in range(1000):
            list(play_bot_turn(game))
            if game.winner:
                break
            game.next_turn()
        assert game.winner is not None
