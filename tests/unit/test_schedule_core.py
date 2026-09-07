from pathlib import Path
import json
import unittest

from scripts.schedule_core import (
    build_ics,
    expected_occurrences,
    load_json,
    normalize_schedule,
    parse_week_expression,
    validate_ics_round_trip,
    validate_schedule,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED = Path(__file__).resolve().parents[1] / "expected"


class ScheduleCoreTests(unittest.TestCase):
    def test_week_expression_range_and_parity(self):
        self.assertEqual(parse_week_expression("1-15周单周"), {"weeks": [1, 3, 5, 7, 9, 11, 13, 15]})
        self.assertEqual(parse_week_expression("2~16周双周"), {"weeks": [2, 4, 6, 8, 10, 12, 14, 16]})
        self.assertEqual(parse_week_expression("第1、2、4、8周"), {"weeks": [1, 2, 4, 8]})

    def test_week_expression_date_based_weekly(self):
        parsed = parse_week_expression(
            "9月15日起每周",
            semester={"start_date": "2026-09-07", "end_date": "2026-09-30"},
            weekday=2,
        )
        self.assertEqual(parsed, {"dates": ["2026-09-15", "2026-09-22", "2026-09-29"]})

    def test_period_and_absolute_occurrence_expansion(self):
        schedule = normalize_schedule(load_json(FIXTURES / "simple_schedule.json"))
        occurrences = expected_occurrences(schedule)
        self.assertEqual(len(occurrences), 4)
        self.assertEqual(occurrences[0]["title"], "Corporate Finance")
        self.assertEqual(occurrences[0]["date"], "2026-09-07")
        self.assertEqual(occurrences[0]["start"], "14:00")
        machine_learning = [item for item in occurrences if item["title"] == "Machine Learning"]
        self.assertEqual(machine_learning[0]["date"], "2026-09-08")
        self.assertEqual(machine_learning[0]["end"], "11:45")

    def test_occurrences_match_expected_fixture(self):
        schedule = normalize_schedule(load_json(FIXTURES / "simple_schedule.json"))
        expected = json.loads((EXPECTED / "simple_occurrences.json").read_text(encoding="utf-8"))
        self.assertEqual({"occurrences": expected_occurrences(schedule)}, expected)

    def test_validate_rejects_unresolved_time(self):
        schedule = load_json(FIXTURES / "unresolved_schedule.json")
        issues = validate_schedule(schedule)
        self.assertTrue(any(issue.level == "error" and "unresolved time" in issue.message for issue in issues))

    def test_visual_candidate_must_be_covered(self):
        schedule = normalize_schedule(load_json(FIXTURES / "simple_schedule.json"))
        schedule["audit"]["visual_candidates"].append(
            {
                "id": "vc_missing",
                "source_id": "pdf_page_001",
                "weekday": 4,
                "start_period": 3,
                "end_period": 4,
                "classification": "course",
                "matched_event_ids": [],
            }
        )
        issues = validate_schedule(schedule)
        self.assertTrue(any("vc_missing" in issue.message for issue in issues))

    def test_ics_round_trip_matches_schedule(self):
        schedule = normalize_schedule(load_json(FIXTURES / "simple_schedule.json"))
        ics_text = build_ics(schedule)
        issues = validate_ics_round_trip(schedule, ics_text)
        self.assertEqual([issue for issue in issues if issue.level == "error"], [])


if __name__ == "__main__":
    unittest.main()
