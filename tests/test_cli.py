import subprocess
import sys
from pathlib import Path
import pytest

ICAL_FUTURE = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
BEGIN:VEVENT
UID:future-001@test
SUMMARY:Gelbe Tonne
DTSTART;VALUE=DATE:20261201
DTEND;VALUE=DATE:20261202
END:VEVENT
END:VCALENDAR"""

CITY_ICAL = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//City//City//EN
BEGIN:VEVENT
UID:city-001@test
SUMMARY:City Event
DTSTART;VALUE=DATE:20261201
DTEND;VALUE=DATE:20261202
END:VEVENT
END:VCALENDAR"""

@pytest.fixture
def ical_file(tmp_path):
    f = tmp_path / "main.ics"
    f.write_bytes(ICAL_FUTURE)
    return f

@pytest.fixture
def city_file(tmp_path):
    f = tmp_path / "city.ics"
    f.write_bytes(CITY_ICAL)
    return f


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "ha_cal", *args],
        capture_output=True, text=True
    )


def test_missing_ical_file_exits_nonzero():
    result = run("--ical-file=/nonexistent.ics", "--output-text=x")
    assert result.returncode != 0

def test_both_output_flags_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--output-text=x", f"--template-file={ical_file}")
    assert result.returncode != 0

def test_no_events_in_window_prints_nothing(ical_file):
    # event is in 2099, window is 7d from today
    result = run(f"--ical-file={ical_file}", "--time=7d", "--output-text={{ events[0].summary if events else '' }}")
    assert result.returncode == 0
    assert result.stdout.strip() == ""

def test_no_template_no_events_prints_nothing(ical_file):
    # no --output-text, events are in 2099 so window is empty — nothing printed
    result = run(f"--ical-file={ical_file}", "--time=7d")
    assert result.returncode == 0
    assert result.stdout.strip() == ""

def test_invalid_ics_exits_nonzero(tmp_path):
    bad = tmp_path / "bad.ics"
    bad.write_text("this is not valid ical content")
    result = run(f"--ical-file={bad}", "--time=7d", "--output-text=x")
    assert result.returncode != 0
    assert result.stderr != ""

def test_template_render_error_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--time=7d", "--output-text={{ undefined_var.missing }}")
    assert result.returncode != 0

def test_merge_mode_prints_summary(ical_file, city_file):
    result = run(f"--ical-file={ical_file}", f"--merge={city_file}")
    assert result.returncode == 0
    assert "Importiert:" in result.stdout
    assert "1 neue Termine" in result.stdout

def test_template_file_flag(ical_file, tmp_path):
    tmpl = tmp_path / "msg.j2"
    tmpl.write_text("{% if next_event %}Nächster: {{ next_event.summary }}{% endif %}")
    result = run(f"--ical-file={ical_file}", "--time=7d", f"--template-file={tmpl}")
    assert result.returncode == 0
    assert "Gelbe Tonne" in result.stdout

def test_stderr_clean_on_success(ical_file):
    result = run(f"--ical-file={ical_file}", "--time=7d", "--output-text=ok")
    assert result.stderr == ""

def test_missing_template_file_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--time=7d", "--template-file=/nonexistent.j2")
    assert result.returncode != 0


def test_add_event_success(ical_file):
    result = run(
        f"--ical-file={ical_file}",
        "--add-date=2026-09-15",
        "--add-summary=Restmüll"
    )
    assert result.returncode == 0
    assert "Hinzugefügt" in result.stdout
    assert "Restmüll" in result.stdout

def test_add_event_with_description(ical_file):
    result = run(
        f"--ical-file={ical_file}",
        "--add-date=2026-09-15",
        "--add-summary=Restmüll",
        "--add-description=An die Strasse stellen"
    )
    assert result.returncode == 0
    assert "Hinzugefügt" in result.stdout

def test_add_date_without_summary_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--add-date=2026-09-15")
    assert result.returncode != 0

def test_add_summary_without_date_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--add-summary=Restmüll")
    assert result.returncode != 0

def test_add_invalid_date_exits_nonzero(ical_file):
    result = run(f"--ical-file={ical_file}", "--add-date=not-a-date", "--add-summary=Restmüll")
    assert result.returncode != 0
