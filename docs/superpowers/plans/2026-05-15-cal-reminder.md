# Calendar Reminder Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI package (`ha_cal`) that queries iCal files and prints formatted German-language reminder text to stdout for Home Assistant/Telegram integration.

**Architecture:** Small package (`ha_cal/`) with four focused modules: calendar reading/filtering, iCal merging, Jinja2 rendering, and CLI orchestration. All run via `python3 -m ha_cal --ical-file=... --time=7d --output-text="..."`.

**Tech Stack:** Python 3.10+, `icalendar`, `recurring_ical_events`, `jinja2`, `pytest`

---

## File Map

| File | Responsibility |
|------|---------------|
| `ha_cal/__init__.py` | Empty package marker |
| `ha_cal/__main__.py` | Entry point (`python3 -m ha_cal`) |
| `ha_cal/calendar_reader.py` | `Event` dataclass, parse `.ics`, filter by date window |
| `ha_cal/merger.py` | Merge city `.ics` into main `.ics`, dedup by UID |
| `ha_cal/renderer.py` | Jinja2 rendering with `datefmt` filter |
| `ha_cal/cli.py` | Argparse + orchestration |
| `pyproject.toml` | Package metadata and dependencies |
| `tests/test_calendar_reader.py` | Unit tests for read/filter logic |
| `tests/test_merger.py` | Unit tests for merge logic |
| `tests/test_renderer.py` | Unit tests for template rendering |
| `tests/test_cli.py` | Integration tests via subprocess |

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `ha_cal/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "ha_cal"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "icalendar>=5.0",
    "recurring_ical_events>=2.1",
    "jinja2>=3.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0"]

[tool.setuptools.packages.find]
where = ["."]
include = ["ha_cal*"]
```

- [ ] **Step 2: Create package and test directories**

```bash
mkdir -p ha_cal tests
touch ha_cal/__init__.py tests/__init__.py
```

- [ ] **Step 3: Install in editable mode**

```bash
pip install -e ".[dev]"
```

Expected: no errors, `python3 -c "import ha_cal"` exits 0.

- [ ] **Step 4: Commit**

```bash
git init
git add pyproject.toml ha_cal/__init__.py tests/__init__.py
git commit -m "chore: scaffold ha_cal package"
```

---

## Task 2: Event dataclass and calendar reader

**Files:**
- Create: `ha_cal/calendar_reader.py`
- Create: `tests/test_calendar_reader.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_calendar_reader.py`:

```python
from datetime import date
from pathlib import Path
import pytest
from ha_cal.calendar_reader import Event, read_events, find_next_event

ICAL_TWO_EVENTS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:test-001@test
SUMMARY:Gelbe Tonne
DTSTART;VALUE=DATE:20260601
DTEND;VALUE=DATE:20260602
END:VEVENT
BEGIN:VEVENT
UID:test-002@test
SUMMARY:Blaue Tonne
DTSTART;VALUE=DATE:20260615
DTEND;VALUE=DATE:20260616
END:VEVENT
END:VCALENDAR"""

@pytest.fixture
def ical_file(tmp_path):
    f = tmp_path / "test.ics"
    f.write_bytes(ICAL_TWO_EVENTS)
    return f

def test_event_in_window(ical_file):
    events = read_events(ical_file, date(2026, 6, 1), date(2026, 6, 7), today=date(2026, 6, 1))
    assert len(events) == 1
    assert events[0].summary == "Gelbe Tonne"

def test_days_until_is_correct(ical_file):
    events = read_events(ical_file, date(2026, 5, 31), date(2026, 6, 7), today=date(2026, 5, 31))
    assert events[0].days_until == 1  # event is tomorrow

def test_empty_window(ical_file):
    events = read_events(ical_file, date(2026, 7, 1), date(2026, 7, 7), today=date(2026, 7, 1))
    assert events == []

def test_events_sorted_by_date(ical_file):
    events = read_events(ical_file, date(2026, 6, 1), date(2026, 6, 30), today=date(2026, 6, 1))
    assert len(events) == 2
    assert events[0].date < events[1].date

def test_find_next_event(ical_file):
    event = find_next_event(ical_file, after=date(2026, 6, 7), today=date(2026, 6, 7))
    assert event is not None
    assert event.summary == "Blaue Tonne"

def test_find_next_event_none_when_no_future(ical_file):
    event = find_next_event(ical_file, after=date(2028, 1, 1), today=date(2028, 1, 1))
    assert event is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_calendar_reader.py -v
```

