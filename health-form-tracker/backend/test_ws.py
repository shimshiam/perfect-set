"""
Quick smoke test for the Perfect Set WebSocket server.
Creates a synthetic test image, encodes it as JPEG/base64, sends it
to the /ws/pushups endpoint, and prints the response.

Usage:
    python test_ws.py
"""

import asyncio
import json
import base64
import numpy as np
import cv2

async def test_websocket():
    try:
        import websockets
    except ImportError:
        print("ERROR: 'websockets' not installed. Run: uv pip install websockets")
        return

    # Create a simple test frame (blank 640x480 image)
    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(test_img, "TEST FRAME", (180, 250),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

    # Encode to JPEG → base64
    _, buffer = cv2.imencode('.jpg', test_img)
    frame_b64 = base64.b64encode(buffer).decode('utf-8')

    uri = "ws://localhost:8000/ws/pushups"
    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        # Send a test frame
        payload = json.dumps({"frame": frame_b64})
        await ws.send(payload)
        print(f"Sent frame ({len(frame_b64)} chars base64)")

        # Get response
        response = await ws.recv()
        data = json.loads(response)
        print(f"\nServer response:")
        print(json.dumps(data, indent=2))

        # Verify expected fields
        expected_fields = ["rep_count", "state", "perfect_form", "warnings",
                          "elbow_angle", "back_angle", "landmarks", "processing_ms"]
        missing = [f for f in expected_fields if f not in data]
        if missing:
            print(f"\n[WARN] Missing fields: {missing}")
        else:
            print(f"\n[OK] All expected fields present")
            print(f"   Processing time: {data['processing_ms']}ms")
            print(f"   State: {data['state']}")
            print(f"   Landmarks detected: {data['landmarks'] is not None}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
