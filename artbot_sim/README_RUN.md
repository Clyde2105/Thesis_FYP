# artbot_sim – run checklist (ROS 2 Jazzy + Gazebo Sim)

## 0) If stuff is "ghosting" (robot not spawning / controllers acting weird)
Kill leftover processes first (VirtualBox + Gazebo loves to leave zombies):
```bash
pkill -f "gz sim" || true
pkill -f ros_gz || true
pkill -f controller_manager || true
```

## 1) Build + source
```bash
cd ~/ros2_ws
colcon build --packages-select artbot_sim --symlink-install
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

## 2) Start the sim
```bash
ros2 launch artbot_sim sim.launch.py
```

Wait a few seconds, then confirm controllers are **active**:
```bash
ros2 control list_controllers
```
Expected:
- `joint_state_broadcaster ... active`
- `diff_drive_controller ... active`

## 3) Make it move (square path)
```bash
ros2 run artbot_sim drive_square_dd.py
```

## 4) Make it draw while it moves (ink trail)
Open a **second** terminal (leave sim running) and run:
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run artbot_sim ink_spawner.py
```

Now run the drive script again — you should see a dotted trail on the paper.

## 5) Collision visualisation (to debug wheels/paper)
In Gazebo Sim:
- click the **☰ (hamburger)** menu (top-left)
- go to **View → Collisions** (toggle ON)

If you don’t see it, also try **View → Transparent** so you can see collision shapes inside visuals.

## 6) Quick sanity checks
While driving (new terminal):
```bash
ros2 topic echo /diff_drive_controller/odom --once
ros2 topic echo /diff_drive_controller/cmd_vel --once
```

And on the Gazebo side:
```bash
gz model --list
```
You should see `artbot` in the list.
