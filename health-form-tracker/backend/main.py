import cv2
import ssl
import sys
import time
from models.pose_detector import PoseDetector
from heuristics.pushup import PushupTracker
from utils.video_utils import draw_skeleton, draw_hud, draw_angles

# ── macOS SSL fix ──
# Python 3.12 on macOS does not bundle root certs, causing MediaPipe's model
# download to fail. Intentionally gated to darwin only so Windows/Linux users
# retain full SSL certificate verification.
if sys.platform == 'darwin':
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except AttributeError:
        pass

def main():
    print("Initializing components...")
    detector = PoseDetector()
    tracker = PushupTracker()
    
    print("Opening webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Allow the camera driver to warm up (especially important for Continuity Camera).
    print("Warming up camera...")
    for _ in range(10):
        cap.read()

    p_time = 0
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 10
    print("Starting tracker. Press 'q' in the video window to quit.")
    
    try:
        while True:
            success, img = cap.read()
            if not success:
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    print(f"Camera lost after {MAX_CONSECUTIVE_FAILURES} consecutive failures. Exiting.")
                    break
                continue
            consecutive_failures = 0
                
            # Mirror the image horizontally for a more natural selfie-view
            img = cv2.flip(img, 1)

            # 1. Pose Inference
            results = detector.find_pose(img)
            landmarks_dict = detector.extract_landmarks(results)
            
            # 2. Heuristic Analysis
            status = tracker.process_frame(landmarks_dict)
            
            # 3. Visualization
            if landmarks_dict:
                draw_skeleton(img, landmarks_dict)
                
                # Use angles already computed by the tracker (no redundant calculation)
                if status['elbow_angle'] is not None:
                    draw_angles(img, landmarks_dict, status['elbow_angle'], status['back_angle'])
            
            # Calculate FPS
            c_time = time.time()
            fps = int(1 / (c_time - p_time)) if (c_time - p_time) > 0 else 0
            p_time = c_time
            
            # Draw the HUD (always shown — displays "waiting" state when no person detected)
            draw_hud(img, status, fps)
            
            # Display the result
            cv2.imshow("Perfect Set - Physical Form Tracker", img)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting...")
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        print("Resources released.")

if __name__ == "__main__":
    main()
