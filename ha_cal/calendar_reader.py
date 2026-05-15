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


def _to_date(dt: date | datetime) -> date:
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
        dtstart = component.get("DTSTART")
        if dtstart is None:
            continue
        event_date = _to_date(dtstart.dt)
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


def list_all_events(ical_path: Path) -> list[Event]:
    """Return all VEVENTs in the file sorted by date, without window filtering."""
    today = date.today()
    with open(ical_path, "rb") as f:
        cal = Calendar.from_ical(f.read())

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("DTSTART")
        if dtstart is None:
            continue
        event_date = _to_date(dtstart.dt)
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
    search_end = after + timedelta(days=730)
    events = read_events(ical_path, after + timedelta(days=1), search_end, today)
    return events[0] if events else None
