#!/usr/bin/env python3
"""Build calendar.ics from canonical schedule JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schedule_core import build_ics, cli_error, load_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", "-i", required=True, help="Canonical schedule JSON")
    parser.add_argument("--output", "-o", required=True, help="Output ICS path")
    args = parser.parse_args()
    try:
        ics_text = build_ics(load_json(args.input))
        Path(args.output).write_text(ics_text, encoding="utf-8")
        print(f"PASS: wrote {args.output}")
        return 0
    except Exception as exc:
        return cli_error(exc)


if __name__ == "__main__":
    sys.exit(main())
