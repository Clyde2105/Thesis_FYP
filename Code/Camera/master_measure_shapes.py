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
current_mode = 3 
mode_names = {
    0: "Circle (Diameter)", 
    1: "Straight Lines", 
    2: "Rectangle (Bounding Box)", 
    3: "Triangle (Line Logic)", 
    4: "Square (Bounding Box)", 
    5: "Star (Line Logic)"
}

print("Master Script Running with Adaptive Lighting and Overlap Filters!")
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
        current_mode = int(chr(key)) 

    # --- 3. ADAPTIVE MASKING (Dynamic Lighting Fix) ---
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Adaptive threshold calculates thresholds locally, ignoring global room shadows
    adaptive_dark = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 21, 12
    )
    
    # Keep the red ink tracker active using HSV
    red_mask1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([10, 255, 255]))
    red_mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
    red_mask = cv2.bitwise_or(red_mask1, red_mask2)
    
    # Combine adaptive dark ink and red ink
    mask_shape = cv2.bitwise_or(adaptive_dark, red_mask)
    
    # Thicken stroke slightly to combine inner/outer edge fragments
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    mask_shape = cv2.dilate(mask_shape, kernel, iterations=1)
    mask_shape = cv2.morphologyEx(mask_shape, cv2.MORPH_CLOSE, kernel)

    cnts_shape = imutils.grab_contours(cv2.findContours(mask_shape.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE))

    # --- 4. MEASUREMENT LOGIC BY MODE ---
    if len(cnts_shape) > 0:
        c = max(cnts_shape, key=cv2.contourArea) 
        
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

        # Modes 1, 3, 5: STRAIGHT LINES / TRIANGLE / STAR
        elif current_mode in [1, 3, 5]:
            edges = cv2.Canny(mask_shape, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=80, maxLineGap=60)
            
            if lines is not None:
                filtered_lines = []
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    
                    is_duplicate = False
                    for fx1, fy1, fx2, fy2 in filtered_lines:
                        f_mid_x = (fx1 + fx2) / 2
                        f_mid_y = (fy1 + fy2) / 2
                        dist = np.hypot(mid_x - f_mid_x, mid_y - f_mid_y)
                        if dist < 30: 
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        filtered_lines.append((x1, y1, x2, y2))
                        cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # --- ANGLE CALCULATION WITH LOCATION DEBOUNCING ---
                if current_mode in [3, 5]:
                    drawn_locations = [] # Keeps track of where text has been placed
                    
                    for i in range(len(filtered_lines)):
                        for j in range(i+1, len(filtered_lines)):
                            l1 = filtered_lines[i]
                            l2 = filtered_lines[j]
                            
                            pts1 = [(l1[0], l1[1]), (l1[2], l1[3])]
                            pts2 = [(l2[0], l2[1]), (l2[2], l2[3])]
                            
                            min_dist = float('inf')
                            best_pair = None
                            
                            for p1 in pts1:
                                for p2 in pts2:
                                    dist = np.hypot(p1[0]-p2[0], p1[1]-p2[1])
                                    if dist < min_dist:
                                        min_dist = dist
                                        best_pair = (p1, p2)
                            
                            # Corners check (within 60px proximity)
                            if min_dist < 60: 
                                cx = (best_pair[0][0] + best_pair[1][0]) / 2
                                cy = (best_pair[0][1] + best_pair[1][1]) / 2
                                
                                other_p1 = pts1[1] if best_pair[0] == pts1[0] else pts1[0]
                                other_p2 = pts2[1] if best_pair[1] == pts2[0] else pts2[0]
                                
                                v1 = np.array([other_p1[0] - cx, other_p1[1] - cy])
                                v2 = np.array([other_p2[0] - cx, other_p2[1] - cy])
                                
                                norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
                                
                                if norm1 > 0 and norm2 > 0:
                                    cos_theta = np.dot(v1, v2) / (norm1 * norm2)
                                    cos_theta = np.clip(cos_theta, -1.0, 1.0)
                                    angle_deg = np.degrees(np.arccos(cos_theta))
                                    
                                    # Filter: Ignore inline lines (~180) and glitches (~0)
                                    if 20.0 < angle_deg < 165.0:
                                        # Overlap Check: See if text is already close to this corner
                                        too_close = False
                                        for dx, dy in drawn_locations:
                                            if np.hypot(cx - dx, cy - dy) < 40:
                                                too_close = True
                                                break
                                        
                                        if not too_close:
                                            cv2.putText(frame, f"{angle_deg:.1f} deg", (int(cx) - 30, int(cy) - 15), 
                                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                                            drawn_locations.append((cx, cy))

    # --- 5. DISPLAY ---
    cv2.putText(frame, f"MODE: {mode_names[current_mode]} [ANGLES]", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.putText(frame, "Press 0-5 to change modes", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    cv2.imshow("Master Thesis Measurement", frame)
    cv2.imshow("Combined Ink Mask (Debug)", mask_shape)

cam.release()
cv2.destroyAllWindows()