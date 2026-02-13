# Purpose: Sensor Linearity Test; Validates the sensor's precision by 
# comparing real angles against measured values.
 
# Goals: 
# 1) If the dots are on the line -> sensor is accurate.
# 2) If the whiskers are small -> sensor is precise (not noisy).


# pip3 install numpy

import time
import board
import adafruit_bno055
import numpy as np  

# Setup
i2c = board.I2C()
sensor = adafruit_bno055.BNO055_I2C(i2c)

# The angles we want to test
target_angles = [0, 30, 60, 90, 120, 150, 180]
results = []

print("BNO055 Linearity Test")
print("---------------------")

for target in target_angles:
    input(f"--> Please rotate sensor to exactly {target}° and press ENTER...")
    print(f"Sampling {target}° for 5 seconds...")
    
    samples = []
    start_time = time.time()
    
    # Collect data for 5 seconds
    while time.time() - start_time < 5:
        heading = sensor.euler[0]
        if heading is not None:
            samples.append(heading)
        time.sleep(0.1)
        
    # Calculate stats
    avg = np.mean(samples)
    min_val = np.min(samples)
    max_val = np.max(samples)
    std_dev = np.std(samples)
    
    print(f"   Saved: Avg={avg:.2f}° | Min={min_val:.2f} | Max={max_val:.2f}")
    results.append([target, avg, min_val, max_val, std_dev])

print("\nDONE! Plot Data:")
print("Target,Average,Min,Max,StdDev")
for r in results:
    print(f"{r[0]},{r[1]:.2f},{r[2]:.2f},{r[3]:.2f},{r[4]:.2f}")