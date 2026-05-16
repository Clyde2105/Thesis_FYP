import time
import serial
import board
import adafruit_bno055

# 1. HARDWARE SETUP
print("--- Initializing Hardware ---")
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


# 2. MOVEMENT FUNCTIONS
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
                

# 3. KINEMATIC SHAPE LOGIC
def draw_star_absolute(line_cm=30.0, offset_fwd_cm=17.3, offset_rev_cm=23.3, ticks_per_cm=0.909):
    TURN_ANGLE = 144
    print("\n[STARTING PRECISION STAR SEQUENCE]")

    # 1. Ensure Pen is UP for the alignment wiggle
    arduino.write(b"P:0\n")
    time.sleep(0.5)

    # 2. THE PRE-DRIVE WIGGLE
    print("-> Performing pre-drive tensioning to align wheels and IMU...")
    temp_heading = sensor.euler[0]
    while temp_heading is None:
        time.sleep(0.1)
        temp_heading = sensor.euler[0]

    # Drive 5 ticks (~5cm) forward and back to lock gears and wheels
    drive_straight_imu_encoders(5, "forward", int(temp_heading))
    drive_straight_imu_encoders(5, "backward", int(temp_heading))

    # Wait 1 full second for chassis and IMU filters to completely settle
    time.sleep(1.0)

    # 3. CAPTURE THE TRUE BASELINE HEADING 
    current_heading = sensor.euler[0]
    while current_heading is None:
        time.sleep(0.1)
        current_heading = sensor.euler[0]
    current_heading = int(current_heading)
    print(f"-> True Baseline Heading Locked: {current_heading}")

    # 4. Lower pen to begin drawing
    arduino.write(b"P:1\n")
    time.sleep(0.5)

    # --- MAIN DRAWING LOOP BEGINS ---
    for side in range(5):
        print(f"\n --- Drawing Side {side + 1} of 5 ---")

        # --- PHASE 1: DRAW LINE ---
        target_float = line_cm * ticks_per_cm
        ticks_to_drive = int(round(target_float))
        drive_straight_imu_encoders(ticks_to_drive, "forward", current_heading)

        if side == 4:
            arduino.write(b"P:0\n")
            print("Star Complete!")
            break

        # --- PHASE 2: CENTER SHIFT FORWARD ---
        arduino.write(b"P:0\n")
        time.sleep(0.6)

        fwd_ticks = int(round(offset_fwd_cm * ticks_per_cm))
        print(f" -> Shifting Center to Vertex ({fwd_ticks} ticks)")
        drive_straight_imu_encoders(fwd_ticks, "forward", current_heading)

        # --- PHASE 3: TURN ---
        current_heading = (current_heading + TURN_ANGLE) % 360
        optimal_imu_turn(current_heading)
        time.sleep(0.5)

        # --- PHASE 4: OVERDRIVE REVERSE ---
        # Using the much larger offset_rev_cm to overcome wheel slip
        rev_ticks = int(round(offset_rev_cm * ticks_per_cm))
        print(f" -> Retracting to Vertex ({rev_ticks} ticks)")
        drive_straight_imu_encoders(rev_ticks, "backward", current_heading)

        arduino. write(b"P:1\n")
        time.sleep(0.6)

# RUN PROGRAM
if __name__ == "__main__":
    time. sleep(1)

    WHEEL_CIRCUMFERENCE_CM = 22.0
    ENCODER_SLOTS = 20.0
    TICKS_PER_CM = ENCODER_SLOTS / WHEEL_CIRCUMFERENCE_CM

    # Decoupled Kinematics
    PEN_OFFSET_FWD = 17.3
    PEN_OFFSET_REV = 23.3   # 17.3 base + 6cm compensation for reverse wheel slip
    LINE_LENGTH = 30.0

    print(f"Calculated Ticks per CM: {TICKS_PER_CM:.3f}")

    draw_star_absolute(
        line_cm=LINE_LENGTH,
        offset_fwd_cm=PEN_OFFSET_FWD,
        offset_rev_cm=PEN_OFFSET_REV,
        ticks_per_cm=TICKS_PER_CM
    )
