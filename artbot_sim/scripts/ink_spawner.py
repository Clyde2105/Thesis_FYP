#!/usr/bin/env python3
import math
import subprocess
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool

class InkSpawner(Node):
    def __init__(self):
        super().__init__("ink_spawner")
        self.counter = 0
        self.last_pos = None
        self.pen_down = False
        
        self.create_subscription(Odometry, "/model/artbot/odometry", self.odom_cb, 10)
        self.create_subscription(Bool, "/pen_down", self.pen_cb, 10)

    def pen_cb(self, msg):
        self.pen_down = msg.data
        if not self.pen_down:
            self.last_pos = None

    def odom_cb(self, msg):
        if not self.pen_down:
            return

        # 1. Get the robot's center position
        center_x = msg.pose.pose.position.x
        center_y = msg.pose.pose.position.y

        # 2. Calculate the robot's rotation (yaw) from the quaternion
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        # 3. Push the ink location 0.2m forward to match the pen_link!
        x = center_x + (0.2 * math.cos(yaw))
        y = center_y + (0.2 * math.sin(yaw))

        # SPAWN DISTANCE: 0.10m (10cm) to prevent crashing the VM
        if self.last_pos is None or math.dist((x,y), self.last_pos) > 0.10:
            self.spawn(x, y)
            self.last_pos = (x, y)

    def spawn(self, x, y):
        name = f"ink_{self.counter}"
        self.counter += 1
        
        # Simple Red Cylinder SDF
        sdf_string = (
            "<?xml version='1.0'?>"
            "<sdf version='1.6'>"
            f"<model name='{name}'>"
            "<static>true</static>"
            "<link name='link'>"
            "<visual name='visual'>"
            "<geometry><cylinder><radius>0.02</radius><length>0.01</length></cylinder></geometry>"
            "<material><ambient>1 0 0 1</ambient><diffuse>1 0 0 1</diffuse></material>"
            "</visual>"
            "</link>"
            "</model>"
            "</sdf>"
        )
        
        # Use the standard ROS 2 tool to create entities
        # This wrapper handles the Gazebo/Ignition versioning for us
        cmd = [
            "ros2", "run", "ros_gz_sim", "create",
            "-world", "art_world",
            "-name", name,
            "-x", str(x),
            "-y", str(y),
            "-z", "0.05",   # 5cm up so it doesn't clip
            "-string", sdf_string
        ]

        # Fire and forget
        subprocess.Popen(cmd)

def main():
    rclpy.init()
    rclpy.spin(InkSpawner())
    rclpy.shutdown()

if __name__ == "__main__":
    main()