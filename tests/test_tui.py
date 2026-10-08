import random

from textual.widgets import DataTable, Static

from kcdice.game import Game
from kcdice.player import Player
from kcdice.tui import DieWidget, KCDiceApp, Phase, SetupScreen, WinScreen


def make_app(rolls, n_players=1, target=4000):
    """An app whose rolls come from the given list of dice lists."""
    game = Game([Player(f"P{i}") for i in range(n_players)], target)
    queue = iter(rolls)
    game.roll = lambda: next(queue)
    return KCDiceApp(game, animate=False)


def text(app, selector):
    return str(app.query_one(selector, Static).render())


async def test_scoreable_dice_are_highlighted():
    app = make_app([[2, 5, 1, 3, 1, 6]])
    async with app.run_test():
        dice = list(app.query(DieWidget))
        assert [d.has_class("scoreable") for d in dice] == [
            False, True, True, False, True, False,
        ]  # fmt: skip


async def test_toggle_previews_score_and_keep_applies_it():
    app = make_app([[2, 5, 1, 3, 1, 6]])
    async with app.run_test() as pilot:
        await pilot.press("2", "3")
        assert "+150" in text(app, "#preview")
        await pilot.press("enter")
        assert app.phase is Phase.KEPT
        assert app.player.temp_score == 150
        assert app.player.available_dice == 4


async def test_invalid_selection_shows_notice_and_stays_selecting():
    app = make_app([[2, 5, 1, 3, 1, 6]])
    async with app.run_test() as pilot:
        await pilot.press("1")
        assert "Not a scoring selection" in text(app, "#preview")
        await pilot.press("enter")
        assert app.phase is Phase.SELECTING
        assert "Invalid selection" in text(app, "#preview")


async def test_cursor_and_space_toggle():
    app = make_app([[1, 2, 3, 4, 6, 6]])
    async with app.run_test() as pilot:
        await pilot.press("space", "right", "right", "left")
        assert app.selection == {0}
        assert app.cursor == 1


async def test_auto_select_picks_best_selection():
    app = make_app([[2, 2, 2, 5, 3, 4]])
    async with app.run_test() as pilot:
        await pilot.press("a")
        assert app.selection == {0, 1, 2, 3}
        await pilot.press("enter")
        assert app.player.temp_score == 250


async def test_roll_again_then_bank():
    app = make_app(
        [[1, 2, 3, 4, 6, 6], [5, 2, 3, 4, 6], [1, 2, 3, 4, 6, 6]], n_players=2
    )
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "r")
        assert app.phase is Phase.SELECTING
        await pilot.press("1", "enter", "b")
        assert app.game.players[0].current_score == 150
        assert app.player is app.game.players[1]


async def test_keys_are_ignored_in_the_wrong_phase():
    app = make_app([[1, 2, 3, 4, 6, 6]])
    async with app.run_test() as pilot:
        await pilot.press("b", "r")
        assert app.phase is Phase.SELECTING
        await pilot.press("1", "enter", "enter", "space")
        assert app.phase is Phase.KEPT


async def test_bust_passes_the_turn():
    app = make_app([[2, 3, 4, 6, 2, 3], [1, 2, 3, 4, 6, 6]], n_players=2)
    async with app.run_test() as pilot:
        assert app.phase is Phase.BUST
        assert "Bust" in text(app, "#preview")
        await pilot.press("enter")
        assert app.player is app.game.players[1]
        assert app.phase is Phase.SELECTING


async def test_hot_dice_gives_all_dice_back():
    app = make_app([[1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 6, 6]])
    async with app.run_test() as pilot:
        await pilot.press("a", "enter")
        assert app.player.temp_score == 1500
        assert app.player.available_dice == 6
        await pilot.press("r")
        assert len(app.dice) == 6


async def test_winning_shows_win_screen():
    app = make_app([[1, 2, 3, 4, 6, 6]], target=100)
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "b")
        assert app.phase is Phase.OVER
        assert isinstance(app.screen, WinScreen)


async def test_new_game_after_win_resets_scores():
    app = make_app([[1, 2, 3, 4, 6, 6]], target=100)
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "b")
        app.game.roll = lambda: [1, 2, 3, 4, 6, 6]
        await pilot.click("#new")
        await pilot.pause()
        assert app.player.current_score == 0
        assert app.phase is Phase.SELECTING


async def test_click_toggles_a_die():
    app = make_app([[1, 2, 3, 4, 6, 6]])
    async with app.run_test() as pilot:
        await pilot.click(DieWidget, offset=(2, 2))
        assert app.selection == {0}


async def test_scoreboard_lists_players():
    app = make_app([[1, 2, 3, 4, 6, 6]], n_players=2)
    async with app.run_test():
        assert app.query_one("#scores", DataTable).row_count == 2


