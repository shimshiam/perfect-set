"""
Perfect Set — FastAPI WebSocket Server

Serves real-time pushup form analysis over WebSocket connections.
Each connected client gets its own PoseDetector + PushupTracker instance.

Usage:
    cd health-form-tracker/backend
    uvicorn server:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import json
import base64
import logging
import time
import numpy as np
import cv2
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from models.pose_detector import PoseDetector
from heuristics.pushup import PushupTracker


def _landmark_image_point(point):
    if isinstance(point, dict):
        return point.get("image")
    return point

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("perfect-set")

# ---------------------------------------------------------------------------
# Connection tracking (asyncio-safe)
# ---------------------------------------------------------------------------
_connection_count: int = 0
_connection_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Perfect Set server starting up...")
    yield
    logger.info("Perfect Set server shutting down...")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Perfect Set API",
    description="Real-time physical form analysis via WebSocket",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """Simple liveness probe."""
    return {
        "status": "ok",
        "active_connections": _connection_count,
    }

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/pushups")
async def pushup_websocket(websocket: WebSocket):
    """
    Accepts a WebSocket connection for real-time pushup tracking.

    Protocol (per message):
        Client → Server:  binary JPEG bytes (preferred) or JSON
                           { "frame": "<base64-encoded JPEG>" }
        Server → Client:  JSON  {
            "rep_count": int,
            "state": str,
            "perfect_form": bool,
            "warnings": [str],
            "elbow_angle": float | null,
            "back_angle": float | null,
            "landmarks": { "left_shoulder": [x, y], ... } | null,
            "processing_ms": float
        }
    """
    global _connection_count
    await websocket.accept()
    async with _connection_lock:
        _connection_count += 1
    logger.info(f"Client connected. Active connections: {_connection_count}")

    # Each connection gets its own stateful instances.
    # MediaPipe Pose is NOT thread-safe, so sharing is not an option.
    detector = PoseDetector()
    tracker = PushupTracker()

    try:
        while True:
            t_start = time.perf_counter()
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect()

            frame_bytes = message.get("bytes")
            if frame_bytes is None:
                raw = message.get("text")
                if raw is None:
                    await websocket.send_json({"error": "Unsupported message type"})
                    continue

                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON"})
                    continue

                frame_b64 = payload.get("frame")
                if not frame_b64:
                    await websocket.send_json({"error": "Missing 'frame' field"})
                    continue

                # Strip optional data-URL prefix (e.g. "data:image/jpeg;base64,...")
                if "," in frame_b64:
                    frame_b64 = frame_b64.split(",", 1)[1]

                try:
                    frame_bytes = base64.b64decode(frame_b64)
                except Exception:
                    await websocket.send_json({"error": "Failed to decode image"})
                    continue

            # Decode base64 → numpy array → OpenCV image
            try:
                np_arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except Exception:
                await websocket.send_json({"error": "Failed to decode image"})
                continue

            if img is None:
                await websocket.send_json({"error": "Image decode returned None"})
                continue

            # --- Core pipeline ---
            try:
                # MediaPipe processing AND landmark extraction are both CPU-bound.
                # Run the full detection pipeline in a thread to avoid blocking
                # the main asyncio event loop.
                def _run_pipeline():
                    r = detector.find_pose(img)
                    return detector.extract_landmarks(r)

                landmarks_dict = await asyncio.to_thread(_run_pipeline)
                status = tracker.process_frame(landmarks_dict)

                rep_completed = status.pop("rep_completed", False)
                rep_aborted = status.pop("rep_aborted", False)
                current_rep_count = status["rep_count"]  # Capture before any further mutation

                processing_ms = (time.perf_counter() - t_start) * 1000

                # Build and send STATUS first so client has the updated rep_count
                response = {
                    "type": "STATUS",
                    **status,
                    "landmarks": (
                        {
                            k: [round(image_point[0], 4), round(image_point[1], 4)]
                            for k, v in landmarks_dict.items()
                            if (image_point := _landmark_image_point(v)) is not None
                        }
                        if landmarks_dict else None
                    ),
                    "processing_ms": round(processing_ms, 1),
                }
                await websocket.send_json(response)

                # Send rep events AFTER STATUS so client sees the correct count
                if rep_completed:
                    await websocket.send_json({"type": "REP_COMPLETED", "count": current_rep_count})
                if rep_aborted:
                    await websocket.send_json({"type": "REP_ABORTED", "count": current_rep_count})
            except Exception as e:
                logger.error(f"Processing error during core pipeline: {e}")
                continue

    except WebSocketDisconnect:
        logger.info("Client disconnected normally.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        detector.close()
        async with _connection_lock:
            _connection_count -= 1
        logger.info(f"Connection closed. Active connections: {_connection_count}")
