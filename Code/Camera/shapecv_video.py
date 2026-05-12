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

# Setup Flask
app = Flask(__name__)

# Setup BNO055 Sensor
try:
    i2c = board.I2C()
    sensor = adafruit_bno055.BNO055_I2C(i2c)
except Exception as e:
    print(f"BNO055 not found: {e}")
    sensor = None

# Setup Serial (Arduino)
arduino = None
# List of common ports the Pi uses for Arduino
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
mp_drawing = mp.solutions.drawing_utils           # For drawing skeleton
mp_drawing_styles = mp.solutions.drawing_styles   # For Google-style colors
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


# BACKGROUND THREADS
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
            # Find the very last start-of-frame to avoid processing stale data
            last_a = bytes_buffer.rfind(b'\xff\xd8')
            if last_a != -1:
                bytes_buffer = bytes_buffer[last_a:]
            else:
                bytes_buffer = b''
            continue

        # 1. Find the start of the JPEG frame
        a = bytes_buffer.find(b'\xff\xd8')
        if a == -1: 
            continue # Keep reading until we find a header

        # 2. Find the end of the frame (MUST start looking AFTER the header 'a')
        b = bytes_buffer.find(b'\xff\xd9', a + 2)
        
        if b != -1:
            jpg = bytes_buffer[a:b+2]
            bytes_buffer = bytes_buffer[b+2:]
            
            # Safety check: Ensures the slice isn't empty before sending to OpenCV
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

# Start background threads
threading.Thread(target=camera_thread, daemon=True).start()
threading.Thread(target=serial_listener_thread, daemon=True).start()


# ROBOT NAVIGATION & PID CONTROL
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

def drive_straight_star_logic(target_ticks, direction="forward", target_heading=None):
    """Specialized drive function for the Star routine with Kp=4 tuning."""
    if arduino is None or sensor is None: return
    
    arduino.reset_input_buffer()
    arduino.write(b"R:\n") 
    time.sleep(0.1)

    if target_heading is None:
        target_heading = get_heading()

    # Star-specific baseline speeds
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
        
        # Update Steering
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
    """Proportional control turn with mechanical backlash compensation."""
    print(f" -> [TURN PID] Locking onto absolute heading: {target_heading: .1f}")

    # We lowered the tolerance to 0.5 degrees for maximum geometric precision
    MIN_MOTOR_SPEED = 48
    TURN_KP = 2
    MAX_TURN_SPEED = 70

    while True:
        current_heading = sensor.euler[0]
        if current_heading is None:
            time.sleep(0.04)
            continue

        error = target_heading - current_heading

        # Normalize error to -180 to 180 degrees
        if error > 180: error -= 360
        if error < -180: error += 360

        # --- 1. FIRST PASS: Have we hit the target? ---
        if abs(error) <= tolerance:
            arduino.write(b"M:0,0,0,0\n") # Cut the engines

            # Wait for physical momentum to stop
            time.sleep(0.6)
            
            # Verify we are still on target after settling
            settled_heading = sensor.euler[0]
            if settled_heading is not None:
                settled_error = target_heading - settled_heading
                if settled_error > 180: settled_error -= 360
                if settled_error < -180: settled_error += 360

                if abs(settled_error) <= tolerance:
                    print(f" -> [LOCKED] Settled Heading: {settled_heading:.1f}degrees")
                    break
                else:
                    print(f" -> [SLIP] Relaxed to {settled_heading:.1f} degrees with error {settled_error:.1f}. Re-adjusting...")
            
            # --- 2. MICRO-PULSE ZONE ---  (To prevent sort of 'ping-pong' oscillation)
            # If close but not quite there, normal PID will overshoot because of USB latency.
            # Instead, give the motors a tiny 40-millisecond "tap" to inch it over.
            elif abs(error) <= 6.0:
                turn_speed = 58 # Just enough to break static friction without overshooting 
                if error > 0:
                    arduino.write(f"M:{turn_speed},{turn_speed},1,0\n".encode()) # Right
                else:
                    arduino.write(f"M:{turn_speed},{turn_speed},0,1\n".encode()) # Left
                    
                time.sleep(0.06) # Small nudge
                arduino.write(b"M:0,0,0,0\n") # Immediate hard stop
                time.sleep(0.06) # Wait for it to settle before next reading
                continue
            
            # --- 3. Normal PID Drive ---   (for large turns)
            else:  
                turn_speed = int(abs(error) * TURN_KP)
                turn_speed = max(MIN_MOTOR_SPEED, min(turn_speed, MAX_TURN_SPEED))
                
                if error > 0:
                    arduino.write(f"M:{turn_speed},{turn_speed},1,0\n".encode()) # Right
                else:
                    arduino.write(f"M:{turn_speed},{turn_speed},0,1\n".encode()) # Left
                
                time.sleep(0.02)
                
