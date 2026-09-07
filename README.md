# EMF-schedule2ics

An installable Codex Agent Skill for converting course schedules into verified `.ics` calendar files.

It is designed for timetable PDFs, screenshots, mixed PDF + image inputs, syllabus text, and course notices.

## Use

In Codex, ask for example:

```text
Use $emf-schedule2ics to convert this PDF course schedule into calendar.ics.
```

Typical requests:

```text
根据这个 PDF 生成 ICS
去掉CN课程
把这张课表截图和老师发的课程通知一起整理成日历
正式课表在 PDF，TA session 在截图里，合并后给我一个 ICS
```

Final output should be:

```text
calendar.ics
```

You can import it into Apple Calendar, Google Calendar, Outlook, or other ICS-compatible calendars.

```bash
python -m unittest discover -s tests -v
```

No network or external service is needed for the core tests.
