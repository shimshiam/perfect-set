import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Dict, Any, Tuple

from utils.ssl_utils import mediapipe_ssl_context


class PoseDetector:
    """
    A wrapper class for initializing and using the MediaPipe Pose model.
    Includes temporal smoothing (EMA) and visibility filtering to reduce
    jitter from noisy or occluded landmarks.
    """
    TARGET_LANDMARKS = (
        'LEFT_SHOULDER', 'RIGHT_SHOULDER',
        'LEFT_ELBOW', 'RIGHT_ELBOW',
        'LEFT_WRIST', 'RIGHT_WRIST',
        'LEFT_HIP', 'RIGHT_HIP',
        'LEFT_KNEE', 'RIGHT_KNEE',
        'LEFT_ANKLE', 'RIGHT_ANKLE',
    )

    def __init__(self,
                 static_image_mode: bool = False,
                 model_complexity: int = 1,
                 smooth_landmarks: bool = True,
                 enable_segmentation: bool = False,
                 smooth_segmentation: bool = True,
                 min_detection_confidence: float = 0.6,
                 min_tracking_confidence: float = 0.6,
                 smoothing_alpha: float = 0.55,
                 visibility_threshold: float = 0.45,
                 max_processing_dimension: int = 512):
        """
        Initializes the MediaPipe Pose detector with smoothing.
        
        Args:
            smoothing_alpha: 0.0 to 1.0. Lower = smoother but more lag. Higher = more responsive but jittery.
        """
        self.mp_pose = mp.solutions.pose
        with mediapipe_ssl_context():
            self.pose = self.mp_pose.Pose(
                static_image_mode=static_image_mode,
                model_complexity=model_complexity,
                smooth_landmarks=smooth_landmarks,
                enable_segmentation=enable_segmentation,
                smooth_segmentation=smooth_segmentation,
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence
            )
        self.alpha = smoothing_alpha
        self.visibility_threshold = visibility_threshold
        self.max_processing_dimension = max_processing_dimension
        self.prev_landmarks: Dict[str, Dict[str, Any]] = {}
        
    def find_pose(self, img: np.ndarray) -> Optional[Any]:
        """Processes an image and returns the pose landmarks."""
        if img is None:
            return None

        h, w = img.shape[:2]
        longest_edge = max(h, w)
        if longest_edge > self.max_processing_dimension:
            scale = self.max_processing_dimension / longest_edge
            img = cv2.resize(
                img,
                (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                interpolation=cv2.INTER_AREA,
            )

        # Convert the BGR image to RGB as MediaPipe expects RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_rgb.flags.writeable = False
        results = self.pose.process(img_rgb)
        img_rgb.flags.writeable = True
        
        return results

    def extract_landmarks(self, results: Any) -> Dict[str, Dict[str, Any]]:
        """
        Extracts key landmarks into a dictionary and applies EMA smoothing.
        Returns an empty dict if no landmarks are detected.
        """
        landmarks_dict = {}
        if not results or not results.pose_landmarks:
            # Clear history if detection is lost to avoid "teleporting" when re-acquired
            self.prev_landmarks = {}
            return landmarks_dict

        world_landmarks = getattr(results, "pose_world_landmarks", None)
        world_landmark_list = getattr(world_landmarks, "landmark", None)

        for lm_name in self.TARGET_LANDMARKS:
            try:
                lm_enum = getattr(self.mp_pose.PoseLandmark, lm_name)
                landmark = results.pose_landmarks.landmark[lm_enum]
                visibility = float(getattr(landmark, "visibility", 1.0))
                if visibility < self.visibility_threshold:
                    self.prev_landmarks.pop(lm_name.lower(), None)
                    continue

                world_landmark = world_landmark_list[lm_enum] if world_landmark_list else None

                # Current raw coordinates
                curr_x, curr_y = landmark.x, landmark.y
                curr_world = (
                    float(world_landmark.x),
                    float(world_landmark.y),
                    float(world_landmark.z),
                ) if world_landmark is not None else None
                lm_key = lm_name.lower()

                # Apply Exponential Moving Average (EMA)
                if lm_key in self.prev_landmarks:
                    prev_entry = self.prev_landmarks[lm_key]
                    prev_x, prev_y = prev_entry["image"]
                    smoothed_x = (self.alpha * curr_x) + ((1 - self.alpha) * prev_x)
                    smoothed_y = (self.alpha * curr_y) + ((1 - self.alpha) * prev_y)
                    prev_world = prev_entry.get("world")
                    if curr_world is not None and prev_world is not None:
                        smoothed_world = tuple(
                            (self.alpha * curr_axis) + ((1 - self.alpha) * prev_axis)
                            for curr_axis, prev_axis in zip(curr_world, prev_world)
                        )
                    else:
                        smoothed_world = curr_world
                else:
                    smoothed_x, smoothed_y = curr_x, curr_y
                    smoothed_world = curr_world

                landmark_entry = {
                    "image": (smoothed_x, smoothed_y),
                    "world": smoothed_world,
                    "visibility": visibility,
                }

                landmarks_dict[lm_key] = landmark_entry
                self.prev_landmarks[lm_key] = landmark_entry

            except (AttributeError, IndexError):
                continue

        return landmarks_dict
        
    def close(self) -> None:
        """Releases the underlying MediaPipe resources."""
        self.pose.close()