def draw_star():
    print("\n[STARTING PRECISION STAR SEQUENCE]")
    
    # Configuration
    TICKS_PER_CM = 20.0 / 22.0 # ENCODER_SLOTS / WHEEL_CIRCUMFERENCE
    PEN_OFFSET_FWD = 17.3
    PEN_OFFSET_REV = 23.3   
    LINE_LENGTH = 30.0
    TURN_ANGLE = 144

    # 1. Align and Lock Heading
    set_pen(down=False)
    base_h = get_heading()
    print(f"-> Baseline Heading: {base_h}")

    # 2. Start Drawing
    set_pen(down=True)
    current_target_h = base_h

    for side in range(5):
        print(f" -> Side {side + 1}")
        
        # Phase A: Draw Line
        ticks = int(round(LINE_LENGTH * TICKS_PER_CM))
        drive_straight_star_logic(ticks, "forward", current_target_h)

        if side == 4: break # Finish last side

        # Phase B: Kinematic Adjustment (Forward -> Turn -> Reverse)
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

    # Best offset to close the gap
    STOP_OFFSET = -2.0
    target_rotation = 360.0 - STOP_OFFSET

    # Balanced speeds so it stays perfectly in place
    base_L = 79
    base_R = 82

    # 1, 0 -> Left Forward (1), Right Backward (0) = CLOCKWISE SPIN
    arduino. write(f"M:{base_L},{base_R},1,0\n".encode())

    # Wait for a valid IMU reading
    last_heading = sensor.euler[0]
    while last_heading is None:
        time.sleep(0.05)
        last_heading = sensor.euler[0]

    last_time = time.time()
    total_rotation = 0.0

    while abs(total_rotation) < target_rotation:
        current_time = time.time()
        current_heading = sensor.euler[0]

        if current_heading is None:
          continue
        
        dt = current_time - last_time
        if dt < 0.005:
            continue

        heading_diff = current_heading - last_heading

        # Handling the 360-to-0 degree crossover on the compass
        if heading_diff < -180: heading_diff += 360
        elif heading_diff > 180: heading_diff -= 360

        total_rotation += heading_diff

        # Print progress so you can monitor the spin
        print(f"Angle: {abs(total_rotation):.1f}/360.0°")

        last_heading = current_heading
        last_time = current_time
        time.sleep(0.02)

    # Hard stop exactly when the IMU hits the target
    print(f"[DRAWING CIRCLE] Stop command sent! Coasting final {STOP_OFFSET} degrees to perfect 360.")
    arduino.write(b"M:0,0,1,1\n")
    time.sleep(0.5)

