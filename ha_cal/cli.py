import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

from ha_cal.calendar_reader import read_events, find_next_event, list_all_events
from ha_cal.merger import merge
from ha_cal.renderer import render, datefmt, weekday as weekday_name
from ha_cal.writer import add_event, replace_in_field


def _parse_days(time_str: str) -> int:
    if not time_str.endswith("d") or not time_str[:-1].isdigit():
        print(f"Error: --time must be in format Nd (e.g. 7d), got: {time_str!r}", file=sys.stderr)
        sys.exit(1)
    return int(time_str[:-1])


def main():
    parser = argparse.ArgumentParser(description="Calendar reminder for Home Assistant")
    parser.add_argument("--ical-file", required=True, type=Path, metavar="PATH")
    parser.add_argument("--time", default="7d", metavar="Nd")
    parser.add_argument("--output-events", type=int, default=1, metavar="N")
    parser.add_argument("--output-text", default=None, metavar="TEMPLATE")
    parser.add_argument("--template-file", type=Path, default=None, metavar="PATH")
    parser.add_argument("--merge", type=Path, default=None, dest="merge_file", metavar="PATH")
    parser.add_argument("--list-all", action="store_true", help="Print all events in the file and exit")
    parser.add_argument("--replace-in-field", default=None, metavar="FIELD", help="iCal field to search in (e.g. DESCRIPTION, SUMMARY)")
    parser.add_argument("--search", default=None, metavar="REGEX", help="Regex pattern to search for")
    parser.add_argument("--replace", default=None, metavar="TEXT", help="Replacement text (empty string to remove)")
    parser.add_argument("--add-date", default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--add-summary", default=None, metavar="TEXT")
    parser.add_argument("--add-description", default=None, metavar="TEXT")
    args = parser.parse_args()

    if not args.ical_file.exists():
        print(f"Error: {args.ical_file} not found", file=sys.stderr)
        sys.exit(1)

    if args.list_all:
        try:
            events = list_all_events(args.ical_file)
        except Exception as exc:
            print(f"Error parsing {args.ical_file}: {exc}", file=sys.stderr)
            sys.exit(1)
        for e in events:
            kw = e.date.isocalendar()[1]
            desc = f"  [{e.description}]" if e.description else ""
            print(f"{e.date}  KW{kw:02}  {weekday_name(e.date):<12}{e.summary}{desc}")
        return

    # Replace mode
    if args.replace_in_field or args.search or args.replace is not None:
        if not (args.replace_in_field and args.search and args.replace is not None):
            print("Error: --replace-in-field, --search and --replace must all be provided together", file=sys.stderr)
            sys.exit(1)
        try:
            count = replace_in_field(args.ical_file, args.replace_in_field, args.search, args.replace)
        except re.error as exc:
            print(f"Error: invalid regex pattern: {exc}", file=sys.stderr)
            sys.exit(1)
        print(f"Ersetzt: {count} Termin(e) aktualisiert")
        return

    # Add mode
    has_add_date = args.add_date is not None
    has_add_summary = args.add_summary is not None
    if has_add_date or has_add_summary or args.add_description:
        if not (has_add_date and has_add_summary):
            print("Error: --add-date and --add-summary must both be provided", file=sys.stderr)
            sys.exit(1)
        try:
            event_date = date.fromisoformat(args.add_date)
        except ValueError:
            print(f"Error: --add-date must be YYYY-MM-DD, got: {args.add_date!r}", file=sys.stderr)
            sys.exit(1)
        add_event(args.ical_file, event_date, args.add_summary, args.add_description)
        print(f"Hinzugefügt: {args.add_summary} am {datefmt(event_date)}")
        return

    if args.merge_file:
        if not args.merge_file.exists():
            print(f"Error: {args.merge_file} not found", file=sys.stderr)
            sys.exit(1)
        added, skipped = merge(args.ical_file, args.merge_file)
        print(f"Importiert: {added} neue Termine, {skipped} übersprungen (bereits vorhanden)")
        return

    if args.output_text and args.template_file:
        print("Error: --output-text and --template-file are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    days = _parse_days(args.time)
    today = date.today()
    start = today
    end = today + timedelta(days=days)

    try:
        events = read_events(args.ical_file, start, end, today)[: args.output_events]
    except Exception as exc:
        print(f"Error parsing {args.ical_file}: {exc}", file=sys.stderr)
        sys.exit(1)

    next_event = None
    if not events:
        next_event = find_next_event(args.ical_file, end, today)

    if args.template_file:
        if not args.template_file.exists():
            print(f"Error: {args.template_file} not found", file=sys.stderr)
            sys.exit(1)
        template_str = args.template_file.read_text()
    elif args.output_text:
        template_str = args.output_text
    else:
        for event in events:
            print(event.summary)
        return

    try:
        result = render(template_str, events, days, next_event)
    except Exception as exc:
        print(f"Error rendering template: {exc}", file=sys.stderr)
        sys.exit(1)
    if result:
        print(result)
