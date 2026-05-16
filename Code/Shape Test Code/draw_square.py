import time
import serial
import board
import busio
import adafruit_bno055

# 1. SETUP SECTION
print("Initializing Hardware...")
try:
    i2c = board. I2C()
    sensor = adafruit_bno055.BN0055_I2C(i2c)
    print("BN0055 initialized successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: BN0055 not found: {e}")
    sensor = None
    exit()

arduino = None
ports_to_try = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1' ]

for port in ports_to_try:
    try:
        arduino = serial. Serial(port, 115200, timeout=1)
        print(f"Arduino connected successfully on {port}!")
        time. sleep(2) # Give Arduino a second to reset
        break
    except serial. SerialException:
        continue

    if arduino is None:
        print("CRITICAL ERROR: Could not find Arduino on any USB port!")
        exit()


# 2. SENSOR FUSION DRIVE FUNCTION
def drive_straight_imu_encoders(target_ticks, direction="forward", absolute_heading=None):
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


# 3. ABSOLUTE ALIGNMENT FUNCTION
def align_to_absolute_heading(target_heading):
    print(f" -> [ALIGNMENT] Fine-tuning to absolute {target_heading:.1f}°...")

    # pulse the motors at 75 power for a tiny fraction of a second to nudge it
    nudge_power = 75
    
    while True:
        current_heading = sensor.euler[0]
        if current_heading is None:
            continue

        error = target_heading - current_heading
        # Normalize error to -180 to 180 degrees
        if error > 180: error -= 360
        if error < -180: error += 360

        # within 0.8 degrees of perfect, good!
        if abs(error) <= 0.8:
            break

        if error < 0:
            # Need to turn right (clockwise)
            arduino.write(f"M:{nudge_power},{nudge_power},1,0\n".encode())
        else:
            # Need to turn left (counterclockwise)
            arduino.write(f"M:{nudge_power},{nudge_power},0,1\n".encode())
            
        time.sleep(0.05) # tiny pulse
        arduino.write(b"M:0,0,0,0\n") # Stop
        time.sleep(0.2) # wait for physical momentum to settle before measuring again    
                
    print(" -> [ALIGNMENT] Perfectly Locked in!")
 
    
def optimal_imu_turn_sqr(target_heading, tolerance=1.0):
    print(f" -> [TURN PID] Locking onto absolute heading: {target_heading:.1f}°")

    # Motor tuning for specific hardware characteristics
    MIN_MOTOR_SPEED = 45    # The lowest PWM value where motors actually move without stalling 
    TURN_KP = 1.2           # Proportional gain for turning

    while True:
        current_heading = sensor.euler[0]
        if current_heading is None:
            time.sleep(0.01)
            continue

        error = target_heading - current_heading
        if error > 180: error -= 360
        if error < -180: error += 360

        # within tolerance (e.g. 1 degree), stop!
        if abs(error) <= tolerance:
            arduino.write(b"M:0,0,0,0\n") # Cut the engines
            print(f" -> [LOCKED] Current Heading: {current_heading:.1f}°")
            break

        # Calculate speed based on how far we are from the target
        # The closer we get, the slower we turn, preventing overshoot.
        turn_speed = int(abs(error) * TURN_KP)
        
        # Determine direction: Positive error = Turn Right, Negative = Turn Left
        turn_speed = max(MIN_MOTOR_SPEED, min(turn_speed, 85))
        
        if error > 0:
            arduino.write(f"M:{turn_speed},{turn_speed},1,0\n".encode()) # Spin Right
        else:
            arduino.write(f"M:{turn_speed},{turn_speed},0,1\n".encode()) # Spin Left
        
        time.sleep(0.02)


