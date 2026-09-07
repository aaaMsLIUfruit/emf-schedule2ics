#!/usr/bin/env python3
"""Round-trip validate calendar.ics against canonical schedule JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schedule_core import load_json, print_issues, validate_ics_round_trip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", "-s", required=True, help="Canonical schedule JSON")
    parser.add_argument("--ics", "-i", required=True, help="ICS file to validate")
    args = parser.parse_args()
    schedule = load_json(args.schedule)
    ics_text = Path(args.ics).read_text(encoding="utf-8")
    return print_issues(validate_ics_round_trip(schedule, ics_text))


if __name__ == "__main__":
    sys.exit(main())
