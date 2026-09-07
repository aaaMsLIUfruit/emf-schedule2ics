# Temporal Rules

## Week Expansion

For `weeks`, scripts compute:

```text
week_1_start_date or semester.start_date
+ (week - 1) * 7 days
+ weekday offset
```

If `semester.start_date` is not the first day used by the school calendar, add `semester.week_1_start_date`.

## Supported Week Expressions

Normalize these with `scripts/normalize_schedule.py`:

- `1-16周`
- `1~16周`
- `第1到16周`
- `1-15周单周`
- `2-16周双周`
- `1,3,5,7周`
- `第1、2、4、8周`
- `9月15日起每周` when semester dates and segment weekday are known

For vague recurrence such as "every two weeks" without a first date/week, mark unresolved.

## One-Off Classes

Use `absolute_date` time or a segment `dates` list:

```json
{
  "time": {"mode": "absolute_date", "date": "2026-09-15", "start": "19:00", "end": "20:30"}
}
```

## Updates and Replacements

When a notice says "from week 9 switch to Friday 16:00":

- keep the old segment for weeks 1-8
- add a new segment for weeks 9+
- preserve evidence from both sources

Do not delete the original segment unless the source explicitly says it was cancelled for those weeks.
