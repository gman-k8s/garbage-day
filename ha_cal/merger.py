from pathlib import Path

from icalendar import Calendar


def _get_uid(component) -> str | None:
    """Return the UID of a calendar component, or None if absent."""
    raw = component.get("UID")
    return str(raw) if raw is not None else None


def merge(main_path: Path, city_path: Path) -> tuple[int, int]:
    """Merge events from city_path into main_path. Returns (added, skipped)."""
    with open(main_path, "rb") as f:
        main_cal = Calendar.from_ical(f.read())
    with open(city_path, "rb") as f:
        city_cal = Calendar.from_ical(f.read())

    existing_uids = {
        uid
        for c in main_cal.walk()
        if c.name == "VEVENT" and (uid := _get_uid(c)) is not None
    }

    added = 0
    skipped = 0
    for component in city_cal.walk():
        if component.name != "VEVENT":
            continue
        uid = _get_uid(component)
        if uid is None:
            continue  # skip malformed event with no UID
        if uid in existing_uids:
            skipped += 1
        else:
            main_cal.add_component(component)
            existing_uids.add(uid)
            added += 1

    with open(main_path, "wb") as f:
        f.write(main_cal.to_ical())

    return added, skipped
