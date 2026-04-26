from pathlib import Path
import sys
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.geometry import calculate_angle


class GeometryTests(unittest.TestCase):
    def test_calculate_angle_supports_2d_points(self):
        angle = calculate_angle((0.0, 0.0), (1.0, 0.0), (1.0, 1.0))
        self.assertAlmostEqual(angle, 90.0)

    def test_calculate_angle_supports_3d_points(self):
        angle = calculate_angle((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        self.assertAlmostEqual(angle, 90.0)


if __name__ == "__main__":
    unittest.main()
