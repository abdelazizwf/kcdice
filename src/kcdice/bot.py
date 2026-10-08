from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from kcdice import scoring
from kcdice.game import Game
from kcdice.player import Player


class Strategy(Protocol):
    def choose(self, dice: list[int], player: Player, game: Game) -> list[int]:
        """1-based positions of the dice to keep from a scoring roll."""
        ...

    def should_bank(self, player: Player, game: Game) -> bool:
        """Whether to bank the turn score rather than roll the remaining dice."""
        ...


class ThresholdStrategy:
    """Keep the best-scoring dice and bank once the turn score is high enough."""

    def __init__(self, threshold: int = 400, min_dice: int = 3):
        self.threshold = threshold
        self.min_dice = min_dice

    def choose(self, dice: list[int], player: Player, game: Game) -> list[int]:
        return scoring.best_selection(dice)

    def should_bank(self, player: Player, game: Game) -> bool:
        if player.current_score + player.temp_score >= game.max_score:
            return True
        # With few dice left a bust is likely, so take the points.
        if player.available_dice < self.min_dice:
            return True
        return player.temp_score >= self.adjusted_threshold(player, game)

    def adjusted_threshold(self, player: Player, game: Game) -> int:
        """Gamble more when behind and play safer when ahead."""
        others = [p.current_score for p in game.players if p is not player]
        if not others:
            return self.threshold
        lead = player.current_score - max(others)
        if lead <= -1000:
            return self.threshold * 3 // 2
        if lead >= 1000:
            return self.threshold * 3 // 4
        return self.threshold


@dataclass
class Rolled:
    dice: list[int]


@dataclass
class Kept:
    dice: list[int]
    positions: list[int]
    score: int
    hot_dice: bool


@dataclass
class Busted:
    dice: list[int]
    lost: int


@dataclass
class Banked:
    points: int


Event = Rolled | Kept | Busted | Banked


def play_bot_turn(game: Game) -> Iterator[Event]:
    """Play the current player's turn, yielding each step as it happens.

    The player's state is already updated when an event is yielded. The
    caller advances the turn and checks for a winner afterwards.
    """
    player = game.current_player
    strategy = player.strategy
    while True:
        dice = game.roll()
        if scoring.is_bust(dice):
            lost = player.temp_score
            player.bust()
            yield Busted(dice, lost)
            return
        yield Rolled(dice)
        positions = strategy.choose(dice, player, game)
        result = player.apply_selection(dice, positions)
        yield Kept(dice, positions, result.score, result.hot_dice)
        if strategy.should_bank(player, game):
            points = player.temp_score
            player.bank()
            yield Banked(points)
            return
