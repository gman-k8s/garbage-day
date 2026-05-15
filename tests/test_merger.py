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
