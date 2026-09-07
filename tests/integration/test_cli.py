import subprocess
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "simple_schedule.json"


def run_cmd(*args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)


class CliTests(unittest.TestCase):
    def test_cli_build_and_validate_round_trip(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            normalized = tmp_path / "schedule.json"
            ics = tmp_path / "calendar.ics"

            result = run_cmd(sys.executable, "scripts/normalize_schedule.py", str(FIXTURE), str(normalized))
            self.assertEqual(result.returncode, 0, result.stderr)

            result = run_cmd(sys.executable, "scripts/validate_schedule.py", str(normalized))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

            result = run_cmd(sys.executable, "scripts/build_ics.py", "--input", str(normalized), "--output", str(ics))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("BEGIN:VCALENDAR", ics.read_text(encoding="utf-8"))

            result = run_cmd(sys.executable, "scripts/validate_ics.py", "--schedule", str(normalized), "--ics", str(ics))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