def draw_line(target_cm) :
    # Converting cm to encoder ticks (approx 1.38 ticks per cm based on tests)
    TICKS_PER_CM = 1.38
    target_ticks = int(target_cm * TICKS_PER_CM)

    print(f"Drawing {target_cm}cm line ({target_ticks} ticks)...")
    
    # Safety check in case hardware disconnects
    if arduino is None or sensor is None:
        print("Error: Arduino or BN0055 not connected. Cannot draw. ")
        return

    # 1. Reset Encoders
    arduino.write(b"R:\n")
    if hasattr(arduino, 'reset_input_buffer'):
        arduino.reset_input_buffer()

    # 2. Lock Target Heading
    target_heading = sensor.euler[0]
    while target_heading is None:
        time.sleep(0.05)
        target_heading = sensor.euler[0]

    BASE_SPEED = 85
    kP = 8.0

    left_ticks = 0
    right_ticks = 0

    # 3. The Self-Correcting Drive Loop
    while left_ticks < target_ticks and right_ticks < target_ticks:
        current_heading = sensor.euler[0]
        if current_heading is None:
         continue

    # Calculate Error
    error = target_heading - current_heading
    if error > 180: error -= 360
    if error < -180: error += 360
    
    # P-Controller logic
    left_speed = int(BASE_SPEED + (error * kP))
    right_speed = int(BASE_SPEED - (error * kP))

    # Constrain speeds
    left_speed = max(40, min(150, left_speed))
    right_speed = max(40, min(150, right_speed))

    # Command Motors
    cmd = f"M:{left_speed},{right_speed},1,1\n"
    arduino. write(cmd. encode())

    # Read Encoders
    if arduino.in_waiting > 0:
        try:
            line = arduino.readline().decode('utf-8').strip()
            if line.startswith("E:"):
                parts = line[2:].split(',')
                if len(parts) == 2:
                    left_ticks = int(parts[0])
                    right_ticks = int(parts[1])
        except:
            pass # Ignore random serial noise

    time.sleep(0.02) # Prevent flooding the serial bus

    # 4. Stop Motors
    arduino.write(b"M:0,0,1,1\n")
    time.sleep(0.2)
    print("Line complete!")

def align_to_absolute_heading(target_heading):
    """Fine-tunes the robot position using tiny motor pulses for geometric precision."""
    print(f" -> [ALIGNMENT] Fine-tuning to absolute {target_heading:.1f}°...")
    nudge_power = 75
    
    while True:
        current_heading = get_heading() # Uses your existing get_heading helper
        error = target_heading - current_heading
        
        if error > 180: error -= 360
        if error < -180: error += 360

        if abs(error) <= 0.8: # Threshold for 'perfect' alignment
            break

        if error < 0:
            arduino.write(f"M:{nudge_power},{nudge_power},1,0\n".encode()) # Right
        else:
            arduino.write(f"M:{nudge_power},{nudge_power},0,1\n".encode()) # Left
            
        time.sleep(0.05) 
        arduino.write(b"M:0,0,0,0\n") 
        time.sleep(0.2) # Wait for physical momentum to settle
        
