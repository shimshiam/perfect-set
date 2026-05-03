# Physical Health Form Correction - Project State

## 1. The Tech Stack
* **Backend:** Python, FastAPI, WebSockets (for real-time streaming).
* **Computer Vision & AI:** OpenCV (frame processing), PyTorch (for potential custom models later), and MediaPipe Pose 0.10.14 tuned for real-time local inference with landmark visibility filtering, EMA temporal smoothing, and 3D world-landmark posture checks.
* **Frontend:** React.js.
* **Hardware:** Standard local webcam. 
* **Environment:** Device-agnostic (handling CPU or CUDA gracefully).

## 2. Project Architecture
```text
/health-form-tracker
├── /frontend                   # React + Vite app
│   ├── index.html
│   └── /src
│       ├── main.jsx
│       ├── App.jsx / App.css
│       ├── index.css           # Design tokens & reset
│       ├── /hooks
│       │   ├── useWebcam.js
│       │   └── useWebSocket.js
│       ├── /components
│       │   ├── VideoFeed.jsx/css
│       │   ├── Dashboard.jsx/css
│       │   └── SessionLog.jsx/css
│       └── /utils
│           ├── drawing.js
│           └── sessionStorage.js
├── /backend
│   ├── server.py               # FastAPI + WebSocket
│   ├── main.py                 # Local OpenCV test
│   ├── /models
│   │   └── pose_detector.py
│   ├── /heuristics
│   │   ├── common.py
│   │   ├── pushup.py
│   │   └── squat.py
│   ├── /tests
│   │   ├── test_pushup.py
│   │   └── test_server.py
│   └── /utils
│       ├── geometry.py
│       ├── ssl_utils.py
│       └── video_utils.py
```

## 3. Core Mathematical Heuristics
* **Shared Response Shape:** Pushup and squat trackers now return `exercise`, structured `faults`, compatibility `warnings`, `setup_guidance`, `calibration`, optional `rep_quality`, and exercise-specific angles.
* **Guided Calibration:** Pushups require a stable plank hold; squats require a tall standing hold. Rep counting stays locked until calibration completes.
* **Pushup Counter:** A rep is only counted if the elbow angle breaks below 90deg on descent and returns to 160deg+ on ascent.
* **Pushup Form Gating:** Sustained bad back form (`BACK_SAG`) rejects the rep. Back-angle evaluation prefers 3D world landmarks, falls back from ankle to knee when ankles are low-confidence, and clears with hysteresis after recovery.
* **Squat Counter:** A rep is only counted if the knee angle descends to 105deg or below and returns to 160deg+ standing extension.
* **Squat Form Gating:** Insufficient depth (`INSUFFICIENT_DEPTH`) and sustained severe torso lean (`TORSO_LEAN`) produce structured faults and reject reps. Torso thresholds were relaxed after live calibration feedback so normal user anatomy/mobility is not over-penalized.
* **Debounce:** Both trackers require 15 consecutive frames without required landmarks before dropping to PAUSED.

## 4. Current State & Progress

### Completed Modules:
* [x] **Project Structure:** Full-stack directory with `__init__.py` markers.
* [x] **`backend/utils/geometry.py`:** `calculate_angle` using vector dot products.
* [x] **`backend/utils/ssl_utils.py`:** Centralizes the macOS MediaPipe certificate workaround. Detector initialization now uses a scoped HTTPS context backed by `certifi`, with an opt-out env var (`PERFECT_SET_DISABLE_MEDIAPIPE_SSL_WORKAROUND=1`) instead of a process-wide import-time override.
* [x] **`backend/models/pose_detector.py`:** `PoseDetector` wrapper for MediaPipe. It now runs in a faster real-time configuration (`model_complexity=1`), downsizes oversized frames before inference, filters out low-visibility landmarks with a practical 0.45 threshold, keeps EMA-smoothed 2D image landmarks for rendering, and preserves EMA-smoothed 3D world landmarks for posture checks. Knee landmarks are included for squat tracking and pushup ankle fallback.
* [x] **`backend/heuristics/common.py`:** Shared helpers for structured faults, warning compatibility, calibration status, and tracker status payloads.
* [x] **`backend/heuristics/pushup.py`:** Calibrated state-machine tracker with form-gated rep counting, structured faults, setup guidance, and per-rep quality metrics (`min_elbow_angle`, `max_elbow_angle`, `min_back_angle`, duration, and fault codes). Pushup calibration now accepts a visible knee when ankles are not reliable and uses a more forgiving plank-orientation gate.
* [x] **`backend/heuristics/squat.py`:** Calibrated squat tracker with depth validation, torso-lean rejection, structured faults, and per-rep quality metrics (`min_knee_angle`, standing knee angle, min torso angle, duration, and fault codes). Torso lean gating now uses a lower 110deg active threshold with a 5-frame grace window and the coaching message "Keep your torso controlled."
* [x] **`backend/utils/video_utils.py`:** Visualization for local OpenCV test suite. Fixed `draw_angles` to resolve the best visible landmark side independently per joint (elbow vs. hip), preventing silent rendering miss.
* [x] **`backend/main.py`:** Local OpenCV test suite. Added camera warmup loop and consecutive-failure retry counter (tolerates up to 10 bad frames before exiting). SSL setup is now inherited through `PoseDetector` instead of duplicated at the entry-point.
* [x] **`backend/server.py`:** FastAPI WebSocket server. `/ws/pushups` remains available and `/ws/squats` now uses the same binary JPEG/JSON compatibility pipeline. `STATUS`, `REP_COMPLETED`, and `REP_ABORTED` payloads include exercise and rep quality data.
* [x] **`backend/tests/`:** Automated `unittest` coverage now includes pushup calibration, structured faults, rep quality, squat calibration, valid squat reps, insufficient-depth aborts, torso-lean aborts, and pushup/squat WebSocket event payloads.
* [x] **`frontend/`:** React + Vite app with manual Pushups/Squats selection, exercise-specific WebSocket reconnects, calibration progress, setup guidance, structured fault display, rep quality summary, skeleton knee rendering, and mixed-exercise session history.
* [x] **Audio Feedback:** Real-time synthesized audio cues for counted reps and structured form faults. Fault coaching is gated by the explicit "Enable Voice Coaching" user action and cooled down by fault code.
* [x] **Session Export:** Session storage is v2 and multi-exercise. Existing v1 pushup sessions migrate automatically, and exports include exercise, result, timestamps, quality metrics, and fault codes.

### Unresolved Bugs / Known Issues:
* No new correctness regressions were found in the 2026-05-03 multi-exercise implementation after backend automated validation and frontend production build.
* `npm run lint` still hung under local Node v25.9.0 before producing diagnostics on 2026-05-03. Recheck lint with a stable Node LTS runtime before treating frontend lint verification as complete.

### Immediate Next Steps:
* **Frontend Lint Runtime:** Re-run `npm run lint` under Node LTS.
* **Exercise Tuning:** Validate pushup/squat thresholds against real webcam sessions and tune calibration thresholds if needed.
* **Production Build:** Deploy with HTTPS for secure webcam access on non-localhost.

## 5. Development Protocols

### "Review the code" Protocol
Whenever the user requests a code review, the AI must:
1.  **Check for Errors:** Identify logic flaws, syntax errors, and potential bugs. 
2.  **Optimize:** Suggest or implement performance improvements and cleaner code patterns.
3.  **Update Docs:** Proactively update `README.md` and `PROJECT_STATE.md` to reflect the latest changes or fixes.  **DO THIS FIRST** 
