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


ICAL_DATETIME_EVENT = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:dt-001@test
SUMMARY:Datetime Event
DTSTART:20260601T090000Z
DTEND:20260601T100000Z
END:VEVENT
END:VCALENDAR"""

def test_datetime_event_truncated_to_date(tmp_path):
    f = tmp_path / "dt.ics"
    f.write_bytes(ICAL_DATETIME_EVENT)
    events = read_events(f, date(2026, 6, 1), date(2026, 6, 7), today=date(2026, 6, 1))
    assert len(events) == 1
    assert events[0].date == date(2026, 6, 1)


ICAL_WITH_DESCRIPTION = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:desc-001@test
SUMMARY:Tonne mit Beschreibung
DESCRIPTION:Bitte an die Strasse stellen
DTSTART;VALUE=DATE:20260601
DTEND;VALUE=DATE:20260602
END:VEVENT
END:VCALENDAR"""

def test_description_captured(tmp_path):
    f = tmp_path / "desc.ics"
    f.write_bytes(ICAL_WITH_DESCRIPTION)
    events = read_events(f, date(2026, 6, 1), date(2026, 6, 7), today=date(2026, 6, 1))
    assert events[0].description == "Bitte an die Strasse stellen"

def test_description_none_when_absent(ical_file):
    events = read_events(ical_file, date(2026, 6, 1), date(2026, 6, 7), today=date(2026, 6, 1))
    assert events[0].description is None
