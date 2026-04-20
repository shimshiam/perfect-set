# Perfect Set: Health Form Tracker

## Description

This project is a real-time, privacy-first computer vision application designed to provide immediate physical form correction and automated workout tracking. Built with React, FastAPI, PyTorch, and OpenCV, it acts as a localized digital personal trainer that runs directly through a standard webcam.

The application currently specializes in automating the tracking of high-volume pushup sets. By leveraging pose estimation (MediaPipe/YOLO) and biomechanical vector math, the system calculates joint angles frame-by-frame to enforce strict form requirements. It actively monitors elbow descent (breaking 90 degrees) and spinal alignment (maintaining a 180-degree posture), automatically filtering out "cheat" reps.

Designed for users managing daily rep goals or strict hypertrophy routines, this tool eliminates the guesswork of solo workouts. It ensures that every logged rep is performed with perfect, injury-free mechanics—all processed locally without sending personal video feeds to the cloud.

## Key Features

*   **Real-Time Inference:** Low-latency video processing and form feedback streamed via WebSockets.
*   **Algorithmic Strictness:** Mathematical heuristics that only count reps meeting exact biomechanical angle thresholds.
*   **Privacy-First:** Edge-based processing means your webcam feed never leaves your local machine.
*   **Modern Stack:** A decoupled architecture utilizing a React frontend and a robust Python/FastAPI backend.
