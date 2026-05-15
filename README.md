# ha_cal — Calendar Reminder for Home Assistant

Reads `.ics` calendar files and prints formatted German-language reminders to stdout.
Designed for use with Home Assistant `command_line` sensor + Telegram bot.

Includes a separate generator script (`generate_garbage.py`) to create garbage collection
schedules with German public holiday support.

---

## Setup

```bash
bash setup_venv.sh
```

This creates a `.venv` directory and installs all dependencies. The scripts use the venv
automatically — no need to activate it manually.

---

## ha_cal.py — Main Tool

### Query upcoming events

Prints matching events using a Jinja2 template. If no events are found in the window,
`next_event` is set to the next future event beyond the window.

```bash
./ha_cal.py \
  --ical-file=data/muell.ics \
  --time=1d \
  --output-events=3 \
  --template-file=examples/garbage_msg.j2
```

**Inline template (short messages):**
```bash
./ha_cal.py \
  --ical-file=data/muell.ics \
  --time=7d \
  --output-events=2 \
  --output-text="{{ events[0].summary if events else 'Keine Termine' }}"
```

**Multi-event natural language output:**
```bash
./ha_cal.py \
  --ical-file=data/muell.ics \
  --time=14d \
  --output-events=2 \
  --output-text="In den nächsten {{ days }} Tagen stehen {{ events|length }} Events an: {% for e in events %}{{ e.summary }} am {{ e.date|weekday }}, {{ e.date.day }}.{{ e.date.month }}.{{ e.date.year }}{% if not loop.last %} und {% endif %}{% endfor %}"
```

### Merge a city calendar into your main file

```bash
./ha_cal.py --ical-file=data/muell.ics --merge=/tmp/city_2026.ics
```

Deduplicates by UID — safe to run multiple times, won't add events twice.

### Add a single event manually

```bash
./ha_cal.py \
  --ical-file=data/muell.ics \
  --add-date=2026-09-15 \
  --add-summary="Restmüll" \
  --add-description="An die Strasse stellen"
```

Output: `Hinzugefügt: Restmüll am 15. September`

### List all events (for verification)

```bash
./ha_cal.py --ical-file=data/muell.ics --list-all
```

Output format:
```
2026-04-07  KW15  Dienstag    Graue Tonne (Restmüll)  [Verschoben wegen Feiertag (ursprünglich Montag, 06.04.2026)]
2026-04-13  KW16  Montag      Braune Tonne (Biotonne)
```

### Search and replace text in a field

Useful to clean up verbose descriptions from city-provided calendars:

```bash
./ha_cal.py --ical-file=data/muell.ics \
  --replace-in-field=DESCRIPTION \
  --search="Grünschnitt.*" \
  --replace="Grünschnitt"
```

Multiple passes for different event types:
```bash
./ha_cal.py --ical-file=data/muell.ics --replace-in-field=DESCRIPTION --search="Grünschnitt.*"  --replace="Grünschnitt"
./ha_cal.py --ical-file=data/muell.ics --replace-in-field=DESCRIPTION --search="In die Gelben.*" --replace="Gelber Sack"
./ha_cal.py --ical-file=data/muell.ics --replace-in-field=DESCRIPTION --search="Altpapier.*"     --replace="Altpapier"
```

Remove all descriptions entirely:
```bash
./ha_cal.py --ical-file=data/muell.ics --replace-in-field=DESCRIPTION --search=".*" --replace=""
```

`--search` is a Python regex with `re.DOTALL` (matches across line breaks).

---

## CLI Reference — ha_cal.py

| Flag | Default | Description |
|------|---------|-------------|
| `--ical-file` | (required) | Path to `.ics` file |
| `--time` | `7d` | Search window from today (e.g. `1d`, `7d`, `30d`) |
| `--output-events` | `1` | Max events to return in window |
| `--output-text` | — | Inline Jinja2 template string |
| `--template-file` | — | Path to `.j2` template file |
| `--merge` | — | City `.ics` file to import into `--ical-file` |
| `--add-date` | — | Date of new event (YYYY-MM-DD), use with `--add-summary` |
| `--add-summary` | — | Title of new event |
| `--add-description` | — | Optional description for new event |
| `--list-all` | — | Print all events in file and exit |
| `--replace-in-field` | — | Field to modify (e.g. `DESCRIPTION`, `SUMMARY`) |
| `--search` | — | Regex pattern to find |
| `--replace` | — | Replacement text (empty string removes match) |

