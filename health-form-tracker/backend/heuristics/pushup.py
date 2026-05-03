from enum import Enum, auto
from typing import Any, Dict, List, Sequence, Tuple
import time

from heuristics.common import base_status, calibration_status, make_fault
from utils.geometry import calculate_angle


class PushupState(Enum):
    PAUSED = auto()
    IDLE = auto()
    CALIBRATING = auto()
    UP = auto()
    DESCENDING = auto()
    BOTTOM = auto()
    ASCENDING = auto()


class PushupTracker:
    """State machine for calibrated pushup counting and form coaching."""

    EXERCISE = "pushup"

    ELBOW_FLEXION = 90.0
    ELBOW_EXTENSION = 160.0
    BACK_TOLERANCE = 140.0
    BACK_RECOVERY_TOLERANCE = 145.0
    BACK_BAD_FRAME_GRACE = 3
    VERTICAL_THRESHOLD = 0.40
    PROXIMITY_THRESHOLD = 0.35
    CALIBRATION_FRAMES = 30
    STABILIZE_FRAMES = CALIBRATION_FRAMES
    DEBOUNCE_FRAMES = 15

    def __init__(self):
        self.state = PushupState.PAUSED
        self.rep_count = 0
        self._form_maintained = True
        self._landmark_loss_counter = 0
        self._bad_back_frame_counter = 0
        self._back_form_bad = False
        self._calibration_counter = 0
        self._calibrated = False
        self._baseline_shoulder_width: float | None = None
        self._rep_start_ms: float | None = None
        self._rep_min_elbow: float | None = None
        self._rep_max_elbow: float | None = None
        self._rep_min_back: float | None = None
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
    def _avg_coord(cls, landmarks: Dict, keys: List[str], axis: int, space: str = "image") -> float | None:
        values = []
        for key in keys:
            coord = cls._coord(landmarks, key, space)
            if coord is not None and len(coord) > axis:
                values.append(coord[axis])
        return sum(values) / len(values) if values else None

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

    def _angles(self, landmarks: Dict[str, Any]) -> Tuple[float | None, float | None]:
        elbow_angles: List[Tuple[float, float]] = []
        back_angles: List[Tuple[float, float]] = []

        for side in ("left", "right"):
            elbow_angle = self._calculate_side_angle(landmarks, side, ("shoulder", "elbow", "wrist"))
            if elbow_angle is not None:
                elbow_angles.append((elbow_angle, self._side_weight(landmarks, side, ["shoulder", "elbow", "wrist"])))

            back_angle = self._calculate_side_angle(landmarks, side, ("shoulder", "hip", "ankle"), space="world")
            if back_angle is None:
                back_angle = self._calculate_side_angle(landmarks, side, ("shoulder", "hip", "ankle"))
            if back_angle is None:
                back_angle = self._calculate_side_angle(landmarks, side, ("shoulder", "hip", "knee"), space="world")
            if back_angle is None:
                back_angle = self._calculate_side_angle(landmarks, side, ("shoulder", "hip", "knee"))
            if back_angle is not None:
                joints = ["shoulder", "hip", "ankle"] if self._coord(landmarks, f"{side}_ankle") is not None else ["shoulder", "hip", "knee"]
                back_angles.append((back_angle, self._side_weight(landmarks, side, joints)))

        return self._weighted_mean(elbow_angles), self._weighted_mean(back_angles)

    def _has_required_side(self, landmarks: Dict[str, Any]) -> bool:
        upper_body_joints = ("shoulder", "elbow", "wrist", "hip")
        return any(
            all(self._coord(landmarks, f"{side}_{joint}") is not None for joint in upper_body_joints) and
            (
                self._coord(landmarks, f"{side}_ankle") is not None or
                self._coord(landmarks, f"{side}_knee") is not None
            )
            for side in ("left", "right")
        )

    def _is_horizontal(self, landmarks: Dict[str, Any]) -> bool:
        shoulder_y = self._avg_coord(landmarks, ["left_shoulder", "right_shoulder"], 1)
        lower_body_y = self._avg_coord(landmarks, ["left_ankle", "right_ankle"], 1)
        if lower_body_y is None:
            lower_body_y = self._avg_coord(landmarks, ["left_knee", "right_knee"], 1)
        if shoulder_y is None or lower_body_y is None:
            return False
        return abs(shoulder_y - lower_body_y) < self.VERTICAL_THRESHOLD

    def _shoulder_width(self, landmarks: Dict[str, Any]) -> float | None:
        left_shoulder = self._coord(landmarks, "left_shoulder")
        right_shoulder = self._coord(landmarks, "right_shoulder")
        if left_shoulder is None or right_shoulder is None:
            return None
        return abs(left_shoulder[0] - right_shoulder[0])

    def _is_too_close(self, landmarks: Dict[str, Any]) -> bool:
        width = self._shoulder_width(landmarks)
        return width is not None and width > self.PROXIMITY_THRESHOLD

    def _reset_back_form_tracking(self) -> None:
        self._bad_back_frame_counter = 0
        self._back_form_bad = False

    def _reset_rep_quality(self) -> None:
        self._rep_start_ms = None
        self._rep_min_elbow = None
        self._rep_max_elbow = None
        self._rep_min_back = None
        self._rep_fault_codes = set()

    def _start_rep_quality(self, timestamp_ms: float, elbow_angle: float, back_angle: float) -> None:
        self._rep_start_ms = timestamp_ms
        self._rep_min_elbow = elbow_angle
        self._rep_max_elbow = elbow_angle
        self._rep_min_back = back_angle
        self._rep_fault_codes = set()

    def _update_rep_quality(self, elbow_angle: float, back_angle: float, faults: List[Dict[str, str]]) -> None:
        if self._rep_start_ms is None:
            return
        self._rep_min_elbow = min(self._rep_min_elbow, elbow_angle) if self._rep_min_elbow is not None else elbow_angle
        self._rep_max_elbow = max(self._rep_max_elbow, elbow_angle) if self._rep_max_elbow is not None else elbow_angle
        self._rep_min_back = min(self._rep_min_back, back_angle) if self._rep_min_back is not None else back_angle
        for fault in faults:
            self._rep_fault_codes.add(fault["code"])

    def _finish_rep_quality(self, timestamp_ms: float, counted: bool, result: str) -> Dict[str, Any]:
        duration_ms = None if self._rep_start_ms is None else max(0, int(timestamp_ms - self._rep_start_ms))
        quality = {
            "exercise": self.EXERCISE,
            "result": result,
            "counted": counted,
            "duration_ms": duration_ms,
            "min_elbow_angle": self._round_angle(self._rep_min_elbow),
            "max_elbow_angle": self._round_angle(self._rep_max_elbow),
            "min_back_angle": self._round_angle(self._rep_min_back),
            "fault_codes": sorted(self._rep_fault_codes),
        }
        self._reset_rep_quality()
        return quality

    @staticmethod
    def _round_angle(value: float | None) -> float | None:
        return round(value, 1) if value is not None else None

    def _calibration(self, message: str = "Hold a stable plank position") -> Dict[str, Any]:
        return calibration_status(self._calibrated, self._calibration_counter / self.CALIBRATION_FRAMES, message)

    def _status(
        self,
        *,
        perfect_form: bool,
        faults: List[Dict[str, str]] | None = None,
        setup_guidance: str | None = None,
        elbow_angle: float | None = None,
        back_angle: float | None = None,
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
            angles={"elbow_angle": elbow_angle, "back_angle": back_angle},
        )

    def _evaluate_back_form(self, back_angle: float, faults: List[Dict[str, str]]) -> bool:
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
            faults.append(make_fault("BACK_SAG", "high", "Keep your back straight"))
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
                self.state = PushupState.PAUSED
                self._calibrated = False
                self._calibration_counter = 0
                self._form_maintained = True
                self._reset_back_form_tracking()
                self._reset_rep_quality()
                faults.append(make_fault("LANDMARKS_MISSING", "high", "Full body not visible"))
            return self._status(perfect_form=False, faults=faults, setup_guidance="Move so shoulders, elbows, wrists, hips, and at least knees are visible")

        self._landmark_loss_counter = 0
        elbow_angle, back_angle = self._angles(landmarks_dict)
        if elbow_angle is None or back_angle is None:
            faults.append(make_fault("LANDMARKS_MISSING", "high", "Full body not visible"))
            return self._status(perfect_form=False, faults=faults, setup_guidance="Move so your full side profile is visible")

        if self._is_too_close(landmarks_dict):
            faults.append(make_fault("TOO_CLOSE", "medium", "Step back from camera"))
            return self._status(perfect_form=False, faults=faults, setup_guidance="Step back until your full body fits", elbow_angle=elbow_angle, back_angle=back_angle)

        if not self._is_horizontal(landmarks_dict):
            self.state = PushupState.IDLE
            self._calibrated = False
            self._calibration_counter = 0
            self._form_maintained = True
            self._reset_back_form_tracking()
            self._reset_rep_quality()
            faults.append(make_fault("BODY_NOT_HORIZONTAL", "medium", "Get into a plank position"))
            return self._status(perfect_form=True, faults=faults, setup_guidance="Get into a side-on plank position", elbow_angle=elbow_angle, back_angle=back_angle)

        if not self._calibrated:
            self.state = PushupState.CALIBRATING
            self._calibration_counter += 1
            width = self._shoulder_width(landmarks_dict)
            if width is not None:
                if self._baseline_shoulder_width is None:
                    self._baseline_shoulder_width = width
                else:
                    self._baseline_shoulder_width = (self._baseline_shoulder_width * 0.9) + (width * 0.1)
            faults.append(make_fault("CALIBRATING", "info", "Hold plank for calibration"))
            if self._calibration_counter >= self.CALIBRATION_FRAMES:
                self._calibrated = True
                self.state = PushupState.UP
                self._form_maintained = True
                self._reset_back_form_tracking()
                faults = []
            return self._status(perfect_form=True, faults=faults, setup_guidance="Hold a stable plank position", elbow_angle=elbow_angle, back_angle=back_angle)

        finalize_rep = False
        rep_completed = False
        rep_aborted = False
        rep_quality = None

        if self.state in (PushupState.PAUSED, PushupState.IDLE, PushupState.CALIBRATING):
            self.state = PushupState.UP

        if self.state == PushupState.UP:
            if elbow_angle < self.ELBOW_EXTENSION:
                self.state = PushupState.DESCENDING
                self._form_maintained = True
                self._start_rep_quality(timestamp_ms, elbow_angle, back_angle)
        elif self.state == PushupState.DESCENDING:
            if elbow_angle <= self.ELBOW_FLEXION:
                self.state = PushupState.BOTTOM
            elif elbow_angle >= self.ELBOW_EXTENSION:
                self.state = PushupState.UP
                self._reset_rep_quality()
        elif self.state == PushupState.BOTTOM:
            if elbow_angle > self.ELBOW_FLEXION:
                self.state = PushupState.ASCENDING
        elif self.state == PushupState.ASCENDING:
            if elbow_angle >= self.ELBOW_EXTENSION:
                self.state = PushupState.UP
                finalize_rep = True
            elif elbow_angle <= self.ELBOW_FLEXION:
                self.state = PushupState.BOTTOM

        if not self._evaluate_back_form(back_angle, faults):
            perfect_form = False

        self._update_rep_quality(elbow_angle, back_angle, faults)

        if finalize_rep:
            if self._form_maintained:
                self.rep_count += 1
                rep_completed = True
                rep_quality = self._finish_rep_quality(timestamp_ms, counted=True, result="completed")
            else:
                faults.append(make_fault("REP_BAD_FORM", "high", "Rep not counted: bad form"))
                self._rep_fault_codes.add("REP_BAD_FORM")
                rep_aborted = True
                rep_quality = self._finish_rep_quality(timestamp_ms, counted=False, result="aborted")
            self._form_maintained = True

        return self._status(
            perfect_form=perfect_form,
            faults=faults,
            elbow_angle=elbow_angle,
            back_angle=back_angle,
            rep_completed=rep_completed,
            rep_aborted=rep_aborted,
            rep_quality=rep_quality,
        )
