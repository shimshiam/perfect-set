from pathlib import Path
import sys
import unittest
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from heuristics.squat import SquatTracker, SquatState


SQUAT_LANDMARKS = {
    "left_shoulder": (0.42, 0.20),
    "left_hip": (0.42, 0.42),
    "left_knee": (0.42, 0.64),
    "left_ankle": (0.42, 0.86),
}


class SquatTrackerTests(unittest.TestCase):
    def _run_frame(self, tracker: SquatTracker, knee_angle: float, torso_angle: float, timestamp_ms: float = 0):
        angles = iter([knee_angle, torso_angle])
        with patch("heuristics.squat.calculate_angle", side_effect=lambda *_args: next(angles)):
            return tracker.process_frame(dict(SQUAT_LANDMARKS), timestamp_ms=timestamp_ms)

    def _calibrate_tracker(self, tracker: SquatTracker):
        status = None
        for i in range(tracker.CALIBRATION_FRAMES):
            status = self._run_frame(tracker, knee_angle=175.0, torso_angle=170.0, timestamp_ms=i * 33)
        return status

    def test_requires_standing_calibration_before_tracking(self):
        tracker = SquatTracker()

        for _ in range(tracker.CALIBRATION_FRAMES - 1):
            status = self._run_frame(tracker, knee_angle=175.0, torso_angle=170.0)
            self.assertEqual(status["state"], SquatState.CALIBRATING.name)
            self.assertEqual(status["faults"][0]["code"], "CALIBRATING")

        status = self._run_frame(tracker, knee_angle=175.0, torso_angle=170.0)
        self.assertEqual(status["state"], SquatState.STANDING.name)
        self.assertTrue(status["calibration"]["complete"])

    def test_squat_counts_valid_full_depth_rep(self):
        tracker = SquatTracker()
        self._calibrate_tracker(tracker)

        self._run_frame(tracker, knee_angle=140.0, torso_angle=160.0, timestamp_ms=100)
        self._run_frame(tracker, knee_angle=95.0, torso_angle=155.0, timestamp_ms=180)
        self._run_frame(tracker, knee_angle=125.0, torso_angle=155.0, timestamp_ms=240)
        status = self._run_frame(tracker, knee_angle=170.0, torso_angle=165.0, timestamp_ms=320)

        self.assertEqual(status["rep_count"], 1)
        self.assertTrue(status["rep_completed"])
        self.assertEqual(status["rep_quality"]["min_knee_angle"], 95.0)
        self.assertEqual(status["rep_quality"]["result"], "completed")

    def test_squat_aborts_when_depth_is_insufficient(self):
        tracker = SquatTracker()
        self._calibrate_tracker(tracker)

        self._run_frame(tracker, knee_angle=140.0, torso_angle=160.0, timestamp_ms=100)
        status = self._run_frame(tracker, knee_angle=170.0, torso_angle=165.0, timestamp_ms=180)

        self.assertEqual(status["rep_count"], 0)
        self.assertTrue(status["rep_aborted"])
        self.assertEqual(status["faults"][0]["code"], "INSUFFICIENT_DEPTH")
        self.assertIn("INSUFFICIENT_DEPTH", status["rep_quality"]["fault_codes"])

    def test_torso_lean_fault_rejects_rep(self):
        tracker = SquatTracker()
        self._calibrate_tracker(tracker)

        self._run_frame(tracker, knee_angle=140.0, torso_angle=100.0, timestamp_ms=100)
        self._run_frame(tracker, knee_angle=120.0, torso_angle=100.0, timestamp_ms=140)
        self._run_frame(tracker, knee_angle=95.0, torso_angle=100.0, timestamp_ms=180)
        self._run_frame(tracker, knee_angle=95.0, torso_angle=100.0, timestamp_ms=220)
        self._run_frame(tracker, knee_angle=125.0, torso_angle=100.0, timestamp_ms=260)
        status = self._run_frame(tracker, knee_angle=170.0, torso_angle=160.0, timestamp_ms=340)

        self.assertEqual(status["rep_count"], 0)
        self.assertTrue(status["rep_aborted"])
        self.assertIn("TORSO_LEAN", status["rep_quality"]["fault_codes"])


if __name__ == "__main__":
    unittest.main()
