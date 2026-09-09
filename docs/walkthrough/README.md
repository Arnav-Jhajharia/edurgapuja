# Line-by-line walkthrough

Every file, every line. Where `CodeTour.md` explains the *decisions*, this
explains the *code* — including the lines that look like boilerplate, because
"boilerplate" usually means "a decision someone else already made for you", and
it is worth knowing which.

Read in this order. Each part assumes the ones before it.

| Part | Covers | Lines |
|---|---|---|
| [01 · Entry points and settings](01-config.md) | `manage.py`, `config/` | ~260 |
| [02 · The common app](02-common.md) | `uuid7`, `models`, `errors`, `pagination`, `views` | ~230 |
| 03 · Geography and accounts | `geo/`, `accounts/` | ~400 |
| 04 · Pandals | `pandals/` | ~200 |
| 05 · Inventory and services | `inventory/`, `services/` | ~280 |
| 06 · Orders, payments, donations, ops | the money and the operations | ~400 |
| 07 · The tests | `tests/` | ~560 |

**A note on how to read the annotations.** Code is quoted exactly as it appears
in the file. Below each chunk, lines are discussed in order. Where a line is
genuinely self-explanatory it still gets a mention, because "nothing to say about
this one" is itself useful information when you are learning.
