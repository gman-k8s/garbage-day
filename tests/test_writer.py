import pytest
from datetime import date
from icalendar import Calendar
from ha_cal.writer import add_event

EMPTY_CAL = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ha_cal//ha_cal//EN
END:VCALENDAR"""

@pytest.fixture
def cal_file(tmp_path):
    f = tmp_path / "cal.ics"
    f.write_bytes(EMPTY_CAL)
    return f

def test_add_event_appears_in_file(cal_file):
    add_event(cal_file, date(2026, 6, 22), "Gelbe Tonne", None)
    content = cal_file.read_bytes()
    assert b"Gelbe Tonne" in content

def test_add_event_date_stored(cal_file):
    add_event(cal_file, date(2026, 6, 22), "Gelbe Tonne", None)
    with open(cal_file, "rb") as f:
        cal = Calendar.from_ical(f.read())
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 1
    assert events[0].get("DTSTART").dt == date(2026, 6, 22)

def test_add_event_with_description(cal_file):
    add_event(cal_file, date(2026, 6, 22), "Gelbe Tonne", "An die Strasse stellen")
    content = cal_file.read_bytes()
    assert b"An die Strasse" in content

def test_add_event_without_description(cal_file):
    add_event(cal_file, date(2026, 6, 22), "Gelbe Tonne", None)
    with open(cal_file, "rb") as f:
        cal = Calendar.from_ical(f.read())
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert events[0].get("DESCRIPTION") is None

def test_add_event_has_uid(cal_file):
    add_event(cal_file, date(2026, 6, 22), "Gelbe Tonne", None)
    with open(cal_file, "rb") as f:
        cal = Calendar.from_ical(f.read())
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    uid = str(events[0].get("UID"))
    assert "2026-06-22" in uid
    assert "@ha-cal" in uid

def test_add_multiple_events_both_present(cal_file):
    add_event(cal_file, date(2026, 6, 22), "Gelbe Tonne", None)
    add_event(cal_file, date(2026, 6, 29), "Blaue Tonne", None)
    with open(cal_file, "rb") as f:
        cal = Calendar.from_ical(f.read())
    events = [c for c in cal.walk() if c.name == "VEVENT"]
    assert len(events) == 2
