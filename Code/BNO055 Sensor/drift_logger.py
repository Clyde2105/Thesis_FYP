# Purpose: Script to generate data for Excel graph. 
# It records the sensor's drift for exactly 5 minutes (300 seconds) and saves it to a CSV file.

import time
import board
import busio
import adafruit_bno055
import csv

# Initialize I2C connection
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bno055.BNO055_I2C(i2c)

# Configuration
FILENAME = "drift_data.csv"
DURATION_SEC = 300  # 5 minutes
INTERVAL = 0.5      # Record every half second

print(f"Starting Data Log for {DURATION_SEC} seconds...")
print(f"Saving to {FILENAME}")
print("Do not move the robot!")

# Open the file and write the header row
with open(FILENAME, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Time_Sec", "Heading", "Roll", "Pitch"])
    
    start_time = time.time()
    
    while (time.time() - start_time) < DURATION_SEC:
        current_time = time.time() - start_time
        heading, roll, pitch = sensor.euler
        
        if heading is not None:
            # Write data to CSV
            writer.writerow([round(current_time, 1), heading, roll, pitch])
            print(f"Time: {round(current_time, 1)}s | Heading: {heading}")
        
        time.sleep(INTERVAL)

print("------------------------------------------")
print("Logging Complete. Data saved.")