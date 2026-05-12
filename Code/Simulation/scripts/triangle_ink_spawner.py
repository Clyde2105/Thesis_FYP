#!/usr/bin/env python3
import math
import subprocess
from collections import deque

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool


def get_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class InkSpawner(Node):
    def __init__(self):
        super().__init__("ink_spawner")

        self.counter = 0
        self.last_pos = None
        self.pen_down = False

        self.pen_offset = 0.20
        self.spawn_spacing = 0.05
        self.max_queue_len = 400
        self.max_active_spawns = 4

        self.spawn_queue = deque()
        self.active_processes = []

        self.create_subscription(Odometry, "/model/artbot/odometry", self.odom_cb, 10)
        self.create_subscription(Bool, "/pen_down", self.pen_cb, 10)

        # Faster queue processing
        self.create_timer(0.01, self.process_queue)

    def pen_cb(self, msg):
        self.pen_down = msg.data
        if not self.pen_down:
            self.last_pos = None

    def odom_cb(self, msg):
        if not self.pen_down:
            return

        yaw = get_yaw(msg.pose.pose.orientation)

        pen_x = msg.pose.pose.position.x + self.pen_offset * math.cos(yaw)
        pen_y = msg.pose.pose.position.y + self.pen_offset * math.sin(yaw)

        if self.last_pos is None:
            self.queue_spawn(pen_x, pen_y)
            self.last_pos = (pen_x, pen_y)
            return

        dist = math.dist((pen_x, pen_y), self.last_pos)

        if dist >= self.spawn_spacing:
            self.queue_spawn(pen_x, pen_y)
            self.last_pos = (pen_x, pen_y)

    def queue_spawn(self, x, y):
        if len(self.spawn_queue) < self.max_queue_len:
            self.spawn_queue.append((x, y))

    def process_queue(self):
        # Remove finished spawn processes
        self.active_processes = [p for p in self.active_processes if p.poll() is None]

        # Launch multiple spawns in parallel
        while self.spawn_queue and len(self.active_processes) < self.max_active_spawns:
            x, y = self.spawn_queue.popleft()
            name = f"ink_{self.counter}"
            self.counter += 1

            sdf_string = (
                "<?xml version='1.0'?>"
                "<sdf version='1.6'>"
                f"<model name='{name}'>"
                "<static>true</static>"
                "<link name='link'>"
                "<visual name='visual'>"
                "<geometry><cylinder><radius>0.01</radius><length>0.001</length></cylinder></geometry>"
                "<material><ambient>1 0 0 1</ambient><diffuse>1 0 0 1</diffuse></material>"
                "</visual>"
                "</link>"
                "</model>"
                "</sdf>"
            )

            cmd = [
                "ros2", "run", "ros_gz_sim", "create",
                "-world", "art_world",
                "-string", sdf_string,
                "-x", str(x),
                "-y", str(y),
                "-z", "0.001",
            ]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.active_processes.append(proc)


def main(args=None):
    rclpy.init(args=args)
    node = InkSpawner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()