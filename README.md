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

## Design Rationale and Supporting Evidence

This section explains the main design choices behind the final prototype and links them to the project evidence, source code and reference spreadsheets used during the write-up.

### Why the Raspberry Pi 5 was chosen

While the Raspberry Pi 3 and 4 are staple choices for robotics, they introduce significant processing bottlenecks for a real-time, multi-threaded computer vision pipeline. The Raspberry Pi 5 was selected to overcome these specific hardware constraints:

* **MediaPipe & OpenCV Computational Overhead:** Real-time hand landmark tracking is incredibly CPU-intensive. The Raspberry Pi 3 struggles to maintain even **5 FPS** with MediaPipe, causing severe lag in gesture command recognition. The Pi 4 can handle basic tracking but suffers from thermal throttling and noticeable frame drops when concurrently running a live web server. The Pi 5's Cortex-A76 architecture delivers a **2x to 3x CPU performance boost**, keeping the pipeline smoothly locked at a stable, responsive **15 FPS**.
* **Multi-Threaded Headroom (Flask + CV + Serial):** The robot's master script isn't just processing video; it simultaneously handles a Flask web server, parses real-time I2C data from the BNO055 IMU, and manages a constant PySerial bidirectional stream with the Arduino. The Pi 5's architecture handles context-switching between these high-priority threads without introducing latency spikes into the closed-loop control loop.
* **Camera Module 3 & RP1 I/O Throughput:** The Raspberry Pi 5 introduces the custom **RP1 southbridge chip**, which drastically improves I/O bandwidth. This ensures that capturing a raw stream from the Raspberry Pi Camera Module 3 via `rpicam-vid` does not choke the I2C bus or USB-serial lanes, maintaining sub-millisecond data delivery between the sensors and the Arduino.

#### Hardware Comparison Matrix for the Drawing Robot Pipeline

| Feature / Bottleneck | Raspberry Pi 3 | Raspberry Pi 4 | Raspberry Pi 5 | Project Impact |
| :--- | :--- | :--- | :--- | :--- |
| **MediaPipe Frame Rate** | < 5 FPS (Severe lag) | ~10–12 FPS (Borderline) | **15+ FPS (Flawless)** | Instant gesture locking before drawing begins. |
| **Thermal Performance** | Low heat, but lacks performance | High heat (Throttles under CV load) | **Managed via Active Cooler** | Prevents system crashes during extended physical testing runs. |
| **Concurrent Threads** | Stutters on Flask + CV | Minor latency spikes | **Zero noticeable overhead** | Ensures PID heading corrections are calculated without delay. |
| **Camera 3 Compatibility** | Limited legacy driver support | Software-defined support | **Native hardware acceleration** | Optimizes image capture for edge/contour detection. |

The Raspberry Pi 5 was selected as the high-level controller because the final system needed to run tasks that are too heavy for the Arduino Uno alone. These tasks included live camera capture, OpenCV processing, MediaPipe hand landmark detection, BNO055 orientation reading, shape-selection logic, serial communication with the Arduino and a Flask-based visual dashboard. The Arduino was still kept in the system, but only for low-level real-time motor, encoder and servo control.

This split was chosen over using only the Arduino because the Arduino is much better suited for deterministic hardware control than for computer vision, camera processing and high-level Python logic. It was also chosen over using a laptop or desktop because the Raspberry Pi 5 allowed the robot to remain self-contained, portable and directly compatible with the Raspberry Pi Camera Module 3, I2C sensors and USB serial communication. The dissertation evidence describes this as a master-slave architecture where the Raspberry Pi 5 acts as the master intelligence node while the Arduino handles the strict execution layer.

### Why these six shapes were chosen

The six supported shapes were not chosen randomly. They were selected to test different levels of kinematic difficulty, from simple movement to high-stress multi-turn drawing.

| Shape | Why it was included |
|---|---|
| Line | Baseline one-dimensional translation test. It checks whether the robot can drive straight without snaking or drifting. |
| Circle | Continuous-curvature test. It checks whether the robot can maintain smooth rotation without sharp stop-and-turn transitions. |
| Square | Orthogonal polygon test. It checks four equal-length sides and repeated 90 degree heading changes. |
| Rectangle | Unequal orthogonal polygon test. It checks whether the same 90 degree logic still works when long and short sides alternate. |
| Triangle | Non-orthogonal polygon test. It checks 120 degree turns and exposes errors that may not appear in square-only testing. |
| Five-pointed star | Stress-test shape. It combines repeated long segments, sharp angular transitions and cumulative closure requirements. |

The external references in `DrawingShapeBotsRefs.xlsx` also support the use of basic geometric shapes in educational drawing robots. For example, GeomBot uses polygons and circles for geometry learning, the Arduino geometrical-shapes robot uses circles, squares and triangles to test motor precision and control, and LEGO SPIKE / NXT plotting examples use geometric paths to teach movement, algebra and coordinate transformations. The additional `Updated References.xlsx` sheet also supports squares, rectangles, circles, arcs, triangles and polygons as useful baseline shapes for testing drawing robots and educational robotics systems.

