# Shape-to-Path Conversion and Drawing with a Mobile Robot

This repository contains the source code, simulation scripts, testing evidence and result files for the final-year thesis project **Shape-to-Path Conversion and Drawing with a Mobile Robot**.

The project explores how a low-cost educational mobile robot can be upgraded from basic open-loop movement into a closed-loop autonomous drawing system. The final system combines computer vision, hand gesture control, wheel encoder odometry, absolute orientation sensing and PID-based motor correction to translate digital geometric shapes into physical drawings on a floor canvas.

## Project Summary

Low-cost differential-drive robots are useful for education but they usually struggle with accurate geometric movement. When a robot attempts to draw shapes using only timed motor commands, small errors caused by wheel slip, uneven motor behaviour, battery voltage changes and sensor noise quickly accumulate. This produces distorted shapes and large closure errors, especially for polygons that require sharp turns.

This project addresses that problem by modifying an Elegoo Smart Robot Car Kit V4 into a mobile drawing robot. A Raspberry Pi 5 handles high-level processing, camera input and gesture recognition. An Arduino Uno handles low-level motor execution. A BNO055 9-axis absolute orientation sensor provides drift-corrected heading data, while LM393 optical wheel encoders provide odometry feedback. Together, these components allow the robot to correct its path while drawing.

The system supports six geometric drawing routines:

- Line
- Circle
- Square
- Rectangle
- Triangle
- Five-pointed star

The project also includes ROS/Gazebo simulation work, physical testing photos, sensor tests, computer vision verification scripts and spreadsheet-based result files.

## Main Features

- **Gesture-based shape selection** using OpenCV, MediaPipe and a Raspberry Pi Camera Module 3.
- **Closed-loop heading correction** using BNO055 absolute orientation data.
- **Wheel odometry feedback** using LM393 infrared encoders and 20-slot encoder discs.
- **Arduino-based motor execution** for real-time low-level control.
- **Servo-actuated pen-lift mechanism** for raising and lowering the drawing tool.
- **PID / proportional correction logic** to reduce drift during straight-line motion and turns.
- **ROS/Gazebo simulation scripts** for testing shape-to-path routines before physical deployment.
- **Computer vision measurement scripts** for analysing drawn shapes from camera input.
- **Physical and simulation result files** for evaluating open-loop vs closed-loop performance.

## Repository Structure

```text
Thesis_FYP/
├── Code/
│   ├── Arduino/
│   │   └── motor_test/
│   │       ├── shape_drawing_robot.ino
│   │       ├── motor_test.ino
│   │       ├── serial_test.ino
│   │       ├── servo_test_2.ino
│   │       ├── LM393_reader_test.ino
│   │       ├── LM393_velocity_change.ino
│   │       └── Encoder_Tick_Progression_test.ino
│   │
│   ├── BNO055 Sensor/
│   │   ├── sensor_test.py
│   │   ├── drift_logger.py
│   │   └── protractor_test.py
│   │
│   ├── Camera/
│   │   ├── shapecv_video.py
│   │   ├── master_measure_shapes.py
│   │   ├── measure_shape.py
│   │   ├── measure_shape_2.py
│   │   └── shapecv_video.py
│   │
│   ├── Paint Software Idea/
│   │   ├── paint.py
│   │   └── trainer.py
│   │
│   ├── Shape Test Code/
│   │   ├── draw_square.py
│   │   ├── draw_star.py
│   │   └── trajectory_drift.py
│   │
│   └── Simulation/
│       ├── launch/
│       ├── scripts/
│       └── urdf/
│
├── Photos of Tests/
│   ├── Simulation Photos/
│   └── Tests Photos/
│
├── Results/
│   └── Thesis Results/
│       ├── BNO055/
│       ├── LM393/
│       ├── Distance Test Results.xlsx
│       ├── Gesture Accuracy Results.xlsx
│       ├── Initial Drift Data Points.txt
│       ├── Light Intensity Test Results.xlsx
│       ├── Simulation Results Table.xlsx
│       └── traj_results.csv
│
└── README.md
```

## System Architecture

The final system is built around a two-level hardware and software architecture.

### 1. Input Layer

The Raspberry Pi Camera captures the user's hand gestures. The camera stream is processed using OpenCV and MediaPipe. The gesture system detects both hands, counts the visible fingers and maps the gesture to one of the supported drawing routines.

### 2. Processing Layer

The Raspberry Pi 5 runs the main Python control software. It handles:

- camera input
- hand landmark detection
- gesture classification
- BNO055 heading readings
- drawing routine selection
- serial communication with the Arduino
- real-time Flask video display

The selected shape is converted into a sequence of movement commands, such as forward movement, reverse correction, heading alignment and pen control.

### 3. Execution Layer

The Arduino Uno receives serial commands from the Raspberry Pi and controls:

- left and right DC motors
- motor speed via PWM
- motor direction pins
- encoder tick counting
- pen-lift servo movement

