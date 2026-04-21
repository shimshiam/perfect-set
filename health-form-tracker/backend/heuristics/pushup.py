from enum import Enum, auto
from typing import Dict, Tuple, List, Any
from utils.geometry import calculate_angle


class PushupState(Enum):
    PAUSED = auto()       # No landmarks detected (debounced)
    IDLE = auto()         # Person detected but standing / not in pushup position
    STABILIZING = auto()  # Horizontal, waiting for posture to stabilize
    UP = auto()           # Arms extended — top of rep
    DESCENDING = auto()   # Lowering body
    BOTTOM = auto()       # Arms fully bent — bottom of rep
    ASCENDING = auto()    # Pushing back up


class PushupTracker:
    """
    State machine that interprets landmark data frame-by-frame
    to count reps and evaluate physical form during a pushup.

    Guards against false positives from:
    - Standing with arm movement (orientation gate)
    - Transitioning into position (stabilization period)
    - Camera proximity distortion (shoulder-width gate)
    - Landmark flicker (debounced loss detection)
    """

    # ── Angle Thresholds ──
    ELBOW_FLEXION = 90.0
    ELBOW_EXTENSION = 160.0
    BACK_TOLERANCE = 165.0

    # ── Orientation Gate ──
    # Max |avg_shoulder_y - avg_ankle_y| to be considered horizontal.
    # Values above this mean the person is standing upright.
    VERTICAL_THRESHOLD = 0.25

    # ── Proximity Gate ──
    # Max normalized x-distance between left & right shoulder.
    # Exceeding this means the person is too close for accurate 2D tracking.
    PROXIMITY_THRESHOLD = 0.35

    # ── Stabilization ──
    # Frames of continuous horizontal posture required before rep counting
    # activates. At 15 FPS (WebSocket rate), 30 frames ≈ 2 seconds.
    STABILIZE_FRAMES = 30

    # ── Debounce ──
    # Consecutive frames without landmarks before dropping to PAUSED.
    # Prevents flickering when the model briefly loses confidence.
    DEBOUNCE_FRAMES = 15

    def __init__(self):
        self.state = PushupState.PAUSED
        self.rep_count = 0
        self._form_maintained = True
        self._stabilize_counter = 0
        self._landmark_loss_counter = 0

    # ──────────────────────────────────────────────────────────────
    # Helper methods
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _avg_coord(landmarks: Dict, keys: List[str], axis: int) -> float | None:
        """Average a specific coordinate axis (0=x, 1=y) for given keys."""
        vals = [landmarks[k][axis] for k in keys if k in landmarks]
        return sum(vals) / len(vals) if vals else None

    def _is_horizontal(self, lm: Dict) -> bool:
        """True if body is roughly parallel to the ground."""
        shoulder_y = self._avg_coord(lm, ['left_shoulder', 'right_shoulder'], 1)
        ankle_y = self._avg_coord(lm, ['left_ankle', 'right_ankle'], 1)
        if shoulder_y is None or ankle_y is None:
            return False
        return abs(shoulder_y - ankle_y) < self.VERTICAL_THRESHOLD

    def _is_too_close(self, lm: Dict) -> bool:
        """True if person is too close to camera for accurate tracking."""
        if 'left_shoulder' in lm and 'right_shoulder' in lm:
            x_gap = abs(lm['left_shoulder'][0] - lm['right_shoulder'][0])
            return x_gap > self.PROXIMITY_THRESHOLD
        return False

    # ──────────────────────────────────────────────────────────────
    # Main processing loop
    # ──────────────────────────────────────────────────────────────

    def process_frame(self, landmarks_dict: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """
        Processes a single frame of landmarks.

        Returns:
            Dictionary with: rep_count, state, perfect_form, warnings,
            elbow_angle, back_angle.
        """
        warnings: List[str] = []
        perfect_form = True

        # ── Landmark presence check ──
        left_keys = ['left_shoulder', 'left_elbow', 'left_wrist', 'left_hip', 'left_ankle']
        right_keys = ['right_shoulder', 'right_elbow', 'right_wrist', 'right_hip', 'right_ankle']
        left_ok = all(k in landmarks_dict for k in left_keys)
        right_ok = all(k in landmarks_dict for k in right_keys)

        # ──────────────────────────────────────────────────────────
        # FIX 4: Debounced landmark loss
        # Hold the last known state for DEBOUNCE_FRAMES before dropping
        # to PAUSED, preventing UI flicker during brief confidence drops.
        # ──────────────────────────────────────────────────────────
        if not left_ok and not right_ok:
            self._landmark_loss_counter += 1
            if self._landmark_loss_counter >= self.DEBOUNCE_FRAMES:
                self.state = PushupState.PAUSED
                self._stabilize_counter = 0
            # During debounce: keep self.state as last known value.
            # After debounce: state is PAUSED.
            return {
                "rep_count": self.rep_count,
                "state": self.state.name,
                "perfect_form": False,
                "warnings": ["Landmarks missing"] if self.state == PushupState.PAUSED else [],
                "elbow_angle": None,
                "back_angle": None,
            }

        # Landmarks found — reset debounce counter
        self._landmark_loss_counter = 0

        # ── Calculate angles ──
        elbow_angles: List[float] = []
        back_angles: List[float] = []

        if left_ok:
            elbow_angles.append(calculate_angle(
                landmarks_dict['left_shoulder'],
                landmarks_dict['left_elbow'],
                landmarks_dict['left_wrist'],
            ))
            back_angles.append(calculate_angle(
                landmarks_dict['left_shoulder'],
                landmarks_dict['left_hip'],
                landmarks_dict['left_ankle'],
            ))

        if right_ok:
            elbow_angles.append(calculate_angle(
                landmarks_dict['right_shoulder'],
                landmarks_dict['right_elbow'],
                landmarks_dict['right_wrist'],
            ))
            back_angles.append(calculate_angle(
                landmarks_dict['right_shoulder'],
                landmarks_dict['right_hip'],
                landmarks_dict['right_ankle'],
            ))

        elbow_angle = sum(elbow_angles) / len(elbow_angles)
        back_angle = sum(back_angles) / len(back_angles)

        # ──────────────────────────────────────────────────────────
        # FIX 3: Proximity gate
        # When too close, 2D foreshortening makes elbows look bent.
        # Freeze the state machine and warn the user.
        # ──────────────────────────────────────────────────────────
        if self._is_too_close(landmarks_dict):
            warnings.append("Step back from camera")
            return {
                "rep_count": self.rep_count,
                "state": self.state.name,
                "perfect_form": True,
                "warnings": warnings,
                "elbow_angle": elbow_angle,
                "back_angle": back_angle,
            }

        # ──────────────────────────────────────────────────────────
        # FIX 1: Orientation gate
        # Only activate pushup tracking when the body is horizontal.
        # Standing + bending elbows must NOT count as reps.
        # ──────────────────────────────────────────────────────────
        if not self._is_horizontal(landmarks_dict):
            self.state = PushupState.IDLE
            self._stabilize_counter = 0
            self._form_maintained = True
            return {
                "rep_count": self.rep_count,
                "state": self.state.name,
                "perfect_form": True,
                "warnings": [],
                "elbow_angle": elbow_angle,
                "back_angle": back_angle,
            }

        # ──────────────────────────────────────────────────────────
        # FIX 2: Stabilization gate
        # Require N frames of continuous horizontal posture before
        # activating form checks. Prevents false "bad form" warnings
        # while the user is bending down to get into position.
        # ──────────────────────────────────────────────────────────
        if self.state in (PushupState.PAUSED, PushupState.IDLE, PushupState.STABILIZING):
            self._stabilize_counter += 1
            if self._stabilize_counter < self.STABILIZE_FRAMES:
                self.state = PushupState.STABILIZING
                return {
                    "rep_count": self.rep_count,
                    "state": self.state.name,
                    "perfect_form": True,
                    "warnings": ["Getting into position..."],
                    "elbow_angle": elbow_angle,
                    "back_angle": back_angle,
                }
            else:
                # Stabilized — enter active tracking
                self.state = PushupState.UP
                self._form_maintained = True

        # ── Form evaluation (only active after stabilization) ──
        if back_angle < self.BACK_TOLERANCE:
            perfect_form = False
            warnings.append("Keep your back straight")
            self._form_maintained = False

        # ── State machine: pushup rep counting ──
        if self.state == PushupState.UP:
            if elbow_angle < self.ELBOW_EXTENSION:
                self.state = PushupState.DESCENDING
                self._form_maintained = True  # Reset for new rep cycle

        elif self.state == PushupState.DESCENDING:
            if elbow_angle <= self.ELBOW_FLEXION:
                self.state = PushupState.BOTTOM
            elif elbow_angle >= self.ELBOW_EXTENSION:
                self.state = PushupState.UP

        elif self.state == PushupState.BOTTOM:
            if elbow_angle > self.ELBOW_FLEXION:
                self.state = PushupState.ASCENDING

        elif self.state == PushupState.ASCENDING:
            if elbow_angle >= self.ELBOW_EXTENSION:
                self.state = PushupState.UP
                if self._form_maintained:
                    self.rep_count += 1
                else:
                    warnings.append("Rep not counted: bad form")
                self._form_maintained = True
            elif elbow_angle <= self.ELBOW_FLEXION:
                self.state = PushupState.BOTTOM

        return {
            "rep_count": self.rep_count,
            "state": self.state.name,
            "perfect_form": perfect_form,
            "warnings": warnings,
            "elbow_angle": elbow_angle,
            "back_angle": back_angle,
        }
