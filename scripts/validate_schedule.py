#!/usr/bin/env python3
"""Validate canonical schedule JSON and run deterministic audits."""

from __future__ import annotations

import argparse
import sys

from schedule_core import load_json, print_issues, validate_schedule


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schedule", help="Canonical schedule JSON")
    args = parser.parse_args()
    return print_issues(validate_schedule(load_json(args.schedule)))


if __name__ == "__main__":
    sys.exit(main())
