from datetime import date

from jinja2 import Environment

from ha_cal.calendar_reader import Event

_GERMAN_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}

_GERMAN_WEEKDAYS = {
    0: "Montag", 1: "Dienstag", 2: "Mittwoch", 3: "Donnerstag",
    4: "Freitag", 5: "Samstag", 6: "Sonntag",
}


def datefmt(d: date) -> str:
    return f"{d.day}. {_GERMAN_MONTHS[d.month]}"


def weekday(d: date) -> str:
    return _GERMAN_WEEKDAYS[d.weekday()]


def render(template_str: str, events: list[Event], days: int, next_event: Event | None) -> str:
    env = Environment()
    env.filters["datefmt"] = datefmt
    env.filters["weekday"] = weekday
    template = env.from_string(template_str)
    return template.render(events=events, days=days, next_event=next_event).strip()
