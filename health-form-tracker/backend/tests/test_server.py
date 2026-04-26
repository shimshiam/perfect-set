import inspect
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if "cv2" not in sys.modules:
    cv2_stub = ModuleType("cv2")
    cv2_stub.IMREAD_COLOR = 1
    cv2_stub.imdecode = lambda *_args, **_kwargs: "decoded-image"
    sys.modules["cv2"] = cv2_stub

if "mediapipe" not in sys.modules:
    mediapipe_stub = ModuleType("mediapipe")
    mediapipe_stub.solutions = SimpleNamespace(pose=SimpleNamespace(Pose=None))
    sys.modules["mediapipe"] = mediapipe_stub

import server


def build_binary_frame_message() -> dict:
    return {"type": "websocket.receive", "bytes": b"test-frame"}


class FakeWebSocket:
    def __init__(self, incoming_messages):
        self._incoming_messages = iter(incoming_messages)
        self.sent_messages = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    async def receive(self):
        try:
            return next(self._incoming_messages)
        except StopIteration:
            return {"type": "websocket.disconnect"}

    async def send_json(self, payload):
        self.sent_messages.append(payload)


class FakeDetector:
    instances = []

    def __init__(self):
        self.find_pose_calls = 0
        self.extract_landmarks_calls = 0
        self.closed = False
        FakeDetector.instances.append(self)

    def find_pose(self, img):
        self.find_pose_calls += 1
        return {"pose": "results"}

    def extract_landmarks(self, results):
        self.extract_landmarks_calls += 1
        return {
            "left_shoulder": {
                "image": (0.12345, 0.67891),
                "world": (0.1, 0.2, 0.3),
                "visibility": 0.99,
            }
        }

    def close(self):
        self.closed = True


class FakeTracker:
    def process_frame(self, landmarks_dict):
        return {
            "rep_count": 3,
            "rep_completed": True,
            "rep_aborted": False,
            "state": "UP",
            "perfect_form": True,
            "warnings": [],
            "elbow_angle": 170.0,
            "back_angle": 175.0,
        }


class ServerWebSocketTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeDetector.instances = []

    async def test_status_precedes_rep_completed_and_pipeline_callable_is_sync(self):
        websocket = FakeWebSocket([build_binary_frame_message()])

        async def fake_to_thread(func, /, *args, **kwargs):
            self.assertFalse(inspect.iscoroutinefunction(func))
            return func(*args, **kwargs)

        with patch.object(server, "PoseDetector", FakeDetector), \
             patch.object(server, "PushupTracker", FakeTracker), \
             patch.object(server.cv2, "imdecode", return_value="decoded-image"), \
             patch.object(server.asyncio, "to_thread", new=fake_to_thread):
            await server.pushup_websocket(websocket)

        self.assertTrue(websocket.accepted)
        self.assertEqual(
            [message["type"] for message in websocket.sent_messages],
            ["STATUS", "REP_COMPLETED"],
        )
        self.assertEqual(websocket.sent_messages[0]["rep_count"], 3)
        self.assertEqual(websocket.sent_messages[1]["count"], 3)
        self.assertEqual(
            websocket.sent_messages[0]["landmarks"]["left_shoulder"],
            [0.1235, 0.6789],
        )
        self.assertTrue(FakeDetector.instances[0].closed)


if __name__ == "__main__":
    unittest.main()