The robot continuously reports encoder data back to the Raspberry Pi while the Pi uses BNO055 heading data to correct the robot's trajectory.

## Hardware Used

The main hardware components used in the project are:

| Component | Purpose |
|---|---|
| Elegoo Smart Robot Car Kit V4 | Base differential-drive robot chassis |
| Arduino Uno R3 | Low-level motor, encoder and servo control |
| Raspberry Pi 5 | High-level computer vision and control processing |
| Raspberry Pi Camera Module 3 | Gesture recognition input |
| BNO055 9-DOF IMU | Absolute heading and orientation feedback |
| LM393 infrared encoders | Wheel odometry and distance estimation |
| MG90S / micro servo | Pen-lift actuation |
| 3D-printed pen-lift mechanism | Raises and lowers the drawing tool |
| Power bank | Dedicated Raspberry Pi power supply |
| Jumper wires and breadboard | Sensor and controller wiring |
| Floor canvas / paper workspace | Physical drawing surface |

## Software Stack

The project uses a mixed software stack across Python, Arduino and ROS/Gazebo:

| Area | Technologies |
|---|---|
| Main control software | Python |
| Computer vision | OpenCV, MediaPipe |
| Camera interface | Raspberry Pi Camera, `rpicam-vid` |
| Web display | Flask |
| Serial communication | PySerial |
| Orientation sensing | Adafruit BNO055 CircuitPython library |
| Low-level control | Arduino C/C++ |
| Simulation | ROS 2, Gazebo, URDF/Xacro |
| Data processing | CSV and Excel result files |

## Gesture Control Logic

The main gesture interface is implemented in `Code/Camera/shapecv_video.py`.

The gesture system uses a two-hand logic gate:

1. The user shows both hands to the camera.
2. The left hand acts as a control/lock gesture.
3. The right hand finger count selects the shape.
4. Once the left hand is lowered, the selected shape is locked and the drawing routine begins.

The implemented shape map is:

| Right-hand finger count | Shape |
|---:|---|
| 0 | Circle |
| 1 | Line |
| 2 | Rectangle |
| 3 | Triangle |
| 4 | Square |
| 5 | Five-pointed star |

For best performance, the user's palm should face the camera. The system is much less reliable when the back of the hand is shown because the thumb landmarks can be misclassified.

## Arduino Serial Protocol

The Arduino sketch `Code/Arduino/motor_test/shape_drawing_robot.ino` accepts simple serial commands from the Raspberry Pi.

| Command | Meaning |
|---|---|
| `P:1` | Lower pen |
| `P:0` | Raise pen |
| `M:leftSpeed,rightSpeed,leftDir,rightDir` | Directly set motor speeds and directions |
| `D:ticks` | Drive forward for a target encoder tick count |
| `B:ticks` | Drive backward for a target encoder tick count |
| `R:` | Reset encoder tick counters |
| `E:leftTicks,rightTicks` | Encoder feedback sent from Arduino to Raspberry Pi |
| `DONE` | Arduino reports completion of an auto-drive movement |

This simple protocol keeps high-level planning on the Raspberry Pi while leaving real-time motor control and encoder counting to the Arduino.

## Setup Notes

This repository is a final-year project repository rather than a fully packaged plug-and-play application. Some file paths, USB serial ports, motor constants and calibration values may need to be changed depending on the robot build, Raspberry Pi setup and operating system version.

### Raspberry Pi Python Environment

A typical Raspberry Pi setup requires Python 3 and the main dependencies below:

```bash
sudo apt update
sudo apt install python3-pip python3-opencv

python3 -m venv venv --system-site-packages
source venv/bin/activate

pip install numpy imutils flask pyserial mediapipe adafruit-circuitpython-bno055
```

Depending on the Raspberry Pi OS version, OpenCV and MediaPipe installation may vary. If `cv2` or `mediapipe` fails to import, install the package version compatible with the current Python and Raspberry Pi architecture.

### Arduino Setup

1. Open `Code/Arduino/motor_test/shape_drawing_robot.ino` in the Arduino IDE.
2. Select the correct board, usually **Arduino Uno**.
3. Select the correct serial port.
4. Upload the sketch to the Arduino.
5. Keep the Arduino connected to the Raspberry Pi by USB.

The Raspberry Pi script attempts to detect the Arduino using common serial paths:

```text
/dev/ttyUSB0
/dev/ttyUSB1
/dev/ttyACM0
/dev/ttyACM1
```

Update these paths in `shapecv_video.py` if your device appears under a different port.

### BNO055 Sensor Setup

The BNO055 is expected to be connected to the Raspberry Pi through I2C. Before running the main script, make sure I2C is enabled on the Raspberry Pi.

```bash
sudo raspi-config
```

Then enable I2C under the interface options. You can test whether the sensor is detected using:

```bash
i2cdetect -y 1
```

The BNO055 test scripts are located in:

```text
Code/BNO055 Sensor/
```

### Camera Setup

