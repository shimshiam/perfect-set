# Perfect Set: Health Form Tracker

## Description

Perfect Set is a real-time computer vision application that provides automated repetition tracking and heuristic form feedback for pushups and squats. It uses React, FastAPI, OpenCV, and MediaPipe Pose, and runs through a standard webcam with a local backend by default.

The application uses MediaPipe's pretrained pose-estimation pipeline to extract body landmarks. Rule-based state machines then calculate joint angles frame by frame to identify exercise phases, count repetitions that cross configured thresholds, and provide feedback about pushup depth and extension, back alignment, squat depth, and body alignment. Temporal smoothing and multi-frame fault checks reduce sensitivity to brief landmark jitter.

Perfect Set is an experimental fitness-tracking project, not a medical, coaching, or injury-prevention system. Its feedback depends on camera placement, landmark visibility, and manually configured thresholds, so it should not be treated as a guarantee of correct or safe exercise form.

## Key Features

* **Real-Time Inference:** Low-latency video processing and form feedback streamed via WebSockets.
* **Stable Tracking:** MediaPipe Pose running in a real-time configuration with EMA (Exponential Moving Average) smoothing, low-visibility landmark filtering, and 3D world-landmark back-angle checks when enough lower-body landmarks are visible.
* **Heuristic Rep Validation:** Configurable joint-angle thresholds determine exercise phases and repetition completion. Multi-frame back and torso checks prevent a single noisy frame from rejecting a repetition.
* **Guided Setup:** Pushups and squats require a 30-frame setup hold before counting begins. This currently verifies that the required pose and landmarks remain available; it does not personalize the exercise thresholds. Pushups are optimized for side or 3-quarter views and can keep tracking when feet are cropped, as long as the working-side shoulder, elbow, wrist, and hip remain visible.
* **Structured Coaching:** Backend responses include structured fault codes, severity, setup guidance, calibration progress, and per-rep quality metrics in addition to compatibility warning strings.
* **Multi-Exercise Sessions:** The frontend supports manual Pushups/Squats selection, persists mixed workout history, migrates old pushup-only sessions, and exports v2 JSON logs with rep quality data.
* **Faster Streaming:** The frontend now captures downscaled JPEG blobs and streams them as binary WebSocket frames, reducing client/server overhead compared with base64 payloads.
* **Audio Feedback:** Built-in synthesized audio cues announce counted repetitions and detected form faults without requiring the user to watch the dashboard continuously.
* **Data Portability:** Export full session logs to JSON, complete with timestamps and form metadata, for integration with personal trackers.
* **Local by Default:** With the default configuration, webcam frames travel from the browser to a FastAPI backend on the same machine and are processed without being stored. If the frontend is configured to use a remote WebSocket backend, frames will leave the local machine and must be protected in transit.
* **Modern Stack:** A decoupled architecture utilizing a React frontend and a robust Python/FastAPI backend.

## Current Technical Scope and Limitations

* MediaPipe Pose supplies the pretrained pose model. Perfect Set does not currently train or fine-tune a custom PyTorch or TensorFlow model.
* Exercise classifications are produced by manually configured thresholds and state machines, not by a learned form-classification model.
* Cropped-leg pushup mode can count repetitions using upper-body landmarks, but it cannot evaluate back alignment without reliable knee or ankle landmarks.
* Full head-on pushups are less reliable than side and 3-quarter views because elbow depth and body alignment are harder to infer from the available landmarks.
* The automated tests validate geometry, state transitions, fault handling, and WebSocket responses using synthetic landmarks and mocked components. They do not yet establish accuracy on a labeled real-world video dataset.
* Before making comparative accuracy claims, the tracker needs an offline evaluation set with ground-truth repetition boundaries and form-fault labels across multiple users, camera angles, lighting conditions, and occlusion levels.

## Getting Started (Local Development)

Use two terminals: one for the Python backend and one for the React frontend.

