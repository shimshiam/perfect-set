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
│           └── drawing.js
├── /backend
│   ├── server.py               # FastAPI + WebSocket
│   ├── main.py                 # Local OpenCV test
│   ├── /models
│   │   └── pose_detector.py
│   ├── /heuristics
│   │   ├── pushup.py
│   │   └── squat.py  # Placeholder for future squat tracking
│   └── /utils
│       ├── geometry.py 
│       └── video_utils.py
```

## 3. Core Mathematical Heuristics (The Pushup Logic)
* **Rep Counter:** A rep is only counted if the elbow angle breaks below 90deg on descent and returns to 160deg+ on ascent.
* **Form Gating:** Reps with bad form (back angle < 140deg) are detected but NOT counted.
* **Orientation Gate:** Compares shoulder Y vs ankle Y. If the person is standing upright, rep counting is locked (prevents "standing pushup" false positives).
* **Stabilization Gate:** Requires 30 frames (~2s) of continuous horizontal posture before form checking activates (prevents false "bad form" during transition to floor).
* **Proximity Gate:** If shoulder-to-shoulder x-distance exceeds 35% of frame width, tracking pauses with "Step back" warning (prevents depth distortion false reps).
* **Debounce:** Requires 15 consecutive frames without landmarks before dropping to PAUSED (prevents UI flickering).
* **State Machine:** PAUSED → IDLE → STABILIZING → UP → DESCENDING → BOTTOM → ASCENDING → UP (rep counted).

## 4. Current State & Progress

### Completed Modules:
* [x] **Project Structure:** Full-stack directory with `__init__.py` markers.
* [x] **`backend/utils/geometry.py`:** `calculate_angle` using vector dot products.
* [x] **`backend/models/pose_detector.py`:** `PoseDetector` wrapper for MediaPipe. Upgraded to `model_complexity=2`, raised confidence thresholds to 0.7, and added Exponential Moving Average (EMA) smoothing (`alpha=0.6`) on all landmarks to reduce tracking jitter.
* [x] **`backend/heuristics/pushup.py`:** State-machine tracker with form-gated rep counting. (Fixed form check overriding bug during UP -> DESCENDING transition).
* [x] **`backend/utils/video_utils.py`:** Visualization for local OpenCV test suite.
* [x] **`backend/main.py`:** Local OpenCV test suite.
* [x] **`backend/server.py`:** FastAPI WebSocket server — verified end-to-end.
* [x] **`frontend/`:** React + Vite app with webcam capture, WebSocket streaming, skeleton overlay, dashboard, and session log. Verified full-stack pipeline.
* [x] **Audio Feedback:** Real-time synthesized audio cues for counted reps (ding) and form warnings (buzz).
* [x] **Session Export:** Download complete session logs as JSON with timestamps and form flags.

### Unresolved Bugs / Known Issues:
* *(None currently — landmark jitter resolved via EMA smoothing and upgraded model complexity.)*

### Immediate Next Steps:
* **Additional Exercises:** Implement squat tracker using the same state-machine pattern.
* **Session Persistence:** Save session data to localStorage or a database.
* **Production Build:** Deploy with HTTPS for secure webcam access on non-localhost.

## 5. Development Protocols

### "Review the code" Protocol
Whenever the user requests a code review, the AI must:
1.  **Check for Errors:** Identify logic flaws, syntax errors, and potential bugs. 
2.  **Optimize:** Suggest or implement performance improvements and cleaner code patterns.
3.  **Update Docs:** Proactively update `README.md` and `PROJECT_STATE.md` to reflect the latest changes or fixes.  **DO THIS FIRST** 


