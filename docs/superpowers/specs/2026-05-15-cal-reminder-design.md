# Calendar Reminder Tool — Design Spec

**Date:** 2026-05-15  
**Status:** Approved

## Overview

A Python CLI tool (`ha_cal`) that reads iCal (`.ics`) files and prints formatted German-language reminder text to stdout. Home Assistant captures the output via `command_line` sensor or `shell_command` and forwards it to Telegram using the existing bot integration. A secondary mode merges city-provided `.ics` files into a main calendar file.

## Architecture

Small package, run as `python3 -m ha_cal`. Dependencies: `icalendar`, `recurring_ical_events`, `jinja2`.

`recurring_ical_events` wraps `icalendar` and correctly expands RRULE/EXDATE entries. City-provided `.ics` files sometimes use recurring rules for bi-weekly collection dates.

```
ha_cal/
├── __main__.py        # entry point, calls cli.main()
├── cli.py             # argparse, orchestrates modules
├── calendar_reader.py # parse .ics, filter events by date window
├── merger.py          # merge city .ics into main .ics (dedup by UID)
└── renderer.py        # Jinja2 rendering, prints to stdout
```

## CLI Interface

```
python3 -m ha_cal [OPTIONS]
```

| Flag | Type | Description |
|------|------|-------------|
| `--ical-file` | path (required) | Main `.ics` file to query or write |
| `--time` | `Nd` (default `7d`) | Search window: today through today + N days |
| `--output-events` | int (default `1`) | Max events to include in output |
| `--output-text` | Jinja2 string | Inline template (mutually exclusive with `--template-file`) |
| `--template-file` | path | Path to `.j2` template file |
| `--merge` | path | City `.ics` file to import into `--ical-file`; skips query mode |

## Data Flow — Query Mode

1. Parse `--ical-file` with `icalendar` library
2. Filter `VEVENT` components: date in `[today, today + N days]`
3. Sort by date, take first `--output-events` results
4. If 0 events found: also resolve the next event beyond the window (`next_event`)
5. Render Jinja2 template with context (see below)
6. Print rendered string to stdout, exit 0

If template produces empty/whitespace output (no events, no `next_event`), print nothing and exit 0. HA automation should guard against sending empty Telegram messages.

## Jinja2 Template Context

| Variable | Type | Notes |
|----------|------|-------|
| `events` | list[Event] | Matched events, sorted by date |
| `events[n].summary` | str | iCal SUMMARY field |
| `events[n].date` | `datetime.date` | Event date |
| `events[n].days_until` | int | Days from today (0 = today, 1 = tomorrow) |
| `events[n].description` | str \| None | iCal DESCRIPTION field |
| `days` | int | N from `--time=Nd` |
| `next_event` | Event \| None | First event beyond the search window |

Built-in custom filter: `datefmt` — formats a date as German locale string (e.g. `"1. Juni"`).

### Example Template

```jinja2
{% if events|length == 0 %}
{% if next_event %}Nächster Termin: {{ next_event.summary }} am {{ next_event.date|datefmt }}{% endif %}
{% elif events|length == 1 %}
Erinnerung: {{ events[0].summary }} {{ "morgen" if events[0].days_until == 1 else "am " ~ events[0].date|datefmt }}
{% else %}
In den nächsten {{ days }} Tagen: {% for e in events %}{{ e.summary }} ({{ e.date|datefmt }}){% if not loop.last %} und {% endif %}{% endfor %}
{% endif %}
```

## Data Flow — Merge Mode

Triggered when `--merge=<city.ics>` is provided.

1. Parse `--ical-file` (main), collect all existing UIDs
2. Parse `--merge` (city file)
3. For each event in city file: skip if UID already in main, else append
4. Write updated main file back to disk
5. Print import summary to stdout: `"Importiert: 12 neue Termine, 3 übersprungen (bereits vorhanden)"`

Merge is additive only — existing events in main file are never modified or deleted.

## HA Integration Pattern

```yaml
# configuration.yaml
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
  - alias: Garbage Reminder
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

## Error Handling

- Missing `--ical-file`: exit 1 with message to stderr
- Unparseable `.ics`: exit 1 with filename + error to stderr
- `--output-text` and `--template-file` both provided: exit 1
- Neither `--output-text` nor `--template-file` provided: print raw event summary lines (one per line), no template
- Template render error: exit 1 with template error to stderr

Stdout is always clean (no debug/error output) so HA never captures error text as a Telegram message.

## Date Handling

Events are compared date-only (no time component). Both all-day `DATE` events and timed `DATETIME` events are supported — `DATETIME` values are truncated to their date for comparison. The search window `[today, today + N days]` is inclusive on both ends.

## Out of Scope

- Authentication / encrypted calendars
- Network fetching of remote `.ics` URLs (caller downloads file first)
- Writing new events manually (only merge from external files)
