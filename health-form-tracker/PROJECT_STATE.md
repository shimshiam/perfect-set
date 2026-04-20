# Physical Health Form Correction - Project State

## 1. The Tech Stack
* **Backend:** Python, FastAPI, WebSockets (for real-time streaming).
* **Computer Vision & AI:** OpenCV (frame processing), PyTorch (for potential custom models later), and MediaPipe Pose (for initial lightweight, CPU-friendly MVP).
* **Frontend:** React.js.
* **Hardware:** Standard local webcam. 
* **Environment:** Device-agnostic (handling CPU or CUDA gracefully).

## 2. Project Architecture
```text
/health-form-tracker
├── /frontend               # React app 
├── /backend
│   ├── main.py             # FastAPI server & WebSockets
│   ├── /models             # MediaPipe/PyTorch initialization
│   ├── /heuristics         # Biomechanical logic (pushup.py)
│   └── /utils              # Math and drawing utilities
```

## 3. Core Mathematical Heuristics (The Pushup Logic)
* **Rep Counter:** A rep is only counted if the elbow angle (shoulder-elbow-wrist) breaks below 90 degrees on the descent and returns to ~160-180 degrees on the ascent.
* **Form Correction:** The back must remain straight. The angle between the shoulder, hip, and ankle must remain approximately 170-180 degrees. If it dips or bows, trigger a form warning.
* **Angle Calculation:** We calculate the angles of specific joints using the dot product of two vectors derived from (x, y) coordinates. 

## 4. Current State & Progress

### Completed Modules:
* [x] **Project Structure:** Initial directory skeleton setup.
* [x] **`backend/utils/geometry.py`:** Created robust `calculate_angle` function using vector dot products.
* [x] **`backend/models/pose_detector.py`:** Built `PoseDetector` wrapper with fallback mechanisms for better environment compatibility.
* [x] **`backend/heuristics/pushup.py`:** Developed a state-machine based tracker for rep counting and form feedback.
* [x] **`backend/utils/video_utils.py`:** Created dedicated visualization module for skeleton drawing and premium HUD.
* [x] **Code Review & Refactoring:** Modularized the local test suite and decoupled visualization from core logic.

### Unresolved Bugs / Known Issues:
* **Environment Jitter:** Potential for minor landmark jitter; may need a temporal smoothing buffer in future iterations.
* *[Fixed]* **HUD Angle Display Bug:** The visual debugger in `main.py` hardcoded the `calculate_angle` check to the `left` side, which would have displayed 0.0 or incorrect angles if the user's left side was occluded. Fixed by dynamically tracking the `anchor_side` to match `draw_angles`.

### Immediate Next Steps:
* **FastAPI Integration:** Refactor `backend/main.py` into a FastAPI application serving results over WebSockets.
* **Frontend Development:** Initialize the React application to consume the WebSocket stream and provide a modern, responsive UI.

## 5. Development Protocols

### "Review the code" Protocol
Whenever the user requests a code review, the AI must:
1.  **Check for Errors:** Identify logic flaws, syntax errors, and potential bugs.
2.  **Optimize:** Suggest or implement performance improvements and cleaner code patterns.
3.  **Update Docs:** Proactively update `README.md` and `PROJECT_STATE.md` to reflect the latest changes or fixes.
