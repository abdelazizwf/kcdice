import random
from enum import Enum, auto
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
)

from kcdice import scoring
from kcdice.bot import Banked, Busted, Kept, Rolled, ThresholdStrategy, play_bot_turn
from kcdice.game import DEFAULT_TARGET, Game
from kcdice.player import InvalidSelection, Player

NUM_DICE = 6
ROLL_ANIMATION_TICKS = 5
MIN_TIMER_DELAY = 0.01  # Textual timers can't have a zero interval

FACES = {
    1: ("       ", "   ●   ", "       "),
    2: (" ●     ", "       ", "     ● "),
    3: (" ●     ", "   ●   ", "     ● "),
    4: (" ●   ● ", "       ", " ●   ● "),
    5: (" ●   ● ", "   ●   ", " ●   ● "),
    6: (" ●   ● ", " ●   ● ", " ●   ● "),
}

RULES = """\
Roll your dice and keep at least one scoring die or combination.
Then bank your turn score, or roll the rest. A roll with nothing to
score is a bust and loses the turn score. Score all six dice and you
get hot dice: roll all six again.

  Single 1 / single 5        100 / 50
  Three of a kind            1s: 1000, otherwise 100 x the number
  Each extra matching die    doubles the score
  Straight 1-5 / 2-6         500 / 750
  Full straight 1-6          1500

Keys: left/right move, space toggles, 1-6 toggle a die, a auto-select,
enter keeps, r rolls again, b banks, q quits.\
"""


class Phase(Enum):
    ROLLING = auto()
    BOT = auto()
    SELECTING = auto()
    KEPT = auto()
    BUST = auto()
    OVER = auto()


class DieWidget(Static):
    class Pressed(Message):
        def __init__(self, index: int):
            super().__init__()
            self.index = index

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.set_value(1)

    def set_value(self, value: int):
        self.value = value
        top, middle, bottom = FACES[value]
        self.update(Text(f"{top}\n{middle}\n{bottom}\n[{self.index + 1}]"))

    def on_click(self):
        self.post_message(self.Pressed(self.index))


class SetupScreen(ModalScreen[tuple[list[str], int, int]]):
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Label("kcdice", id="setup-title")
            yield Label("Player names (comma separated)")
            yield Input("Player 1", id="names")
            yield Label("Computer players")
            yield Input("0", id="bots", type="integer")
            yield Label("Score to win")
            yield Input(str(DEFAULT_TARGET), id="target", type="integer")
            yield Label("", id="setup-error")
            with Horizontal():
                yield Button("Start", variant="primary", id="start")
                yield Button("Quit", id="quit")

    @on(Input.Submitted)
    @on(Button.Pressed, "#start")
    def start(self):
        names = [n.strip() for n in self.query_one("#names", Input).value.split(",")]
        names = [n for n in names if n]
        bots = self.query_one("#bots", Input).value or "0"
        target = self.query_one("#target", Input).value
        error = self.query_one("#setup-error", Label)
        if not bots.isdigit():
            error.update("Computer players must be a number.")
        elif not names and int(bots) == 0:
            error.update("Enter a player name or add a computer player.")
        elif not target.isdigit() or int(target) <= 0:
            error.update("Enter a positive score.")
        else:
            self.dismiss((names, int(bots), int(target)))

    @on(Button.Pressed, "#quit")
    def quit(self):
        self.app.exit()


class WinScreen(ModalScreen[bool]):
    def __init__(self, game: Game):
        super().__init__()
        self.game = game

    def compose(self) -> ComposeResult:
        winner = self.game.winner
        with Vertical(classes="dialog"):
            yield Label(f"{winner.name} wins with {winner.current_score} points!")
            for player in self.game.players:
                yield Label(f"{player.name}: {player.current_score}")
            with Horizontal():
                yield Button("New game", variant="primary", id="new")
                yield Button("Quit", id="quit")

    @on(Button.Pressed)
    def pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "new")


