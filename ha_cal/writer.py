import re
import uuid
from datetime import date
from pathlib import Path

from icalendar import Calendar, Event as ICalEvent


def add_event(ical_path: Path, event_date: date, summary: str, description: str | None) -> None:
    """Append a new VEVENT to an existing .ics file."""
    with open(ical_path, "rb") as f:
        cal = Calendar.from_ical(f.read())

    event = ICalEvent()
    uid = f"{event_date.isoformat()}-{uuid.uuid4()}@ha-cal"
    event.add("UID", uid)
    event.add("SUMMARY", summary)
    event.add("DTSTART", event_date)
    event.add("DTEND", event_date)
    if description:
        event.add("DESCRIPTION", description)

    cal.add_component(event)

    with open(ical_path, "wb") as f:
        f.write(cal.to_ical())


def replace_in_field(ical_path: Path, field: str, pattern: str, replacement: str) -> int:
    """Apply regex search/replace to a field in all VEVENTs. Returns number of modified events."""
    compiled = re.compile(pattern, re.DOTALL)

    with open(ical_path, "rb") as f:
        cal = Calendar.from_ical(f.read())

    modified = 0
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        raw = component.get(field)
        if raw is None:
            continue
        original = str(raw)
        updated = compiled.sub(replacement, original).strip()
        if updated != original:
            del component[field]
            if updated:
                component.add(field, updated)
            modified += 1

    with open(ical_path, "wb") as f:
        f.write(cal.to_ical())

    return modified
