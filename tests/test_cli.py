import random

import pytest

from kcdice import cli
from kcdice.game import Game
from kcdice.player import Player


def feed(monkeypatch, *answers):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))


def test_ask_int_uses_default_on_empty(monkeypatch):
    feed(monkeypatch, "")
    assert cli.ask_int("n", 4) == 4


def test_ask_int_reprompts_until_valid(monkeypatch, capsys):
    feed(monkeypatch, "abc", "0", "-2", "7")
    assert cli.ask_int("n", 4) == 7
    assert capsys.readouterr().out.count("positive number") == 3


def test_ask_finish_reprompts_until_valid(monkeypatch):
    feed(monkeypatch, "3", "", "2")
    assert cli.ask_finish() is False
    feed(monkeypatch, "1")
    assert cli.ask_finish() is True


def test_select_dice_reprompts_on_bad_input(monkeypatch, capsys):
    player = Player()
    feed(monkeypatch, "x", "", "9", "1 1", "2", "1")
    result = cli.select_dice(player, [1, 2, 3])
    assert result.score == 100
    out = capsys.readouterr().out
    assert "numbers separated by spaces" in out
    assert "at least one" in out
    assert "between 1 and 3" in out
    assert "only be selected once" in out
    assert "Invalid selection" in out


def test_play_turn_busts_without_prompting(monkeypatch, capsys):
    player = Player()
    game = Game([player], rng=random.Random(0))
    monkeypatch.setattr(game, "roll", lambda: [2, 3, 4, 6, 2, 3])
    player.temp_score = 500
    cli.play_turn(game)
    assert player.temp_score == 0
    assert player.current_score == 0
    assert "Bust!" in capsys.readouterr().out


def test_play_turn_banks_score(monkeypatch):
    player = Player()
    game = Game([player])
    monkeypatch.setattr(game, "roll", lambda: [1, 2, 3, 4, 6, 6])
    feed(monkeypatch, "1", "1")
    cli.play_turn(game)
    assert player.current_score == 100


def test_play_turn_roll_again_then_bank(monkeypatch):
    player = Player()
    game = Game([player])
    rolls = iter([[1, 2, 3, 4, 6], [5, 2, 3, 4, 6]])
    monkeypatch.setattr(game, "roll", lambda: next(rolls))
    feed(monkeypatch, "1", "2", "1", "1")
    cli.play_turn(game)
    assert player.current_score == 150


def test_run_ends_immediately_on_win(monkeypatch, capsys):
    p1, p2 = Player("A"), Player("B")
    game = Game([p1, p2], max_score=100)
    monkeypatch.setattr(game, "roll", lambda: [1, 2, 3, 4, 6, 6])
    feed(monkeypatch, "1", "1")
    cli.run(game)
    assert p1.current_score == 100
    assert p2.current_score == 0
    assert "A wins with 100 points!" in capsys.readouterr().out


def test_main_with_flags(monkeypatch, capsys):
    monkeypatch.setattr(
        random.Random, "randint", lambda self, a, b: 1
    )  # every die is a 1
    feed(monkeypatch, "1", "1")
    cli.main(["-p", "2", "-t", "100", "--seed", "1"])
    assert "Player 1 wins" in capsys.readouterr().out


def test_main_aborts_cleanly_on_eof(monkeypatch, capsys):
    def raise_eof(_prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    cli.main([])
    assert "Game aborted." in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["-p", "-t", "--seed"])
def test_parse_args_rejects_non_integers(flag):
    with pytest.raises(SystemExit):
        cli.parse_args([flag, "abc"])
