from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.pose_detector import PoseDetector


class FakeLandmark:
    def __init__(self, x, y, z=0.0, visibility=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


class PoseDetectorTests(unittest.TestCase):
    def _make_detector(self):
        detector = PoseDetector.__new__(PoseDetector)
        detector.alpha = 0.5
        detector.visibility_threshold = 0.65
        detector.max_processing_dimension = 512
        detector.prev_landmarks = {}
        detector.mp_pose = SimpleNamespace(
            PoseLandmark=SimpleNamespace(
                LEFT_SHOULDER=0,
                RIGHT_SHOULDER=1,
                LEFT_ELBOW=2,
                RIGHT_ELBOW=3,
                LEFT_WRIST=4,
                RIGHT_WRIST=5,
                LEFT_HIP=6,
                RIGHT_HIP=7,
                LEFT_ANKLE=8,
                RIGHT_ANKLE=9,
            )
        )
        return detector

    def test_extract_landmarks_skips_low_visibility_points(self):
        detector = self._make_detector()
        results = SimpleNamespace(
            pose_landmarks=SimpleNamespace(
                landmark=[
                    FakeLandmark(0.10, 0.20, visibility=0.90),
                    FakeLandmark(0.15, 0.25, visibility=0.40),
                    FakeLandmark(0.20, 0.30, visibility=0.90),
                    FakeLandmark(0.25, 0.35, visibility=0.90),
                    FakeLandmark(0.30, 0.40, visibility=0.90),
                    FakeLandmark(0.35, 0.45, visibility=0.90),
                    FakeLandmark(0.40, 0.50, visibility=0.90),
                    FakeLandmark(0.45, 0.55, visibility=0.90),
                    FakeLandmark(0.50, 0.60, visibility=0.90),
                    FakeLandmark(0.55, 0.65, visibility=0.90),
                ]
            ),
            pose_world_landmarks=SimpleNamespace(
                landmark=[
                    FakeLandmark(1.0, 2.0, 3.0),
                    FakeLandmark(1.5, 2.5, 3.5),
                    FakeLandmark(2.0, 3.0, 4.0),
                    FakeLandmark(2.5, 3.5, 4.5),
                    FakeLandmark(3.0, 4.0, 5.0),
                    FakeLandmark(3.5, 4.5, 5.5),
                    FakeLandmark(4.0, 5.0, 6.0),
                    FakeLandmark(4.5, 5.5, 6.5),
                    FakeLandmark(5.0, 6.0, 7.0),
                    FakeLandmark(5.5, 6.5, 7.5),
                ]
            ),
        )

        landmarks = detector.extract_landmarks(results)

        self.assertIn("left_shoulder", landmarks)
        self.assertNotIn("right_shoulder", landmarks)
        self.assertEqual(landmarks["left_shoulder"]["image"], (0.10, 0.20))
        self.assertEqual(landmarks["left_shoulder"]["world"], (1.0, 2.0, 3.0))
        self.assertEqual(landmarks["left_shoulder"]["visibility"], 0.90)


if __name__ == "__main__":
    unittest.main()
