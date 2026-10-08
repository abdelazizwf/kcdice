# kcdice

A Farkle-style dice game for the terminal, inspired by the dice game in
Kingdom Come: Deliverance.

## Run

```
uv run kcdice                       # prompts for players and target score
uv run kcdice -p 2 -t 2000          # two players, first to 2000
uv run kcdice --seed 42             # reproducible rolls
```

## Rules

Each turn you roll your dice and must keep at least one scoring die (or
combination). You may then bank your turn score or roll the remaining dice.
If a roll has no scoring dice you **bust** and lose the turn score. If you
score all six dice you get **hot dice** and roll all six again. The first
player to reach the target score (default 4000) wins immediately.

| Combination            | Score                                     |
| ---------------------- | ----------------------------------------- |
| Single 1 / single 5    | 100 / 50                                  |
| Three of a kind        | 1s: 1000, otherwise 100 x the number      |
| Each extra matching die| Doubles the three-of-a-kind score         |
| Straight 1-5 / 2-6     | 500 / 750                                 |
| Full straight 1-6      | 1500                                      |

## Layout

- `scoring.py` - pure scoring and bust rules
- `player.py` - player state and turn actions
- `game.py` - turn order and win condition
- `cli.py` - all terminal input/output
