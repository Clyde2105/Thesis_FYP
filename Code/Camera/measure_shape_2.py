import cv2
import numpy as np
from imutils import perspective
import imutils
import collections

# --- 1. CONFIGURATION (YOUR MAGIC NUMBER) ---
# Your calibrated scale!
PIXELS_PER_CM = 10.0

# Camera Setup
cam = cv2.VideoCapture(1) 
if not cam.isOpened():
    cam = cv2.VideoCapture(0)

# Smoothing buffers for stable readings
history_W = collections.deque(maxlen=20)
history_H = collections.deque(maxlen=20)

# --- 2. COLOR TRACKING (Looking for Dark Ink) ---
# Value (Brightness) goes from 0 to 255. 
# Capping it at 80 means it will only see very dark colors (black/dark blue)
dark_lower = np.array([0, 0, 0])
dark_upper = np.array([180, 255, 80]) 

print("Fixed-Scale Measurement Running. Press 'q' to quit.")

while True:
    ret, frame = cam.read()
    if not ret: 
        print("Failed to grab frame.")
        break

    # Convert to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7,7))

    # --- 3. CREATE SHAPE MASK ---
    mask_shape = cv2.inRange(hsv, dark_lower, dark_upper)
    
    # Thicken the lines to fix any gaps in the ink/shadows
    mask_shape = cv2.dilate(mask_shape, kernel, iterations=3)
    mask_shape = cv2.morphologyEx(mask_shape, cv2.MORPH_CLOSE, kernel)
    
    cnts_shape = imutils.grab_contours(cv2.findContours(mask_shape.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE))

    # --- 4. MEASUREMENT LOGIC (FINDING STRAIGHT PEN STROKES) ---
    edges = cv2.Canny(mask_shape, 50, 150)
    
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=60, minLineLength=100, maxLineGap=100)
    
    if lines is not None:
        # Create a list to store only the unique lines
        filtered_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # Find the middle point of the current line
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            # Check if this line is sitting right next to one we already found
            is_duplicate = False
            for fx1, fy1, fx2, fy2 in filtered_lines:
                f_mid_x = (fx1 + fx2) / 2
                f_mid_y = (fy1 + fy2) / 2
                
                # If the middle of this line is within 40 pixels of another line, it's a duplicate!
                dist = np.sqrt((mid_x - f_mid_x)**2 + (mid_y - f_mid_y)**2)
                if dist < 40: 
                    is_duplicate = True
                    break
            
            # If it's a unique pen stroke, measure it and draw it
            if not is_duplicate:
                filtered_lines.append((x1, y1, x2, y2))
                
                pt1 = np.array([x1, y1])
                pt2 = np.array([x2, y2])
                
                # Calculate the exact length of the pen stroke
                dist_px = np.linalg.norm(pt1 - pt2)
                dist_cm = dist_px / PIXELS_PER_CM
                
                # Draw a single green line over the pen stroke
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                
                # Print the measurement
                cv2.putText(frame, f"{dist_cm:.1f}cm", (int(mid_x), int(mid_y) - 10), 1, 1.2, (255, 0, 0), 2)

    # --- 5. DISPLAY WINDOWS ---
    cv2.imshow("Thesis Measurement - Fixed Scale", frame)
    cv2.imshow("Dark Ink Mask (Debug)", mask_shape) # Watch this window!
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()