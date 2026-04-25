from pathlib import Path
import sys
import unittest
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from heuristics.pushup import PushupTracker, PushupState


HORIZONTAL_LANDMARKS = {
    "left_shoulder": (0.30, 0.40),
    "left_elbow": (0.38, 0.42),
    "left_wrist": (0.46, 0.44),
    "left_hip": (0.42, 0.43),
    "left_ankle": (0.58, 0.47),
}


class PushupTrackerTests(unittest.TestCase):
    def _run_frame(self, tracker: PushupTracker, elbow_angle: float, back_angle: float):
        angles = iter([elbow_angle, back_angle])
        with patch("heuristics.pushup.calculate_angle", side_effect=lambda *_args: next(angles)):
            return tracker.process_frame(dict(HORIZONTAL_LANDMARKS))

    def _stabilize_tracker(self, tracker: PushupTracker):
        status = None
        for _ in range(tracker.STABILIZE_FRAMES):
            status = self._run_frame(tracker, elbow_angle=170.0, back_angle=170.0)
        return status

    def test_requires_full_stabilization_before_tracking(self):
        tracker = PushupTracker()

        for _ in range(tracker.STABILIZE_FRAMES - 1):
            status = self._run_frame(tracker, elbow_angle=170.0, back_angle=170.0)
            self.assertEqual(status["state"], PushupState.STABILIZING.name)
            self.assertEqual(status["warnings"], ["Getting into position..."])

        status = self._run_frame(tracker, elbow_angle=170.0, back_angle=170.0)
        self.assertEqual(status["state"], PushupState.UP.name)
        self.assertEqual(status["rep_count"], 0)

    def test_landmarks_missing_only_pause_after_debounce_window(self):
        tracker = PushupTracker()
        self._stabilize_tracker(tracker)

        for _ in range(tracker.DEBOUNCE_FRAMES - 1):
            status = tracker.process_frame({})
            self.assertEqual(status["state"], PushupState.UP.name)
            self.assertEqual(status["warnings"], [])

        status = tracker.process_frame({})
        self.assertEqual(status["state"], PushupState.PAUSED.name)
        self.assertEqual(status["warnings"], ["Landmarks missing"])

    def test_bad_form_persists_through_bottom_bounce(self):
        tracker = PushupTracker()
        self._stabilize_tracker(tracker)

        self._run_frame(tracker, elbow_angle=120.0, back_angle=130.0)
        self._run_frame(tracker, elbow_angle=85.0, back_angle=130.0)
        self._run_frame(tracker, elbow_angle=120.0, back_angle=150.0)
        bounce = self._run_frame(tracker, elbow_angle=85.0, back_angle=150.0)
        self.assertEqual(bounce["state"], PushupState.BOTTOM.name)

        self._run_frame(tracker, elbow_angle=120.0, back_angle=150.0)
        status = self._run_frame(tracker, elbow_angle=170.0, back_angle=150.0)

        self.assertEqual(status["rep_count"], 0)
        self.assertFalse(status["rep_completed"])
        self.assertTrue(status["rep_aborted"])
        self.assertIn("Rep not counted: bad form", status["warnings"])


if __name__ == "__main__":
    unittest.main()
