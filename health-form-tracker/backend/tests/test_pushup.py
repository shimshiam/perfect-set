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

KNEE_FALLBACK_LANDMARKS = {
    "left_shoulder": (0.30, 0.40),
    "left_elbow": (0.38, 0.42),
    "left_wrist": (0.46, 0.44),
    "left_hip": (0.42, 0.43),
    "left_knee": (0.52, 0.48),
}

UPPER_BODY_ONLY_LANDMARKS = {
    "left_shoulder": (0.30, 0.40),
    "left_elbow": (0.38, 0.42),
    "left_wrist": (0.46, 0.44),
    "left_hip": (0.42, 0.43),
}


def visible_point(x, y, visibility):
    return {"image": (x, y), "world": None, "visibility": visibility}


AMBIGUOUS_TWO_SIDE_LANDMARKS = {
    "left_shoulder": (0.30, 0.40),
    "left_elbow": (0.38, 0.42),
    "left_wrist": (0.46, 0.44),
    "left_hip": (0.42, 0.43),
    "right_shoulder": (0.70, 0.40),
    "right_elbow": (0.62, 0.42),
    "right_wrist": (0.54, 0.44),
    "right_hip": (0.58, 0.43),
}

RIGHT_SIDE_STRONGER_LANDMARKS = {
    "left_shoulder": visible_point(0.30, 0.40, 0.50),
    "left_elbow": visible_point(0.38, 0.42, 0.50),
    "left_wrist": visible_point(0.46, 0.44, 0.50),
    "left_hip": visible_point(0.42, 0.43, 0.50),
    "right_shoulder": visible_point(0.62, 0.40, 0.95),
    "right_elbow": visible_point(0.56, 0.42, 0.95),
    "right_wrist": visible_point(0.50, 0.44, 0.95),
    "right_hip": visible_point(0.54, 0.43, 0.95),
}


