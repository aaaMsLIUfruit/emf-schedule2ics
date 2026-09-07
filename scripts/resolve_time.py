#!/usr/bin/env python3
"""Expand canonical schedule JSON into dated occurrences for inspection."""

from __future__ import annotations

import argparse
import sys

from schedule_core import cli_error, expected_occurrences, load_json, normalize_schedule, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schedule", help="Canonical schedule JSON")
    parser.add_argument("output", nargs="?", help="Output occurrences JSON")
    args = parser.parse_args()
    try:
        data = normalize_schedule(load_json(args.schedule))
        result = {"occurrences": expected_occurrences(data)}
        if args.output:
            write_json(args.output, result)
        else:
            write_json("-", result)
        return 0
    except Exception as exc:
        return cli_error(exc)


if __name__ == "__main__":
    sys.exit(main())