Expected: `ImportError: cannot import name 'Event' from 'ha_cal.calendar_reader'`

- [ ] **Step 3: Implement `ha_cal/calendar_reader.py`**

```python
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import recurring_ical_events
from icalendar import Calendar


@dataclass
class Event:
    summary: str
    date: date
    days_until: int
    description: str | None


def _to_date(dt) -> date:
    if isinstance(dt, datetime):
        return dt.date()
    return dt


def read_events(ical_path: Path, start: date, end: date, today: date) -> list[Event]:
    with open(ical_path, "rb") as f:
        cal = Calendar.from_ical(f.read())

    components = recurring_ical_events.of(cal).between(start, end)
    events = []
    for component in components:
        if component.name != "VEVENT":
            continue
        event_date = _to_date(component.get("DTSTART").dt)
        summary = str(component.get("SUMMARY", ""))
        raw_desc = component.get("DESCRIPTION")
        description = str(raw_desc) if raw_desc else None
        events.append(Event(
            summary=summary,
            date=event_date,
            days_until=(event_date - today).days,
            description=description,
        ))

    return sorted(events, key=lambda e: e.date)


def find_next_event(ical_path: Path, after: date, today: date) -> Event | None:
    search_end = date(after.year + 2, after.month, after.day)
    events = read_events(ical_path, after + timedelta(days=1), search_end, today)
    return events[0] if events else None
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_calendar_reader.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ha_cal/calendar_reader.py tests/test_calendar_reader.py
git commit -m "feat: add calendar reader with event filtering"
```

---

## Task 3: iCal merger

**Files:**
- Create: `ha_cal/merger.py`
- Create: `tests/test_merger.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_merger.py`:

```python
import pytest
from ha_cal.merger import merge

MAIN_ICAL = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:existing-001@test
SUMMARY:Existing Event
DTSTART;VALUE=DATE:20260601
DTEND;VALUE=DATE:20260602
END:VEVENT
END:VCALENDAR"""

CITY_ICAL = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//City//City//EN
BEGIN:VEVENT
UID:existing-001@test
SUMMARY:Existing Event
DTSTART;VALUE=DATE:20260601
DTEND;VALUE=DATE:20260602
END:VEVENT
BEGIN:VEVENT
UID:new-001@test
SUMMARY:New Event
DTSTART;VALUE=DATE:20260615
DTEND;VALUE=DATE:20260616
END:VEVENT
END:VCALENDAR"""

@pytest.fixture
def main_ical(tmp_path):
    f = tmp_path / "main.ics"
    f.write_bytes(MAIN_ICAL)
    return f

@pytest.fixture
def city_ical(tmp_path):
    f = tmp_path / "city.ics"
    f.write_bytes(CITY_ICAL)
    return f

def test_merge_counts(main_ical, city_ical):
    added, skipped = merge(main_ical, city_ical)
    assert added == 1
    assert skipped == 1

def test_merge_writes_new_event(main_ical, city_ical):
    merge(main_ical, city_ical)
    content = main_ical.read_bytes()
    assert b"New Event" in content

def test_merge_keeps_existing_event(main_ical, city_ical):
    merge(main_ical, city_ical)
    content = main_ical.read_bytes()
    assert b"Existing Event" in content

def test_merge_no_duplicate_uids(main_ical, city_ical):
    merge(main_ical, city_ical)
    # second merge should add 0, skip 2
    added, skipped = merge(main_ical, city_ical)
    assert added == 0
    assert skipped == 2
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_merger.py -v
```

Expected: `ImportError: cannot import name 'merge' from 'ha_cal.merger'`

- [ ] **Step 3: Implement `ha_cal/merger.py`**

```python
from pathlib import Path

from icalendar import Calendar


def merge(main_path: Path, city_path: Path) -> tuple[int, int]:
    """Merge events from city_path into main_path. Returns (added, skipped)."""
    with open(main_path, "rb") as f:
        main_cal = Calendar.from_ical(f.read())
    with open(city_path, "rb") as f:
        city_cal = Calendar.from_ical(f.read())

    existing_uids = {
        str(c.get("UID"))
        for c in main_cal.walk()
        if c.name == "VEVENT"
    }

    added = 0
    skipped = 0
    for component in city_cal.walk():
        if component.name != "VEVENT":
            continue
        uid = str(component.get("UID", ""))
        if uid in existing_uids:
            skipped += 1
        else:
            main_cal.add_component(component)
            existing_uids.add(uid)
            added += 1

    with open(main_path, "wb") as f:
        f.write(main_cal.to_ical())

    return added, skipped
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_merger.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ha_cal/merger.py tests/test_merger.py
git commit -m "feat: add ical merger with uid deduplication"
```