async def test_help_screen_blocks_game_keys():
    app = make_app([[1, 2, 3, 4, 6, 6]])
    async with app.run_test() as pilot:
        await pilot.press("question_mark", "1")
        assert app.selection == set()
        await pilot.press("escape")
        await pilot.press("1")
        assert app.selection == {0}


async def test_setup_screen_starts_a_game():
    app = KCDiceApp(None, seed=1, animate=False)
    async with app.run_test() as pilot:
        assert isinstance(app.screen, SetupScreen)
        app.screen.query_one("#names").value = "Ann, Bob"
        app.screen.query_one("#target").value = "500"
        await pilot.click("#start")
        await pilot.pause()
        assert [p.name for p in app.game.players] == ["Ann", "Bob"]
        assert app.game.max_score == 500
        assert app.game.rng is not None


async def test_setup_screen_rejects_bad_target():
    app = KCDiceApp(None, animate=False)
    async with app.run_test() as pilot:
        app.screen.query_one("#target").value = "0"
        await pilot.click("#start")
        assert isinstance(app.screen, SetupScreen)


async def test_roll_animation_settles_on_the_real_roll():
    game = Game([Player("A")], rng=random.Random(5))
    expected = Player("A").roll(random.Random(5))
    app = KCDiceApp(game, animate=True)
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        assert app.dice == expected


async def test_enter_works_even_if_the_scoreboard_is_focused():
    app = make_app([[1, 2, 3, 4, 6, 6]])
    async with app.run_test() as pilot:
        app.query_one("#scores").focus()
        await pilot.press("1", "enter")
        assert app.phase is Phase.KEPT
        assert app.focused is None


def make_bot_app(rolls, target=4000, humans=1):
    from kcdice.bot import ThresholdStrategy

    players = [Player(f"P{i}") for i in range(humans)]
    players.append(Player("Bot", strategy=ThresholdStrategy()))
    game = Game(players, target)
    queue = iter(rolls)
    game.roll = lambda: next(queue)
    return KCDiceApp(game, animate=False, bot_delay=0)


async def settle(pilot, app):
    for _ in range(50):
        await pilot.pause(0.02)
        if app.phase is not Phase.BOT:
            return


async def test_bot_plays_after_the_human_banks():
    rolls = [[1, 2, 3, 4, 6, 6], [5, 5, 5, 3, 4, 6], [1, 5, 5, 3, 4, 6]]
    app = make_bot_app([[1, 2, 3, 4, 6, 6], *rolls[1:]])
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "b")
        await settle(pilot, app)
        bot = app.game.players[1]
        assert bot.current_score == 500
        assert app.player is app.game.players[0]
        assert app.phase is Phase.SELECTING
        assert app.game.players[0].current_score == 100


async def test_bot_bust_returns_control_to_the_human():
    app = make_bot_app([[1, 2, 3, 4, 6, 6], [2, 3, 4, 6, 2, 3], [1, 2, 3, 4, 6, 6]])
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "b")
        await settle(pilot, app)
        assert app.player is app.game.players[0]
        assert app.phase is Phase.SELECTING
        assert app.game.players[1].current_score == 0


async def test_human_keys_are_ignored_during_a_bot_turn():
    app = make_bot_app([[1, 2, 3, 4, 6, 6], [2, 3, 4, 6, 2, 3]])
    app.bot_delay = 30
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "b")
        assert app.phase is Phase.BOT
        await pilot.press("space", "r", "b", "1")
        assert app.phase is Phase.BOT
        assert app.selection == set()


async def test_bot_winning_shows_the_win_screen():
    app = make_bot_app([[1, 2, 3, 4, 6, 6], [1, 1, 1, 3, 4, 6]], target=1000)
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "b")
        await settle(pilot, app)
        assert app.phase is Phase.OVER
        assert isinstance(app.screen, WinScreen)


async def test_new_game_keeps_the_bots():
    app = make_bot_app([[1, 2, 3, 4, 6, 6], [1, 1, 1, 3, 4, 6]], target=1000)
    async with app.run_test() as pilot:
        await pilot.press("1", "enter", "b")
        await settle(pilot, app)
        app.game.roll = lambda: [1, 2, 3, 4, 6, 6]
        await pilot.click("#new")
        await pilot.pause()
        assert [p.is_bot for p in app.game.players] == [False, True]


async def test_setup_screen_adds_computer_players():
    app = KCDiceApp(None, seed=1, animate=False, bot_delay=30)
    async with app.run_test() as pilot:
        app.screen.query_one("#names").value = "Ann"
        app.screen.query_one("#bots").value = "2"
        await pilot.click("#start")
        await pilot.pause()
        assert [p.name for p in app.game.players] == ["Ann", "Bot 1", "Bot 2"]
        assert [p.is_bot for p in app.game.players] == [False, True, True]


async def test_setup_screen_needs_at_least_one_player():
    app = KCDiceApp(None, animate=False)
    async with app.run_test() as pilot:
        app.screen.query_one("#names").value = ""
        await pilot.click("#start")
        assert isinstance(app.screen, SetupScreen)
