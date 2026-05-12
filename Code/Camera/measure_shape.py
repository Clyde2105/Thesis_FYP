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

    # --- 4. MEASUREMENT LOGIC ---
    if len(cnts_shape) > 0:
        # Filter out tiny background noise/dust (must be longer than 50 pixels)
        valid_cnts = [c for c in cnts_shape if cv2.arcLength(c, closed=False) > 50]
        
        if len(valid_cnts) > 0:
            # Mash all drawn lines together into one object
            all_pts = np.vstack(valid_cnts)
            
            # Draw the smallest bounding box around the whole shape
            rect_draw = cv2.minAreaRect(all_pts)
            box_draw = perspective.order_points(cv2.boxPoints(rect_draw).astype("int"))

            # Calculate dimensions in pixels
            (dtl, dtr, dbr, dbl) = box_draw
            mid_top_d = np.array([(dtl[0]+dtr[0])/2, (dtl[1]+dtr[1])/2])
            mid_bot_d = np.array([(dbl[0]+dbr[0])/2, (dbl[1]+dbr[1])/2])
            mid_left_d = np.array([(dtl[0]+dbl[0])/2, (dtl[1]+dbl[1])/2])
            mid_right_d = np.array([(dtr[0]+dbr[0])/2, (dtr[1]+dbr[1])/2])
            
            w_px = np.linalg.norm(mid_top_d - mid_bot_d)
            print(f"RAW PIXEL WIDTH: {w_px}")
            h_px = np.linalg.norm(mid_left_d - mid_right_d)

            # Convert to CM using your hardcoded scale
            avg_w = sum(history_W.append(w_px / PIXELS_PER_CM) or history_W) / len(history_W)
            avg_h = sum(history_H.append(h_px / PIXELS_PER_CM) or history_H) / len(history_H)

            # Draw the UI
            cv2.drawContours(frame, [box_draw.astype("int")], -1, (255, 0, 0), 3)
            cv2.putText(frame, f"{avg_w:.1f}cm x {avg_h:.1f}cm", (int(dtl[0]), int(dtl[1]-10)), 1, 1.5, (255, 0, 0), 2)

    # --- 5. DISPLAY WINDOWS ---
    cv2.imshow("Thesis Measurement - Fixed Scale", frame)
    cv2.imshow("Dark Ink Mask (Debug)", mask_shape) # Watch this window!
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cv2.destroyAllWindows()