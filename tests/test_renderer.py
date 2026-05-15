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