### Backend

The backend uses OpenCV and MediaPipe. On macOS, use Python 3.12 for the virtual environment; Python 3.13 may not have a compatible MediaPipe wheel for the pinned dependency.

1.  **Create and activate the backend environment:**
    ```bash
    cd health-form-tracker
    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    ```
2.  **Verify the required backend packages import:**
    ```bash
    python -c "import cv2, mediapipe, uvicorn; print('backend deps ok')"
    ```
3.  **Start the API/WebSocket server:**
    ```bash
    cd backend
    python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
    ```
4.  **Check that it is running:**
    ```bash
    curl http://127.0.0.1:8000/health
    ```

Leave this terminal running while using the frontend.

### Frontend

In a second terminal:

1.  **Install frontend dependencies:**
    ```bash
    cd health-form-tracker/frontend
    npm install
    ```
2.  **Start the Vite dev server:**
    ```bash
    npm run dev -- --host 127.0.0.1
    ```
3.  **Open the app:**
    Visit `http://127.0.0.1:5173/` in your browser. Choose **Pushups** or **Squats**, allow camera access, hold the guided calibration pose until the dashboard shows ready, then begin the set.

For pushups, use a side or 3-quarter camera angle. The tracker can infer lower-body position when feet or knees leave the frame, but it still needs a clear shoulder, elbow, wrist, and hip on at least one side for reliable rep counting.

### Optional Local OpenCV Test

To test the pushup tracker without the React frontend:

```bash
cd health-form-tracker
source .venv/bin/activate
cd backend
python main.py
```

A window will open mirroring your webcam. Perform pushups to see the rep counter and form feedback in real time. Press **'q'** in the video window to exit.

## Running the WebSocket Server

To serve the tracker as an API for the React frontend:

1.  **Start the server:**
    ```bash
    cd health-form-tracker
    source .venv/bin/activate
    cd backend
    python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
    ```
2.  **Health check:** Visit `http://127.0.0.1:8000/health` to verify the server is running.
3.  **WebSocket endpoints:** Connect to `ws://127.0.0.1:8000/ws/pushups` or `ws://127.0.0.1:8000/ws/squats` and send binary JPEG frames. JSON/base64 payloads are still accepted for compatibility:
    ```json
    { "frame": "<base64-encoded JPEG>" }
    ```
4.  **Status payload:** Each `STATUS` response includes the current exercise, calibration state, structured faults, setup guidance, landmarks, angles, processing latency, and optional `rep_quality`. Rep events include the same exercise and quality object:
    ```json
    {
      "type": "STATUS",
      "exercise": "pushup",
      "rep_count": 3,
      "state": "UP",
      "faults": [],
      "calibration": { "complete": true, "progress": 1.0, "message": "Ready" },
      "rep_quality": null
    }
    ```

## Running the Frontend

1.  **Install dependencies** (first time only):
    ```bash
    cd health-form-tracker/frontend
    npm install
    ```
2.  **Start the dev server:**
    ```bash
    npm run dev -- --host 127.0.0.1
    ```
3.  Open `http://127.0.0.1:5173/` in your browser. Make sure the backend server is also running.
4.  Choose **Pushups** or **Squats** in the header. Hold the guided calibration pose until the dashboard shows ready, then start the set.

For best pushup results, keep one side of your upper body visible. Feet and knees may be cropped after setup; missing lower-body landmarks reduce posture strictness instead of blocking counting.

## Validation

Backend unit tests can be run from `health-form-tracker`:

```bash
python3 -m unittest discover backend/tests
```

These tests exercise deterministic tracker behavior with synthetic inputs. They should be supplemented with an offline video evaluation harness before reporting real-world precision, recall, or form-detection accuracy.

Frontend production build can be checked from `health-form-tracker/frontend`:

```bash
npm run build
```

If `npm run lint` hangs under Node 25, rerun it with a stable Node LTS runtime.