---

## Task 4: Jinja2 renderer

**Files:**
- Create: `ha_cal/renderer.py`
- Create: `tests/test_renderer.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_renderer.py`:

```python
from datetime import date
import pytest
from ha_cal.calendar_reader import Event
from ha_cal.renderer import render, datefmt


def make_event(summary, event_date, days_until=0, description=None):
    return Event(summary=summary, date=event_date, days_until=days_until, description=description)


def test_datefmt_june():
    assert datefmt(date(2026, 6, 1)) == "1. Juni"

def test_datefmt_december():
    assert datefmt(date(2026, 12, 24)) == "24. Dezember"

def test_datefmt_march_umlaut():
    assert datefmt(date(2026, 3, 15)) == "15. März"

def test_render_single_event():
    events = [make_event("Gelbe Tonne", date(2026, 6, 1), days_until=1)]
    result = render("{{ events[0].summary }}", events, days=1, next_event=None)
    assert result == "Gelbe Tonne"

def test_render_uses_datefmt_filter():
    events = [make_event("Gelbe Tonne", date(2026, 6, 1))]
    result = render("{{ events[0].date|datefmt }}", events, days=1, next_event=None)
    assert result == "1. Juni"

def test_render_no_events_with_next():
    next_ev = make_event("Blaue Tonne", date(2026, 6, 15), days_until=15)
    result = render(
        "{% if events %}{{ events[0].summary }}{% elif next_event %}Nächster: {{ next_event.summary }}{% endif %}",
        [], days=7, next_event=next_ev
    )
    assert result == "Nächster: Blaue Tonne"

def test_render_strips_whitespace():
    result = render("  {{ events[0].summary }}  ", [make_event("X", date(2026, 6, 1))], days=1, next_event=None)
    assert result == "X"

def test_render_empty_returns_empty_string():
    result = render("{% if events %}{{ events[0].summary }}{% endif %}", [], days=1, next_event=None)
    assert result == ""
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_renderer.py -v
```

Expected: `ImportError: cannot import name 'render' from 'ha_cal.renderer'`

- [ ] **Step 3: Implement `ha_cal/renderer.py`**

```python
from datetime import date

from jinja2 import Environment

from ha_cal.calendar_reader import Event

_GERMAN_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def datefmt(d: date) -> str:
    return f"{d.day}. {_GERMAN_MONTHS[d.month]}"


def render(template_str: str, events: list[Event], days: int, next_event: Event | None) -> str:
    env = Environment()
    env.filters["datefmt"] = datefmt
    template = env.from_string(template_str)
    return template.render(events=events, days=days, next_event=next_event).strip()
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_renderer.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ha_cal/renderer.py tests/test_renderer.py
git commit -m "feat: add jinja2 renderer with german datefmt filter"
```

---

## Task 5: CLI and entry point

