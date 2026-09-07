# Canonical Schedule Schema

Read `schemas/schedule.schema.json` for the formal JSON Schema.

## Weekday Convention

Use ISO weekday numbers:

- 1 Monday
- 2 Tuesday
- 3 Wednesday
- 4 Thursday
- 5 Friday
- 6 Saturday
- 7 Sunday

## Semester

Required fields:

```json
{
  "start_date": "2026-09-07",
  "end_date": "2027-01-10",
  "timezone": "Asia/Shanghai"
}
```

Optional `week_1_start_date` controls week numbering. If omitted, scripts use `semester.start_date` as the week 1 anchor. Add `week_1_start_date` when the school defines week 1 as starting on a different date.

## Periods

Use period rows only for deterministic time conversion:

```json
{"index": 3, "start": "10:10", "end": "10:55"}
```

Grid course blocks should point to periods:

```json
{"mode": "period", "weekday": 3, "start_period": 3, "end_period": 4}
```

## Events and Segments

One course can have many segments. Use separate segments for different weeks, dates, rooms, instructors, or times.

Segment recurrence should prefer:

- `weeks`: numbered semester weeks
- `dates`: explicit ISO dates
- `week_expression`: raw expression to normalize when safe

Do not put long OCR text in ICS. Keep short source evidence in JSON.
