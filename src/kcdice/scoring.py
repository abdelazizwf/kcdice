from collections import Counter

STRAIGHTS = [
    (Counter(range(1, 7)), 1500),  # Full straight
    (Counter(range(2, 7)), 750),  # Partial straight 2:6
    (Counter(range(1, 6)), 500),  # Partial straight 1:5
]
SAME_NUMBER_SCORING = [1000, 200, 300, 400, 500, 600]


def score(selected_dice: list[int]) -> int:
    """Score a selection of dice; 0 if any selected die doesn't contribute."""
    counts = Counter(selected_dice)

    # Try without a straight, then with each straight that fits.
    best = score_groups(counts)
    for straight, straight_score in STRAIGHTS:
        if not straight <= counts:
            continue
        remainder = score_groups(counts - straight)
        if remainder is not None:
            best = max(best or 0, straight_score + remainder)
    return best or 0


def score_groups(counts: Counter) -> int | None:
    """Score dice as 3+ of a kind and single ones/fives.

    Returns None if any die doesn't contribute to the score.
    """
    total = 0
    for number, n in counts.items():
        if n >= 3:
            total += SAME_NUMBER_SCORING[number - 1] * (2 ** (n - 3))
        elif number == 1:
            total += 100 * n
        elif number == 5:
            total += 50 * n
        else:
            return None
    return total


def is_bust(dice: list[int]) -> bool:
    """A roll busts when no subset of it scores."""
    # Any 1 or 5 scores, which also covers every straight.
    if 1 in dice or 5 in dice:
        return False
    # Otherwise only three or more of a kind can score.
    return all(dice.count(d) < 3 for d in set(dice))
