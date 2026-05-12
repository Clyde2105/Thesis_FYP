import cv2
import numpy as np
from imutils import perspective
import imutils

# --- 1. CONFIGURATION ---
PIXELS_PER_CM = 10.0 

cam = cv2.VideoCapture(1) 
if not cam.isOpened():
    cam = cv2.VideoCapture(0)

# Default starting mode
current_mode = 5 
mode_names = {
    0: "Circle (Diameter)", 
    1: "Straight Lines", 
    2: "Rectangle (Bounding Box)", 
    3: "Triangle (Line Logic)", 
    4: "Square (Bounding Box)", 
    5: "Star (Line Logic)"
}

print("Master Script Running!")
print("Press 0-5 to switch modes. Press 'q' to quit.")

while True:
    ret, frame = cam.read()
    if not ret: 
        break

    # --- 2. KEYBOARD CONTROLS ---
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key in [ord(str(i)) for i in range(6)]:
        current_mode = int(chr(key)) # Change mode based on number pressed

    # --- 3. DUAL-COLOR MASKING (Finds Black AND Red Ink) ---
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Mask 1: Dark Ink
    dark_mask = cv2.inRange(hsv, np.array([0, 0, 0]), np.array([180, 255, 100]))
    # Mask 2: Red Ink (Red wraps around the HSV spectrum, so it needs two ranges)
    red_mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
    
    # Combine them all together
    mask_shape = cv2.bitwise_or(dark_mask, red_mask1)
    mask_shape = cv2.bitwise_or(mask_shape, red_mask2)
    
    # Thicken ink to close gaps
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    mask_shape = cv2.dilate(mask_shape, kernel, iterations=2)
    mask_shape = cv2.morphologyEx(mask_shape, cv2.MORPH_CLOSE, kernel)

    cnts_shape = imutils.grab_contours(cv2.findContours(mask_shape.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE))

    # --- 4. MEASUREMENT LOGIC BY MODE ---
    if len(cnts_shape) > 0:
        c = max(cnts_shape, key=cv2.contourArea) # Get the biggest drawn object
        
        # Mode 0: CIRCLE (Diameter)
        if current_mode == 0:
            if cv2.contourArea(c) > 500:
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                diameter_cm = (radius * 2) / PIXELS_PER_CM
                
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 3)
                cv2.putText(frame, f"Diameter: {diameter_cm:.1f}cm", (int(x - 80), int(y - radius - 10)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        # Modes 2 & 4: RECTANGLE / SQUARE (Bounding Box)
        elif current_mode in [2, 4]:
            if cv2.contourArea(c) > 500:
                rect_draw = cv2.minAreaRect(c)
                box_draw = perspective.order_points(cv2.boxPoints(rect_draw).astype("int"))
                
                (dtl, dtr, dbr, dbl) = box_draw
                mid_top_d = np.array([(dtl[0]+dtr[0])/2, (dtl[1]+dtr[1])/2])
                mid_bot_d = np.array([(dbl[0]+dbr[0])/2, (dbl[1]+dbr[1])/2])
                mid_left_d = np.array([(dtl[0]+dbl[0])/2, (dtl[1]+dbl[1])/2])
                mid_right_d = np.array([(dtr[0]+dbr[0])/2, (dtr[1]+dbr[1])/2])
                
                w_px = np.linalg.norm(mid_top_d - mid_bot_d)
                h_px = np.linalg.norm(mid_left_d - mid_right_d)
                
                cv2.drawContours(frame, [box_draw.astype("int")], -1, (0, 255, 0), 3)
                cv2.putText(frame, f"{w_px/PIXELS_PER_CM:.1f}cm x {h_px/PIXELS_PER_CM:.1f}cm", (int(dtl[0]), int(dtl[1]-10)), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        # Modes 1, 3, 5: STRAIGHT LINES / TRIANGLE / STAR (Hough Lines Logic)
        elif current_mode in [1, 3, 5]:
            edges = cv2.Canny(mask_shape, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=60, minLineLength=100, maxLineGap=100)
            
            if lines is not None:
                filtered_lines = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    
                    # Filter out double-lines
                    is_duplicate = False
                    for fx1, fy1, fx2, fy2 in filtered_lines:
                        f_mid_x = (fx1 + fx2) / 2
                        f_mid_y = (fy1 + fy2) / 2
                        dist = np.sqrt((mid_x - f_mid_x)**2 + (mid_y - f_mid_y)**2)
                        if dist < 40: 
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        filtered_lines.append((x1, y1, x2, y2))
                        pt1 = np.array([x1, y1])
                        pt2 = np.array([x2, y2])
                        
                        dist_px = np.linalg.norm(pt1 - pt2)
                        dist_cm = dist_px / PIXELS_PER_CM
                        
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        cv2.putText(frame, f"{dist_cm:.1f}cm", (int(mid_x), int(mid_y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

    # --- 5. DISPLAY ---
    # Display current mode on screen
    cv2.putText(frame, f"MODE: {mode_names[current_mode]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(frame, "Press 0-5 to change modes", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imshow("Master Thesis Measurement", frame)
    cv2.imshow("Combined Ink Mask (Debug)", mask_shape)

cam.release()
cv2.destroyAllWindows()