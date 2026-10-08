import random

from kcdice.player import Player

DEFAULT_TARGET = 4000


class Game:
    def __init__(
        self,
        players: list[Player],
        max_score: int = DEFAULT_TARGET,
        rng: random.Random | None = None,
    ):
        self.players = players
        self.max_score = max_score
        self.rng = rng or random.Random()
        self._turn = 0

    @property
    def current_player(self) -> Player:
        return self.players[self._turn % len(self.players)]

    @property
    def winner(self) -> Player | None:
        """The player who has reached the target score, if any."""
        for player in self.players:
            if player.current_score >= self.max_score:
                return player
        return None

    def roll(self) -> list[int]:
        return self.current_player.roll(self.rng)

    def next_turn(self):
        self._turn += 1
