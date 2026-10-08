import random
from dataclasses import dataclass

from kcdice import scoring


class InvalidSelection(ValueError):
    """Raised when a dice selection can't be applied."""


@dataclass
class SelectionResult:
    score: int
    hot_dice: bool


class Player:
    def __init__(self, name: str = "Player", n_dice: int = 6):
        self.name = name
        self.n_dice = n_dice
        self.current_score = 0
        self.temp_score = 0
        self.available_dice = n_dice

    def roll(self, rng: random.Random | None = None) -> list[int]:
        rng = rng or random
        return [rng.randint(1, 6) for _ in range(self.available_dice)]

    def apply_selection(self, dice: list[int], positions: list[int]) -> SelectionResult:
        """Keep the dice at the given 1-based positions and add their score."""
        if not positions:
            raise InvalidSelection("Select at least one die.")
        if any(not 1 <= p <= len(dice) for p in positions):
            raise InvalidSelection(f"Positions must be between 1 and {len(dice)}.")
        if len(set(positions)) != len(positions):
            raise InvalidSelection("Each die can only be selected once.")
        score = scoring.score([dice[p - 1] for p in positions])
        if score == 0:
            raise InvalidSelection("Invalid selection.")

        self.available_dice -= len(positions)
        self.temp_score += score
        hot_dice = self.available_dice == 0
        if hot_dice:
            self.available_dice = self.n_dice
        return SelectionResult(score, hot_dice)

    def bank(self):
        self.current_score += self.temp_score
        self.temp_score = 0
        self.available_dice = self.n_dice

    def bust(self):
        self.temp_score = 0
        self.available_dice = self.n_dice
