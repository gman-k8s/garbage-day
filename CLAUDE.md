# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
bash setup_venv.sh   # creates .venv via uv sync --extra dev
```

Both `ha_cal.py` and `generate_garbage.py` auto-exec into `.venv/bin/python3` — no manual activation needed.

## Commands

```bash
# Run tests
.venv/bin/pytest

# Run a single test file
.venv/bin/pytest tests/test_calendar_reader.py

# Run the main tool
./ha_cal.py --ical-file=data/muell.ics --time=7d --output-events=2 --template-file=examples/garbage_msg.j2

# Generate a schedule
./generate_garbage.py --year=2026 --bundesland=RLP --weekday=montag --output=generated.ics
```

## Architecture

Two entry-point scripts that both self-bootstrap into `.venv`:

- **`ha_cal.py`** — thin wrapper that re-execs into `.venv/bin/python3`, then calls `ha_cal.cli.main()`
- **`generate_garbage.py`** — standalone script (no package import), re-execs into venv then runs inline

The `ha_cal/` package has clear module boundaries:

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Argument parsing, mode dispatch (query / merge / add / replace / list) |
| `calendar_reader.py` | Read `.ics` → `Event` dataclass list, using `recurring_ical_events` for recurrence expansion |
| `renderer.py` | Jinja2 rendering with `|datefmt` and `|weekday` filters (German locale, hardcoded) |
| `merger.py` | Merge a city `.ics` into the main file, deduplicating by UID |
| `writer.py` | Append events or regex-replace fields in an existing `.ics` file |

**Data flow for query mode:** `read_events()` → list of `Event` objects → `render()` → stdout. If no events found in window, `find_next_event()` searches 730 days forward and passes result as `next_event` to the template.

**`Event` dataclass** (`calendar_reader.py`): `summary`, `date`, `days_until`, `description`. `days_until` is always relative to `today` passed at call time — not re-computed at render time.

**Holiday logic** (`generate_garbage.py`): uses `holidays.Germany(state=bundesland)`. If collection day falls on a public holiday, shifts forward day-by-day until non-holiday. Shifted events get a DESCRIPTION noting the original planned date.

## Key Constraints

- Templates use Jinja2 but with no autoescaping (`Environment()` bare). Output is plain text for Home Assistant / Telegram.
- `--merge` deduplicates by UID only — events without UID are silently skipped.
- `--replace-in-field` uses `re.DOTALL` (pattern matches across line breaks).
- `.ics` files are always read as binary (`rb`) and written as binary (`wb`) to preserve iCal encoding.
