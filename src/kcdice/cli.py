import argparse
import random
import sys

from kcdice import scoring
from kcdice.game import DEFAULT_TARGET, Game
from kcdice.player import InvalidSelection, Player


def ask_int(prompt: str, default: int) -> int:
    while True:
        answer = input(f"{prompt} [{default}] >").strip()
        if not answer:
            return default
        if answer.isdigit() and int(answer) > 0:
            return int(answer)
        print("Please enter a positive number.")


def ask_finish() -> bool:
    while True:
        choice = input("Finish turn (1) or play again (2) >").strip()
        if choice in ("1", "2"):
            return choice == "1"
        print("Please enter 1 or 2.")


def select_dice(player: Player, dice: list[int]):
    while True:
        print(dice)
        try:
            positions = [int(s) for s in input("Select Dice >").split()]
            return player.apply_selection(dice, positions)
        except ValueError as e:
            message = (
                e
                if isinstance(e, InvalidSelection)
                else "Enter dice positions as numbers separated by spaces."
            )
            print(f"{message}\n")


def play_turn(game: Game):
    player = game.current_player
    print(f"\n--- {player.name}'s turn ---")
    while True:
        dice = game.roll()
        if scoring.is_bust(dice):
            print(dice)
            print("Bust! You lose your turn score.")
            player.bust()
            print("Current score:", player.current_score)
            return
        result = select_dice(player, dice)
        if result.hot_dice:
            print("Hot dice! You get all your dice back.")
        print("Temp score:", player.temp_score)
        if ask_finish():
            player.bank()
            print("Current score:", player.current_score)
            return


def print_scoreboard(game: Game):
    print("\nScores:")
    for player in game.players:
        print(f"  {player.name}: {player.current_score}")


def run(game: Game):
    while (winner := game.winner) is None:
        play_turn(game)
        print_scoreboard(game)
        if game.winner is None:
            game.next_turn()
    print(f"\n{winner.name} wins with {winner.current_score} points!")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="kcdice", description="A Farkle-style dice game."
    )
    parser.add_argument("-p", "--players", type=int, help="number of players")
    parser.add_argument(
        "-t",
        "--target",
        type=int,
        help=f"score needed to win (default {DEFAULT_TARGET})",
    )
    parser.add_argument("--seed", type=int, help="seed for reproducible rolls")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="use the plain prompt interface instead of the full-screen UI",
    )
    return parser.parse_args(argv)


def run_tui(args: argparse.Namespace):
    from kcdice.tui import KCDiceApp

    game = None
    if args.players or args.target:
        players = [Player(f"Player {i}") for i in range(1, (args.players or 1) + 1)]
        game = Game(players, args.target or DEFAULT_TARGET, random.Random(args.seed))
    KCDiceApp(game, seed=args.seed).run()


def main(argv: list[str] | None = None):
    args = parse_args(argv)
    if not args.plain and sys.stdin.isatty() and sys.stdout.isatty():
        run_tui(args)
        return
    try:
        n_players = args.players or ask_int("Number of players", 1)
        target = args.target or ask_int("Score to win", DEFAULT_TARGET)
        players = [Player(f"Player {i}") for i in range(1, n_players + 1)]
        game = Game(players, target, random.Random(args.seed))
        run(game)
    except (KeyboardInterrupt, EOFError):
        print("\nGame aborted.")
