import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Dict, Any, Tuple
import ssl

# Fix for macOS SSL CERTIFICATE_VERIFY_FAILED error when MediaPipe downloads models
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

class PoseDetector:
    """
    A wrapper class for initializing and using the MediaPipe Pose model.
    Includes temporal smoothing (EMA) to reduce landmark jitter.
    """
    def __init__(self,
                 static_image_mode: bool = False,
                 model_complexity: int = 2,
                 smooth_landmarks: bool = True,
                 enable_segmentation: bool = False,
                 smooth_segmentation: bool = True,
                 min_detection_confidence: float = 0.7,
                 min_tracking_confidence: float = 0.7,
                 smoothing_alpha: float = 0.6):
        """
        Initializes the MediaPipe Pose detector with smoothing.
        
        Args:
            smoothing_alpha: 0.0 to 1.0. Lower = smoother but more lag. Higher = more responsive but jittery.
        """
        self.mp_pose = mp.solutions.pose
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
        self.prev_landmarks: Dict[str, Tuple[float, float]] = {}
        
    def find_pose(self, img: np.ndarray) -> Optional[Any]:
        """Processes an image and returns the pose landmarks."""
        if img is None:
            return None
            
        # Convert the BGR image to RGB as MediaPipe expects RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_rgb.flags.writeable = False
        results = self.pose.process(img_rgb)
        img_rgb.flags.writeable = True
        
        return results

    def extract_landmarks(self, results: Any) -> Dict[str, Tuple[float, float]]:
        """
        Extracts key landmarks into a dictionary and applies EMA smoothing.
        Returns an empty dict if no landmarks are detected.
        """
        landmarks_dict = {}
        if not results or not results.pose_landmarks:
            # Clear history if detection is lost to avoid "teleporting" when re-acquired
            self.prev_landmarks = {}
            return landmarks_dict
            
        target_landmarks = [
            'LEFT_SHOULDER', 'RIGHT_SHOULDER', 
            'LEFT_ELBOW', 'RIGHT_ELBOW', 
            'LEFT_WRIST', 'RIGHT_WRIST',
            'LEFT_HIP', 'RIGHT_HIP',
            'LEFT_ANKLE', 'RIGHT_ANKLE'
        ]
        
        for lm_name in target_landmarks:
            try:
                lm_enum = getattr(self.mp_pose.PoseLandmark, lm_name)
                landmark = results.pose_landmarks.landmark[lm_enum]
                
                # Current raw coordinates
                curr_x, curr_y = landmark.x, landmark.y
                lm_key = lm_name.lower()
                
                # Apply Exponential Moving Average (EMA) smoothing
                if lm_key in self.prev_landmarks:
                    prev_x, prev_y = self.prev_landmarks[lm_key]
                    smoothed_x = (self.alpha * curr_x) + ((1 - self.alpha) * prev_x)
                    smoothed_y = (self.alpha * curr_y) + ((1 - self.alpha) * prev_y)
                else:
                    smoothed_x, smoothed_y = curr_x, curr_y
                
                # Store and save for next frame
                landmarks_dict[lm_key] = (smoothed_x, smoothed_y)
                self.prev_landmarks[lm_key] = (smoothed_x, smoothed_y)
                
            except (AttributeError, IndexError):
                continue
                
        return landmarks_dict
        
    def close(self) -> None:
        """Releases the underlying MediaPipe resources."""
        self.pose.close()
