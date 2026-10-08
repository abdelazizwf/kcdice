# kcdice

A Farkle-style dice game for the terminal, inspired by the dice game in
Kingdom Come: Deliverance.

## Run

```
uv run kcdice                       # full-screen UI, asks for names and target
uv run kcdice -p 2 -t 2000          # two players, first to 2000
uv run kcdice -p 1 --bots 2         # one human against two computer players
uv run kcdice --seed 42             # reproducible rolls
uv run kcdice --plain               # simple prompt-based interface
```

The full-screen UI (built with [Textual](https://textual.textualize.io/)) is
used when running in a terminal; otherwise, or with `--plain`, the game falls
back to line-based prompts.

### Controls

| Key                   | Action                                      |
| --------------------- | ------------------------------------------- |
| left / right, click   | move the cursor / pick a die                |
| space, `1`-`6`        | toggle the cursor die / die number          |
| `a`                   | auto-select the best scoring dice           |
| enter                 | keep the selected dice (or pass after bust) |
| `r` / `b`             | roll again / bank the turn score            |
| enter (bot's turn)    | speed up the computer player                |
| `?` / `q`             | rules / quit                                |

Dice with a green border can contribute to a score, and the selection's score
is previewed before you keep it.

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

- `scoring.py` - pure scoring, bust rules and selection helpers
- `player.py` - player state and turn actions
- `bot.py` - computer player strategy and turn events
- `game.py` - turn order and win condition
- `tui.py` / `kcdice.tcss` - full-screen Textual interface
- `cli.py` - argument parsing and the plain prompt interface
