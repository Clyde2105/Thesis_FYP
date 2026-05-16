import cv2
import numpy as np
import mediapipe as mp
import board
import adafruit_bno055
from flask import Flask, Response, render_template_string
import subprocess
import threading
import time
import serial

# 1. SETUP HARDWARE & FLASK
app = Flask(__name__)

# Setup BNO055 Sensor
try:
    i2c = board.I2C()
    sensor = adafruit_bno055.BNO055_I2C(i2c)
    print("BNO055 initialized successfully.")
except Exception as e:
    print(f"BNO055 not found: {e}")
    sensor = None

# Setup Serial (Arduino)
arduino = None
ports_to_try = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']

for port in ports_to_try:
    try:
        arduino = serial.Serial(port, 115200, timeout=1)
        print(f"Arduino connected successfully on {port}!")
        time.sleep(2)  # Give Arduino a second to reset after connecting
        break  # Stop looking once connected
    except serial.SerialException:
        continue  # Try the next port in the list

if arduino is None:
    print("CRITICAL ERROR: Could not find Arduino on any USB port!")
    exit()  # Stop the script so it doesn't crash later

# Setup MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.6)

# Global State
latest_frame = None
current_state = "WAITING"
detected_shape = ""
live_finger_count = 0
last_sent_shape = ""
last_time_taken = 0.0

# Robot Odometry State
global_left_ticks = 0
global_right_ticks = 0
is_drawing = False

shape_map = {0: "Circle", 1: "Line", 2: "Rectangle", 3: "Triangle", 4: "Square", 5: "5 Pointed Star"}

