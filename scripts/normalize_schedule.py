#!/usr/bin/env python3
"""Normalize flexible extracted schedule JSON into canonical schedule JSON."""

from __future__ import annotations

import argparse
import sys

from schedule_core import cli_error, load_json, normalize_schedule, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Raw schedule JSON from Agent extraction")
    parser.add_argument("output", nargs="?", help="Canonical schedule JSON output path")
    args = parser.parse_args()
    try:
        normalized = normalize_schedule(load_json(args.input))
        if args.output:
            write_json(args.output, normalized)
        else:
            write_json("-", normalized)
        return 0
    except Exception as exc:
        return cli_error(exc)


if __name__ == "__main__":
    sys.exit(main())
