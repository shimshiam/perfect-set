import cv2
import time
from models.pose_detector import PoseDetector
from heuristics.pushup import PushupTracker
from utils.geometry import calculate_angle
from utils.video_utils import draw_skeleton, draw_hud, draw_angles

def main():
    print("Initializing components...")
    # Initialize detector and tracker
    detector = PoseDetector()
    tracker = PushupTracker()
    
    print("Opening webcam...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    p_time = 0
    print("Starting tracker. Press 'q' in the video window to quit.")
    
    try:
        while True:
            success, img = cap.read()
            if not success:
                print("Failed to read frame.")
                break
                
            # Mirror the image horizontally for a more natural selfie-view
            img = cv2.flip(img, 1)

            # 1. Pose Inference
            results = detector.find_pose(img)
            landmarks_dict = detector.extract_landmarks(results)
            
            # 2. Heuristic Analysis
            status = tracker.process_frame(landmarks_dict)
            
            # 3. Visualization logic
            if landmarks_dict:
                # Draw skeleton lines
                draw_skeleton(img, landmarks_dict)
                
                # Extract angles for visualization
                # We dynamically anchor to whichever side is visible so angles draw correctly.
                anchor = 'right' if 'right_elbow' in landmarks_dict else 'left'
                
                v_elbow = 0.0
                if f'{anchor}_shoulder' in landmarks_dict and f'{anchor}_elbow' in landmarks_dict and f'{anchor}_wrist' in landmarks_dict:
                    v_elbow = calculate_angle(landmarks_dict[f'{anchor}_shoulder'], 
                                            landmarks_dict[f'{anchor}_elbow'], 
                                            landmarks_dict[f'{anchor}_wrist'])
                                            
                v_back = 0.0
                if f'{anchor}_shoulder' in landmarks_dict and f'{anchor}_hip' in landmarks_dict and f'{anchor}_ankle' in landmarks_dict:
                    v_back = calculate_angle(landmarks_dict[f'{anchor}_shoulder'], 
                                           landmarks_dict[f'{anchor}_hip'], 
                                           landmarks_dict[f'{anchor}_ankle'])
                
                draw_angles(img, landmarks_dict, v_elbow, v_back)
            
            # Calculate FPS
            c_time = time.time()
            fps = int(1 / (c_time - p_time)) if (c_time - p_time) > 0 else 0
            p_time = c_time
            
            # Draw the premium HUD
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
