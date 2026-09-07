#!/usr/bin/env python3
"""Conservatively merge multiple canonical schedule JSON files."""

from __future__ import annotations

import argparse
import sys

from schedule_core import cli_error, load_json, merge_schedules, validate_schedule, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", help="Input schedule JSON files")
    parser.add_argument("--output", "-o", required=True, help="Merged schedule JSON path")
    args = parser.parse_args()
    try:
        merged = merge_schedules([load_json(path) for path in args.inputs])
        errors = [issue.message for issue in validate_schedule(merged) if issue.level == "error"]
        if errors:
            raise RuntimeError("merged schedule is invalid:\n- " + "\n- ".join(errors))
        write_json(args.output, merged)
        print("PASS")
        return 0
    except Exception as exc:
        return cli_error(exc)


if __name__ == "__main__":
    sys.exit(main())