**Files:**
- Create: `ha_cal/cli.py`
- Create: `ha_cal/__main__.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
import subprocess
import sys
from pathlib import Path
import pytest

ICAL_FUTURE = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:future-001@test
SUMMARY:Gelbe Tonne
DTSTART;VALUE=DATE:20991201
DTEND;VALUE=DATE:20991202
END:VEVENT
END:VCALENDAR"""

CITY_ICAL = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//City//City//EN
BEGIN:VEVENT
UID:city-001@test
SUMMARY:City Event
DTSTART;VALUE=DATE:20991201
DTEND;VALUE=DATE:20991202
END:VEVENT
END:VCALENDAR"""

@pytest.fixture
def ical_file(tmp_path):
    f = tmp_path / "main.ics"
    f.write_bytes(ICAL_FUTURE)
    return f

@pytest.fixture
def city_file(tmp_path):
    f = tmp_path / "city.ics"
    f.write_bytes(CITY_ICAL)
    return f


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "ha_cal", *args],
        capture_output=True, text=True
    )


def test_missing_ical_file_exits_nonzero():
    result = run("--ical-file=/nonexistent.ics", "--output-text=x")
    assert result.returncode != 0

def test_both_output_flags_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--output-text=x", f"--template-file={ical_file}")
    assert result.returncode != 0

def test_no_events_in_window_prints_nothing(ical_file):
    # event is in 2099, window is 7d from today
    result = run(f"--ical-file={ical_file}", "--time=7d", "--output-text={{ events[0].summary if events else '' }}")
    assert result.returncode == 0
    assert result.stdout.strip() == ""

def test_no_template_no_events_prints_nothing(ical_file):
    # no --output-text, events are in 2099 so window is empty — nothing printed
    result = run(f"--ical-file={ical_file}", "--time=7d")
    assert result.returncode == 0
    assert result.stdout.strip() == ""

def test_invalid_ics_exits_nonzero(tmp_path):
    bad = tmp_path / "bad.ics"
    bad.write_text("this is not valid ical content")
    result = run(f"--ical-file={bad}", "--time=7d", "--output-text=x")
    assert result.returncode != 0
    assert result.stderr != ""

def test_template_render_error_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--time=7d", "--output-text={{ undefined_var.missing }}")
    assert result.returncode != 0

def test_merge_mode_prints_summary(ical_file, city_file):
    result = run(f"--ical-file={ical_file}", f"--merge={city_file}")
    assert result.returncode == 0
    assert "Importiert:" in result.stdout
    assert "1 neue Termine" in result.stdout

def test_template_file_flag(ical_file, tmp_path):
    tmpl = tmp_path / "msg.j2"
    tmpl.write_text("{% if next_event %}Nächster: {{ next_event.summary }}{% endif %}")
    result = run(f"--ical-file={ical_file}", "--time=7d", f"--template-file={tmpl}")
    assert result.returncode == 0
    assert "Gelbe Tonne" in result.stdout

def test_stderr_clean_on_success(ical_file):
    result = run(f"--ical-file={ical_file}", "--time=7d", "--output-text=ok")
    assert result.stderr == ""

def test_missing_template_file_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--time=7d", "--template-file=/nonexistent.j2")
    assert result.returncode != 0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_cli.py -v
```

Expected: `No module named ha_cal.__main__`

- [ ] **Step 3: Implement `ha_cal/cli.py`**

```python
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from ha_cal.calendar_reader import read_events, find_next_event
from ha_cal.merger import merge
from ha_cal.renderer import render


def _parse_days(time_str: str) -> int:
    if not time_str.endswith("d") or not time_str[:-1].isdigit():
        print(f"Error: --time must be in format Nd (e.g. 7d), got: {time_str!r}", file=sys.stderr)
        sys.exit(1)
    return int(time_str[:-1])


def main():
    parser = argparse.ArgumentParser(description="Calendar reminder for Home Assistant")
    parser.add_argument("--ical-file", required=True, type=Path, metavar="PATH")
    parser.add_argument("--time", default="7d", metavar="Nd")
    parser.add_argument("--output-events", type=int, default=1, metavar="N")
    parser.add_argument("--output-text", default=None, metavar="TEMPLATE")
    parser.add_argument("--template-file", type=Path, default=None, metavar="PATH")
    parser.add_argument("--merge", type=Path, default=None, dest="merge_file", metavar="PATH")
    args = parser.parse_args()

    if not args.ical_file.exists():
        print(f"Error: {args.ical_file} not found", file=sys.stderr)
        sys.exit(1)

    if args.merge_file:
        if not args.merge_file.exists():
            print(f"Error: {args.merge_file} not found", file=sys.stderr)
            sys.exit(1)
        added, skipped = merge(args.ical_file, args.merge_file)
        print(f"Importiert: {added} neue Termine, {skipped} übersprungen (bereits vorhanden)")
        return

    if args.output_text and args.template_file:
        print("Error: --output-text and --template-file are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    days = _parse_days(args.time)
    today = date.today()
    start = today
    end = today + timedelta(days=days)

    try:
        events = read_events(args.ical_file, start, end, today)[: args.output_events]
    except Exception as exc:
        print(f"Error parsing {args.ical_file}: {exc}", file=sys.stderr)
        sys.exit(1)

    next_event = None
    if not events:
        next_event = find_next_event(args.ical_file, end, today)

    if args.template_file:
        if not args.template_file.exists():
            print(f"Error: {args.template_file} not found", file=sys.stderr)
            sys.exit(1)
        template_str = args.template_file.read_text()
    elif args.output_text:
        template_str = args.output_text
    else:
        for event in events:
            print(event.summary)
        return

    try:
        result = render(template_str, events, days, next_event)
    except Exception as exc:
        print(f"Error rendering template: {exc}", file=sys.stderr)
        sys.exit(1)
    if result:
        print(result)
```