def draw_rectangle():
    print("\n=== STARTING ROUTINE: DRAWING A RECTANGLE ===")

    # Define alternating lengths: [Long, Short, Long, Short]
    # Adjust these numbers to change the size of your rectangle
    SIDE_TICKS = [80, 40, 80, 40] 
    
    # These stay the same as the square because the pen position hasn't changed
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

        # 1. Draw the line (Uses the alternating lengths)
        set_pen(down=True)
        drive_straight_imu_encoders(SIDE_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        # 2. Lift and Kinematic Overshoot
        set_pen(down=False)
        drive_straight_imu_encoders(FORWARD_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        # 3. Fast Relative Spin
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
        
        # 4. Sensor Settle
        print("[WAIT] Allowing sensor filters to settle...")
        time.sleep(1.5)

        # 5. Precise Alignment and Reverse back
        align_to_absolute_heading(next_line_heading)
        time.sleep(0.5)
        drive_straight_imu_encoders(REVERSE_TICKS[side], "backward", next_line_heading)
        time.sleep(1.0) 

    print("\n[FINISHED] Rectangle complete!")
    set_pen(down=False)        

def draw_square():
    print("\n=== STARTING ROUTINE: DRAWING AN ABSOLUTE SQUARE ===")

    # Finely-tuned physical constants from your test file
    SIDE_TICKS = [50, 51, 50, 51]
    FORWARD_TICKS = [21, 20, 20, 22]
    REVERSE_TICKS = [21, 20, 20, 20]
    COAST_ANGLE = 66.0
    turn_L, turn_R = 79, 82

    set_pen(down=False)
    time.sleep(1.0)

    # Grab the starting orientation
    true_north = get_heading()
    print(f"[CALIBRATION] True North Locked at: {true_north:.1f}°")

    for side in range(4):
        print(f"\n--- DRAWING SIDE {side + 1} OF 4 ---")
        current_line_heading = (true_north + (side * 90.0)) % 360.0
        next_line_heading = (true_north + ((side + 1) * 90.0)) % 360.0

        # 1. Draw the line
        set_pen(down=True)
        drive_straight_imu_encoders(SIDE_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        # 2. Lift and clear the corner (Kinematic Overshoot)
        set_pen(down=False)
        drive_straight_imu_encoders(FORWARD_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        # 3. Fast Relative Spin
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
        
        # 4. CRITICAL: Allow BNO055 Kalman filter to settle before precision alignment
        print("[WAIT] Allowing sensor filters to settle...")
        time.sleep(1.5)

        # 5. Precise Alignment and Reverse back to corner
        align_to_absolute_heading(next_line_heading)
        time.sleep(0.5)
        drive_straight_imu_encoders(REVERSE_TICKS[side], "backward", next_line_heading)
        time.sleep(1.0) 

    print("\n[FINISHED] Absolute Square complete!")
    set_pen(down=False)
        
def set_pen(down=True):
    if arduino:
        arduino.write(b"P:1\n" if down else b"P:0\n")
    time.sleep(0.5)
    

# SHAPE DRAWING ROUTINES
def draw_shape_routine(shape_name):
    global is_drawing
    is_drawing = True
    print(f"\=== STARTING ROUTINE: {shape_name.upper()} ===")
    
    # 1. Start Timer
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
    time. sleep(0.5) # Ensures the servo actually lifts before the robot moves again!
    
    # 2. End Timer & Calculate
    end_time = time.time()
    last_time_taken = end_time - start_time
    
    print("=== DRAWING COMPLETE ===")
    print(f"*** TIME TAKEN: {last_time_taken:.2f}seconds ***")
    is_drawing = False


# COMPUTER VISION & FLASK
def count_fingers(hand_landmarks, hand_label):
    count = 0
    # Thumb logic (different for left/right hands)
    if hand_label == "Right":
        if hand_landmarks.landmark[4].x < hand_landmarks.landmark[3].x: count += 1
    else:
        if hand_landmarks.landmark[4].x > hand_landmarks.landmark[3].x: count += 1
    
    # Fingers logic
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
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        left_hand_fingers, right_hand_fingers, num_hands = -1, -1, 0
        
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            for idx, hand_lms in enumerate(results.multi_hand_landmarks):
                # DRAW HAND LANDMARKS ON SCREEN
                mp_drawing.draw_landmarks(
                    frame, 
                    hand_lms, 
                    mp_hands.HAND_CONNECTIONS,
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

        # State Machine Logic
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

        # WEB UI OVERLAYS
        # 1. Compass Data
        if sensor:
            euler = sensor.euler
            if euler[0] is not None:
                cv2.putText(frame, f"H:{euler[0]:.1f} R:{euler[1]:.1f} P:{euler[2]:.1f}", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # 2. Dynamic Status Messages
        if is_drawing:
            cv2.putText(frame, f"DRAWING: {detected_shape.upper()}", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        elif num_hands < 2 and current_state != "LOCKED":
            cv2.putText(frame, "Status: Show BOTH hands", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        elif current_state == "WAITING":
            cv2.putText(frame, "Status: Ready for gesture...", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        elif current_state == "READING":
            cv2.putText(frame, "Status: Reading shape...", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # 3. Shape Locked Notification
        if current_state == "LOCKED" and detected_shape and not is_drawing:
            cv2.putText(frame, f"{detected_shape.upper()} Read! Starting...", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)
            
        # 4. Show the time taken for the last drawn shape
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
	
