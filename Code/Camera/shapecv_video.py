import cv2
import numpy as np
import mediapipe as mp
import board
import adafruit_bno055
from flask import Flask, Response, render_template_string
import math
import subprocess
import threading
import time

# Setup Flask
app = Flask(__name__)

# Setup BNO055 Sensor
try:
    i2c = board.I2C()
    sensor = adafruit_bno055.BNO055_I2C(i2c)
except Exception as e:
    print(f"BNO055 not found: {e}")
    sensor = None

# Setup MediaPipe 
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,  
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

# Global State 
latest_frame = None
current_state = "WAITING" # WAITING, READING, LOCKED
detected_shape = ""
live_finger_count = 0

shape_map = {
    0: "Circle",
    1: "Line",
    2: "Rectangle",
    3: "Triangle",
    4: "Square",
    5: "5 Pointed Star"
}

def camera_thread():
    """Runs in the background, constantly pulling the newest frame."""
    global latest_frame
    cmd = [
        "rpicam-vid", "-t", "0", "--inline", 
        "--codec", "mjpeg", "--width", "640", "--height", "480", 
        "--framerate", "30", "-o", "-"
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    bytes_buffer = b''
    while True:
        bytes_buffer += process.stdout.read(8192) 
        a = bytes_buffer.find(b'\xff\xd8')
        b = bytes_buffer.find(b'\xff\xd9')
        
        if a != -1 and b != -1:
            jpg = bytes_buffer[a:b+2]
            bytes_buffer = bytes_buffer[b+2:]
            
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                latest_frame = frame

threading.Thread(target=camera_thread, daemon=True).start()

def count_fingers(hand_landmarks, hand_label):
    """Accurately counts fingers based on hand landmarks."""
    count = 0
    
    # 1. Thumb (Relies on x-coordinates relative to the palm)
    if hand_label == "Right":
        if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x:
            count += 1
    else: # Left
        if hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x:
            count += 1
            
    # 2. Index, Middle, Ring, Pinky (Relies on y-coordinates)
    tips = [8, 12, 16, 20] 
    pips = [6, 10, 14, 18] 
    for tip, pip in zip(tips, pips):
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y:
            count += 1
            
    return count

def draw_shape_icon(frame, shape_name, cx, cy):
    """Draws a visual icon of the selected shape in BLUE."""
    color = (255, 0, 0) # BGR format: Blue
    thickness = 3
    
    if shape_name == "Circle":
        cv2.circle(frame, (cx, cy), 35, color, thickness)
    elif shape_name == "Line":
        cv2.line(frame, (cx - 40, cy), (cx + 40, cy), color, thickness)
    elif shape_name == "Rectangle":
        cv2.rectangle(frame, (cx - 50, cy - 25), (cx + 50, cy + 25), color, thickness)
    elif shape_name == "Square":
        cv2.rectangle(frame, (cx - 35, cy - 35), (cx + 35, cy + 35), color, thickness)
    elif shape_name == "Triangle":
        pts = np.array([[cx, cy - 35], [cx - 35, cy + 25], [cx + 35, cy + 25]], np.int32)
        cv2.polylines(frame, [pts], True, color, thickness)
    elif shape_name == "5 Pointed Star":
        pts = []
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            r = 40 if i % 2 == 0 else 15
            pts.append([int(cx + math.cos(angle) * r), int(cy + math.sin(angle) * r)])
        pts = np.array(pts, np.int32)
        cv2.polylines(frame, [pts], True, color, thickness)

def generate_frames():
    global latest_frame, current_state, detected_shape, live_finger_count
    
    while True:
        if latest_frame is None:
            time.sleep(0.01)
            continue
            
        frame = latest_frame.copy()
        frame = cv2.flip(frame, 1) # Mirror image
        h, w, _ = frame.shape
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        left_hand_fingers = -1
        right_hand_fingers = -1
        num_hands = 0
        
        #  Analyze Hands 
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            for idx, hand_lms in enumerate(results.multi_hand_landmarks):
                label = results.multi_handedness[idx].classification[0].label 
                fingers = count_fingers(hand_lms, label)
                
                if label == "Left":
                    left_hand_fingers = fingers
                elif label == "Right":
                    right_hand_fingers = fingers

        #  State Machine Logic 
        
        # Reset completely if no hands are visible 
        if num_hands == 0:
             current_state = "WAITING"
             detected_shape = ""

        # 1. Start Reading if Left hand is Open (4 or 5 fingers)
        elif current_state == "WAITING" or current_state == "LOCKED":
            if left_hand_fingers >= 4: 
                current_state = "READING"
                detected_shape = ""
                
        # 2. Read Right Hand Fingers while Active
        elif current_state == "READING":
            if right_hand_fingers != -1:
                # Constrain count to 0-5
                live_finger_count = min(5, max(0, right_hand_fingers))
                
            # 3. Lock Selection if Left hand closes into a Fist (0 or 1 finger)
            if left_hand_fingers <= 1 and left_hand_fingers != -1:
                detected_shape = shape_map.get(live_finger_count, "Unknown")
                current_state = "LOCKED"

     
	# **UI Overlay** 
        
        # Sensor Data (Top Left, Green)
        if sensor:
            euler = sensor.euler
            if euler[0] is not None:
                cv2.putText(frame, f"H:{euler[0]:.1f} R:{euler[1]:.1f} P:{euler[2]:.1f}", 
                            (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # Status Indicator (Top Left under sensor)
        if num_hands == 1:
            cv2.putText(frame, "Status: Present both hands", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2) # Orange
        elif current_state == "WAITING":
            cv2.putText(frame, "Status: Waiting for Left Hand", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        elif current_state == "READING":
            cv2.putText(frame, f"Status: Reading Right Hand...", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Output Text & Shape Drawing (Top Right, Blue)
        # Suppress drawing if only 1 hand is present
        if current_state == "LOCKED" and detected_shape and num_hands == 2:
            # Draw Label
            text_size = cv2.getTextSize(detected_shape, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
            text_x = w - text_size[0] - 20 
            cv2.putText(frame, detected_shape, (text_x, 45), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 0, 0), 3) # Blue
            
            # Draw Icon directly under the text
            icon_cx = w - (text_size[0] // 2) - 20
            icon_cy = 110
            draw_shape_icon(frame, detected_shape, icon_cx, icon_cy)

        # Compress stream to 70% quality for speed
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return render_template_string('''
        <html>
            <head><title>Drawing Bot Live Stream</title></head>
            <body style="background: #222; color: white; text-align: center;">
                <h1>Drawing Bot HUD</h1>
                <img src="/video_feed" style="border: 2px solid #555; width: 80%;">
            </body>
        </html>
    ''')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