---

## Template Reference

### Variables

| Variable | Type | Example |
|----------|------|---------|
| `events` | list | matched events, sorted by date |
| `events[n].summary` | str | `"Gelbe Tonne"` |
| `events[n].date` | date | `2026-06-01` |
| `events[n].days_until` | int | `0` today, `1` tomorrow |
| `events[n].description` | str\|None | optional description |
| `days` | int | `7` (from `--time=7d`) |
| `next_event` | Event\|None | first event beyond the search window |

### Filters

| Filter | Example | Output |
|--------|---------|--------|
| `\|datefmt` | `{{ e.date\|datefmt }}` | `1. Juni` |
| `\|weekday` | `{{ e.date\|weekday }}` | `Montag` |

Date parts are also directly accessible: `e.date.day`, `e.date.month`, `e.date.year`.

### Example template (examples/garbage_msg.j2)

```jinja2
{% if events|length == 0 %}
{% if next_event %}Nächster Termin: {{ next_event.summary }} am {{ next_event.date|weekday }}, {{ next_event.date.day }}.{{ next_event.date.month }}.{{ next_event.date.year }}{% endif %}
{% elif events|length == 1 %}
Erinnerung: {{ events[0].summary }} {{ "morgen" if events[0].days_until == 1 else "am " ~ events[0].date|datefmt }}
{% else %}
In den nächsten {{ days }} Tagen: {% for e in events %}{{ e.summary }} ({{ e.date|datefmt }}){% if not loop.last %} und {% endif %}{% endfor %}
{% endif %}
```

---

## Home Assistant Integration

```yaml
# configuration.yaml
command_line:
  - sensor:
      name: garbage_reminder
      command: >
        /config/ha_cal/ha_cal.py
        --ical-file=/config/calendars/muell.ics
        --time=1d
        --output-events=3
        --template-file=/config/calendars/garbage_msg.j2
      scan_interval: 3600

automation:
  - alias: Müll-Erinnerung Abends
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

The sensor runs every hour and stores the output as its state. The automation fires at 20:00
and sends a Telegram message only when the sensor has content (i.e. there is something
to pick up tomorrow).

---

## generate_garbage.py — Schedule Generator

Generates a garbage collection `.ics` file based on calendar week parity, with automatic
shifting for German public holidays (Bundesland-specific).

**Rules:**
- Odd calendar weeks → one bin type (e.g. Graue Tonne)
- Even calendar weeks → other bin type (e.g. Braune Tonne)
- If the collection day is a public holiday → shifted +1 day until a non-holiday is found
- Shifted events include a DESCRIPTION noting the original planned date

### Usage

```bash
./generate_garbage.py \
  --year=2026 \
  --bundesland=RLP \
  --weekday=montag \
  --odd-week="Graue Tonne (Restmüll)" \
  --even-week="Braune Tonne (Biotonne)" \
  --output=generated_2026.ics
