# Perfect Set: Health Form Tracker

## Description

This project is a real-time, privacy-first computer vision application designed to provide immediate physical form correction and automated workout tracking. Built with React, FastAPI, PyTorch, and OpenCV, it acts as a localized digital personal trainer that runs directly through a standard webcam.

The application currently specializes in automating the tracking of high-volume pushup sets. By leveraging pose estimation (MediaPipe) and biomechanical vector math, the system calculates joint angles frame-by-frame to enforce strict form requirements. It actively monitors elbow descent (breaking 90 degrees) and spinal alignment (maintaining a 180-degree posture), automatically filtering out "cheat" reps.

Designed for users managing daily rep goals or strict hypertrophy routines, this tool eliminates the guesswork of solo workouts. It ensures that every logged rep is performed with perfect, injury-free mechanics—all processed locally without sending personal video feeds to the cloud.

## Key Features

*   **Real-Time Inference:** Low-latency video processing and form feedback streamed via WebSockets.
*   **Stable Tracking:** MediaPipe Pose running at `model_complexity=2` with EMA (Exponential Moving Average) temporal smoothing applied to all landmarks, eliminating jitter and ensuring skeleton lines stay precisely appended to limbs.
*   **Algorithmic Strictness:** Mathematical heuristics that only count reps meeting exact biomechanical angle thresholds. Reps performed with bad form are detected and rejected.
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
3.  **WebSocket endpoint:** Connect to `ws://[IP_ADDRESS]/ws/pushups` and send JSON frames:
    ```json
    { "frame": "<base64-encoded JPEG>" }
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
