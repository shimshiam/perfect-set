# Physical Health Form Correction - Project State

## 1. The Tech Stack
* **Backend:** Python, FastAPI, WebSockets (for real-time streaming).
* **Computer Vision & AI:** OpenCV (frame processing), PyTorch (for potential custom models later), and MediaPipe Pose 0.10.14 (for initial lightweight, CPU-friendly MVP).
* **Frontend:** React.js.
* **Hardware:** Standard local webcam. 
* **Environment:** Device-agnostic (handling CPU or CUDA gracefully).

## 2. Project Architecture
```text
/health-form-tracker
├── /frontend               # React app (next)
├── /backend
│   ├── __init__.py         # Package marker
│   ├── server.py           # FastAPI + WebSocket server
│   ├── main.py             # Local OpenCV test suite
│   ├── test_ws.py          # WebSocket integration test
│   ├── /models
│   │   └── pose_detector.py
│   ├── /heuristics
│   │   ├── pushup.py
│   │   └── squat.py        # Placeholder
│   └── /utils
│       ├── geometry.py
│       └── video_utils.py
```

## 3. Core Mathematical Heuristics (The Pushup Logic)
* **Rep Counter:** A rep is only counted if the elbow angle (shoulder-elbow-wrist) breaks below 90 degrees on the descent and returns to ~160-180 degrees on the ascent.
* **Form Gating:** Reps performed with bad form (back angle below 165°) are detected but NOT counted. The user sees "Rep not counted: bad form."
* **Form Correction:** The back must remain straight. The angle between the shoulder, hip, and ankle must remain approximately 170-180 degrees. If it dips or bows, trigger a form warning.
* **Angle Calculation:** We calculate the angles of specific joints using the dot product of two vectors derived from (x, y) coordinates. 

## 4. Current State & Progress

### Completed Modules:
* [x] **Project Structure:** Directory skeleton with proper `__init__.py` package markers.
* [x] **`backend/utils/geometry.py`:** Robust `calculate_angle` function using vector dot products.
* [x] **`backend/models/pose_detector.py`:** `PoseDetector` wrapper for MediaPipe Pose.
* [x] **`backend/heuristics/pushup.py`:** State-machine tracker with form-gated rep counting.
* [x] **`backend/utils/video_utils.py`:** Visualization module for skeleton drawing and HUD overlay.
* [x] **`backend/main.py`:** Local OpenCV test suite consuming tracker angles directly.
* [x] **`backend/server.py`:** FastAPI WebSocket server — tested and verified end-to-end.

### Unresolved Bugs / Known Issues:
* **Environment Jitter:** Potential for minor landmark jitter; may need a temporal smoothing buffer in future iterations.
* *[Fixed]* **HUD Angle Display Bug:** Hardcoded left-side anchoring replaced with dynamic side detection.
* *[Fixed]* **Bad-Form Reps Counted:** Reps are now form-gated; only counted if back alignment was maintained throughout the full cycle.
* *[Fixed]* **Redundant Angle Calculation:** `main.py` no longer recalculates angles; consumes them from the tracker's status dict.
* *[Fixed]* **Missing `__init__.py` Files:** All backend subdirectories now have package markers.

### Immediate Next Steps:
* **Frontend Development:** Initialize the React + Vite application to consume the WebSocket stream.
* **Canvas Rendering:** Draw skeleton and HUD on the client side using landmark data from the server.
* **Session Dashboard:** Build a polished dark-mode UI with rep history, form stats, and live feedback.

## 5. Development Protocols

### "Review the code" Protocol
Whenever the user requests a code review, the AI must:
1.  **Check for Errors:** Identify logic flaws, syntax errors, and potential bugs.
2.  **Optimize:** Suggest or implement performance improvements and cleaner code patterns.
3.  **Update Docs:** Proactively update `README.md` and `PROJECT_STATE.md` to reflect the latest changes or fixes.
