# Audit Protocol

Completeness is more important than elegance.

## Visual Candidate Count

For each grid source, record candidate counts:

```text
Monday: 4
Tuesday: 3
Wednesday: 5
Thursday: 3
Friday: 4
```

If visual regions outnumber matched extracted blocks, do not silently pass.

## Occupancy Map

Represent each visual region as weekday plus period range. The validator compares visual candidates to period-mode schedule occupancy.

If the visual audit says Thursday P3-P4 contains a course and no event covers it, validation fails.

## Coverage

Every visual candidate must either:

- match one or more event IDs in `matched_event_ids`
- be covered by schedule occupancy
- be marked `classification: "non_course"`

## Localized Recovery

When audit fails:

1. Locate the missing candidate by `source_id`, weekday, and period range.
2. Inspect only that area.
3. Add or correct the event/segment.
4. Rerun `validate_schedule.py`.

Avoid re-extracting the whole table unless the layout pass itself was wrong.
