# EMF-schedule2ics

An installable Codex Agent Skill for converting course schedules into verified `.ics` calendar files.

It is designed for timetable PDFs, screenshots, mixed PDF + image inputs, syllabus text, and course notices.

The workflow is:

```text
Extract -> Resolve -> Verify -> Generate
```

The Agent reads PDFs/images/text and creates `schedule.json`. The bundled Python scripts then do deterministic validation, date expansion, conflict checks, ICS generation, and round-trip validation.

## Install

Clone this repo:

```bash
git clone https://github.com/aaaMsLIUfruit/emf-schedule2ics.git
```

Install into Codex skills:

```bash
mkdir -p ~/.codex/skills
cp -a emf-schedule2ics ~/.codex/skills/emf-schedule2ics
```

Or use a symlink while developing:

```bash
ln -s "$(pwd)/emf-schedule2ics" ~/.codex/skills/emf-schedule2ics
```

Restart or open a new Codex task after installing.

## Use

In Codex, ask for example:

```text
Use $emf-schedule2ics to convert this PDF course schedule into calendar.ics.
```

Typical requests:

```text
把这个课表转成苹果日历
根据这个 PDF 生成 ICS
把这张课表截图和老师发的课程通知一起整理成日历
正式课表在 PDF，TA session 在截图里，合并后给我一个 ICS
```

Final output should be:

```text
calendar.ics
```

You can import it into Apple Calendar, Google Calendar, Outlook, or other ICS-compatible calendars.

## CLI Helpers

Validate a canonical schedule:

```bash
python scripts/validate_schedule.py schedule.json
```

Generate ICS:

```bash
python scripts/build_ics.py --input schedule.json --output calendar.ics
```

Validate generated ICS:

```bash
python scripts/validate_ics.py --schedule schedule.json --ics calendar.ics
```

Render a PDF into page images:

```bash
python scripts/render_pdf.py timetable.pdf rendered_pages/
```

If the Python PDF renderer dependencies are not installed, use Poppler directly:

```bash
pdftoppm -r 220 -png timetable.pdf rendered_pages/page
```

## Test

The test suite uses Python standard library `unittest`:

```bash
python -m unittest discover -s tests -v
```

No network or external service is needed for the core tests.
