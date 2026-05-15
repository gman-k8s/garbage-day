#!/usr/bin/env python3
import os
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_VENV_PYTHON = os.path.join(_SCRIPT_DIR, ".venv", "bin", "python3")

if not os.path.exists(_VENV_PYTHON):
    print(
        f"Error: .venv not found in {_SCRIPT_DIR}\n"
        f"Run: bash {os.path.join(_SCRIPT_DIR, 'setup_venv.sh')}",
        file=sys.stderr,
    )
    sys.exit(1)

_VENV_DIR = os.path.join(_SCRIPT_DIR, ".venv")
if sys.prefix != _VENV_DIR:
    os.execv(_VENV_PYTHON, [_VENV_PYTHON] + sys.argv)

# --- main logic below ---

import argparse
import uuid
from datetime import date, timedelta
from pathlib import Path

import holidays
from icalendar import Calendar, Event as ICalEvent

BUNDESLAENDER = {
    "BB": "Brandenburg", "BE": "Berlin", "BW": "Baden-Württemberg",
    "BY": "Bayern", "HB": "Bremen", "HE": "Hessen", "HH": "Hamburg",
    "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
    "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz",
    "SH": "Schleswig-Holstein", "SL": "Saarland", "SN": "Sachsen",
    "ST": "Sachsen-Anhalt", "TH": "Thüringen",
}

# Common alternative abbreviations → canonical code
_BL_ALIASES = {
    "RLP": "RP", "BAY": "BY", "NRW": "NW", "BAWUE": "BW", "BWÜ": "BW",
    "SAC": "SN", "SAT": "ST", "THUE": "TH", "MEC": "MV",
}


def _resolve_bundesland(value: str) -> str:
    code = value.strip().upper()
    code = _BL_ALIASES.get(code, code)
    if code not in BUNDESLAENDER:
        valid = ", ".join(sorted(BUNDESLAENDER.keys()))
        print(
            f"Error: unknown Bundesland {value!r}. Valid codes: {valid}\n"
            f"Known aliases: RLP=RP, BAY=BY, NRW=NW, BAWUE=BW, SAC=SN, SAT=ST, THUE=TH",
            file=sys.stderr,
        )
        sys.exit(1)
    return code

# Offset from ISO week's Monday (0=Monday … 6=Sunday)
WEEKDAY_OFFSET = {
    "montag": 0, "monday": 0,
    "dienstag": 1, "tuesday": 1,
    "mittwoch": 2, "wednesday": 2,
    "donnerstag": 3, "thursday": 3,
    "freitag": 4, "friday": 4,
    "samstag": 5, "saturday": 5,
    "sonntag": 6, "sunday": 6,
}

WEEKDAY_NAMES_DE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]


def _parse_weekday(value: str) -> int:
    key = value.strip().lower()
    if key not in WEEKDAY_OFFSET:
        valid = ", ".join(sorted({k for k in WEEKDAY_OFFSET if not k[0].isupper()}))
        print(f"Error: unknown weekday {value!r}. Valid: {valid}", file=sys.stderr)
        sys.exit(1)
    return WEEKDAY_OFFSET[key]


def _first_monday(year: int) -> date:
    jan1 = date(year, 1, 1)
    # weekday(): 0=Monday … 6=Sunday
    days_until_monday = (7 - jan1.weekday()) % 7
    return jan1 if jan1.weekday() == 0 else jan1 + timedelta(days=days_until_monday)


def _shift_past_holidays(day: date, public_holidays) -> date:
    """Advance day by 1 until it is not a public holiday."""
    while day in public_holidays:
        day += timedelta(days=1)
    return day


def generate(
    years: list[int],
    bundesland: str,
    odd_summary: str,
    even_summary: str,
    weekday_offset: int,
    output_path: Path,
) -> None:
    all_years = set(years) | {max(years) + 1}   # +1 so Dec holiday shift stays covered
    public_holidays = holidays.Germany(state=bundesland, years=all_years)

    cal = Calendar()
    cal.add("PRODID", "-//ha_cal//garbage-generator//EN")
    cal.add("VERSION", "2.0")
    cal.add("X-WR-CALNAME", "Müllkalender (generiert)")

    total = 0
    for year in sorted(years):
        monday = _first_monday(year)
        while monday.year == year:
            iso_week = monday.isocalendar()[1]
            summary = odd_summary if iso_week % 2 == 1 else even_summary

            planned_day = monday + timedelta(days=weekday_offset)
            collection_day = _shift_past_holidays(planned_day, public_holidays)

            event = ICalEvent()
            event.add("UID", f"{collection_day.isoformat()}-{uuid.uuid4()}@garbage-gen")
            event.add("SUMMARY", summary)
            event.add("DTSTART", collection_day)
            event.add("DTEND", collection_day + timedelta(days=1))
            if collection_day != planned_day:
                event.add(
                    "DESCRIPTION",
                    f"Verschoben wegen Feiertag "
                    f"(ursprünglich {WEEKDAY_NAMES_DE[planned_day.weekday()]}, "
                    f"{planned_day.strftime('%d.%m.%Y')})",
                )

            cal.add_component(event)
            total += 1
            monday += timedelta(weeks=1)

    output_path.write_bytes(cal.to_ical())
    print(f"Generiert: {total} Termine → {output_path}")


def main() -> None:
    bl_list = ", ".join(sorted(BUNDESLAENDER.keys()))
    parser = argparse.ArgumentParser(
        description="Generate iCal garbage collection schedule with German holiday support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Bundesland codes: {bl_list}",
    )
    parser.add_argument(
        "--year", required=True,
        help="Year(s) to generate, e.g. 2026 or 2026-2028",
    )
    parser.add_argument(
        "--bundesland", required=True,
        metavar="CODE",
        help=f"Federal state code or alias (e.g. RP, RLP, NW, NRW). Valid: {bl_list}",
    )
    parser.add_argument(
        "--odd-week", default="Graue Tonne (Restmüll)",
        metavar="TEXT",
        help="Summary for odd calendar weeks (default: 'Graue Tonne (Restmüll)')",
    )
    parser.add_argument(
        "--even-week", default="Braune Tonne (Biotonne)",
        metavar="TEXT",
        help="Summary for even calendar weeks (default: 'Braune Tonne (Biotonne)')",
    )
    parser.add_argument(
        "--weekday", default="montag",
        metavar="TAG",
        help="Collection weekday in German or English (default: montag)",
    )
    parser.add_argument(
        "--output", required=True, type=Path,
        metavar="PATH",
        help="Output .ics file path",
    )
    args = parser.parse_args()

    # Parse year range: "2026" or "2026-2028"
    try:
        if "-" in args.year and args.year.count("-") == 1:
            start, end = args.year.split("-")
            years = list(range(int(start), int(end) + 1))
        else:
            years = [int(args.year)]
    except ValueError:
        print(f"Error: --year must be a year (2026) or range (2026-2028), got: {args.year!r}", file=sys.stderr)
        sys.exit(1)

    if not years or any(y < 2000 or y > 2100 for y in years):
        print("Error: years must be between 2000 and 2100", file=sys.stderr)
        sys.exit(1)

    bundesland = _resolve_bundesland(args.bundesland)
    weekday_offset = _parse_weekday(args.weekday)
    generate(years, bundesland, args.odd_week, args.even_week, weekday_offset, args.output)


main()
