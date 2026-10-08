from collections import Counter
from itertools import combinations

STRAIGHTS = [
    (Counter(range(1, 7)), 1500, "Full straight"),
    (Counter(range(2, 7)), 750, "Straight 2-6"),
    (Counter(range(1, 6)), 500, "Straight 1-5"),
]
SAME_NUMBER_SCORING = [1000, 200, 300, 400, 500, 600]
COUNT_WORDS = {1: "Single", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}


def score(selected_dice: list[int]) -> int:
    """Score a selection of dice; 0 if any selected die doesn't contribute."""
    return _analyze(selected_dice)[0]


def describe(selected_dice: list[int]) -> str:
    """Human-readable label for the best scoring of a selection."""
    parts = _analyze(selected_dice)[1]
    return " + ".join(parts) if parts else "No score"


def _analyze(selected_dice: list[int]) -> tuple[int, list[str]]:
    """Return the best (score, labels) for a selection, or (0, []) if invalid."""
    counts = Counter(selected_dice)

    # Try without a straight, then with each straight that fits.
    best = _score_groups(counts) or (0, [])
    for straight, straight_score, label in STRAIGHTS:
        if not straight <= counts:
            continue
        remainder = _score_groups(counts - straight)
        if remainder is not None and straight_score + remainder[0] > best[0]:
            best = (straight_score + remainder[0], [label, *remainder[1]])
    return best


def _score_groups(counts: Counter) -> tuple[int, list[str]] | None:
    """Score dice as 3+ of a kind and single ones/fives.

    Returns None if any die doesn't contribute to the score.
    """
    total = 0
    parts = []
    for number, n in sorted(counts.items()):
        if n >= 3:
            total += SAME_NUMBER_SCORING[number - 1] * (2 ** (n - 3))
        elif number == 1:
            total += 100 * n
        elif number == 5:
            total += 50 * n
        else:
            return None
        plural = "" if n == 1 and number in (1, 5) else "s"
        parts.append(f"{COUNT_WORDS[n]} {number}{plural}")
    return total, parts


def is_bust(dice: list[int]) -> bool:
    """A roll busts when no subset of it scores."""
    # Any 1 or 5 scores, which also covers every straight.
    if 1 in dice or 5 in dice:
        return False
    # Otherwise only three or more of a kind can score.
    return all(dice.count(d) < 3 for d in set(dice))


def scoring_positions(dice: list[int]) -> set[int]:
    """1-based positions of dice that can contribute to a score."""
    counts = Counter(dice)
    useful = {1, 5} | {d for d, n in counts.items() if n >= 3}
    for straight, _, _ in STRAIGHTS:
        if straight <= counts:
            useful |= set(straight)
    return {i for i, d in enumerate(dice, start=1) if d in useful}


def positions_for_values(dice: list[int], values: list[int]) -> list[int]:
    """Map die values to distinct 1-based positions in the roll."""
    free = list(enumerate(dice, start=1))
    positions = []
    for value in values:
        for k, (position, die) in enumerate(free):
            if die == value:
                positions.append(position)
                del free[k]
                break
        else:
            raise ValueError(f"No {value} available in the roll.")
    return positions


def best_selection(dice: list[int]) -> list[int]:
    """1-based positions of the highest-scoring selection (fewest dice on ties)."""
    best_key, best = (0, 0), []
    for size in range(1, len(dice) + 1):
        for combo in combinations(range(1, len(dice) + 1), size):
            points = score([dice[p - 1] for p in combo])
            if (points, -size) > best_key:
                best_key, best = (points, -size), list(combo)
    return best
