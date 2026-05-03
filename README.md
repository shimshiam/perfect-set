# Perfect Set: Health Form Tracker

## Description

This project is a real-time, privacy-first computer vision application designed to provide immediate physical form correction and automated workout tracking. Built with React, FastAPI, PyTorch, and OpenCV, it acts as a localized digital personal trainer that runs directly through a standard webcam.

The application tracks high-volume pushup and squat sets. By leveraging pose estimation (MediaPipe) and biomechanical vector math, the system calculates joint angles frame-by-frame to enforce strict form requirements. It actively monitors pushup depth/lockout, squat depth, and spinal/torso alignment, automatically filtering out "cheat" reps while tolerating brief landmark jitter instead of failing form on a single noisy frame.

Designed for users managing daily rep goals or strict hypertrophy routines, this tool eliminates the guesswork of solo workouts. It ensures that every logged rep is performed with perfect, injury-free mechanics—all processed locally without sending personal video feeds to the cloud.

## Key Features

*   **Real-Time Inference:** Low-latency video processing and form feedback streamed via WebSockets.
*   **Stable Tracking:** MediaPipe Pose running in a real-time configuration with EMA (Exponential Moving Average) smoothing, low-visibility landmark filtering, and 3D world-landmark back-angle checks to reduce jitter and false posture warnings.
*   **Algorithmic Strictness:** Mathematical heuristics only count reps meeting biomechanical angle thresholds, with back-form checks debounced so brief pose-estimation noise does not incorrectly reject an otherwise clean rep.
*   **Guided Calibration:** Pushups and squats require a short stable setup hold before counting begins, adapting the tracker to the current camera/body position.
*   **Structured Coaching:** Backend responses include structured fault codes, severity, setup guidance, calibration progress, and per-rep quality metrics in addition to compatibility warning strings.
*   **Multi-Exercise Sessions:** The frontend supports manual Pushups/Squats selection, persists mixed workout history, migrates old pushup-only sessions, and exports v2 JSON logs with rep quality data.
*   **Faster Streaming:** The frontend now captures downscaled JPEG blobs and streams them as binary WebSocket frames, reducing client/server overhead compared with base64 payloads.
*   **Audio Coaching:** Built-in synthesized audio cues (ding for a perfect rep, buzz for bad form) allow you to maintain neutral neck posture while exercising.
*   **Data Portability:** Export full session logs to JSON, complete with timestamps and form metadata, for integration with personal trackers.
*   **Privacy-First:** Edge-based processing means your webcam feed never leaves your local machine.
*   **Modern Stack:** A decoupled architecture utilizing a React frontend and a robust Python/FastAPI backend.

## Getting Started (Local Development)

To test the pushup tracker locally using your webcam:

1.  **Install dependencies:**
    ```bash
    cd health-form-tracker
    uv pip install -r requirements.txt
    ```
2.  **Run the local test script:**
    ```bash
    # From the health-form-tracker/backend/ directory
    cd backend
    python main.py
    ```
3.  **Usage:** A window will open mirroring your webcam. Perform pushups to see the rep counter and form feedback in real-time. Press **'q'** in the video window to exit.

## Running the WebSocket Server

To serve the tracker as an API for the React frontend:

1.  **Start the server:**
    ```bash
    cd health-form-tracker/backend
    python -m uvicorn server:app --host [IP_ADDRESS] --port 8000 --reload
    ```
2.  **Health check:** Visit `http://[IP_ADDRESS]/health` to verify the server is running.
3.  **WebSocket endpoints:** Connect to `ws://[IP_ADDRESS]/ws/pushups` or `ws://[IP_ADDRESS]/ws/squats` and send binary JPEG frames. JSON/base64 payloads are still accepted for compatibility:
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
    npm run dev
    ```
3.  Open `http://localhost:5173` in your browser. Make sure the backend server is also running.
4.  Choose **Pushups** or **Squats** in the header. Hold the guided calibration pose until the dashboard shows ready, then start the set.

## Validation

Backend unit tests can be run from `health-form-tracker`:

```bash
python3 -m unittest discover backend/tests
```

Frontend production build can be checked from `health-form-tracker/frontend`:

```bash
npm run build
```

If `npm run lint` hangs under Node 25, rerun it with a stable Node LTS runtime.
