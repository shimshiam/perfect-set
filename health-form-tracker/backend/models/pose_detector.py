import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Dict, Any, Tuple

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
        """
        Initializes the MediaPipe Pose detector.
        
        Args:
            static_image_mode: Whether to treat the input images as a batch of static 
                               and possibly unrelated images, or a video stream.
            model_complexity: Complexity of the pose landmark model: 0, 1 or 2.
            smooth_landmarks: Whether to filter landmarks across different input images to reduce jitter.
            enable_segmentation: Whether to predict segmentation mask.
            smooth_segmentation: Whether to filter segmentation across different input images.
            min_detection_confidence: Minimum confidence value for the person detection to be considered successful.
            min_tracking_confidence: Minimum confidence value for the pose tracking to be considered successful.
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
        
    def find_pose(self, img: np.ndarray) -> Optional[Any]:
        """
        Processes an image and returns the pose landmarks.
        
        Args:
            img: A numpy ndarray representing an image (BGR format from OpenCV).
            
        Returns:
            The MediaPipe pose results object, or None if an error occurs.
        """
        if img is None:
            return None
            
        # Convert the BGR image to RGB as MediaPipe expects RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # To improve performance, optionally mark the image as not writeable to pass by reference
        img_rgb.flags.writeable = False
        results = self.pose.process(img_rgb)
        img_rgb.flags.writeable = True
        
        return results

    def extract_landmarks(self, results: Any) -> Dict[str, Tuple[float, float]]:
        """
        Extracts key landmarks into a dictionary mapping body part names to (x, y) coordinates.
        Coordinates are normalized [0.0, 1.0].
        
        Args:
            results: The pose landmarks result from find_pose.
            
        Returns:
            A dictionary of landmarks with names like 'left_shoulder', 'right_elbow', etc.
            Returns an empty dict if no landmarks are found.
        """
        landmarks_dict = {}
        if not results or not results.pose_landmarks:
            return landmarks_dict
            
        # Map MediaPipe landmark enums to their normalized x, y coordinates
        # For the pushup tracker, we primarily need shoulders, elbows, wrists, hips, and ankles.
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
                # Store as normalized coordinates. 
                landmarks_dict[lm_name.lower()] = (landmark.x, landmark.y)
            except AttributeError:
                continue
                
        return landmarks_dict
        
    def close(self) -> None:
        """Releases the underlying MediaPipe resources."""
        self.pose.close()
