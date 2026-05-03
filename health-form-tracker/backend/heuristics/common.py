from typing import Any, Dict, Iterable, List


def make_fault(code: str, severity: str, message: str) -> Dict[str, str]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
    }


def warnings_from_faults(faults: Iterable[Dict[str, str]]) -> List[str]:
    return [fault["message"] for fault in faults if fault.get("message")]


def calibration_status(complete: bool, progress: float, message: str) -> Dict[str, Any]:
    return {
        "complete": complete,
        "progress": round(max(0.0, min(1.0, progress)), 2),
        "message": message,
    }


def base_status(
    *,
    exercise: str,
    rep_count: int,
    state: str,
    perfect_form: bool,
    faults: List[Dict[str, str]] | None = None,
    setup_guidance: str | None = None,
    calibration: Dict[str, Any] | None = None,
    rep_quality: Dict[str, Any] | None = None,
    angles: Dict[str, float | None] | None = None,
    rep_completed: bool = False,
    rep_aborted: bool = False,
) -> Dict[str, Any]:
    fault_list = faults or []
    status = {
        "exercise": exercise,
        "rep_count": rep_count,
        "rep_completed": rep_completed,
        "rep_aborted": rep_aborted,
        "state": state,
        "perfect_form": perfect_form,
        "faults": fault_list,
        "warnings": warnings_from_faults(fault_list),
        "setup_guidance": setup_guidance,
        "calibration": calibration or calibration_status(True, 1.0, "Ready"),
        "rep_quality": rep_quality,
    }
    if angles:
        status.update(angles)
    return status