- [ ] **Step 4: Implement `ha_cal/__main__.py`**

```python
from ha_cal.cli import main

main()
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_cli.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
pytest -v
```

Expected: all tests PASS, 0 failures.

- [ ] **Step 7: Commit**

```bash
git add ha_cal/cli.py ha_cal/__main__.py tests/test_cli.py
git commit -m "feat: add cli entry point with full argument handling"
```

---

## Task 6: Example files and README

**Files:**
- Create: `examples/garbage.ics`
- Create: `examples/garbage_msg.j2`
- Create: `README.md`

- [ ] **Step 1: Create example iCal file**

Create `examples/garbage.ics`:

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ha_cal//ha_cal//EN
X-WR-CALNAME:Müllkalender
BEGIN:VEVENT
UID:garbage-2026-06-01@ha-cal
SUMMARY:Gelbe Tonne
DTSTART;VALUE=DATE:20260601
DTEND;VALUE=DATE:20260602
END:VEVENT
BEGIN:VEVENT
UID:garbage-2026-06-15@ha-cal
SUMMARY:Blaue Tonne
DTSTART;VALUE=DATE:20260615
DTEND;VALUE=DATE:20260616
END:VEVENT
BEGIN:VEVENT
UID:garbage-2026-06-08@ha-cal
SUMMARY:Restmüll
DTSTART;VALUE=DATE:20260608
DTEND;VALUE=DATE:20260609
END:VEVENT
END:VCALENDAR
```

- [ ] **Step 2: Create example Jinja2 template**

Create `examples/garbage_msg.j2`:

```jinja2
{% if events|length == 0 %}
{% if next_event %}Nächster Termin: {{ next_event.summary }} am {{ next_event.date|datefmt }}{% endif %}
{% elif events|length == 1 %}
Erinnerung: {{ events[0].summary }} {{ "morgen" if events[0].days_until == 1 else "am " ~ events[0].date|datefmt }}
{% else %}
In den nächsten {{ days }} Tagen: {% for e in events %}{{ e.summary }} ({{ e.date|datefmt }}){% if not loop.last %} und {% endif %}{% endfor %}
{% endif %}
```

- [ ] **Step 3: Create README.md**

Create `README.md`:

```markdown
# ha_cal — Calendar Reminder for Home Assistant

Reads `.ics` calendar files and prints formatted German-language reminders to stdout. Designed for use with Home Assistant `shell_command` + Telegram bot.

## Install

```bash
pip install -e ".[dev]"
```

## Usage

**Query upcoming events:**
```bash
python3 -m ha_cal \
  --ical-file=/config/calendars/garbage.ics \
  --time=1d \
  --output-events=3 \
  --template-file=/config/calendars/garbage_msg.j2
```

**Inline template:**
```bash
python3 -m ha_cal \
  --ical-file=examples/garbage.ics \
  --time=7d \
  --output-text="{{ events[0].summary if events else 'Keine Termine' }}"
```

**Merge city calendar:**
```bash
python3 -m ha_cal \
  --ical-file=/config/calendars/garbage.ics \
  --merge=/tmp/city_2026.ics
```

## Template Variables

| Variable | Type | Example |
|----------|------|---------|
| `events` | list | matched events |
| `events[n].summary` | str | `"Gelbe Tonne"` |
| `events[n].date` | date | `2026-06-01` |
| `events[n].days_until` | int | `1` (tomorrow) |
| `events[n].description` | str\|None | optional |
| `days` | int | `7` |
| `next_event` | Event\|None | first event beyond window |

Custom filter: `{{ date_value|datefmt }}` → `"1. Juni"`

## Home Assistant Integration

```yaml
command_line:
  - sensor:
      name: garbage_reminder
      command: >
        python3 -m ha_cal
        --ical-file=/config/calendars/garbage.ics
        --time=1d
        --output-events=3
        --template-file=/config/calendars/garbage_msg.j2
      scan_interval: 3600

automation:
  - alias: Garbage Reminder Evening
    trigger:
      platform: time
      at: "20:00:00"
    condition:
      condition: template
      value_template: "{{ states('sensor.garbage_reminder') != '' }}"
    action:
      service: telegram_bot.send_message
      data:
        message: "{{ states('sensor.garbage_reminder') }}"
```
```

- [ ] **Step 4: Commit**

```bash
git add examples/ README.md
git commit -m "docs: add example ics file, jinja2 template, and readme"
```
