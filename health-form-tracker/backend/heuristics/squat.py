from enum import Enum, auto
from typing import Any, Dict, List, Sequence, Tuple
import time

from heuristics.common import base_status, calibration_status, make_fault
from utils.geometry import calculate_angle


class SquatState(Enum):
    PAUSED = auto()
    IDLE = auto()
    CALIBRATING = auto()
    STANDING = auto()
    DESCENDING = auto()
    BOTTOM = auto()
    ASCENDING = auto()


class SquatTracker:
    """State machine for calibrated bodyweight squat counting."""

    EXERCISE = "squat"

    KNEE_EXTENSION = 160.0
    DESCENT_START = 145.0
    DEPTH_THRESHOLD = 105.0
    TORSO_TOLERANCE = 110.0
    TORSO_RECOVERY_TOLERANCE = 120.0
    TORSO_BAD_FRAME_GRACE = 5
    CALIBRATION_FRAMES = 30
    DEBOUNCE_FRAMES = 15

    def __init__(self):
        self.state = SquatState.PAUSED
        self.rep_count = 0
        self._calibrated = False
        self._calibration_counter = 0
        self._landmark_loss_counter = 0
        self._form_maintained = True
        self._torso_bad_frame_counter = 0
        self._torso_form_bad = False
        self._standing_knee_baseline: float | None = None
        self._rep_start_ms: float | None = None
        self._rep_min_knee: float | None = None
        self._rep_max_knee: float | None = None
        self._rep_min_torso: float | None = None
        self._rep_fault_codes: set[str] = set()

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

    def _has_required_side(self, landmarks: Dict[str, Any]) -> bool:
        joints = ("shoulder", "hip", "knee", "ankle")
        return any(all(self._coord(landmarks, f"{side}_{joint}") is not None for joint in joints) for side in ("left", "right"))

    def _angles(self, landmarks: Dict[str, Any]) -> Tuple[float | None, float | None]:
        knee_angles: List[Tuple[float, float]] = []
        torso_angles: List[Tuple[float, float]] = []

        for side in ("left", "right"):
            knee_angle = self._calculate_side_angle(landmarks, side, ("hip", "knee", "ankle"))
            if knee_angle is not None:
                knee_angles.append((knee_angle, self._side_weight(landmarks, side, ["hip", "knee", "ankle"])))

            torso_angle = self._calculate_side_angle(landmarks, side, ("shoulder", "hip", "ankle"), space="world")
            if torso_angle is None:
                torso_angle = self._calculate_side_angle(landmarks, side, ("shoulder", "hip", "ankle"))
            if torso_angle is not None:
                torso_angles.append((torso_angle, self._side_weight(landmarks, side, ["shoulder", "hip", "ankle"])))

        return self._weighted_mean(knee_angles), self._weighted_mean(torso_angles)

    @staticmethod
    def _round_angle(value: float | None) -> float | None:
        return round(value, 1) if value is not None else None

    def _calibration(self, message: str = "Stand tall for calibration") -> Dict[str, Any]:
        return calibration_status(self._calibrated, self._calibration_counter / self.CALIBRATION_FRAMES, message)

    def _status(
        self,
        *,
        perfect_form: bool,
        faults: List[Dict[str, str]] | None = None,
        setup_guidance: str | None = None,
        knee_angle: float | None = None,
        torso_angle: float | None = None,
        rep_completed: bool = False,
        rep_aborted: bool = False,
        rep_quality: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return base_status(
            exercise=self.EXERCISE,
            rep_count=self.rep_count,
            rep_completed=rep_completed,
            rep_aborted=rep_aborted,
            state=self.state.name,
            perfect_form=perfect_form,
            faults=faults,
            setup_guidance=setup_guidance,
            calibration=self._calibration(setup_guidance or "Ready"),
            rep_quality=rep_quality,
            angles={
                "knee_angle": knee_angle,
                "torso_angle": torso_angle,
                "elbow_angle": None,
                "back_angle": torso_angle,
            },
        )

    def _reset_form_tracking(self) -> None:
        self._torso_bad_frame_counter = 0
        self._torso_form_bad = False

    def _reset_rep_quality(self) -> None:
        self._rep_start_ms = None
        self._rep_min_knee = None
        self._rep_max_knee = None
        self._rep_min_torso = None
        self._rep_fault_codes = set()

    def _start_rep_quality(self, timestamp_ms: float, knee_angle: float, torso_angle: float) -> None:
        self._rep_start_ms = timestamp_ms
        self._rep_min_knee = knee_angle
        self._rep_max_knee = knee_angle
        self._rep_min_torso = torso_angle
        self._rep_fault_codes = set()

    def _update_rep_quality(self, knee_angle: float, torso_angle: float, faults: List[Dict[str, str]]) -> None:
        if self._rep_start_ms is None:
            return
        self._rep_min_knee = min(self._rep_min_knee, knee_angle) if self._rep_min_knee is not None else knee_angle
        self._rep_max_knee = max(self._rep_max_knee, knee_angle) if self._rep_max_knee is not None else knee_angle
        self._rep_min_torso = min(self._rep_min_torso, torso_angle) if self._rep_min_torso is not None else torso_angle
        for fault in faults:
            self._rep_fault_codes.add(fault["code"])

    def _finish_rep_quality(self, timestamp_ms: float, counted: bool, result: str) -> Dict[str, Any]:
        duration_ms = None if self._rep_start_ms is None else max(0, int(timestamp_ms - self._rep_start_ms))
        quality = {
            "exercise": self.EXERCISE,
            "result": result,
            "counted": counted,
            "duration_ms": duration_ms,
            "min_knee_angle": self._round_angle(self._rep_min_knee),
            "standing_knee_angle": self._round_angle(self._rep_max_knee),
            "min_torso_angle": self._round_angle(self._rep_min_torso),
            "fault_codes": sorted(self._rep_fault_codes),
        }
        self._reset_rep_quality()
        return quality

    def _is_standing_for_calibration(self, knee_angle: float, torso_angle: float) -> bool:
        return knee_angle >= self.KNEE_EXTENSION and torso_angle >= self.TORSO_TOLERANCE

    def _evaluate_torso_form(self, torso_angle: float, faults: List[Dict[str, str]]) -> bool:
        if torso_angle < self.TORSO_TOLERANCE:
            self._torso_bad_frame_counter += 1
        else:
            self._torso_bad_frame_counter = 0

        if self._torso_form_bad:
            if torso_angle >= self.TORSO_RECOVERY_TOLERANCE:
                self._torso_form_bad = False
        elif self._torso_bad_frame_counter >= self.TORSO_BAD_FRAME_GRACE:
            self._torso_form_bad = True

        if self._torso_form_bad:
            faults.append(make_fault("TORSO_LEAN", "high", "Keep your torso controlled"))
            self._form_maintained = False
            return False
        return True

    def process_frame(self, landmarks_dict: Dict[str, Any], timestamp_ms: float | None = None) -> Dict[str, Any]:
        timestamp_ms = timestamp_ms if timestamp_ms is not None else time.monotonic() * 1000
        faults: List[Dict[str, str]] = []
        perfect_form = True

        if not self._has_required_side(landmarks_dict):
            self._landmark_loss_counter += 1
            if self._landmark_loss_counter >= self.DEBOUNCE_FRAMES:
                self.state = SquatState.PAUSED
                self._calibrated = False
                self._calibration_counter = 0
                self._form_maintained = True
                self._reset_form_tracking()
                self._reset_rep_quality()
                faults.append(make_fault("FULL_BODY_NOT_VISIBLE", "high", "Full body not visible"))
            return self._status(perfect_form=False, faults=faults, setup_guidance="Move so shoulders, hips, knees, and ankles are visible")

        self._landmark_loss_counter = 0
        knee_angle, torso_angle = self._angles(landmarks_dict)
        if knee_angle is None or torso_angle is None:
            faults.append(make_fault("LANDMARKS_MISSING", "high", "Full body not visible"))
            return self._status(perfect_form=False, faults=faults, setup_guidance="Move so your full body is visible")

        if not self._calibrated:
            if not self._is_standing_for_calibration(knee_angle, torso_angle):
                self.state = SquatState.IDLE
                self._calibration_counter = 0
                faults.append(make_fault("NOT_STANDING", "medium", "Stand tall for calibration"))
                return self._status(perfect_form=True, faults=faults, setup_guidance="Stand tall with knees and hips extended", knee_angle=knee_angle, torso_angle=torso_angle)

            self.state = SquatState.CALIBRATING
            self._calibration_counter += 1
            if self._standing_knee_baseline is None:
                self._standing_knee_baseline = knee_angle
            else:
                self._standing_knee_baseline = (self._standing_knee_baseline * 0.9) + (knee_angle * 0.1)
            faults.append(make_fault("CALIBRATING", "info", "Stand still for calibration"))
            if self._calibration_counter >= self.CALIBRATION_FRAMES:
                self._calibrated = True
                self.state = SquatState.STANDING
                self._form_maintained = True
                self._reset_form_tracking()
                faults = []
            return self._status(perfect_form=True, faults=faults, setup_guidance="Stand tall for calibration", knee_angle=knee_angle, torso_angle=torso_angle)

        rep_completed = False
        rep_aborted = False
        rep_quality = None

        if self.state in (SquatState.PAUSED, SquatState.IDLE, SquatState.CALIBRATING):
            self.state = SquatState.STANDING

        if self.state == SquatState.STANDING:
            if knee_angle < self.DESCENT_START:
                self.state = SquatState.DESCENDING
                self._form_maintained = True
                self._start_rep_quality(timestamp_ms, knee_angle, torso_angle)
        elif self.state == SquatState.DESCENDING:
            if knee_angle <= self.DEPTH_THRESHOLD:
                self.state = SquatState.BOTTOM
            elif knee_angle >= self.KNEE_EXTENSION:
                faults.append(make_fault("INSUFFICIENT_DEPTH", "high", "Squat lower before standing"))
                self._rep_fault_codes.add("INSUFFICIENT_DEPTH")
                self.state = SquatState.STANDING
                rep_aborted = True
                rep_quality = self._finish_rep_quality(timestamp_ms, counted=False, result="aborted")
        elif self.state == SquatState.BOTTOM:
            if knee_angle > self.DEPTH_THRESHOLD:
                self.state = SquatState.ASCENDING
        elif self.state == SquatState.ASCENDING:
            if knee_angle >= self.KNEE_EXTENSION:
                self.state = SquatState.STANDING
                if self._form_maintained:
                    self.rep_count += 1
                    rep_completed = True
                    rep_quality = self._finish_rep_quality(timestamp_ms, counted=True, result="completed")
                else:
                    rep_aborted = True
                    rep_quality = self._finish_rep_quality(timestamp_ms, counted=False, result="aborted")

        if self.state in (SquatState.DESCENDING, SquatState.BOTTOM, SquatState.ASCENDING):
            if not self._evaluate_torso_form(torso_angle, faults):
                perfect_form = False

        self._update_rep_quality(knee_angle, torso_angle, faults)

        return self._status(
            perfect_form=perfect_form,
            faults=faults,
            knee_angle=knee_angle,
            torso_angle=torso_angle,
            rep_completed=rep_completed,
            rep_aborted=rep_aborted,
            rep_quality=rep_quality,
        )
