import time
import board
import busio
import adafruit_bno055

# Initialize I2C connection
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_bno055.BNO055_I2C(i2c)

print("BNO055 Sensor Test - Press Ctrl+C to stop")
print("------------------------------------------")

while True:
    # Read the Euler angles (Heading, Roll, Pitch)
    heading, roll, pitch = sensor.euler
    
    # Sometimes the sensor returns None if it's busy, handle that safely
    if heading is not None:
        print(f"Heading: {heading:.2f}° | Roll: {roll:.2f}° | Pitch: {pitch:.2f}°")
    else:
        print("Waiting for data...")
        
    time.sleep(0.5)