### Computer vision libraries used

The computer vision and camera-related implementation mainly uses the following libraries and tools:

| Library / tool | Used for |
|---|---|
| OpenCV / `cv2` | Camera frame handling, image conversion, thresholding, contour detection, Canny edges, Hough line detection, drawing overlays and measurement visualisation. |
| MediaPipe | Real-time hand landmark detection and finger-count gesture recognition. |
| NumPy | Vector maths, angle calculations, arrays and image-mask operations. |
| imutils | Convenience contour handling and image-processing helpers in the measurement scripts. |
| Raspberry Pi `rpicam-vid` | Camera stream capture from the Raspberry Pi Camera Module 3. |
| Flask | Web dashboard used to display the live camera feed, state, detected shape and sensor heading. |
| PySerial | Communication bridge between the Raspberry Pi vision/control software and the Arduino motor controller. |
| Adafruit BNO055 CircuitPython library | Reading drift-corrected orientation values from the BNO055 sensor. |

In the codebase, the main gesture-recognition pipeline is implemented in `Code/Camera/shapecv_video.py`, while the shape-measurement and verification logic is mainly implemented in `Code/Camera/master_measure_shapes.py`. The `PaintCodeRefs.xlsx` spreadsheet contains supporting references for earlier GUI, canvas, IoU, JSON and object-detection ideas that informed earlier prototype work before the final hand-gesture pipeline was implemented.

### Paint Software Idea folder note

The `Code/Paint Software Idea/` folder contains basic prototype code that was explored before the final computer-vision hand gesture system was implemented. These files were originally intended to support a simple paint-style input workflow, using a basic GUI/canvas approach. However, this approach was fairly limited, highly inaccurate for the final robot use case and too basic compared to the more direct camera-based gesture selection system.

For that reason, the paint-code approach was replaced by the final OpenCV and MediaPipe hand gesture recognition pipeline. The folder is kept in the repository as development evidence, showing an earlier direction that was tested before the system moved toward real-time computer vision input. The references in `PaintCodeRefs.xlsx` support this early stage, including Tkinter paint-app tutorials, button handling, freehand canvas drawing, shape creation on a canvas, IoU/object-detection references and JSON-handling references.

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

## References and Useful Links

The following links were used as supporting references during the project and README documentation. They are grouped by relevance so the repository can show the evidence behind the design decisions without making the main explanation messy.

### Drawing robot and shape-selection references

| # | Reference | Link | Relevance |
|---:|---|---|---|
| 1 | GeomBot: educational drawing robot for geometry lessons using polygons on paper | https://www.mdpi.com/2227-7102/10/12/387/pdf | Supports the use of polygons and circles as educational geometry shapes. |
| 2 | Geometrical Shapes Drawing Robot: Arduino-based plotter for basic forms | https://iarjset.com/wp-content/uploads/2024/07/IARJSET.2024.11790.pdf | Uses circles, squares and triangles to test drawing precision and control. |
| 3 | LEGO NXT 2D Shape Plotter | https://brianpinto91.github.io/leJOS-NXT-2D-plotter/ | Related educational plotting system involving odometry and coordinate transformations. |
| 4 | Mechatronics Workshop Arduino Pen Plotter | https://www.scribd.com/presentation/640899630/Untitled | Arduino and motor-based drawing platform reference. |
| 5 | Drawing Robotic Arm Thesis | https://www.diva-portal.org/smash/get/diva2:1200466/FULLTEXT01.pdf | Fixed drawing robot reference for line and contour drawing techniques. |
| 6 | LEGO SPIKE Prime Geometric Drawing Robot | https://learningcorner.co/lesson/24373 | Educational robot reference using squares and more complex geometric drawings. |
| 7 | Arduino Drawing Robot / OSTurtle | https://www.instructables.com/Arduino-Drawing-Robot/ | Basic mobile robot drawing reference using DC motors and pen up/down control. |
| 8 | Bachelor Thesis Robotic Arm drawing digits | https://ph504.github.io/projects/projects-2/ | Simulation and robotic drawing reference. |
| 9 | Stroke-based Robotic Artistic Drawing | https://arxiv.org/pdf/2210.07590.pdf | Related robotic drawing work using image-derived strokes and visual planning. |

### Paint software prototype and computer vision references