class HelpScreen(ModalScreen[None]):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape,q,question_mark,enter", "dismiss", "Close")
    ]

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog"):
            yield Static(RULES)
            yield Label("Press escape to close.")


class KCDiceApp(App):
    CSS_PATH = "kcdice.tcss"
    TITLE = "kcdice"
    HORIZONTAL_BREAKPOINTS: ClassVar[list[tuple[int, str]]] = [
        (0, "-narrow"),
        (100, "-wide"),
    ]
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("left,h", "move(-1)", "Left", show=False),
        Binding("right,l", "move(1)", "Right", show=False),
        Binding("space", "toggle", "Toggle die"),
        Binding("enter", "primary", "Keep / Continue / Skip"),
        Binding("a", "auto", "Auto-select"),
        Binding("r", "roll", "Roll again"),
        Binding("b", "bank", "Bank"),
        Binding("question_mark", "help", "Help"),
        Binding("q", "quit", "Quit"),
        *[Binding(str(n), f"toggle_die({n})", show=False) for n in range(1, 7)],
    ]

    def __init__(
        self,
        game: Game | None = None,
        seed: int | None = None,
        animate: bool = True,
        bot_delay: float = 0.8,
    ):
        super().__init__()
        self.game = game
        self.seed = seed
        self.animate = animate
        self.bot_delay = bot_delay
        self.bot_fast = False
        self.bot_bust = False
        self.bot_events = None
        self.last_event = None
        self.phase = Phase.OVER
        self.dice: list[int] = []
        self.selection: set[int] = set()
        self.kept: set[int] = set()
        self.cursor = 0
        self.notice = ""
        self._timer: Timer | None = None
        self._ticks = 0

    # --- layout ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static(id="status")
                with Horizontal(id="dice"):
                    for i in range(NUM_DICE):
                        yield DieWidget(i)
                yield Static(id="preview")
            with Vertical(id="right"):
                # Never focusable: a focused DataTable would swallow enter.
                scores = DataTable(id="scores", cursor_type="none")
                scores.can_focus = False
                yield scores
                log = RichLog(id="log", wrap=True, markup=False)
                log.can_focus = False
                yield log
        yield Footer()

    def on_mount(self):
        table = self.query_one("#scores", DataTable)
        table.add_columns("", "Player", "Score")
        if self.game is None:
            self.push_screen(SetupScreen(), self.setup_done)
        else:
            self.start_game()

    def setup_done(self, result: tuple[list[str], int, int] | None):
        if result is None:
            return
        names, n_bots, target = result
        players = [Player(name) for name in names]
        players += [
            Player(f"Bot {i}", strategy=ThresholdStrategy())
            for i in range(1, n_bots + 1)
        ]
        self.game = Game(players, target, random.Random(self.seed))
        self.start_game()

    # --- game flow --------------------------------------------------------

    @property
    def player(self) -> Player:
        return self.game.current_player

    def log_line(self, message: str):
        self.query_one("#log", RichLog).write(message)

    def start_game(self):
        self.query_one("#log", RichLog).clear()
        self.sub_title = f"first to {self.game.max_score}"
        self.start_turn()

    def start_turn(self):
        self.log_line(f"--- {self.player.name}'s turn ---")
        if self.player.is_bot:
            self.start_bot_turn()
        else:
            self.bot_fast = False
            self.roll_dice()

    def start_bot_turn(self):
        self.selection = set()
        self.kept = set()
        self.bot_bust = False
        self.notice = ""
        self.last_event = None
        self.bot_events = play_bot_turn(self.game)
        self.phase = Phase.BOT
        self.refresh_view()
        self.set_timer(max(self.bot_delay, MIN_TIMER_DELAY), self.bot_step)

    def bot_step(self):
        if self.phase is not Phase.BOT:
            return
        try:
            event = next(self.bot_events)
        except StopIteration:
            self.end_bot_turn()
            return
        self.last_event = event
        match event:
            case Rolled(dice):
                self.dice = dice
                self.selection = set()
                self.bot_bust = False
                self.log_line(f"Rolled {dice}")
            case Kept(dice, positions, score, hot_dice):
                self.selection = {p - 1 for p in positions}
                kept_dice = [dice[p - 1] for p in positions]
                self.log_line(
                    f"Kept {kept_dice}: {scoring.describe(kept_dice)} (+{score})"
                )
                if hot_dice:
                    self.log_line("Hot dice!")
            case Busted(dice, lost):
                self.dice = dice
                self.selection = set()
                self.bot_bust = True
                self.log_line(f"Rolled {dice}: bust! Lost {lost} points.")
            case Banked(points):
                self.log_line(f"{self.player.name} banks {points} points.")
        self.refresh_view()
        delay = 0 if self.bot_fast else self.bot_delay
        self.set_timer(max(delay, MIN_TIMER_DELAY), self.bot_step)

    def end_bot_turn(self):
        if isinstance(self.last_event, Banked) and self.game.winner is not None:
            self.phase = Phase.OVER
            self.refresh_view()
            self.push_screen(WinScreen(self.game), self.win_done)
            return
        self.game.next_turn()
        self.start_turn()

    def roll_dice(self):
        self.selection = set()
        self.kept = set()
        self.cursor = 0
        self.notice = ""
        if self.animate:
            self.phase = Phase.ROLLING
            self._ticks = 0
            self._timer = self.set_interval(0.07, self._animate_tick)
            self._animate_tick()
        else:
            self.finish_roll()

    def _animate_tick(self):
        self._ticks += 1
        if self._ticks > ROLL_ANIMATION_TICKS:
            self._timer.stop()
            self.finish_roll()
            return
        self.dice = [random.randint(1, 6) for _ in range(self.player.available_dice)]
        self.refresh_view()

    def finish_roll(self):
        self.dice = self.game.roll()
        if scoring.is_bust(self.dice):
            lost = self.player.temp_score
            self.log_line(f"Rolled {self.dice}: bust! Lost {lost} points.")
            self.player.bust()
            self.phase = Phase.BUST
        else:
            self.log_line(f"Rolled {self.dice}")
            self.phase = Phase.SELECTING
        self.refresh_view()

    def keep_selection(self):
        if not self.selection:
            self.notice = "Select at least one die first."
            self.refresh_view()
            return
        positions = sorted(i + 1 for i in self.selection)
        try:
            result = self.player.apply_selection(self.dice, positions)
        except InvalidSelection as error:
            self.notice = str(error)
            self.refresh_view()
            return
        kept_dice = [self.dice[p - 1] for p in positions]
        self.log_line(
            f"Kept {kept_dice}: {scoring.describe(kept_dice)} (+{result.score})"
        )
        if result.hot_dice:
            self.log_line("Hot dice! You roll all your dice again.")
        self.kept = set(self.selection)
        self.selection = set()
        self.notice = ""
        self.phase = Phase.KEPT
        self.refresh_view()

    def bank_score(self):
        points = self.player.temp_score
        self.player.bank()
        self.log_line(f"{self.player.name} banks {points} points.")
        if self.game.winner is not None:
            self.phase = Phase.OVER
            self.refresh_view()
            self.push_screen(WinScreen(self.game), self.win_done)
            return
        self.game.next_turn()
        self.start_turn()

    def win_done(self, new_game: bool | None):
        if new_game:
            players = [Player(p.name, p.n_dice, p.strategy) for p in self.game.players]
            self.game = Game(players, self.game.max_score, self.game.rng)
            self.start_game()
        else:
            self.exit()

    # --- actions ----------------------------------------------------------

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool:
        if isinstance(self.screen, ModalScreen):
            return action in ("quit",) and not isinstance(self.screen, SetupScreen)
        if action in ("quit", "help"):
            return True
        if self.game is None:
            return False
        selecting = self.phase is Phase.SELECTING
        return {
            "move": self.phase in (Phase.SELECTING, Phase.KEPT, Phase.BUST),
            "toggle": selecting,
            "toggle_die": selecting,
            "auto": selecting,
            "primary": selecting or self.phase in (Phase.BUST, Phase.BOT),
            "roll": self.phase is Phase.KEPT,
            "bank": self.phase is Phase.KEPT,
        }.get(action, True)

    def action_move(self, delta: int):
        if self.dice:
            self.cursor = (self.cursor + delta) % len(self.dice)
            self.refresh_view()

    def toggle(self, index: int):
        self.notice = ""
        self.selection ^= {index}
        self.cursor = index
        self.refresh_view()

    def action_toggle(self):
        self.toggle(self.cursor)

    def action_toggle_die(self, number: int):
        if number <= len(self.dice):
            self.toggle(number - 1)

    def action_auto(self):
        self.notice = ""
        self.selection = {p - 1 for p in scoring.best_selection(self.dice)}
        self.refresh_view()

    def action_primary(self):
        if self.phase is Phase.SELECTING:
            self.keep_selection()
        elif self.phase is Phase.BUST:
            self.game.next_turn()
            self.start_turn()
        elif self.phase is Phase.BOT:
            self.bot_fast = True

    def action_roll(self):
        self.roll_dice()

    def action_bank(self):
        self.bank_score()

    def action_help(self):
        self.push_screen(HelpScreen())

    @on(DieWidget.Pressed)
    def die_pressed(self, event: DieWidget.Pressed):
        if self.phase is Phase.SELECTING and event.index < len(self.dice):
            self.toggle(event.index)

    # --- rendering --------------------------------------------------------

    def refresh_view(self):
        self.refresh_bindings()
        if self.game is None:
            return
        player = self.player
        self.query_one("#status", Static).update(
            Text(
                f"{player.name}   banked {player.current_score}"
                f" / {self.game.max_score}   turn score {player.temp_score}"
                f"   dice left {player.available_dice}"
            )
        )
        self.query_one("#preview", Static).update(self.preview_text())
        self.refresh_dice()
        self.refresh_scoreboard()

    def refresh_dice(self):
        hints = (
            scoring.scoring_positions(self.dice)
            if self.phase is Phase.SELECTING
            else set()
        )
        for i, widget in enumerate(self.query(DieWidget)):
            widget.display = i < len(self.dice)
            if i >= len(self.dice):
                continue
            if widget.value != self.dice[i]:
                widget.set_value(self.dice[i])
            selecting = self.phase is Phase.SELECTING
            shown = (
                self.selection
                if self.phase in (Phase.SELECTING, Phase.BOT)
                else self.kept
            )
            widget.set_class(i in shown, "selected")
            widget.set_class(selecting and (i + 1) in hints, "scoreable")
            widget.set_class(selecting and i == self.cursor, "cursor")
            widget.set_class(self.phase is Phase.KEPT, "dimmed")
            widget.set_class(self.phase is Phase.BUST or self.bot_bust, "bust")

    def refresh_scoreboard(self):
        table = self.query_one("#scores", DataTable)
        table.clear()
        for p in self.game.players:
            marker = "▶" if p is self.player else ""
            table.add_row(marker, p.name, p.current_score)

    def preview_text(self) -> Text:
        if self.notice:
            return Text(self.notice, style="bold red")
        match self.phase:
            case Phase.SELECTING if self.selection:
                chosen = [self.dice[i] for i in sorted(self.selection)]
                points = scoring.score(chosen)
                if points:
                    return Text(
                        f"{scoring.describe(chosen)}: +{points}", style="bold green"
                    )
                return Text("Not a scoring selection", style="bold red")
            case Phase.SELECTING:
                return Text(
                    "Pick scoring dice (green borders). space/click toggles, a auto-selects."
                )
            case Phase.KEPT:
                return Text(
                    f"r: roll again   b: bank {self.player.temp_score} points",
                    style="bold",
                )
            case Phase.BUST:
                return Text("Bust! Press enter to pass the turn.", style="bold red")
            case Phase.ROLLING:
                return Text("Rolling...")
            case Phase.BOT:
                return Text(f"{self.player.name} is playing... (enter to speed up)")
        return Text("")
