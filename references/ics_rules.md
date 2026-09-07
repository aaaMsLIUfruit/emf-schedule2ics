# ICS Rules

The generator intentionally emits explicit VEVENT instances instead of complex RRULEs. This favors correctness in Apple Calendar, Google Calendar, and Outlook over compact output.

Each event includes:

- `VCALENDAR`
- `VEVENT`
- stable `UID`
- `DTSTAMP`
- `DTSTART;TZID=...`
- `DTEND;TZID=...`
- `SUMMARY`
- `LOCATION`
- optional `DESCRIPTION`

Stable UID input:

```text
title | date | start | end | location | event_id | segment_id
```

Round-trip validation parses the generated ICS and compares semantic fields with the canonical schedule:

- event count
- title
- location
- date
- start
- end

Do not deliver `calendar.ics` when round-trip validation fails.
