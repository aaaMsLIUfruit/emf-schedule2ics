# Architecture

Use a layered pipeline:

```text
Input files
-> Source normalization
-> Document understanding by the host Agent
-> Event candidates
-> Temporal resolution
-> Canonical schedule JSON
-> Completeness and conflict audit
-> ICS generation
-> ICS round-trip validation
```

The only durable truth source is `schedule.json`. Treat `calendar.ics` as a generated artifact.

## Boundaries

The host Agent handles:

- OCR
- visual layout reasoning
- natural-language interpretation
- deciding whether a later notice modifies an earlier timetable
- asking the user for missing facts

Python scripts handle:

- PDF page rendering
- JSON normalization
- schema-shaped validation
- week and date expansion
- period table to clock time conversion
- conservative merge
- conflict warnings
- ICS writing
- ICS semantic round-trip checks

## Recommended Artifacts

During a real conversion, keep these working files near the user's inputs:

- `rendered_pages/page_001.png`
- `raw_schedule.json`
- `schedule.json`
- `resolved_occurrences.json`
- `calendar.ics`

Only show raw JSON to the user when debugging or when the user asks.