class PushupTrackerTests(unittest.TestCase):
    def _run_frame(self, tracker: PushupTracker, elbow_angle: float, back_angle: float, timestamp_ms: float = 0):
        angles = iter([elbow_angle, back_angle])
        with patch("heuristics.pushup.calculate_angle", side_effect=lambda *_args: next(angles)):
            return tracker.process_frame(dict(HORIZONTAL_LANDMARKS), timestamp_ms=timestamp_ms)

    def _run_upper_body_frame(self, tracker: PushupTracker, elbow_angle: float, timestamp_ms: float = 0):
        with patch("heuristics.pushup.calculate_angle", return_value=elbow_angle):
            return tracker.process_frame(dict(UPPER_BODY_ONLY_LANDMARKS), timestamp_ms=timestamp_ms)

    def _calibrate_tracker(self, tracker: PushupTracker):
        status = None
        for i in range(tracker.CALIBRATION_FRAMES):
            status = self._run_frame(tracker, elbow_angle=170.0, back_angle=170.0, timestamp_ms=i * 33)
        return status

    def test_requires_calibration_before_tracking(self):
        tracker = PushupTracker()

        for _ in range(tracker.CALIBRATION_FRAMES - 1):
            status = self._run_frame(tracker, elbow_angle=170.0, back_angle=170.0)
            self.assertEqual(status["state"], PushupState.CALIBRATING.name)
            self.assertFalse(status["calibration"]["complete"])
            self.assertEqual(status["faults"][0]["code"], "CALIBRATING")

        status = self._run_frame(tracker, elbow_angle=170.0, back_angle=170.0)
        self.assertEqual(status["state"], PushupState.UP.name)
        self.assertTrue(status["calibration"]["complete"])
        self.assertEqual(status["rep_count"], 0)

    def test_pushup_setup_accepts_knee_when_ankle_is_not_visible(self):
        tracker = PushupTracker()
        angles = iter([170.0, 170.0])
        with patch("heuristics.pushup.calculate_angle", side_effect=lambda *_args: next(angles)):
            status = tracker.process_frame(dict(KNEE_FALLBACK_LANDMARKS))

        self.assertEqual(status["state"], PushupState.CALIBRATING.name)
        self.assertEqual(status["faults"][0]["code"], "CALIBRATING")
        self.assertEqual(status["back_angle"], 170.0)

    def test_pushup_setup_accepts_upper_body_when_feet_and_knees_are_cropped(self):
        tracker = PushupTracker()

        for i in range(tracker.CALIBRATION_FRAMES):
            status = self._run_upper_body_frame(tracker, elbow_angle=170.0, timestamp_ms=i * 33)

        self.assertEqual(status["state"], PushupState.UP.name)
        self.assertTrue(status["calibration"]["complete"])
        self.assertIsNone(status["back_angle"])

        self._run_upper_body_frame(tracker, elbow_angle=120.0, timestamp_ms=1100)
        self._run_upper_body_frame(tracker, elbow_angle=85.0, timestamp_ms=1140)
        self._run_upper_body_frame(tracker, elbow_angle=120.0, timestamp_ms=1180)
        status = self._run_upper_body_frame(tracker, elbow_angle=170.0, timestamp_ms=1220)

        self.assertEqual(status["rep_count"], 1)
        self.assertTrue(status["rep_completed"])
        self.assertEqual(status["rep_quality"]["min_elbow_angle"], 85.0)
        self.assertIsNone(status["rep_quality"]["min_back_angle"])

    def test_missing_lower_body_does_not_emit_plank_or_back_faults(self):
        tracker = PushupTracker()
        for i in range(tracker.CALIBRATION_FRAMES):
            self._run_upper_body_frame(tracker, elbow_angle=170.0, timestamp_ms=i * 33)

        for i in range(tracker.BACK_BAD_FRAME_GRACE + 2):
            status = self._run_upper_body_frame(tracker, elbow_angle=120.0, timestamp_ms=1100 + i)

        fault_codes = [fault["code"] for fault in status["faults"]]
        self.assertNotIn("BODY_NOT_HORIZONTAL", fault_codes)
        self.assertNotIn("LANDMARKS_MISSING", fault_codes)
        self.assertNotIn("BACK_SAG", fault_codes)

    def test_landmarks_missing_only_pause_after_debounce_window(self):
        tracker = PushupTracker()
        self._calibrate_tracker(tracker)

        for _ in range(tracker.DEBOUNCE_FRAMES - 1):
            status = tracker.process_frame({})
            self.assertEqual(status["state"], PushupState.UP.name)
            self.assertEqual(status["faults"], [])

        status = tracker.process_frame({})
        self.assertEqual(status["state"], PushupState.PAUSED.name)
        self.assertEqual(status["faults"][0]["code"], "LANDMARKS_MISSING")

    def test_bad_form_persists_through_bottom_bounce(self):
        tracker = PushupTracker()
        self._calibrate_tracker(tracker)

        for i in range(tracker.BACK_BAD_FRAME_GRACE):
            self._run_frame(tracker, elbow_angle=120.0, back_angle=130.0, timestamp_ms=100 + i)
        self._run_frame(tracker, elbow_angle=85.0, back_angle=130.0, timestamp_ms=140)
        self._run_frame(tracker, elbow_angle=120.0, back_angle=150.0, timestamp_ms=180)
        bounce = self._run_frame(tracker, elbow_angle=85.0, back_angle=150.0, timestamp_ms=220)
        self.assertEqual(bounce["state"], PushupState.BOTTOM.name)

        self._run_frame(tracker, elbow_angle=120.0, back_angle=150.0, timestamp_ms=260)
        status = self._run_frame(tracker, elbow_angle=170.0, back_angle=150.0, timestamp_ms=300)

        self.assertEqual(status["rep_count"], 0)
        self.assertFalse(status["rep_completed"])
        self.assertTrue(status["rep_aborted"])
        self.assertEqual(status["rep_quality"]["result"], "aborted")
        self.assertIn("REP_BAD_FORM", status["rep_quality"]["fault_codes"])

    def test_single_bad_back_frame_does_not_fail_rep(self):
        tracker = PushupTracker()
        self._calibrate_tracker(tracker)

        self._run_frame(tracker, elbow_angle=120.0, back_angle=130.0, timestamp_ms=100)
        self._run_frame(tracker, elbow_angle=85.0, back_angle=150.0, timestamp_ms=140)
        self._run_frame(tracker, elbow_angle=120.0, back_angle=150.0, timestamp_ms=180)
        status = self._run_frame(tracker, elbow_angle=170.0, back_angle=150.0, timestamp_ms=220)

        self.assertEqual(status["rep_count"], 1)
        self.assertTrue(status["rep_completed"])
        self.assertFalse(status["rep_aborted"])
        self.assertEqual(status["rep_quality"]["result"], "completed")
        self.assertEqual(status["rep_quality"]["min_elbow_angle"], 85.0)

    def test_final_frame_bad_form_can_abort_rep(self):
        tracker = PushupTracker()
        self._calibrate_tracker(tracker)

        self._run_frame(tracker, elbow_angle=120.0, back_angle=150.0, timestamp_ms=100)
        self._run_frame(tracker, elbow_angle=85.0, back_angle=150.0, timestamp_ms=140)
        self._run_frame(tracker, elbow_angle=120.0, back_angle=150.0, timestamp_ms=180)
        for i in range(tracker.BACK_BAD_FRAME_GRACE - 1):
            self._run_frame(tracker, elbow_angle=120.0, back_angle=130.0, timestamp_ms=200 + i)
        status = self._run_frame(tracker, elbow_angle=170.0, back_angle=130.0, timestamp_ms=240)

        self.assertEqual(status["rep_count"], 0)
        self.assertFalse(status["rep_completed"])
        self.assertTrue(status["rep_aborted"])
        self.assertEqual([fault["code"] for fault in status["faults"]], ["BACK_SAG", "REP_BAD_FORM"])

    def test_uses_stronger_side_when_both_sides_are_visible(self):
        tracker = PushupTracker()
        angles = iter([88.0, 170.0])
        with patch("heuristics.pushup.calculate_angle", side_effect=lambda *_args: next(angles)):
            status = tracker.process_frame(dict(RIGHT_SIDE_STRONGER_LANDMARKS))

        self.assertEqual(status["elbow_angle"], 88.0)
        self.assertEqual(status["faults"][0]["code"], "CALIBRATING")

    def test_ambiguous_two_side_elbow_angles_request_better_camera_angle(self):
        tracker = PushupTracker()
        angles = iter([170.0, 80.0])
        with patch("heuristics.pushup.calculate_angle", side_effect=lambda *_args: next(angles)):
            status = tracker.process_frame(dict(AMBIGUOUS_TWO_SIDE_LANDMARKS))

        self.assertEqual(status["state"], PushupState.PAUSED.name)
        self.assertEqual(status["faults"][0]["code"], "CAMERA_ANGLE_UNCERTAIN")
        self.assertIn("side", status["setup_guidance"])

    def test_ambiguous_active_rep_is_not_counted_later(self):
        tracker = PushupTracker()
        for i in range(tracker.CALIBRATION_FRAMES):
            self._run_upper_body_frame(tracker, elbow_angle=170.0, timestamp_ms=i * 33)

        self._run_upper_body_frame(tracker, elbow_angle=120.0, timestamp_ms=1100)
        angles = iter([120.0, 40.0])
        with patch("heuristics.pushup.calculate_angle", side_effect=lambda *_args: next(angles)):
            ambiguous = tracker.process_frame(dict(AMBIGUOUS_TWO_SIDE_LANDMARKS), timestamp_ms=1120)

        self.assertEqual(ambiguous["faults"][0]["code"], "CAMERA_ANGLE_UNCERTAIN")

        self._run_upper_body_frame(tracker, elbow_angle=85.0, timestamp_ms=1140)
        self._run_upper_body_frame(tracker, elbow_angle=120.0, timestamp_ms=1180)
        status = self._run_upper_body_frame(tracker, elbow_angle=170.0, timestamp_ms=1220)

        self.assertEqual(status["rep_count"], 0)
        self.assertTrue(status["rep_aborted"])
        self.assertIn("CAMERA_ANGLE_UNCERTAIN", status["rep_quality"]["fault_codes"])


if __name__ == "__main__":
    unittest.main()
