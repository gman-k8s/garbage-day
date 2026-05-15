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

# Re-exec with venv interpreter if not already running inside it
if sys.prefix != _VENV_DIR:
    os.execv(_VENV_PYTHON, [_VENV_PYTHON] + sys.argv)

from ha_cal.cli import main
main()