# 4. THE FULL SQUARE ROUTINE
def draw_square():
    print("=== STARTING ROUTINE: DRAWING AN ABSOLUTE SQUARE ===")

    # Your updated, finely-tuned values!
    # Array mapping: [Side 0, Side 1, Side 2, Side 3]
    SIDE_TICKS = [50, 51, 50, 51]
    FORWARD_TICKS = [21, 20, 20, 22]
    REVERSE_TICKS = [21, 20, 20, 20]

    COAST_ANGLE = 66.0
    turn_L = 79
    turn_R = 82

    arduino.write(b"P:0\n")
    time.sleep(1.0)

    # Grab TRUE NORTH
    true_north = sensor.euler[0]
    while true_north is None:
        time.sleep(0.05)
        true_north = sensor.euler[0]

    print(f"\n[CALIBRATION] True North Locked at: {true_north:.1f}°")

    for side in range(4):
        print(f"\n--- DRAWING SIDE {side + 1} OF 4 ---")

        current_line_heading = (true_north + (side * 90.0)) % 360.0
        next_line_heading = (true_north + ((side + 1) * 90.0)) % 360.0

        # STEP 1: Lower pen
        arduino.write(b"P:1\n")
        time.sleep(1.0) # Let pen stop bouncing

        # STEP 2: Draw the line (LM393 for distance, BNO055 for heading)
        # With SIDE_TICKS at 80, Kp=4 will actually have time to work
        drive_straight_imu_encoders(SIDE_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        # STEP 3: Lift pen
        arduino.write(b"P:0\n")
        time.sleep(0.5)

        # STEP 4: Kinematic Overshoot (LM393 purely)
        drive_straight_imu_encoders(FORWARD_TICKS[side], "forward", current_line_heading)
        time.sleep(0.5)

        # STEP 5: Fast Relative Spin
        arduino.write(f"M:{turn_L},{turn_R},1,0\n".encode())

        last_heading = sensor.euler[0]
        while last_heading is None:
            time.sleep(0.05)
            last_heading = sensor.euler[0]

        last_time = time.time()
        total_rotation = 0.0

        while abs(total_rotation) < COAST_ANGLE:
            current_time = time.time()
            current_heading = sensor.euler[0]
            if current_heading is None: continue

            dt = current_time - last_time
            if dt < 0.005: continue

            heading_diff = current_heading - last_heading
            if heading_diff < -180: heading_diff += 360
            elif heading_diff > 180: heading_diff -= 360

            total_rotation += heading_diff
            last_heading = current_heading
            last_time = current_time
            time.sleep(0.02)

        # Stop the motors
        arduino.write(b"M:0,0,0,0\n")
        
        # ==========================================
        # CRITICAL UPDATE: THE SENSOR SETTLING DELAY
        # ==========================================
        # We must wait 1.5 seconds here!
        # The BNO055 magnetometer gets distorted by the sudden burst
        # of the motor's magnetic fields during the spin.
        # We must let the physical momentum stop AND the IMU filter settle.
        print("[WAIT] Allowing BNO055 Kalman filter to settle...")
        time.sleep(1.5)

        # STEP 5.5: Absolute Alignment (The True 90-degree lock)
        align_to_absolute_heading(next_line_heading)

        # Optional: Another tiny delay to ensure we are locked before reversing
        time.sleep(0.5)

        # STEP 6: Reverse back into position (LM393 purely)
        drive_straight_imu_encoders(REVERSE_TICKS[side], "backward", next_line_heading)
        time.sleep(1.0) # Let momentum stop before dropping pen again

        print(f"--- SIDE {side + 1} COMPLETE ---")

    print("\n[FINISHED] Absolute Square complete! Lifting pen...")
    arduino.write(b"P:0\n")
    
# ==========================================
# 5. EXECUTE
# ==========================================
if __name__ == "__main__":
    print("Test will begin in 3 seconds. Put robot in position!")
    time.sleep(3)
    try:
        draw_square()
    except KeyboardInterrupt:
        print("\n[EMERGENCY STOP] Script aborted by user.")
        arduino.write(b"M:0,0,0,0\n")
        arduino.write(b"P:0\n")