```

Generate multiple years at once:
```bash
./generate_garbage.py --year=2026-2028 --bundesland=BW --weekday=dienstag --output=generated.ics
```

Then merge into your main calendar:
```bash
./ha_cal.py --ical-file=data/muell.ics --merge=generated_2026.ics
```

### CLI Reference — generate_garbage.py

| Flag | Default | Description |
|------|---------|-------------|
| `--year` | (required) | Year (`2026`) or range (`2026-2028`) |
| `--bundesland` | (required) | Federal state code (see below) |
| `--weekday` | `montag` | Collection day in German or English |
| `--odd-week` | `Graue Tonne (Restmüll)` | Summary for odd calendar weeks |
| `--even-week` | `Braune Tonne (Biotonne)` | Summary for even calendar weeks |
| `--output` | (required) | Output `.ics` file path |

### Bundesland codes

| Code | Aliases | State |
|------|---------|-------|
| `BB` | — | Brandenburg |
| `BE` | — | Berlin |
| `BW` | `BAWUE` | Baden-Württemberg |
| `BY` | `BAY` | Bayern |
| `HB` | — | Bremen |
| `HE` | — | Hessen |
| `HH` | — | Hamburg |
| `MV` | `MEC` | Mecklenburg-Vorpommern |
| `NI` | — | Niedersachsen |
| `NW` | `NRW` | Nordrhein-Westfalen |
| `RP` | `RLP` | Rheinland-Pfalz |
| `SH` | — | Schleswig-Holstein |
| `SL` | — | Saarland |
| `SN` | `SAC` | Sachsen |
| `ST` | `SAT` | Sachsen-Anhalt |
| `TH` | `THUE` | Thüringen |

### Weekday names

Accepts German or English, case-insensitive:
`montag`, `dienstag`, `mittwoch`, `donnerstag`, `freitag`, `samstag`, `sonntag`
(or `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`)


# My own Setup

1) Download the Calendar from your city

2) copy it into the data-directory

3) create missing events for garbage bins that are missing from the calendar

```bash
./generate_garbage.py \
  --year=2026 \
  --bundesland=RLP \
  --weekday=montag \
  --odd-week="Graue Tonne (Restmüll)" \
  --even-week="Braune Tonne (Biotonne)" \
  --output=generated_2026.ics
```

4) merge that calendar to the one we just downloaded

```bash
./ha_cal.py --ical-file=data/ics-rauental.ics --merge=generated_2026.ics
```

## setup home assistant, we need 2 software packages that might not be installed yet

5) open Terminal addon
```bash
apk add python3
apk add uv
```

6) open /config/configuration.yaml (it's a symlink to /homeassistant/configuration.yaml)

add into the yaml code

```yaml
shell_command:
  garbage_day: >-
    bash -c 'cd /config/garbage-day && ./ha_cal.py
    --ical-file=data/ics-rauental.ics
    --time={{ days }}d
    --output-events=50
    --output-text={% raw %}"In den nächsten {{ days }} Tagen {% if events|length == 1 %}steht 1 Event an{% else %}stehen {{ events|length }} Events an{% endif %}{% if events|length == 0 %}.{% else %}: {% for e in events %}{{ e.summary }} am {{ e.date|weekday }}, {{ e.date.day }}.{{ e.date.month }}.{{ e.date.year }}{% if not loop.last %} und {% endif %}{% endfor %}{% endif %}"{% endraw %}'
  setup_garbage_venv: "bash -c 'cd /config/garbage-day && bash setup_venv.sh'"
```

7) reload / restart home assistant

8) go to settings -> developer tools and execute "action: shell_command.setup_garbage_venv". It cannot be the terminal, it is a different docker instance.

9) go to settings -> automation

9.1) add automation
```yaml
alias: Telegram Abfall-Erinnerung (daily)
description: schickt mir Telegramm-Nachrichten wenn Abfall rauszustellen ist
triggers:
  - trigger: time
    at: "16:00:00"
    weekday:
      - wed
      - mon
      - tue
      - thu
      - sat
      - fri
      - sun
conditions: []
actions:
  - action: shell_command.garbage_day
    data:
      days: 2
    response_variable: script_ergebnis
  - condition: template
    value_template: "{{ '0 Events' not in script_ergebnis['stdout'] }}"
  - action: telegram_bot.send_message
    data:
      title: Abfallerinnerung! 🗑️
      message: "{{ script_ergebnis['stdout'] }}"
mode: single
```

9.2) add automation
```yaml
alias: Telegram Abfall-Erinnerung (weekly)
description: schickt mir Telegramm-Nachrichten wenn Abfall rauszustellen ist
triggers:
  - trigger: time
    at: "12:00:00"
    weekday:
      - sun
conditions: []
actions:
  - action: shell_command.garbage_day
    data:
      days: 7
    response_variable: script_ergebnis
  - condition: template
    value_template: "{{ '0 Events' not in script_ergebnis['stdout'] }}"
  - action: telegram_bot.send_message
    data:
      title: Abfallerinnerung (weekly)! 🚛
      message: "{{ script_ergebnis['stdout'] }}"
mode: single
```

works on my machine (tm)