The main system uses the Raspberry Pi camera pipeline through `rpicam-vid`. Make sure the camera is enabled and working before running the gesture system.

A basic camera test can be performed using:

```bash
rpicam-hello
```

The main script uses a 640x480 MJPEG stream at 15 FPS.

## Running the Main Drawing System

After uploading the Arduino sketch and connecting the hardware, run the main gesture-controlled drawing system from the Raspberry Pi:

```bash
cd Code/Camera
python3 shapecv_video.py
```

The Flask interface starts on port `5000`. From a browser on the same network, open:

```text
http://<raspberry-pi-ip>:5000
```

The interface displays the live camera feed, detected hand landmarks, robot status, detected shape and active BNO055 heading values.

## Running the Shape Measurement Scripts

The repository includes camera-based measurement scripts for checking drawn shapes.

The master measurement script is:

```bash
cd Code/Camera
python3 master_measure_shapes.py
```

The measurement script supports mode switching using keys `0` to `5`:

| Key | Mode |
|---:|---|
| 0 | Circle diameter |
| 1 | Straight lines |
| 2 | Rectangle bounding box |
| 3 | Triangle line/angle logic |
| 4 | Square bounding box |
| 5 | Star line/angle logic |

Press `q` to quit.

## Simulation

Simulation files are stored under:

```text
Code/Simulation/
```

This folder contains:

- ROS/Gazebo launch files
- shape-specific drive scripts
- URDF/Xacro robot descriptions
- ink-spawner scripts used to visualise drawn paths

The simulation work was used to test the shape-to-path algorithms before running them on the physical robot. Depending on your ROS 2 setup, these files may need to be placed inside a valid ROS 2 workspace/package before they can be launched.

Example workflow:

```bash
mkdir -p ~/ros2_ws/src
# copy or symlink the Simulation folder into a ROS 2 package structure
cd ~/ros2_ws
colcon build
source install/setup.bash
```

Then launch the desired simulation file according to your local ROS 2 package name and workspace layout.

## Evaluation Summary

The project evaluated both the physical drawing accuracy and the reliability of the gesture-based interface.

### Open-Loop vs Closed-Loop Drawing

The closed-loop system substantially reduced trajectory drift compared to open-loop movement.

| Shape | Open-loop closure error | Closed-loop closure error | Drift reduction |
|---|---:|---:|---:|
| Line | 4.0 mm | 2.0 mm | 50.0% |
| Circle | 8.0 mm | 1.0 mm | 87.5% |
| Square | 180.0 mm | 37.4 mm | 79.2% |
| Rectangle | 174.0 mm | 58.1 mm | 66.6% |
| Triangle | 310.0 mm | 65.0 mm | 79.0% |
| Five-pointed star | 275.0 mm | 20.7 mm | 92.5% |
| Mean summary | 158.5 mm | 30.7 mm | 80.6% |

The results show that integrating absolute heading correction and encoder feedback reduced mean closure error from **158.5 mm** to **30.7 mm**, giving an overall drift reduction of **80.6%**.

### Computer Vision Performance

The MediaPipe hand gesture pipeline performed reliably inside its operational envelope:

| Condition | Accuracy | Effect |
|---|---:|---|
| Fully lit | 100% | Immediate and stable gesture detection |
| Background lit | 100% | Stable tracking despite backlighting |
| Dimly lit | 0% | Landmark detection failed |
| Distance from 30 cm to 300 cm | 100% | Reliable command recognition |
| Palm-facing hand orientation | 100% | Reliable shape selection |
| Back-of-hand orientation | 3.6% | Thumb landmark errors caused misclassification |

## Known Limitations

- The robot still depends heavily on mechanical calibration.
- The off-centre pen mount produces a visible “hash” artefact during some sharp polygon turns.
- Dim lighting prevents reliable hand landmark detection.
- Back-of-hand gestures are unreliable because thumb position is often misclassified.
- Wheel slip can still occur on low-friction surfaces.
- The robot is tuned for the specific chassis, motor behaviour, pen offset and test surface used in this project.
- Some simulation files may require local ROS 2 workspace restructuring before execution.

## Future Improvements

Possible future work includes:

- Repositioning the drawing tool so the pen tip coincides with the robot’s centre of rotation.
- Adding closed-loop visual feedback so the robot can see and correct the drawn path in real time.
- Exploring holonomic drive systems to reduce the need for stop-and-turn manoeuvres.
- Improving power regulation to reduce motor behaviour changes caused by voltage drops.
- Improving the gesture interface for low-light and non-palm-facing scenarios.
- Converting the codebase into a cleaner installable package with separate configuration files.

## Academic Context

This repository supports the dissertation:

**Shape-to-Path Conversion and Drawing with a Mobile Robot**  
Clyde Vella  
Bachelor of Science in Information Technology (Honours) (Artificial Intelligence)  
Faculty of ICT, University of Malta  
Supervisor: Dr Ingrid Galea  
May 2026