| # | Reference | Link | Relevance |
|---:|---|---|---|
| 1 | Python/Tkinter paint app tutorial | https://medium.com/@tsbeverything/how-to-make-a-paint-app-using-python-and-tkinter-f0d4fda8b7de | Early paint UI prototype reference. |
| 2 | Tkinter button click tutorial | https://pythonguides.com/python-tkinter-button/ | Button handling reference for the early UI prototype. |
| 3 | Pop-up window UI tutorial | https://youtu.be/Au6FPjkgbUE?si=NsqF3VDGGKQyoH9F | Early GUI pop-up/window reference. |
| 4 | Freehand drawing with Python Tkinter | https://www.w3resource.com/python-exercises/tkinter/python-tkinter-events-and-event-handling-exercise-9.php | Early freehand drawing logic reference. |
| 5 | Canvas graphics coordinate system and mouse events | https://lambertk.academic.wlu.edu/breezypythongui/tutorial-for-breezypythongui/simple-graphics/ | Canvas coordinate and mouse event reference. |
| 6 | Intersection over Union object/shape detection | https://pyimagesearch.com/2016/11/07/intersection-over-union-iou-for-object-detection/ | Computer vision measurement and object-overlap reference. |
| 7 | Ultralytics IoU glossary | https://www.ultralytics.com/glossary/intersection-over-union-iou | Additional IoU explanation. |
| 8 | Working with JSON data in Python | https://realpython.com/python-json/ | JSON handling reference. |
| 9 | Convert JSON to dictionary in Python | https://www.geeksforgeeks.org/python/convert-json-to-dictionary-in-python/ | JSON-to-dictionary handling reference. |
| 10 | Drawing and spawning shapes on Tkinter | https://www.geeksforgeeks.org/python/python-tkinter-create-different-shapes-using-canvas-class/ | Early canvas shape-spawning reference. |
| 11 | Tkinter Canvas tutorial for shapes and text | https://www.pythontutorial.net/tkinter/tkinter-canvas/ | Early canvas drawing reference. |

### Additional hardware, sensor and simulation references

| # | Reference | Link | Relevance |
|---:|---|---|---|
| 1 | Arduino UNO XY plotter for large vector drawings | https://ijarsct.co.in/Paper194.pdf | Related Arduino-controlled plotter using stepper motors and servo pen-lift logic. |
| 2 | CNC plotter review with stepper motors, servo pen-lift and G-code conversion | https://www.irjet.net/archives/V7/i10/IRJET-V7I1057.pdf | Background reference for affordable CNC-style plotter mechanisms. |
| 3 | Mini CNC plotter using Arduino, CNC shield, steppers and servo pen-lift | https://www.iosrjournals.org/iosr-jmce/papers/NCRIME-2018/Volume-6/9.%2044-46.pdf | Low-cost plotter reference for simple and transportable drawing systems. |
| 4 | Arduino image-to-coordinate drawing system | https://futajeet.ng/manager/papers/paper_18_1721307460.pdf | Reference for converting image/vector information into motor coordinates. |
| 5 | Generative AI and robotic-arm drawing using BrachioGraph | https://dergipark.org.tr/en/download/article-file/4985569 | Related Raspberry Pi / servo-based drawing robot reference. |
| 6 | Multi-purpose CNC ink plotter using Arduino | https://www.ijraset.com/research-paper/multi-purpose-cnc-ink-plotter-using-arduino | Reference for Arduino, stepper motor and SG90 pen-lift drawing platforms. |
| 7 | Low-cost robotic handwriting system with AI-generated trajectory data | https://arxiv.org/html/2501.06783v1 | Related low-cost trajectory-based drawing system using embedded control. |
| 8 | SCARA drawing robot with servo-controlled joints | https://www.jetir.org/papers/JETIRFX06137.pdf | Reference for an alternative arm-based drawing mechanism. |
| 9 | CNC Pen Lift build guide | https://www.instructables.com/CNC-Pen-Lift-1/ | Practical reference for the 3D-printed servo-actuated pen-lift mechanism. |
| 10 | Picasso the Drawing Robot: An Application of Inverse Kinematics | Menon, Vishal, Ashwin V. and Gayathri G. (2021). DOI: 10.1109/ICCISc52257.2021.9484972 | Drawing robot reference using squares and rectangles as baseline geometric tests. |
| 11 | Robotics and storytelling for computational thinking in primary education | https://www.mdpi.com/2227-7102/12/1/10 | Educational robotics reference involving continuous paths such as circles and arcs. |
| 12 | Educational robotics and mathematical geometry review | https://www.mdpi.com/2071-1050/10/4/905 | Supports the use of triangles and polygons for algorithmic geometry and repeated movement logic. |
| 13 | University-level robotics for teaching advanced mathematics | https://www.mdpi.com/2071-1050/16/22/9684 | Related SPIKE Prime reference for mapping robotic movement to mathematical curves and geometric outputs. |
| 14 | Differential-drive drawing robot simulation in ROS2 / Gazebo | https://helda.helsinki.fi/server/api/core/bitstreams/9beb8bc7-a1cd-4c7a-9d66-8070a62fd743/content | Reference for simulating differential-drive drawing behaviour, virtual IMU/encoder feedback and trajectory testing before physical deployment. |
