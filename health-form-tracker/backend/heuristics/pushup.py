from enum import Enum, auto
from typing import Dict, Tuple, List, Any, Sequence
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
    BACK_TOLERANCE = 140.0
    BACK_RECOVERY_TOLERANCE = 145.0
    BACK_BAD_FRAME_GRACE = 3

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
        self._bad_back_frame_counter = 0
        self._back_form_bad = False

    # ──────────────────────────────────────────────────────────────
    # Helper methods
    # ──────────────────────────────────────────────────────────────

    @staticmethod
    def _coord(landmarks: Dict, key: str, space: str = "image") -> Sequence[float] | None:
        point = landmarks.get(key)
        if point is None:
            return None
        if isinstance(point, dict):
            return point.get(space)
        return point if space == "image" else None

    @staticmethod
    def _visibility(landmarks: Dict, key: str) -> float:
        point = landmarks.get(key)
        if isinstance(point, dict):
            return float(point.get("visibility", 1.0))
        return 1.0

    @staticmethod
    def _weighted_mean(measures: List[Tuple[float, float]]) -> float | None:
        if not measures:
            return None
        total_weight = sum(weight for _, weight in measures)
        if total_weight <= 0:
            return None
        return sum(value * weight for value, weight in measures) / total_weight

    @classmethod
    def _avg_coord(cls, landmarks: Dict, keys: List[str], axis: int, space: str = "image") -> float | None:
        """Average a specific coordinate axis (0=x, 1=y) for given keys."""
        vals = []
        for key in keys:
            coord = cls._coord(landmarks, key, space)
            if coord is not None and len(coord) > axis:
                vals.append(coord[axis])
        return sum(vals) / len(vals) if vals else None

    @classmethod
    def _side_weight(cls, landmarks: Dict, side: str, joints: List[str]) -> float:
        return sum(cls._visibility(landmarks, f"{side}_{joint}") for joint in joints) / len(joints)

    @classmethod
    def _calculate_side_angle(
        cls,
        landmarks: Dict,
        side: str,
        joints: Tuple[str, str, str],
        space: str = "image",
    ) -> float | None:
        coords = [cls._coord(landmarks, f"{side}_{joint}", space) for joint in joints]
        if any(coord is None for coord in coords):
            return None
        return calculate_angle(coords[0], coords[1], coords[2])

    def _is_horizontal(self, lm: Dict) -> bool:
        """True if body is roughly parallel to the ground."""
        shoulder_y = self._avg_coord(lm, ['left_shoulder', 'right_shoulder'], 1)
        ankle_y = self._avg_coord(lm, ['left_ankle', 'right_ankle'], 1)
        if shoulder_y is None or ankle_y is None:
            return False
        return abs(shoulder_y - ankle_y) < self.VERTICAL_THRESHOLD

    def _is_too_close(self, lm: Dict) -> bool:
        """True if person is too close to camera for accurate tracking."""
        left_shoulder = self._coord(lm, 'left_shoulder')
        right_shoulder = self._coord(lm, 'right_shoulder')
        if left_shoulder is not None and right_shoulder is not None:
            x_gap = abs(left_shoulder[0] - right_shoulder[0])
            return x_gap > self.PROXIMITY_THRESHOLD
        return False

    def _reset_back_form_tracking(self) -> None:
        self._bad_back_frame_counter = 0
        self._back_form_bad = False

    def _evaluate_back_form(self, back_angle: float, warnings: List[str]) -> bool:
        if back_angle < self.BACK_TOLERANCE:
            self._bad_back_frame_counter += 1
        else:
            self._bad_back_frame_counter = 0

        if self._back_form_bad:
            if back_angle >= self.BACK_RECOVERY_TOLERANCE:
                self._back_form_bad = False
        elif self._bad_back_frame_counter >= self.BACK_BAD_FRAME_GRACE:
            self._back_form_bad = True

        if self._back_form_bad:
            warnings.append("Keep your back straight")
            self._form_maintained = False
            return False

        return True

    # ──────────────────────────────────────────────────────────────
    # Main processing loop
    # ──────────────────────────────────────────────────────────────

    def process_frame(self, landmarks_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single frame of landmarks.

        Returns:
            Dictionary with: rep_count, state, perfect_form, warnings,
            elbow_angle, back_angle.
        """
        warnings: List[str] = []
        perfect_form = True
        rep_completed = False
        rep_aborted = False

        # ── Landmark presence check ──
        left_keys = ['left_shoulder', 'left_elbow', 'left_wrist', 'left_hip', 'left_ankle']
        right_keys = ['right_shoulder', 'right_elbow', 'right_wrist', 'right_hip', 'right_ankle']
        left_ok = all(self._coord(landmarks_dict, k) is not None for k in left_keys)
        right_ok = all(self._coord(landmarks_dict, k) is not None for k in right_keys)

        # ── Debounced landmark loss ──
        # Hold the last known state for DEBOUNCE_FRAMES before dropping
        # to PAUSED, preventing UI flicker during brief confidence drops.
        if not left_ok and not right_ok:
            self._landmark_loss_counter += 1
            if self._landmark_loss_counter >= self.DEBOUNCE_FRAMES:
                self.state = PushupState.PAUSED
                self._stabilize_counter = 0
                self._form_maintained = True
                self._reset_back_form_tracking()
            # During debounce: keep self.state as last known value.
            # After debounce: state is PAUSED.
            return {
                "rep_count": self.rep_count,
                "rep_completed": False,
                "rep_aborted": False,
                "state": self.state.name,
                "perfect_form": False,
                "warnings": ["Landmarks missing"] if self.state == PushupState.PAUSED else [],
                "elbow_angle": None,
                "back_angle": None,
            }

        # Landmarks found — reset debounce counter
        self._landmark_loss_counter = 0

        # ── Calculate angles ──
        elbow_angles: List[Tuple[float, float]] = []
        back_angles: List[Tuple[float, float]] = []

        if left_ok:
            left_elbow_angle = self._calculate_side_angle(
                landmarks_dict,
                "left",
                ("shoulder", "elbow", "wrist"),
            )
            if left_elbow_angle is not None:
                elbow_angles.append((left_elbow_angle, self._side_weight(landmarks_dict, "left", ["shoulder", "elbow", "wrist"])))

            left_back_angle = self._calculate_side_angle(
                landmarks_dict,
                "left",
                ("shoulder", "hip", "ankle"),
                space="world",
            )
            if left_back_angle is None:
                left_back_angle = self._calculate_side_angle(
                    landmarks_dict,
                    "left",
                    ("shoulder", "hip", "ankle"),
                )
            if left_back_angle is not None:
                back_angles.append((left_back_angle, self._side_weight(landmarks_dict, "left", ["shoulder", "hip", "ankle"])))

        if right_ok:
            right_elbow_angle = self._calculate_side_angle(
                landmarks_dict,
                "right",
                ("shoulder", "elbow", "wrist"),
            )
            if right_elbow_angle is not None:
                elbow_angles.append((right_elbow_angle, self._side_weight(landmarks_dict, "right", ["shoulder", "elbow", "wrist"])))

            right_back_angle = self._calculate_side_angle(
                landmarks_dict,
                "right",
                ("shoulder", "hip", "ankle"),
                space="world",
            )
            if right_back_angle is None:
                right_back_angle = self._calculate_side_angle(
                    landmarks_dict,
                    "right",
                    ("shoulder", "hip", "ankle"),
                )
            if right_back_angle is not None:
                back_angles.append((right_back_angle, self._side_weight(landmarks_dict, "right", ["shoulder", "hip", "ankle"])))

        elbow_angle = self._weighted_mean(elbow_angles)
        back_angle = self._weighted_mean(back_angles)
        if elbow_angle is None or back_angle is None:
            return {
                "rep_count": self.rep_count,
                "rep_completed": False,
                "rep_aborted": False,
                "state": self.state.name,
                "perfect_form": False,
                "warnings": ["Landmarks missing"],
                "elbow_angle": None,
                "back_angle": None,
            }

        # ── Proximity gate ──
        # When too close, 2D foreshortening makes elbows look bent.
        # Freeze the state machine and warn the user.
        if self._is_too_close(landmarks_dict):
            warnings.append("Step back from camera")
            return {
                "rep_count": self.rep_count,
                "rep_completed": False,
                "rep_aborted": False,
                "state": self.state.name,
                "perfect_form": True,
                "warnings": warnings,
                "elbow_angle": elbow_angle,
                "back_angle": back_angle,
            }

        # ── Orientation gate ──
        # Only activate pushup tracking when the body is horizontal.
        # Standing + bending elbows must NOT count as reps.
        if not self._is_horizontal(landmarks_dict):
            self.state = PushupState.IDLE
            self._stabilize_counter = 0
            self._form_maintained = True
            self._reset_back_form_tracking()
            return {
                "rep_count": self.rep_count,
                "rep_completed": False,
                "rep_aborted": False,
                "state": self.state.name,
                "perfect_form": True,
                "warnings": [],
                "elbow_angle": elbow_angle,
                "back_angle": back_angle,
            }

        # ── Stabilization gate ──
        # Require N frames of continuous horizontal posture before
        # activating form checks. Prevents false "bad form" warnings
        # while the user is bending down to get into position.
        if self.state in (PushupState.PAUSED, PushupState.IDLE, PushupState.STABILIZING):
            self._stabilize_counter += 1
            if self._stabilize_counter < self.STABILIZE_FRAMES:
                self.state = PushupState.STABILIZING
                self._reset_back_form_tracking()
                return {
                    "rep_count": self.rep_count,
                    "rep_completed": False,
                    "rep_aborted": False,
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
                self._reset_back_form_tracking()

        # ── State machine: pushup rep counting ──
        finalize_rep = False
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
                finalize_rep = True
            elif elbow_angle <= self.ELBOW_FLEXION:
                # A bounce returns to BOTTOM inside the same rep cycle, so preserve
                # any prior bad-form history until the rep either aborts or finishes.
                self.state = PushupState.BOTTOM

        # ── Form evaluation (only active after stabilization) ──
        if not self._evaluate_back_form(back_angle, warnings):
            perfect_form = False

        if finalize_rep:
            if self._form_maintained:
                self.rep_count += 1
                rep_completed = True
            else:
                warnings.append("Rep not counted: bad form")
                rep_aborted = True
            self._form_maintained = True

        return {
            "rep_count": self.rep_count,
            "rep_completed": rep_completed,
            "rep_aborted": rep_aborted,
            "state": self.state.name,
            "perfect_form": perfect_form,
            "warnings": warnings,
            "elbow_angle": elbow_angle,
            "back_angle": back_angle,
        }
