import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Dict, Any, Tuple

# Direct import of solutions can sometimes bypass naming conflicts in certain environments
# We define it at the module level to ensure it's available
try:
    mp_pose = mp.solutions.pose
except AttributeError:
    # Fallback for older or specific versions of MediaPipe
    import mediapipe.python.solutions.pose as mp_pose

class PoseDetector:
    """
    A wrapper class for initializing and using the MediaPipe Pose model.
    Designed to be lightweight and CPU-friendly for real-time inference.
    """
    def __init__(self,
                 static_image_mode: bool = False,
                 model_complexity: int = 1,
                 smooth_landmarks: bool = True,
                 enable_segmentation: bool = False,
                 smooth_segmentation: bool = True,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        """Initializes the MediaPipe Pose detector."""
        self.pose = mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            smooth_landmarks=smooth_landmarks,
            enable_segmentation=enable_segmentation,
            smooth_segmentation=smooth_segmentation,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
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
        Extracts key landmarks into a dictionary mapping body part names to (x, y) coordinates.
        Returns an empty dict if no landmarks are detected.
        """
        landmarks_dict = {}
        if not results or not results.pose_landmarks:
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
                lm_enum = getattr(mp_pose.PoseLandmark, lm_name)
                landmark = results.pose_landmarks.landmark[lm_enum]
                # Store as normalized coordinates (0.0 to 1.0)
                landmarks_dict[lm_name.lower()] = (landmark.x, landmark.y)
            except (AttributeError, IndexError):
                continue
                
        return landmarks_dict
        
    def close(self) -> None:
        """Releases the underlying MediaPipe resources."""
        self.pose.close()
