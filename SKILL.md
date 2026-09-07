---
name: emf-schedule2ics
description: Convert course schedules, timetable PDFs, screenshots, syllabus text, course notices, and mixed-source class schedule materials into verified ICS calendar files for Apple Calendar, Google Calendar, Outlook, and compatible apps. Use when Codex needs to extract, resolve, audit, merge, generate, or validate course calendar events from PDFs, images, tables, text notices, TA sessions, or schedule updates.
---

# EMF-schedule2ics

Use this skill to turn course schedule materials into a deterministic `calendar.ics`.
Never generate ICS directly from visual or natural-language extraction. Always use:

```text
Extract -> Resolve -> Verify -> Generate
```

The host Agent performs OCR, visual understanding, and semantic extraction. The bundled Python scripts perform deterministic rendering, normalization, validation, time expansion, merging, conflict checks, ICS generation, and round-trip validation.

## Workflow

1. Inspect inputs
   - List every PDF, image, text file, syllabus, notice, and chat screenshot.
   - Assign stable `source_id` values such as `pdf_page_001`, `screenshot_02`, `notice_email_01`.
   - For PDFs, render pages first with `scripts/render_pdf.py` when visual layout matters.

2. Classify source types
   - Use grid extraction for standard timetable grids or dense table screenshots.
   - Use text extraction for full-time text schedules, syllabi, and notices.
   - Use mixed-source extraction when official schedules and later updates must be combined.

3. Extract candidates
   - Build structured event candidates; keep source provenance on every event or segment.
   - Do not invent missing times, dates, rooms, instructors, or week ranges.
   - Put unclear values in `unresolved` fields or use `time.mode = "unresolved"`.

4. Resolve to canonical schedule JSON
   - Save the single truth source as `schedule.json`.
   - Run `scripts/normalize_schedule.py` to normalize shorthand fields and week expressions.
   - Run `scripts/validate_schedule.py` before generating ICS.

5. Audit completeness and conflicts
   - For grid sources, compare visual candidates and occupancy maps against extracted schedule segments.
   - If audit fails, perform localized recovery: inspect only the missing weekday/period/source area, update `schedule.json`, and rerun the audit.
   - Treat overlapping classes as warnings unless the evidence proves one is a duplicate or replacement.

6. Generate and validate ICS
   - Run `scripts/build_ics.py --input schedule.json --output calendar.ics`.
   - Run `scripts/validate_ics.py --schedule schedule.json --ics calendar.ics`.
   - Deliver `calendar.ics` only after round-trip validation passes.

## Grid Extraction

For table-like schedules, extract in four passes:

1. Pass A: layout and time axis
   - Identify weekday columns, period rows, period indexes, start/end times, and table bounds.
   - Do not read course text in this pass.

2. Pass B: visual occupancy and course candidates
   - Scan each weekday top to bottom.
   - Record every non-empty course-like region with `weekday`, `start_period`, `end_period`, and `source_id`.
   - Count candidates per day.

3. Pass C: semantic reading
   - Read each candidate region for title, room, instructor, week info, and remarks.
   - Attach `evidence` pointing to the candidate/source.

4. Pass D: independent audit
   - Rescan the whole grid independently.
   - Compare the visual candidate count, occupancy map, and candidate coverage against `schedule.json`.

Represent the visual audit in `schedule.json` under:

```json
{
  "audit": {
    "visual_candidates": [
      {
        "id": "vc_001",
        "source_id": "pdf_page_001",
        "weekday": 1,
        "start_period": 3,
        "end_period": 4,
        "classification": "course",
        "matched_event_ids": ["event_001"]
      }
    ]
  }
}
```

## Canonical JSON

Read `references/schedule_schema.md` and `schemas/schedule.schema.json` when constructing or debugging `schedule.json`.

Minimum shape:

```json
{
  "schema_version": "1.0",
  "semester": {
    "start_date": "2026-09-07",
    "end_date": "2027-01-10",
    "timezone": "Asia/Shanghai"
  },
  "periods": [
    {"index": 1, "start": "08:00", "end": "08:45"}
  ],
  "sources": [
    {"source_id": "pdf_page_001", "type": "pdf_page", "description": "official timetable"}
  ],
  "events": [
    {
      "id": "event_001",
      "title": "Machine Learning",
      "location": "Room A201",
      "segments": [
        {
          "id": "seg_001",
          "time": {"mode": "period", "weekday": 2, "start_period": 3, "end_period": 4},
          "weeks": [1, 2, 3, 4, 5, 6, 7, 8],
          "evidence": [{"source_id": "pdf_page_001", "description": "grid block Tue P3-P4"}]
        }
      ]
    }
  ]
}
```

Time modes:

- `period`: requires `weekday`, `start_period`, `end_period`, and a period table.
- `absolute`: requires `weekday`, `start`, `end`.
- `absolute_date`: requires `date`, `start`, `end`.
- `unresolved`: requires `expression`; this blocks ICS generation.

Use multiple `segments` for the same course when time, room, instructor, or recurrence changes across weeks.

## Recurrence

Prefer explicit `weeks` or `dates` in canonical JSON.

Supported week expressions for `normalize_schedule.py` include:

- `1-16周`, `1~16周`, `第1到16周`
- `1-15周单周`, `2-16周双周`
- `1,3,5,7周`, `第1、2、4、8周`
- `9月15日起每周` when semester year/end date and segment weekday are known

If a phrase like "Wednesday afternoon" lacks exact time or a usable period table, mark it unresolved and ask the user for only the missing detail.

## Mixed Sources

Read `references/temporal_rules.md` and `references/audit_protocol.md` for complex updates.

- Preserve provenance from all sources.
- Do not overwrite the official schedule wholesale when a later notice changes only weeks 9+.
- Encode replacements as separate segments with non-overlapping `weeks` or `dates`.
- Use `scripts/merge_schedule.py` only after the semantic extraction already identifies what each source says.

## Commands

Render PDFs:

```bash
python scripts/render_pdf.py timetable.pdf rendered_pages/
```

Normalize:

```bash
python scripts/normalize_schedule.py raw_schedule.json schedule.json
```

Validate:

```bash
python scripts/validate_schedule.py schedule.json
```

Resolve occurrences for inspection:

```bash
python scripts/resolve_time.py schedule.json resolved_occurrences.json
```

Merge:

```bash
python scripts/merge_schedule.py official.json notice.json --output schedule.json
```

Build ICS:

```bash
python scripts/build_ics.py --input schedule.json --output calendar.ics
```

Round-trip validate:

```bash
python scripts/validate_ics.py --schedule schedule.json --ics calendar.ics
```

## User Output

By default, give a concise summary, not raw JSON:

- number of courses
- number of schedule segments
- whether visual/table audit passed
- whether notices or TA sessions were merged
- unresolved items, if any
- generated `calendar.ics` path

Do not deliver a guessed calendar when unresolved information blocks correct dates or times.
