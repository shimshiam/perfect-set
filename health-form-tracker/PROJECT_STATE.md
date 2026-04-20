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
* [x] **`backend/utils/geometry.py`:** Created robust `calculate_angle` function using vector dot products, handling floating-point errors and division by zero.
* [x] **`backend/models/pose_detector.py`:** Built `PoseDetector` wrapper for MediaPipe to ingest OpenCV frames and extract normalized (x,y) landmarks for relevant joints.

### Unresolved Bugs / Known Issues:
* None currently. 

### Immediate Next Steps:
* Await direction for the next sprint (expected to be `backend/heuristics/pushup.py` implementation, integrating the geometry utilities and the pose detector).
