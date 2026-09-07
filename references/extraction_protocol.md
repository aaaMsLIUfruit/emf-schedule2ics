# Extraction Protocol

## Source IDs

Assign deterministic IDs before extraction:

- `pdf_page_001`
- `pdf_page_002`
- `screenshot_01`
- `notice_01`
- `syllabus_01`

Use these IDs in `sources`, segment `evidence`, and visual audit candidates.

## Grid/Table Sources

Use four passes.

Pass A: layout and time axis

- Identify weekday columns.
- Identify period rows.
- Extract period index, start time, and end time.
- Record uncertain time rows as unresolved; do not guess.

Pass B: visual occupancy

- Scan Monday to Sunday, top to bottom.
- Count non-empty course-like regions.
- Record `weekday`, `start_period`, `end_period`, and a candidate ID.
- Focus on completeness, not course text.

Pass C: semantic reading

- Read each candidate region.
- Extract title, instructor, room, weeks, notes.
- Attach evidence with `source_id` and candidate/region description.

Pass D: independent audit

- Rescan the whole source without looking only at the extracted events.
- Compare candidate counts, period occupancy, and coverage.
- Every course-like visual candidate must match an event or be marked `non_course`.

## Text Sources

Extract semantic events directly when text includes full time information, for example:

```json
{
  "title": "Corporate Finance",
  "location": "Room A201",
  "segments": [
    {
      "time": {"mode": "absolute", "weekday": 1, "start": "10:30", "end": "12:00"},
      "weeks": [1, 2, 3, 4, 5, 6, 7, 8],
      "evidence": [{"source_id": "notice_01", "description": "course notice"}]
    }
  ]
}
```

## Unresolved Extraction

Use unresolved time when exact timing cannot be determined:

```json
{
  "time": {"mode": "unresolved", "expression": "Wednesday afternoon"},
  "unresolved": {"reason": "No absolute time or period table available"}
}
```

Ask the user only for details that block correct ICS generation.
