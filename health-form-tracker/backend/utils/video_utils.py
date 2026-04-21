import cv2
import numpy as np
from typing import Dict, Tuple, List, Any

def draw_skeleton(img: np.ndarray, landmarks: Dict[str, Tuple[float, float]], color: Tuple[int, int, int] = (255, 255, 255)):
    """
    Draws the primary skeletal lines for pushup tracking.
    
    Args:
        img: The image to draw on.
        landmarks: Dictionary of normalized landmarks.
        color: RGB color for the lines.
    """
    h, w, _ = img.shape
    
    # Define connection pairs for a side
    connections = [
        ('shoulder', 'elbow'), ('elbow', 'wrist'),
        ('shoulder', 'hip'), ('hip', 'ankle')
    ]
    
    # We use specific colors for left/right for better visual debugging
    # Left: Cyan-ish, Right: Orange-ish
    sides = [('left', (255, 200, 0)), ('right', (0, 165, 255))]
    
    for side, side_color in sides:
        for p1_name, p2_name in connections:
            k1, k2 = f"{side}_{p1_name}", f"{side}_{p2_name}"
            if k1 in landmarks and k2 in landmarks:
                pt1 = (int(landmarks[k1][0] * w), int(landmarks[k1][1] * h))
                pt2 = (int(landmarks[k2][0] * w), int(landmarks[k2][1] * h))
                
                # Draw the line
                cv2.line(img, pt1, pt2, side_color, 3)
                # Draw joint circles
                cv2.circle(img, pt1, 6, (255, 255, 255), -1)
                cv2.circle(img, pt1, 4, side_color, -1)
                cv2.circle(img, pt2, 6, (255, 255, 255), -1)
                cv2.circle(img, pt2, 4, side_color, -1)

def draw_angles(img: np.ndarray, landmarks: Dict[str, Tuple[float, float]], elbow_angle: float, back_angle: float):
    """Draws angle values near the relevant joints."""
    h, w, _ = img.shape
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Anchor text to whichever side is visible (prefer right since pushups are often filmed from the side)
    anchor_side = 'right' if 'right_elbow' in landmarks else 'left'
    
    if f'{anchor_side}_elbow' in landmarks:
        e_pt = landmarks[f'{anchor_side}_elbow']
        cv2.putText(img, f"{int(elbow_angle)}deg", 
                    (int(e_pt[0] * w) + 15, int(e_pt[1] * h)), 
                    font, 0.6, (255, 255, 255), 2)
                    
    if f'{anchor_side}_hip' in landmarks:
        h_pt = landmarks[f'{anchor_side}_hip']
        cv2.putText(img, f"{int(back_angle)}deg", 
                    (int(h_pt[0] * w) + 15, int(h_pt[1] * h)), 
                    font, 0.6, (255, 255, 255), 2)

def draw_hud(img: np.ndarray, status: Dict[str, Any], fps: int):
    """
    Draws a premium HUD overlay with rep counts and form feedback.
    Handles both active tracking and "no person detected" states.
    """
    h, w, _ = img.shape
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # Clamp HUD dimensions to the image size
    hud_w = min(320, w - 20)
    hud_h = min(220, h - 20)
    
    # Semi-transparent overlay using ROI blending (avoids copying the entire frame)
    x1, y1, x2, y2 = 10, 10, 10 + hud_w, 10 + hud_h
    roi = img[y1:y2, x1:x2]
    dark = np.full_like(roi, (30, 30, 30), dtype=np.uint8)
    cv2.addWeighted(dark, 0.6, roi, 0.4, 0, roi)
    img[y1:y2, x1:x2] = roi
    
    # Check if we have a person (angles are None when landmarks are missing)
    has_person = status.get('elbow_angle') is not None
    
    if has_person:
        # Rep Count
        cv2.putText(img, "REPS", (30, 50), font, 0.6, (180, 180, 180), 1)
        cv2.putText(img, f"{status['rep_count']}", (30, 100), font, 1.8, (0, 255, 0), 4)
        
        # State / Phase
        cv2.putText(img, "PHASE", (160, 50), font, 0.6, (180, 180, 180), 1)
        cv2.putText(img, status['state'], (160, 90), font, 1.0, (255, 255, 0), 2)
        
        # Form Feedback
        form_color = (0, 255, 0) if status['perfect_form'] else (0, 0, 255)
        form_text = "FORM: PERFECT" if status['perfect_form'] else "FORM: ADJUST"
        cv2.putText(img, form_text, (30, 150), font, 0.8, form_color, 2)
        
        # Warning message
        if status['warnings']:
            cv2.putText(img, f"! {status['warnings'][0]}", (30, 190), font, 0.6, (0, 0, 255), 2)
    else:
        # No person detected — show waiting state
        cv2.putText(img, "REPS", (30, 50), font, 0.6, (180, 180, 180), 1)
        cv2.putText(img, f"{status['rep_count']}", (30, 100), font, 1.8, (100, 100, 100), 4)
        cv2.putText(img, "Waiting for pose...", (30, 150), font, 0.7, (100, 100, 255), 2)
        
    # FPS in top-right corner (clamped to image width)
    fps_x = max(w - 120, 10)
    cv2.putText(img, f"FPS: {fps}", (fps_x, 30), font, 0.7, (0, 255, 0), 2)
