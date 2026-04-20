from enum import Enum, auto
from typing import Dict, Tuple, List, Any
from utils.geometry import calculate_angle

class PushupState(Enum):
    UP = auto()
    DESCENDING = auto()
    BOTTOM = auto()
    ASCENDING = auto()
    PAUSED = auto()

class PushupTracker:
    """
    State machine that interprets landmark data frame-by-frame 
    to count reps and evaluate physical form during a pushup.
    """
    
    def __init__(self, 
                 elbow_flexion_threshold: float = 90.0, 
                 elbow_extension_threshold: float = 160.0,
                 back_extension_tolerance: float = 165.0):
        """
        Initializes the tracker with configurable angle thresholds.
        
        Args:
            elbow_flexion_threshold: Max elbow angle to be considered at the bottom of the rep.
            elbow_extension_threshold: Min elbow angle to be considered at the top of the rep.
            back_extension_tolerance: Min back angle for perfect posture.
        """
        self.elbow_flexion_threshold = elbow_flexion_threshold
        self.elbow_extension_threshold = elbow_extension_threshold
        self.back_extension_tolerance = back_extension_tolerance
        
        self.state = PushupState.PAUSED
        self.rep_count = 0
        # Track whether form was maintained throughout the current rep cycle
        self._form_maintained_during_rep = True
        
    def process_frame(self, landmarks_dict: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """
        Processes a single frame of landmarks.
        
        Args:
            landmarks_dict: Dictionary mapping landmark names to (x, y) coordinate tuples.
            
        Returns:
            Dictionary containing tracking state:
            - rep_count: Current number of completed reps.
            - state: String representation of current phase (e.g., 'UP', 'DESCENDING').
            - perfect_form: Boolean indicating if posture is currently good.
            - warnings: List of warning strings.
            - elbow_angle: Current computed elbow angle (or None).
            - back_angle: Current computed back angle (or None).
        """
        warnings: List[str] = []
        perfect_form = True
        
        # Define necessary landmarks for each side
        critical_landmarks_left = ['left_shoulder', 'left_elbow', 'left_wrist', 'left_hip', 'left_ankle']
        critical_landmarks_right = ['right_shoulder', 'right_elbow', 'right_wrist', 'right_hip', 'right_ankle']
        
        # Check presence of landmarks
        left_present = all(k in landmarks_dict for k in critical_landmarks_left)
        right_present = all(k in landmarks_dict for k in critical_landmarks_right)
        
        if not left_present and not right_present:
            self.state = PushupState.PAUSED
            return {
                "rep_count": self.rep_count,
                "state": self.state.name,
                "perfect_form": False,
                "warnings": ["Landmarks missing"],
                "elbow_angle": None,
                "back_angle": None
            }
            
        # Calculate angles
        elbow_angles: List[float] = []
        back_angles: List[float] = []
        
        if left_present:
            elbow_angles.append(calculate_angle(
                landmarks_dict['left_shoulder'], 
                landmarks_dict['left_elbow'], 
                landmarks_dict['left_wrist']
            ))
            back_angles.append(calculate_angle(
                landmarks_dict['left_shoulder'], 
                landmarks_dict['left_hip'], 
                landmarks_dict['left_ankle']
            ))
            
        if right_present:
            elbow_angles.append(calculate_angle(
                landmarks_dict['right_shoulder'], 
                landmarks_dict['right_elbow'], 
                landmarks_dict['right_wrist']
            ))
            back_angles.append(calculate_angle(
                landmarks_dict['right_shoulder'], 
                landmarks_dict['right_hip'], 
                landmarks_dict['right_ankle']
            ))
            
        # Average angles from available sides
        elbow_angle = sum(elbow_angles) / len(elbow_angles)
        back_angle = sum(back_angles) / len(back_angles)
        
        # Form Evaluation
        if back_angle < self.back_extension_tolerance:
            perfect_form = False
            warnings.append("Keep your back straight")
            # Mark that form was broken during this rep cycle
            self._form_maintained_during_rep = False
            
        # State Machine Logic
        if self.state == PushupState.PAUSED:
            if elbow_angle >= self.elbow_extension_threshold:
                self.state = PushupState.UP
            elif elbow_angle <= self.elbow_flexion_threshold:
                self.state = PushupState.BOTTOM
            else:
                self.state = PushupState.DESCENDING
                
        elif self.state == PushupState.UP:
            if elbow_angle < self.elbow_extension_threshold:
                self.state = PushupState.DESCENDING
                # Reset form tracking for the new rep cycle
                self._form_maintained_during_rep = True
                
        elif self.state == PushupState.DESCENDING:
            if elbow_angle <= self.elbow_flexion_threshold:
                self.state = PushupState.BOTTOM
            elif elbow_angle >= self.elbow_extension_threshold:
                self.state = PushupState.UP
                
        elif self.state == PushupState.BOTTOM:
            if elbow_angle > self.elbow_flexion_threshold:
                self.state = PushupState.ASCENDING
                
        elif self.state == PushupState.ASCENDING:
            if elbow_angle >= self.elbow_extension_threshold:
                self.state = PushupState.UP
                # Only count the rep if form was maintained throughout
                if self._form_maintained_during_rep:
                    self.rep_count += 1
                else:
                    warnings.append("Rep not counted: bad form")
                # Reset for next rep
                self._form_maintained_during_rep = True
            elif elbow_angle <= self.elbow_flexion_threshold:
                self.state = PushupState.BOTTOM
                
        return {
            "rep_count": self.rep_count,
            "state": self.state.name,
            "perfect_form": perfect_form,
            "warnings": warnings,
            "elbow_angle": elbow_angle,
            "back_angle": back_angle
        }
