import cv2
import time
import mediapipe as mp
from models.pose_detector import PoseDetector
from heuristics.pushup import PushupTracker

def main():
    print("Initializing components...")
    detector = PoseDetector()
    tracker = PushupTracker()
    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose
    
    print("Opening webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    p_time = 0
    print("Starting test. Press 'q' in the video window to quit.")
    
    try:
        while True:
            success, img = cap.read()
            if not success:
                print("Failed to read frame.")
                break
                
            # Mirror the image horizontally for a more natural selfie-view
            img = cv2.flip(img, 1)

            results = detector.find_pose(img)
            landmarks_dict = detector.extract_landmarks(results)
            
            # Draw landmarks on the image
            if results and results.pose_landmarks:
                mp_drawing.draw_landmarks(img, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            
            if landmarks_dict:
                status = tracker.process_frame(landmarks_dict)
                
                # Display HUD
                cv2.putText(img, f"Reps: {status['rep_count']}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                cv2.putText(img, f"State: {status['state']}", (10, 130), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                
                form_color = (0, 255, 0) if status['perfect_form'] else (0, 0, 255)
                form_text = "Form: Perfect" if status['perfect_form'] else "Form: Bad"
                cv2.putText(img, form_text, (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, form_color, 2)
                
                if not status['perfect_form'] and status['warnings']:
                    cv2.putText(img, f"Warning: {status['warnings'][0]}", (10, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(img, "No person detected", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            # Calculate and display FPS
            c_time = time.time()
            fps = 1 / (c_time - p_time) if (c_time - p_time) > 0 else 0
            p_time = c_time
            cv2.putText(img, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
            
            # Show the final frame
            cv2.imshow("Pushup Tracker Test", img)
            
            # Wait for 1ms and check for 'q' key press to break the loop
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting test...")
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()
        print("Resources released.")

if __name__ == "__main__":
    main()
