#!/usr/bin/env python3
"""Deterministic schedule utilities for EMF-schedule2ics."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None  # type: ignore
    ZoneInfoNotFoundError = Exception  # type: ignore


WEEKDAY_MIN = 1
WEEKDAY_MAX = 7
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ScheduleError(Exception):
    """Raised for deterministic schedule failures."""


@dataclass(frozen=True)
class Issue:
    level: str
    message: str


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ScheduleError(f"{path} must contain a JSON object")
    return data


def write_json(path: str | Path, data: Any) -> None:
    if str(path) == "-":
        json.dump(data, sys.stdout, ensure_ascii=False, indent=2, sort_keys=False)
        sys.stdout.write("\n")
        return
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")


def parse_date(value: str, field: str = "date") -> date:
    if not isinstance(value, str) or not DATE_RE.match(value):
        raise ScheduleError(f"{field} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ScheduleError(f"{field} is not a valid date: {value}") from exc


def parse_time(value: str, field: str = "time") -> time:
    if not isinstance(value, str) or not TIME_RE.match(value):
        raise ScheduleError(f"{field} must be HH:MM")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ScheduleError(f"{field} is not a valid time: {value}") from exc


def parse_datetime_local(day: date, value: str) -> datetime:
    return datetime.combine(day, parse_time(value))


def iso_date(day: date) -> str:
    return day.isoformat()


def normalize_schedule(raw: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(raw)
    data.setdefault("schema_version", "1.0")
    data.setdefault("semester", {})
    data.setdefault("periods", [])
    data.setdefault("sources", [])
    data.setdefault("events", [])

    for event_index, event in enumerate(data["events"], start=1):
        event.setdefault("id", f"event_{event_index:03d}")
        if "segments" not in event:
            segment: dict[str, Any] = {}
            if "time" in event:
                segment["time"] = event.pop("time")
            elif {"weekday", "start_period", "end_period"} <= event.keys():
                segment["time"] = {
                    "mode": "period",
                    "weekday": event.pop("weekday"),
                    "start_period": event.pop("start_period"),
                    "end_period": event.pop("end_period"),
                }
            elif {"weekday", "start", "end"} <= event.keys():
                segment["time"] = {
                    "mode": "absolute",
                    "weekday": event.pop("weekday"),
                    "start": event.pop("start"),
                    "end": event.pop("end"),
                }
            for key in ("weeks", "dates", "week_expression", "recurrence", "evidence", "location", "instructor", "description"):
                if key in event:
                    segment[key] = event.pop(key)
            event["segments"] = [segment] if segment else []

        for segment_index, segment in enumerate(event.get("segments", []), start=1):
            segment.setdefault("id", f"{event['id']}_seg_{segment_index:03d}")
            if "time" not in segment:
                if {"weekday", "start_period", "end_period"} <= segment.keys():
                    segment["time"] = {
                        "mode": "period",
                        "weekday": segment.pop("weekday"),
                        "start_period": segment.pop("start_period"),
                        "end_period": segment.pop("end_period"),
                    }
                elif {"weekday", "start", "end"} <= segment.keys():
                    segment["time"] = {
                        "mode": "absolute",
                        "weekday": segment.pop("weekday"),
                        "start": segment.pop("start"),
                        "end": segment.pop("end"),
                    }
                elif {"date", "start", "end"} <= segment.keys():
                    segment["time"] = {
                        "mode": "absolute_date",
                        "date": segment.pop("date"),
                        "start": segment.pop("start"),
                        "end": segment.pop("end"),
                    }
            expr = segment.get("week_expression")
            if expr and "weeks" not in segment and "dates" not in segment:
                parsed = parse_week_expression(
                    str(expr),
                    semester=data.get("semester", {}),
                    weekday=segment.get("time", {}).get("weekday"),
                )
                segment.update(parsed)
    return data


def parse_week_expression(expression: str, semester: dict[str, Any] | None = None, weekday: int | None = None) -> dict[str, Any]:
    text = normalize_digits(expression).strip()
    text = text.replace(" ", "")
    odd = any(marker in text for marker in ("单", "odd"))
    even = any(marker in text for marker in ("双", "even"))

    start_date_match = re.search(r"(?P<month>\d{1,2})月(?P<day>\d{1,2})日?起每周", text)
    if start_date_match:
        if not semester or not semester.get("start_date") or not semester.get("end_date") or not weekday:
            return {"unresolved": {"reason": "Date-based weekly expression needs semester dates and segment weekday", "expression": expression}}
        year = parse_date(semester["start_date"], "semester.start_date").year
        start_day = date(year, int(start_date_match.group("month")), int(start_date_match.group("day")))
        end_day = parse_date(semester["end_date"], "semester.end_date")
        dates = []
        current = start_day
        while current.isoweekday() != int(weekday):
            current += timedelta(days=1)
        while current <= end_day:
            dates.append(iso_date(current))
            current += timedelta(days=7)
        return {"dates": dates}

    text = text.replace("Weeks", "").replace("Week", "").replace("weeks", "").replace("week", "")
    text = text.replace("第", "").replace("周", "")
    text_for_numbers = text.replace("单", "").replace("双", "").replace("odd", "").replace("even", "")
    numbers = [int(n) for n in re.findall(r"\d+", text_for_numbers)]
    if not numbers:
        return {"unresolved": {"reason": "Could not parse week expression", "expression": expression}}

    if any(sep in text_for_numbers for sep in ("-", "~", "到", "至")) and len(numbers) >= 2:
        start, end = numbers[0], numbers[1]
        if end < start:
            return {"unresolved": {"reason": "Week range end is before start", "expression": expression}}
        weeks = list(range(start, end + 1))
    else:
        weeks = numbers

    if odd:
        weeks = [week for week in weeks if week % 2 == 1]
    if even:
        weeks = [week for week in weeks if week % 2 == 0]
    return {"weeks": sorted(dict.fromkeys(weeks))}


def normalize_digits(text: str) -> str:
    table = str.maketrans("０１２３４５６７８９，、；：－～", "0123456789,,;:-~")
    return text.translate(table)


def period_map(schedule: dict[str, Any]) -> dict[int, tuple[str, str]]:
    result = {}
    for period in schedule.get("periods", []):
        idx = int(period["index"])
        result[idx] = (period["start"], period["end"])
    return result


def semester_week_one_start(semester: dict[str, Any]) -> date:
    if semester.get("week_1_start_date"):
        return parse_date(semester["week_1_start_date"], "semester.week_1_start_date")
    return parse_date(semester["start_date"], "semester.start_date")


def date_for_weekday(semester: dict[str, Any], week: int, weekday: int) -> date:
    anchor = semester_week_one_start(semester)
    return anchor + timedelta(days=(int(week) - 1) * 7 + (int(weekday) - anchor.isoweekday()))


def all_weeks_for_semester(semester: dict[str, Any], weekday: int) -> list[int]:
    start = parse_date(semester["start_date"], "semester.start_date")
    end = parse_date(semester["end_date"], "semester.end_date")
    anchor = semester_week_one_start(semester)
    weeks = []
    week = 1
    while True:
        day = date_for_weekday(semester, week, weekday)
        if day > end:
            break
        if day >= start:
            weeks.append(week)
        week += 1
        if week > 80:
            raise ScheduleError("semester produces more than 80 weeks")
    if not weeks and anchor <= end:
        return [1]
    return weeks


def segment_dates(schedule: dict[str, Any], segment: dict[str, Any]) -> list[date]:
    time_info = segment.get("time", {})
    if segment.get("dates"):
        return [parse_date(item, "segment.dates[]") for item in segment["dates"]]
    if time_info.get("mode") == "absolute_date":
        return [parse_date(time_info["date"], "time.date")]
    weekday = time_info.get("weekday")
    if not weekday:
        raise ScheduleError(f"segment {segment.get('id', '<unknown>')} has no weekday or dates")
    semester = schedule.get("semester", {})
    weeks = segment.get("weeks")
    if not weeks:
        weeks = all_weeks_for_semester(semester, int(weekday))
    return [date_for_weekday(semester, int(week), int(weekday)) for week in weeks]


def resolve_segment_time(schedule: dict[str, Any], segment: dict[str, Any]) -> tuple[str, str]:
    time_info = segment.get("time", {})
    mode = time_info.get("mode")
    if mode == "period":
        periods = period_map(schedule)
        start_period = int(time_info["start_period"])
        end_period = int(time_info["end_period"])
        if start_period not in periods:
            raise ScheduleError(f"unknown start_period {start_period}")
        if end_period not in periods:
            raise ScheduleError(f"unknown end_period {end_period}")
        return periods[start_period][0], periods[end_period][1]
    if mode in ("absolute", "absolute_date"):
        return time_info["start"], time_info["end"]
    raise ScheduleError(f"segment {segment.get('id', '<unknown>')} has unresolved time")


def expected_occurrences(schedule: dict[str, Any]) -> list[dict[str, Any]]:
    occurrences = []
    semester = schedule.get("semester", {})
    semester_start = parse_date(semester["start_date"], "semester.start_date")
    semester_end = parse_date(semester["end_date"], "semester.end_date")
    for event in schedule.get("events", []):
        for segment in event.get("segments", []):
            if segment.get("time", {}).get("mode") == "unresolved" or segment.get("unresolved"):
                raise ScheduleError(f"segment {segment.get('id', '<unknown>')} is unresolved")
            start_text, end_text = resolve_segment_time(schedule, segment)
            for day in segment_dates(schedule, segment):
                if day < semester_start or day > semester_end:
                    continue
                start_dt = parse_datetime_local(day, start_text)
                end_dt = parse_datetime_local(day, end_text)
                if end_dt <= start_dt:
                    raise ScheduleError(f"event {event.get('id')} segment {segment.get('id')} end <= start")
                location = segment.get("location", event.get("location", ""))
                instructor = segment.get("instructor", event.get("instructor", ""))
                description_parts = []
                if event.get("description"):
                    description_parts.append(str(event["description"]))
                if segment.get("description"):
                    description_parts.append(str(segment["description"]))
                evidence = segment.get("evidence", event.get("evidence", []))
                if evidence:
                    source_ids = [str(item.get("source_id", "")) for item in evidence if isinstance(item, dict) and item.get("source_id")]
                    if source_ids:
                        description_parts.append("Sources: " + ", ".join(dict.fromkeys(source_ids)))
                occurrence = {
                    "event_id": event.get("id", ""),
                    "segment_id": segment.get("id", ""),
                    "title": str(event.get("title", "")).strip(),
                    "location": str(location).strip(),
                    "instructor": str(instructor).strip(),
                    "description": "\n".join(description_parts).strip(),
                    "date": iso_date(day),
                    "start": start_dt.strftime("%H:%M"),
                    "end": end_dt.strftime("%H:%M"),
                    "timezone": semester.get("timezone", "UTC"),
                }
                occurrence["uid"] = stable_uid(occurrence)
                occurrences.append(occurrence)
    occurrences.sort(key=lambda item: (item["date"], item["start"], item["end"], item["title"], item["uid"]))
    return occurrences


def stable_uid(occurrence: dict[str, Any]) -> str:
    base = "|".join(
        str(occurrence.get(key, ""))
        for key in ("title", "date", "start", "end", "location", "event_id", "segment_id")
    )
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]
    return f"{digest}@emf-schedule2ics"


def validate_schedule(schedule: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    try:
        schedule = normalize_schedule(schedule)
    except Exception as exc:
        return [Issue("error", f"normalization failed: {exc}")]

    issues.extend(json_schema_issues(schedule))

    semester = schedule.get("semester", {})
    for field in ("start_date", "end_date", "timezone"):
        if not semester.get(field):
            issues.append(Issue("error", f"semester.{field} is required"))
    if semester.get("timezone"):
        if ZoneInfo is not None:
            try:
                ZoneInfo(str(semester["timezone"]))
            except ZoneInfoNotFoundError:
                issues.append(Issue("warning", f"semester.timezone is not recognized by Python zoneinfo: {semester['timezone']}"))
    if semester.get("start_date") and semester.get("end_date"):
        try:
            if parse_date(semester["end_date"], "semester.end_date") < parse_date(semester["start_date"], "semester.start_date"):
                issues.append(Issue("error", "semester.end_date is before semester.start_date"))
        except ScheduleError as exc:
            issues.append(Issue("error", str(exc)))

    seen_periods = set()
    for period in schedule.get("periods", []):
        try:
            idx = int(period.get("index"))
            if idx in seen_periods:
                issues.append(Issue("error", f"duplicate period index {idx}"))
            seen_periods.add(idx)
            start = parse_time(period.get("start", ""), f"period {idx}.start")
            end = parse_time(period.get("end", ""), f"period {idx}.end")
            if end <= start:
                issues.append(Issue("error", f"period {idx} end <= start"))
        except Exception as exc:
            issues.append(Issue("error", f"invalid period entry: {exc}"))

    event_ids = set()
    for event in schedule.get("events", []):
        event_id = str(event.get("id", ""))
        if not event.get("title"):
            issues.append(Issue("error", f"{event_id or '<missing id>'} title is required"))
        if event_id:
            if event_id in event_ids:
                issues.append(Issue("error", f"duplicate event id {event_id}"))
            event_ids.add(event_id)
        if not event.get("segments"):
            issues.append(Issue("error", f"{event_id or event.get('title', '<event>')} has no segments"))
        for segment in event.get("segments", []):
            try:
                issues.extend(validate_segment(schedule, event, segment))
            except Exception as exc:
                issues.append(Issue("error", f"{event_id}/{segment.get('id', '<segment>')} validation failed: {exc}"))

    issues.extend(audit_visual_coverage(schedule))
    issues.extend(conflict_warnings(schedule))
    return issues


def json_schema_issues(schedule: dict[str, Any]) -> list[Issue]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return []
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "schedule.schema.json"
    if not schema_path.exists():
        return [Issue("warning", f"schema file not found: {schema_path}")]
    try:
        schema = load_json(schema_path)
        validator_cls = getattr(jsonschema, "Draft202012Validator", None) or getattr(jsonschema, "Draft7Validator", None)
        if validator_cls is None:
            return [Issue("warning", "schema validation skipped: no supported jsonschema validator")]
        validator = validator_cls(schema)
        return [
            Issue("error", f"schema {'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}")
            for error in sorted(validator.iter_errors(schedule), key=lambda err: list(err.path))
        ]
    except Exception as exc:
        return [Issue("warning", f"schema validation skipped: {exc}")]


def validate_segment(schedule: dict[str, Any], event: dict[str, Any], segment: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    event_id = event.get("id", event.get("title", "<event>"))
    segment_id = segment.get("id", "<segment>")
    time_info = segment.get("time", {})
    mode = time_info.get("mode")
    if segment.get("unresolved"):
        issues.append(Issue("error", f"{event_id}/{segment_id} has unresolved data: {segment.get('unresolved')}"))
    if mode == "unresolved":
        issues.append(Issue("error", f"{event_id}/{segment_id} has unresolved time: {time_info.get('expression', '')}"))
        return issues
    if mode == "period":
        for key in ("weekday", "start_period", "end_period"):
            if key not in time_info:
                issues.append(Issue("error", f"{event_id}/{segment_id} time.{key} is required"))
        if not issues:
            weekday = int(time_info["weekday"])
            if weekday < WEEKDAY_MIN or weekday > WEEKDAY_MAX:
                issues.append(Issue("error", f"{event_id}/{segment_id} weekday must be 1..7"))
            if int(time_info["end_period"]) < int(time_info["start_period"]):
                issues.append(Issue("error", f"{event_id}/{segment_id} end_period < start_period"))
            periods = period_map(schedule)
            if int(time_info["start_period"]) not in periods or int(time_info["end_period"]) not in periods:
                issues.append(Issue("error", f"{event_id}/{segment_id} references missing period table rows"))
    elif mode == "absolute":
        for key in ("weekday", "start", "end"):
            if key not in time_info:
                issues.append(Issue("error", f"{event_id}/{segment_id} time.{key} is required"))
        if not issues:
            if int(time_info["weekday"]) < WEEKDAY_MIN or int(time_info["weekday"]) > WEEKDAY_MAX:
                issues.append(Issue("error", f"{event_id}/{segment_id} weekday must be 1..7"))
            if parse_time(time_info["end"], "time.end") <= parse_time(time_info["start"], "time.start"):
                issues.append(Issue("error", f"{event_id}/{segment_id} end <= start"))
    elif mode == "absolute_date":
        for key in ("date", "start", "end"):
            if key not in time_info:
                issues.append(Issue("error", f"{event_id}/{segment_id} time.{key} is required"))
        if not issues:
            parse_date(time_info["date"], "time.date")
            if parse_time(time_info["end"], "time.end") <= parse_time(time_info["start"], "time.start"):
                issues.append(Issue("error", f"{event_id}/{segment_id} end <= start"))
    else:
        issues.append(Issue("error", f"{event_id}/{segment_id} unsupported time mode {mode!r}"))

    for week in segment.get("weeks", []):
        try:
            if int(week) <= 0:
                issues.append(Issue("error", f"{event_id}/{segment_id} invalid week {week}"))
        except Exception:
            issues.append(Issue("error", f"{event_id}/{segment_id} invalid week {week}"))
    for item in segment.get("dates", []):
        try:
            parse_date(item, "segment.dates[]")
        except ScheduleError as exc:
            issues.append(Issue("error", f"{event_id}/{segment_id} {exc}"))
    if schedule.get("semester", {}).get("start_date") and schedule.get("semester", {}).get("end_date"):
        try:
            semester_start = parse_date(schedule["semester"]["start_date"], "semester.start_date")
            semester_end = parse_date(schedule["semester"]["end_date"], "semester.end_date")
            for day in segment_dates(schedule, segment):
                if day < semester_start or day > semester_end:
                    issues.append(Issue("error", f"{event_id}/{segment_id} resolves outside semester: {day.isoformat()}"))
        except Exception as exc:
            issues.append(Issue("error", f"{event_id}/{segment_id} date expansion failed: {exc}"))
    return issues


def audit_visual_coverage(schedule: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    candidates = schedule.get("audit", {}).get("visual_candidates", [])
    if not candidates:
        return issues
    schedule_cells: set[tuple[int, int]] = set()
    for event in schedule.get("events", []):
        for segment in event.get("segments", []):
            time_info = segment.get("time", {})
            if time_info.get("mode") != "period":
                continue
            for period in range(int(time_info["start_period"]), int(time_info["end_period"]) + 1):
                schedule_cells.add((int(time_info["weekday"]), period))

    for candidate in candidates:
        if candidate.get("classification", "course") != "course":
            continue
        matched = candidate.get("matched_event_ids") or []
        candidate_cells = {
            (int(candidate["weekday"]), period)
            for period in range(int(candidate["start_period"]), int(candidate["end_period"]) + 1)
        }
        if not matched and not candidate_cells <= schedule_cells:
            issues.append(
                Issue(
                    "error",
                    "visual candidate "
                    f"{candidate.get('id', '<unknown>')} is not covered by extracted schedule",
                )
            )
    return issues


def conflict_warnings(schedule: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    try:
        occurrences = expected_occurrences(schedule)
    except Exception:
        return issues

    for first_index, first in enumerate(occurrences):
        first_start = parse_datetime_local(parse_date(first["date"]), first["start"])
        first_end = parse_datetime_local(parse_date(first["date"]), first["end"])
        for second in occurrences[first_index + 1 :]:
            if second["date"] != first["date"]:
                continue
            second_start = parse_datetime_local(parse_date(second["date"]), second["start"])
            second_end = parse_datetime_local(parse_date(second["date"]), second["end"])
            same = (
                first["title"] == second["title"]
                and first["start"] == second["start"]
                and first["end"] == second["end"]
                and first["location"] == second["location"]
            )
            if same:
                issues.append(Issue("warning", f"possible duplicate event on {first['date']} {first['start']} {first['title']}"))
            elif max(first_start, second_start) < min(first_end, second_end):
                issues.append(
                    Issue(
                        "warning",
                        f"time overlap on {first['date']}: {first['title']} {first['start']}-{first['end']} "
                        f"and {second['title']} {second['start']}-{second['end']}",
                    )
                )
    return issues


def merge_schedules(schedules: list[dict[str, Any]]) -> dict[str, Any]:
    if not schedules:
        raise ScheduleError("at least one schedule is required")
    merged = copy.deepcopy(normalize_schedule(schedules[0]))
    merged.setdefault("sources", [])
    merged.setdefault("events", [])
    merged.setdefault("merge_report", {"warnings": []})

    source_ids = {source.get("source_id") for source in merged.get("sources", [])}
    event_by_key: dict[str, dict[str, Any]] = {event_key(event): event for event in merged["events"]}
    event_by_title: dict[str, dict[str, Any]] = {
        str(event.get("title", "")).strip().casefold(): event for event in merged["events"] if event.get("title")
    }

    for schedule in schedules[1:]:
        current = normalize_schedule(schedule)
        for field in ("start_date", "end_date", "timezone", "week_1_start_date"):
            incoming = current.get("semester", {}).get(field)
            existing = merged.get("semester", {}).get(field)
            if incoming and existing and incoming != existing:
                merged["merge_report"]["warnings"].append(f"semester.{field} differs: {existing} vs {incoming}")
            elif incoming and not existing:
                merged.setdefault("semester", {})[field] = incoming
        for period in current.get("periods", []):
            if period not in merged.get("periods", []):
                merged.setdefault("periods", []).append(period)
        for source in current.get("sources", []):
            source_id = source.get("source_id")
            if source_id not in source_ids:
                merged["sources"].append(source)
                source_ids.add(source_id)
        for event in current.get("events", []):
            title_key = str(event.get("title", "")).strip().casefold()
            if title_key in event_by_title:
                existing = event_by_title[title_key]
                for field in ("location", "instructor"):
                    incoming_value = str(event.get(field, "")).strip()
                    existing_value = str(existing.get(field, "")).strip()
                    if incoming_value and existing_value and incoming_value != existing_value:
                        merged["merge_report"]["warnings"].append(
                            f"{event.get('title')} {field} differs across sources: {existing_value} vs {incoming_value}"
                        )
            key = event_key(event)
            if key not in event_by_key:
                merged["events"].append(event)
                event_by_key[key] = event
                if title_key and title_key not in event_by_title:
                    event_by_title[title_key] = event
            else:
                target = event_by_key[key]
                target.setdefault("segments", [])
                segment_by_key = {segment_key(seg): seg for seg in target["segments"]}
                for seg in event.get("segments", []):
                    skey = segment_key(seg)
                    if skey in segment_by_key:
                        merge_evidence(segment_by_key[skey], seg)
                    else:
                        target["segments"].append(seg)
                        segment_by_key[skey] = seg
                merge_evidence(target, event)
    return normalize_schedule(merged)


def event_key(event: dict[str, Any]) -> str:
    return "|".join([str(event.get("title", "")).strip().casefold(), str(event.get("location", "")).strip().casefold()])


def segment_key(segment: dict[str, Any]) -> str:
    return json.dumps(
        {
            "time": segment.get("time"),
            "weeks": segment.get("weeks"),
            "dates": segment.get("dates"),
            "location": segment.get("location"),
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def merge_evidence(target: dict[str, Any], incoming: dict[str, Any]) -> None:
    existing = target.setdefault("evidence", [])
    existing_keys = {json.dumps(item, sort_keys=True, ensure_ascii=False) for item in existing}
    for item in incoming.get("evidence", []):
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in existing_keys:
            existing.append(item)
            existing_keys.add(key)


def ics_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")


def fold_ics_line(line: str) -> str:
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    chunks = []
    current = ""
    for char in line:
        candidate = current + char
        if len(candidate.encode("utf-8")) > 73:
            chunks.append(current)
            current = " " + char
        else:
            current = candidate
    if current:
        chunks.append(current)
    return "\r\n".join(chunks)


def build_ics(schedule: dict[str, Any]) -> str:
    schedule = normalize_schedule(schedule)
    errors = [issue.message for issue in validate_schedule(schedule) if issue.level == "error"]
    if errors:
        raise ScheduleError("schedule validation failed before ICS generation:\n- " + "\n- ".join(errors))
    tzid = schedule.get("semester", {}).get("timezone", "UTC")
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//EMF-schedule2ics//Course Schedule to ICS//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for occurrence in expected_occurrences(schedule):
        day = parse_date(occurrence["date"])
        start = parse_datetime_local(day, occurrence["start"]).strftime("%Y%m%dT%H%M%S")
        end = parse_datetime_local(day, occurrence["end"]).strftime("%Y%m%dT%H%M%S")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{occurrence['uid']}",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART;TZID={tzid}:{start}",
                f"DTEND;TZID={tzid}:{end}",
                f"SUMMARY:{ics_escape(occurrence['title'])}",
                f"LOCATION:{ics_escape(occurrence['location'])}",
            ]
        )
        description = occurrence.get("description")
        if occurrence.get("instructor"):
            description = (description + "\n" if description else "") + f"Instructor: {occurrence['instructor']}"
        if description:
            lines.append(f"DESCRIPTION:{ics_escape(description)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold_ics_line(line) for line in lines) + "\r\n"


def parse_ics(ics_text: str) -> list[dict[str, str]]:
    raw_lines = ics_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines: list[str] = []
    for raw in raw_lines:
        if not raw:
            continue
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    events = []
    current: dict[str, str] | None = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
        elif current is not None:
            key, _, value = line.partition(":")
            parts = key.split(";")
            prop = parts[0].upper()
            current[prop] = ics_unescape(value)
            for param in parts[1:]:
                name, sep, param_value = param.partition("=")
                if sep and name.upper() == "TZID":
                    current[f"{prop}_TZID"] = param_value
    return events


def ics_unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def ics_event_semantics(events: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    result = []
    for event in events:
        result.append(
            {
                "title": event.get("SUMMARY", ""),
                "location": event.get("LOCATION", ""),
                "date": parse_ics_datetime_date(event.get("DTSTART", "")),
                "start": parse_ics_datetime_time(event.get("DTSTART", "")),
                "end": parse_ics_datetime_time(event.get("DTEND", "")),
                "timezone": event.get("DTSTART_TZID", ""),
            }
        )
    result.sort(key=lambda item: (item["date"], item["start"], item["end"], item["title"], item["location"]))
    return result


def parse_ics_datetime_date(value: str) -> str:
    match = re.search(r"(\d{8})T\d{6}", value)
    if not match:
        return ""
    raw = match.group(1)
    return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"


def parse_ics_datetime_time(value: str) -> str:
    match = re.search(r"\d{8}T(\d{2})(\d{2})\d{2}", value)
    if not match:
        return ""
    return f"{match.group(1)}:{match.group(2)}"


def expected_semantics(schedule: dict[str, Any]) -> list[dict[str, str]]:
    result = [
        {
            "title": item["title"],
            "location": item["location"],
            "date": item["date"],
            "start": item["start"],
            "end": item["end"],
            "timezone": item["timezone"],
        }
        for item in expected_occurrences(normalize_schedule(schedule))
    ]
    result.sort(key=lambda item: (item["date"], item["start"], item["end"], item["title"], item["location"]))
    return result


def validate_ics_round_trip(schedule: dict[str, Any], ics_text: str) -> list[Issue]:
    expected = expected_semantics(schedule)
    actual = ics_event_semantics(parse_ics(ics_text))
    issues: list[Issue] = []
    if len(actual) != len(expected):
        issues.append(Issue("error", f"ICS event count {len(actual)} != expected {len(expected)}"))
    missing = [item for item in expected if item not in actual]
    extra = [item for item in actual if item not in expected]
    for item in missing[:20]:
        issues.append(Issue("error", f"missing ICS event: {item}"))
    for item in extra[:20]:
        issues.append(Issue("error", f"unexpected ICS event: {item}"))
    return issues


def print_issues(issues: list[Issue]) -> int:
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    if errors:
        print("FAIL")
        print()
        for issue in errors:
            print(f"- {issue.message}")
        for issue in warnings:
            print(f"WARNING: {issue.message}")
        return 1
    print("PASS")
    for issue in warnings:
        print(f"WARNING: {issue.message}")
    return 0


def cli_error(exc: Exception) -> int:
    print(f"ERROR: {exc}", file=sys.stderr)
    return 1


def add_common_json_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input", help="Input schedule JSON")
    parser.add_argument("output", nargs="?", help="Output JSON path")