# 2. BACKGROUND THREADS
def camera_thread():
    global latest_frame
    cmd = ["rpicam-vid", "-t", "0", "--inline", "--codec", "mjpeg", "--width", "640", "--height", "480", "--framerate", "15", "--flush", "1", "-o", "-"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    bytes_buffer = b''
    
    while True:
        chunk = process.stdout.read(16384)
        if not chunk: break
        bytes_buffer += chunk
        
        if len(bytes_buffer) > 65536:
            last_a = bytes_buffer.rfind(b'\xff\xd8')
            if last_a != -1:
                bytes_buffer = bytes_buffer[last_a:]
            else:
                bytes_buffer = b''
            continue

        a = bytes_buffer.find(b'\xff\xd8')
        if a == -1: continue

        b = bytes_buffer.find(b'\xff\xd9', a + 2)
        if b != -1:
            jpg = bytes_buffer[a:b+2]
            bytes_buffer = bytes_buffer[b+2:]
            
            if len(jpg) > 0:
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    latest_frame = frame

def serial_listener_thread():
    global global_left_ticks, global_right_ticks
    while True:
        if arduino and arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("E:"):
                    parts = line[2:].split(',')
                    global_left_ticks = int(parts[0])
                    global_right_ticks = int(parts[1])
            except:
                pass
        time.sleep(0.01)

threading.Thread(target=camera_thread, daemon=True).start()
threading.Thread(target=serial_listener_thread, daemon=True).start()

# 3. HELPER FUNCTIONS
def get_heading():
    if not sensor: return 0.0
    euler = sensor.euler
    return euler[0] if euler[0] is not None else 0.0

def get_angle_diff(target, current):
    diff = (target - current)
    diff = (diff + 180) % 360 - 180
    return diff

def send_motor_cmd(speedL, speedR, dirL, dirR):
    if arduino:
        cmd_str = f"M:{int(speedL)},{int(speedR)},{dirL},{dirR}\n"
        arduino.write(cmd_str.encode('utf-8'))

def set_pen(down=True):
    if arduino:
        arduino.write(b"P:1\n" if down else b"P:0\n")
    time.sleep(0.5)

# 4. ROBOT NAVIGATION & PID CONTROL
def drive_straight_star_logic(target_ticks, direction="forward", target_heading=None):
    """Specialized drive function for the Star routine with Kp=4 tuning."""
    if arduino is None or sensor is None: return
    
    arduino.reset_input_buffer()
    arduino.write(b"R:\n") 
    time.sleep(0.1)

    if target_heading is None:
        target_heading = get_heading()

    if direction == "forward":
        base_L, base_R = 58, 75
        dir_L, dir_R = 1, 1
    else:
        base_L, base_R = 73, 69
        dir_L, dir_R = 0, 0

    Kp = 4
    current_ticks = 0

    while current_ticks < target_ticks:
        if arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("E:"):
                    parts = line[2:].split(',')
                    current_ticks = max(int(parts[0]), int(parts[1]))
            except: pass
        
        if current_ticks >= target_ticks: break
        
        curr_h = get_heading()
        error = curr_h - target_heading
        if error > 180: error -= 360
        elif error < -180: error += 360

        correction = error * Kp
        speedL = int(base_L - correction) if direction == "forward" else int(base_L + correction)
        speedR = int(base_R + correction) if direction == "forward" else int(base_R - correction)

        send_motor_cmd(max(40, min(130, speedL)), max(40, min(130, speedR)), dir_L, dir_R)
        time.sleep(0.04)

    send_motor_cmd(0, 0, 0, 0)

def drive_straight_imu_encoders(target_ticks, direction="forward", absolute_heading=None):
    """Drives straight using LM393 ticks for distance and BN0055 for heading lock."""
    arduino.reset_input_buffer()
    arduino.write(b"R:\n") # Reset encoders on Arduino side
    time.sleep(0.1)

    if absolute_heading is None:
        target_heading = sensor.euler[0]
        while target_heading is None:
            time.sleep(0.05)
            target_heading = sensor.euler[0]
    else:
        target_heading = absolute_heading

    # Baseline speeds
    if direction == "forward":
        base_L, base_R = 58, 75
        dir_L, dir_R = 1, 1
    else:
        base_L, base_R = 73, 69
        dir_L, dir_R = 0, 0

    Kp = 4
    current_ticks = 0

    while current_ticks < target_ticks:
        while arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("E:"):
                    parts = line[2:].split(',')
                    current_ticks = max(int(parts[0]), int(parts[1]))
            except:
                pass

        if current_ticks >= target_ticks:
            break

        current_heading = sensor.euler[0]
        if current_heading is None: continue

        error = current_heading - target_heading
        if error > 180: error -= 360
        elif error < -180: error += 360

        correction = error * Kp

        if direction == "forward":
            speedL = int(base_L - correction)
            speedR = int(base_R + correction)
        else:
            speedL = int(base_L + correction)
            speedR = int(base_R - correction)

        speedL = max(40, min(130, speedL))
        speedR = max(40, min(130, speedR))

        arduino. write(f"M:{speedL},{speedR},{dir_L},{dir_R}\n".encode())
        time.sleep(0.04)

    arduino.write(b"M:0,0,0,0\n") # Stop

def optimal_imu_turn(target_heading, tolerance=0.5):
    """The high-precision PID turn logic for the Star's 144-degree points."""
    while True:
        curr_h = get_heading()
        error = target_heading - curr_h
        if error > 180: error -= 360
        if error < -180: error += 360

        if abs(error) <= tolerance:
            send_motor_cmd(0,0,0,0)
            time.sleep(0.6) # Settle
            break

        # Micro-pulse for precision
        if abs(error) <= 6.0:
            turn_speed = 58
            if error > 0: send_motor_cmd(turn_speed, turn_speed, 1, 0)
            else: send_motor_cmd(turn_speed, turn_speed, 0, 1)
            time.sleep(0.06)
            send_motor_cmd(0,0,0,0)
            time.sleep(0.06)
            continue
        else:
            turn_speed = max(48, min(int(abs(error) * 2), 70))
            if error > 0: send_motor_cmd(turn_speed, turn_speed, 1, 0)
            else: send_motor_cmd(turn_speed, turn_speed, 0, 1)
            time.sleep(0.02)

def align_to_absolute_heading(target_heading):
    """Fine-tunes the robot position using tiny motor pulses for geometric precision."""
    print(f" -> [ALIGNMENT] Fine-tuning to absolute {target_heading:.1f}°...")
    nudge_power = 75
    
    while True:
        current_heading = get_heading() 
        error = target_heading - current_heading
        
        if error > 180: error -= 360
        if error < -180: error += 360

        if abs(error) <= 0.8:
            break

        if error > 0:
            arduino.write(f"M:{nudge_power},{nudge_power},1,0\n".encode())
        else:
            arduino.write(f"M:{nudge_power},{nudge_power},0,1\n".encode())
            
        time.sleep(0.05) 
        arduino.write(b"M:0,0,0,0\n") 
        time.sleep(0.2)

# 5. SHAPE DRAWING ROUTINES
def draw_star():
    print("\n[STARTING PRECISION STAR SEQUENCE]")
    TICKS_PER_CM = 20.0 / 22.0
    PEN_OFFSET_FWD = 17.3
    PEN_OFFSET_REV = 23.3   
    LINE_LENGTH = 30.0
    TURN_ANGLE = 144

    set_pen(down=False)
    base_h = get_heading()
    print(f"-> Baseline Heading: {base_h}")

    set_pen(down=True)
    current_target_h = base_h

    for side in range(5):
        print(f" -> Side {side + 1}")
        
        ticks = int(round(LINE_LENGTH * TICKS_PER_CM))
        drive_straight_star_logic(ticks, "forward", current_target_h)

        if side == 4: break

        set_pen(down=False)
        fwd_ticks = int(round(PEN_OFFSET_FWD * TICKS_PER_CM))
        drive_straight_star_logic(fwd_ticks, "forward", current_target_h)

        current_target_h = (current_target_h + TURN_ANGLE) % 360
        optimal_imu_turn(current_target_h)

        rev_ticks = int(round(PEN_OFFSET_REV * TICKS_PER_CM))
        drive_straight_star_logic(rev_ticks, "backward", current_target_h)

        set_pen(down=True)

    set_pen(down=False)

def draw_circle():
    print("\n === STARTING ROUTINE: CIRCLE === ")
    print("[DRAWING CIRCLE] Starting IMU-Governed Clockwise Spin ... ")

    STOP_OFFSET = -2.0
    target_rotation = 360.0 - STOP_OFFSET
    base_L, base_R = 79, 82

    arduino.write(f"M:{base_L},{base_R},1,0\n".encode())

    last_heading = get_heading()
    last_time = time.time()
    total_rotation = 0.0

    while abs(total_rotation) < target_rotation:
        current_time = time.time()
        current_heading = get_heading()
        
        dt = current_time - last_time
        if dt < 0.005: continue

        heading_diff = current_heading - last_heading
        if heading_diff < -180: heading_diff += 360
        elif heading_diff > 180: heading_diff -= 360

        total_rotation += heading_diff
        print(f"Angle: {abs(total_rotation):.1f}/360.0°")

        last_heading, last_time = current_heading, current_time
        time.sleep(0.02)

    print(f"[DRAWING CIRCLE] Stop command sent! Coasting final {STOP_OFFSET} degrees to perfect 360.")
    arduino.write(b"M:0,0,1,1\n")
    time.sleep(0.5)

def draw_line(target_cm):
    TICKS_PER_CM = 1.38
    target_ticks = int(target_cm * TICKS_PER_CM)
    print(f"Drawing {target_cm}cm line ({target_ticks} ticks)...")
    
    if arduino is None or sensor is None: return

    arduino.write(b"R:\n")
    if hasattr(arduino, 'reset_input_buffer'):
        arduino.reset_input_buffer()

    target_heading = get_heading()
    BASE_SPEED, kP = 85, 8.0
    left_ticks, right_ticks = 0, 0

    while left_ticks < target_ticks and right_ticks < target_ticks:
        current_heading = get_heading()
        error = target_heading - current_heading
        if error > 180: error -= 360
        if error < -180: error += 360
        
        left_speed = max(40, min(150, int(BASE_SPEED + (error * kP))))
        right_speed = max(40, min(150, int(BASE_SPEED - (error * kP))))

        arduino.write(f"M:{left_speed},{right_speed},1,1\n".encode())

        if arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8').strip()
                if line.startswith("E:"):
                    parts = line[2:].split(',')
                    if len(parts) == 2:
                        left_ticks, right_ticks = int(parts[0]), int(parts[1])
            except: pass
        time.sleep(0.02)

    arduino.write(b"M:0,0,1,1\n")
    time.sleep(0.2)
    print("Line complete!")

def draw_triangle():
    print("\n=== STARTING ROUTINE: EQUILATERAL TRIANGLE ===")
    SIDE_TICKS = 30
    FORWARD_TICKS = 21
    REVERSE_TICKS = 21
    TURN_ANGLE = 120.0
    COAST_ANGLE = 96.0
    turn_L, turn_R = 79, 82

    set_pen(down=False)
    time.sleep(1.0)
    true_north = get_heading()
    print(f"[CALIBRATION] True North Locked at: {true_north:.1f}°")

    for side in range(3):
        print(f"\n--- DRAWING SIDE {side + 1} OF 3 ---")
        current_line_heading = (true_north + (side * TURN_ANGLE)) % 360.0
        next_line_heading = (true_north + ((side + 1) * TURN_ANGLE)) % 360.0

        set_pen(down=True)
        drive_straight_imu_encoders(SIDE_TICKS, "forward", current_line_heading)
        time.sleep(0.5)

        set_pen(down=False)
        drive_straight_imu_encoders(FORWARD_TICKS, "forward", current_line_heading)
        time.sleep(0.5)

        print(f" -> Spinning towards {next_line_heading:.1f}°...")
        arduino.write(f"M:{turn_L},{turn_R},1,0\n".encode())
        last_heading = get_heading()
        total_rotation = 0.0
        last_time = time.time()

        while abs(total_rotation) < COAST_ANGLE:
            curr_t = time.time()
            curr_h = get_heading()
            dt = curr_t - last_time
            if dt < 0.005: continue

            diff = curr_h - last_heading
            if diff < -180: diff += 360
            elif diff > 180: diff -= 360

            total_rotation += diff
            last_heading, last_time = curr_h, curr_t
            time.sleep(0.02)

        arduino.write(b"M:0,0,0,0\n")
        
        print("[WAIT] Allowing sensor filters to settle...")
        time.sleep(1.5)

        align_to_absolute_heading(next_line_heading)
        time.sleep(0.5)
        
        drive_straight_imu_encoders(REVERSE_TICKS, "backward", next_line_heading)
        time.sleep(1.0) 

    print("\n[FINISHED] Equilateral Triangle complete!")
    set_pen(down=False)

def draw_rectangle():
    print("\n=== STARTING ROUTINE: DRAWING A RECTANGLE ===")
    SIDE_TICKS = [60, 31, 60, 31] 
    FORWARD_TICKS = [21, 20, 20, 22]
    REVERSE_TICKS = [21, 20, 20, 20]
    COAST_ANGLE = 66.0
    turn_L, turn_R = 79, 82

    set_pen(down=False)
    time.sleep(1.0)
    true_north = get_heading()
    print(f"[CALIBRATION] True North Locked at: {true_north:.1f}°")

    for side in range(4):
        print(f"\n--- DRAWING SIDE {side + 1} (Ticks: {SIDE_TICKS[side]}) ---")
        current_line_heading = (true_north + (side * 90.0)) % 360.0
        next_line_heading = (true_north + ((side + 1) * 90.0)) % 360.0

        set_pen(down=True)
        drive_straight_imu_encoders(SIDE_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        set_pen(down=False)
        drive_straight_imu_encoders(FORWARD_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        arduino.write(f"M:{turn_L},{turn_R},1,0\n".encode())
        last_heading = get_heading()
        total_rotation = 0.0
        last_time = time.time()

        while abs(total_rotation) < COAST_ANGLE:
            curr_t = time.time()
            curr_h = get_heading()
            dt = curr_t - last_time
            if dt < 0.005: continue
            diff = curr_h - last_heading
            if diff < -180: diff += 360
            elif diff > 180: diff -= 360
            total_rotation += diff
            last_heading, last_time = curr_h, curr_t
            time.sleep(0.02)

        arduino.write(b"M:0,0,0,0\n")
        
        print("[WAIT] Allowing sensor filters to settle...")
        time.sleep(1.5)

        align_to_absolute_heading(next_line_heading)
        time.sleep(0.5)
        drive_straight_imu_encoders(REVERSE_TICKS[side], "backward", next_line_heading)
        time.sleep(1.0) 

    print("\n[FINISHED] Rectangle complete!")
    set_pen(down=False)        

def draw_square():
    print("\n=== STARTING ROUTINE: DRAWING AN ABSOLUTE SQUARE ===")
    SIDE_TICKS = [50, 51, 50, 51]
    FORWARD_TICKS = [21, 20, 20, 22]
    REVERSE_TICKS = [21, 20, 20, 20]
    COAST_ANGLE = 66.0
    turn_L, turn_R = 79, 82

    set_pen(down=False)
    time.sleep(1.0)
    true_north = get_heading()
    print(f"[CALIBRATION] True North Locked at: {true_north:.1f}°")

    for side in range(4):
        print(f"\n--- DRAWING SIDE {side + 1} OF 4 ---")
        current_line_heading = (true_north + (side * 90.0)) % 360.0
        next_line_heading = (true_north + ((side + 1) * 90.0)) % 360.0

        set_pen(down=True)
        drive_straight_imu_encoders(SIDE_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        set_pen(down=False)
        drive_straight_imu_encoders(FORWARD_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        arduino.write(f"M:{turn_L},{turn_R},1,0\n".encode())
        last_heading = get_heading()
        total_rotation = 0.0
        last_time = time.time()

        while abs(total_rotation) < COAST_ANGLE:
            curr_t = time.time()
            curr_h = get_heading()
            dt = curr_t - last_time
            if dt < 0.005: continue
            diff = curr_h - last_heading
            if diff < -180: diff += 360
            elif diff > 180: diff -= 360
            total_rotation += diff
            last_heading, last_time = curr_h, curr_t
            time.sleep(0.02)

        arduino.write(b"M:0,0,0,0\n")
        
        print("[WAIT] Allowing sensor filters to settle...")
        time.sleep(1.5)

        align_to_absolute_heading(next_line_heading)
        time.sleep(0.5)
        drive_straight_imu_encoders(REVERSE_TICKS[side], "backward", next_line_heading)
        time.sleep(1.0) 

    print("\n[FINISHED] Absolute Square complete!")
    set_pen(down=False)

# 6. SHAPE DISPATCHER & TIMING
def draw_shape_routine(shape_name):
    global is_drawing, last_time_taken
    is_drawing = True
    print(f"\n=== STARTING ROUTINE: {shape_name.upper()} ===")
    
    start_time = time.time() 
    
    set_pen(down=True) 
    time.sleep(0.5) 
    
    if shape_name == "Line":
        draw_line(20)  
    elif shape_name == "Square":
        draw_square()
    elif shape_name == "Rectangle":
        draw_rectangle()
    elif shape_name == "Triangle":
        draw_triangle()
    elif shape_name == "Circle":
        draw_circle()
    elif shape_name == "5 Pointed Star":
        draw_star()
    
    set_pen(down=False)
    time.sleep(0.5) 
    
    end_time = time.time()
    last_time_taken = end_time - start_time
    
    print("=== DRAWING COMPLETE ===")
    print(f"*** TIME TAKEN: {last_time_taken:.2f} seconds ***")
    is_drawing = False

# 7. COMPUTER VISION & FLASK
def count_fingers(hand_landmarks, hand_label):
    count = 0
    if hand_label == "Right":
        if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x: count += 1
    else:
        if hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x: count += 1
    
    tips, pips = [8, 12, 16, 20], [6, 10, 14, 18]
    for tip, pip in zip(tips, pips):
        if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[pip].y: count += 1
    return count

def generate_frames():
    global latest_frame, current_state, detected_shape, live_finger_count, last_sent_shape, is_drawing, last_time_taken
    
    while True:
        if latest_frame is None:
            time.sleep(0.01)
            continue
            
        frame = latest_frame.copy()
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        left_hand_fingers, right_hand_fingers, num_hands = -1, -1, 0
        
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            for idx, hand_lms in enumerate(results.multi_hand_landmarks):
                mp_drawing.draw_landmarks(
                    frame, hand_lms, mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style()
                )

                label = results.multi_handedness[idx].classification[0].label
                fingers = count_fingers(hand_lms, label)
                if label == "Left": 
                    left_hand_fingers = fingers
                elif label == "Right": 
                    right_hand_fingers = fingers
                    
        if num_hands == 0 and not is_drawing:
            current_state = "WAITING"
            detected_shape = ""
            last_sent_shape = ""

        elif not is_drawing:
            if current_state in ["WAITING", "LOCKED"] and left_hand_fingers >= 4:
                current_state = "READING"
                detected_shape = ""
            elif current_state == "READING":
                if right_hand_fingers != -1:
                    live_finger_count = min(5, max(0, right_hand_fingers))
                if left_hand_fingers <= 1 and left_hand_fingers != -1:
                    detected_shape = shape_map.get(live_finger_count, "Unknown")
                    current_state = "LOCKED"
                    if detected_shape != last_sent_shape and num_hands == 2:
                        last_sent_shape = detected_shape
                        threading.Thread(target=draw_shape_routine, args=(detected_shape,), daemon=True).start()

        if sensor:
            euler = sensor.euler
            if euler[0] is not None:
                cv2.putText(frame, f"H:{euler[0]:.1f} R:{euler[1]:.1f} P:{euler[2]:.1f}", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        if is_drawing:
            cv2.putText(frame, f"DRAWING: {detected_shape.upper()}", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        elif num_hands < 2 and current_state != "LOCKED":
            cv2.putText(frame, "Status: Show BOTH hands", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        elif current_state == "WAITING":
            cv2.putText(frame, "Status: Ready for gesture...", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        elif current_state == "READING":
            cv2.putText(frame, "Status: Reading shape...", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        if current_state == "LOCKED" and detected_shape and not is_drawing:
            cv2.putText(frame, f"{detected_shape.upper()} Read! Starting...", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)
            
        if last_time_taken > 0 and not is_drawing:
            cv2.putText(frame, f"Last Draw Time: {last_time_taken:.1f}s", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/')
def index():
    return render_template_string('<html><body style="background:#222;color:white;text-align:center;"><h1>Drawing Bot HUD</h1><img src="/video_feed" style="width:80%;"></body></html>')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
