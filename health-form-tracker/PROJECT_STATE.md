# Physical Health Form Correction - Project State

## 1. The Tech Stack
* **Backend:** Python, FastAPI, WebSockets (for real-time streaming).
* **Computer Vision & AI:** OpenCV (frame processing), PyTorch (for potential custom models later), and MediaPipe Pose 0.10.14 (`model_complexity=2` for maximum landmark accuracy, with EMA temporal smoothing for jitter reduction).
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
│   │   ├── pushup.py
│   │   └── squat.py  # Placeholder for future squat tracking
│   ├── /tests
│   │   ├── test_pushup.py
│   │   └── test_server.py
│   └── /utils
│       ├── geometry.py
│       ├── ssl_utils.py
│       └── video_utils.py
```

## 3. Core Mathematical Heuristics (The Pushup Logic)
* **Rep Counter:** A rep is only counted if the elbow angle breaks below 90deg on descent and returns to 160deg+ on ascent.
* **Form Gating:** Reps with sustained bad form (back angle < 140deg for 3 consecutive active frames) are detected but NOT counted. The warning only clears after the back recovers above 145deg, reducing jitter-induced flicker.
* **Orientation Gate:** Compares shoulder Y vs ankle Y. If the person is standing upright, rep counting is locked (prevents "standing pushup" false positives).
* **Stabilization Gate:** Requires 30 frames (~2s) of continuous horizontal posture before form checking activates (prevents false "bad form" during transition to floor).
* **Proximity Gate:** If shoulder-to-shoulder x-distance exceeds 35% of frame width, tracking pauses with "Step back" warning (prevents depth distortion false reps).
* **Debounce:** Requires 15 consecutive frames without landmarks before dropping to PAUSED (prevents UI flickering).
* **State Machine:** PAUSED → IDLE → STABILIZING → UP → DESCENDING → BOTTOM → ASCENDING → UP (rep counted).

## 4. Current State & Progress

### Completed Modules:
* [x] **Project Structure:** Full-stack directory with `__init__.py` markers.
* [x] **`backend/utils/geometry.py`:** `calculate_angle` using vector dot products.
* [x] **`backend/utils/ssl_utils.py`:** Centralizes the macOS MediaPipe certificate workaround. Detector initialization now uses a scoped HTTPS context backed by `certifi`, with an opt-out env var (`PERFECT_SET_DISABLE_MEDIAPIPE_SSL_WORKAROUND=1`) instead of a process-wide import-time override.
* [x] **`backend/models/pose_detector.py`:** `PoseDetector` wrapper for MediaPipe. Upgraded to `model_complexity=2`, raised confidence thresholds to 0.7, added Exponential Moving Average (EMA) smoothing (`alpha=0.6`) on all landmarks to reduce tracking jitter, and moved macOS certificate handling into the scoped SSL helper used only during `Pose()` initialization.
* [x] **`backend/heuristics/pushup.py`:** State-machine tracker with form-gated rep counting. Bad-form history now stays sticky through ASCENDING→BOTTOM bounces so a rep that already broke form cannot become countable again mid-cycle. Back-form warnings now require 3 consecutive below-threshold frames and clear with hysteresis after recovery above 145deg, which reduces false positives from pose jitter. Rep completion is also evaluated after the final back-form check so a noisy last frame cannot be counted before being rejected.
* [x] **`backend/utils/video_utils.py`:** Visualization for local OpenCV test suite. Fixed `draw_angles` to resolve the best visible landmark side independently per joint (elbow vs. hip), preventing silent rendering miss.
* [x] **`backend/main.py`:** Local OpenCV test suite. Added camera warmup loop and consecutive-failure retry counter (tolerates up to 10 bad frames before exiting). SSL setup is now inherited through `PoseDetector` instead of duplicated at the entry-point.
* [x] **`backend/server.py`:** FastAPI WebSocket server. Fixed `REP_COMPLETED`/`REP_ABORTED` event ordering. The full pose pipeline now runs in `asyncio.to_thread` via a synchronous callable so the event loop stays responsive and the worker thread returns actual landmarks, not a coroutine. `rep_count` is captured before status mutation for reliable event delivery.
* [x] **`backend/tests/`:** Added automated `unittest` regression coverage for stabilization gating, debounced landmark loss, bad-form bounce handling, and WebSocket message ordering / synchronous pipeline execution.
* [x] **`frontend/`:** React + Vite app with webcam capture, WebSocket streaming, skeleton overlay, dashboard, and session log. Session history and rep counters persist in `localStorage`, survive refresh, and still export as JSON. Frame upload now uses one-frame-in-flight backpressure with a latest-frame queue, and the overlay canvas only resizes when the video dimensions actually change.
* [x] **Audio Feedback:** Real-time synthesized audio cues for counted reps (ding) and form warnings (buzz).
* [x] **Session Export:** Download complete session logs as JSON with timestamps and form flags.

### Unresolved Bugs / Known Issues:
* No new correctness regressions were found in the first safety batch after automated validation on 2026-04-23.

### Immediate Next Steps:
* **Additional Exercises:** Implement squat tracker using the same state-machine pattern.
* **Session Expansion:** Extend the persisted session model for multi-exercise support once squat tracking lands.
* **Production Build:** Deploy with HTTPS for secure webcam access on non-localhost.

## 5. Development Protocols

### "Review the code" Protocol
Whenever the user requests a code review, the AI must:
1.  **Check for Errors:** Identify logic flaws, syntax errors, and potential bugs. 
2.  **Optimize:** Suggest or implement performance improvements and cleaner code patterns.
3.  **Update Docs:** Proactively update `README.md` and `PROJECT_STATE.md` to reflect the latest changes or fixes.  **DO THIS FIRST** 
