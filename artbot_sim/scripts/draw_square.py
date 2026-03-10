#!/usr/bin/env python3
"""Drive a square and drop "ink" dots in Gazebo Sim.

- Drives using the diff_drive_controller's TwistStamped topic.
- Drops tiny red static cylinders by calling Gazebo's /world/<world>/create service.

This is intentionally "dumb but reliable" for a VM setup.
"""

import argparse
import math
import os
import subprocess
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from ament_index_python.packages import get_package_share_directory


def yaw_from_quat(q):
    # ROS quaternion -> yaw
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class DrawSquare(Node):
    def __init__(self, args):
        super().__init__("draw_square")

        self.world = args.world
        self.enable_ink = not args.no_ink
        self.ink_every_s = args.ink_dt

        self.pub = self.create_publisher(TwistStamped, "/diff_drive_controller/cmd_vel", 10)
        self.odom_sub = self.create_subscription(Odometry, "/diff_drive_controller/odom", self.on_odom, 10)

        self.x = 0.0
        self.y = 0.0
        self.yaw = 0.0
        self.have_odom = False

        # Motion params (bigger so you can SEE it)
        self.speed = args.speed          # m/s
        self.side_len = args.side        # meters
        self.turn_speed = args.turn      # rad/s

        self.side_time = self.side_len / max(self.speed, 1e-6)
        self.turn_time = (math.pi / 2.0) / max(self.turn_speed, 1e-6)

        # Ink model path (installed into share/artbot_sim/models)
        pkg_share = get_package_share_directory("artbot_sim")
        self.ink_sdf = os.path.join(pkg_share, "models", "ink_spot.sdf")

        self.ink_id = 0

        # Wait a bit for topics + sim time
        t0 = time.time()
        while rclpy.ok() and time.time() - t0 < 3.0:
            rclpy.spin_once(self, timeout_sec=0.1)
            if self.have_odom:
                break

        if not self.have_odom:
            self.get_logger().warn("No /diff_drive_controller/odom yet (still driving anyway)")

        # Sanity: ensure gz exists if ink enabled
        if self.enable_ink:
            if not os.path.exists(self.ink_sdf):
                self.get_logger().error(f"Ink SDF not found: {self.ink_sdf}")
                self.enable_ink = False
            elif subprocess.call(["bash", "-lc", "command -v gz >/dev/null 2>&1"]) != 0:
                self.get_logger().error("'gz' command not found. Disabling ink.")
                self.enable_ink = False

        self.run()

    def on_odom(self, msg: Odometry):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)
        self.have_odom = True

    def publish_cmd(self, vx: float, wz: float):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.twist.linear.x = float(vx)
        msg.twist.angular.z = float(wz)
        self.pub.publish(msg)

    def spawn_ink(self):
        # Drop dot at current (odom) pose
        name = f"ink_{self.ink_id:04d}"
        self.ink_id += 1

        # Slightly above the paper visual (paper is at z=0.001 with 0.001 thickness)
        z = 0.002

        req = (
            f'sdf_filename: "{self.ink_sdf}" '
            f'name: "{name}" '
            f'pose: {{ position: {{ x: {self.x:.4f}, y: {self.y:.4f}, z: {z:.4f} }} }}'
        )

        cmd = [
            "gz", "service",
            "-s", f"/world/{self.world}/create",
            "--reqtype", "gz.msgs.EntityFactory",
            "--reptype", "gz.msgs.Boolean",
            "--timeout", "1000",
            "--req", req,
        ]

        # Don't spam the terminal; ignore failures (but log first few)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0 and self.ink_id < 5:
                self.get_logger().warn(f"Ink spawn failed: {res.stderr.strip()}")
        except Exception as e:
            if self.ink_id < 5:
                self.get_logger().warn(f"Ink spawn exception: {e}")

    def run_for(self, vx: float, wz: float, duration: float, drop_ink: bool):
        end = time.time() + duration
        next_ink = 0.0

        while rclpy.ok() and time.time() < end:
            self.publish_cmd(vx, wz)
            rclpy.spin_once(self, timeout_sec=0.0)

            if self.enable_ink and drop_ink:
                now = time.time()
                if now >= next_ink:
                    self.spawn_ink()
                    next_ink = now + self.ink_every_s

            time.sleep(0.05)

    def run(self):
        self.get_logger().info(
            f"Drawing square: side={self.side_len}m speed={self.speed}m/s turn={self.turn_speed}rad/s ink={'on' if self.enable_ink else 'off'}"
        )

        for _ in range(4):
            self.run_for(self.speed, 0.0, self.side_time, drop_ink=True)
            self.run_for(0.0, self.turn_speed, self.turn_time, drop_ink=False)

        self.run_for(0.0, 0.0, 0.2, drop_ink=False)
        self.get_logger().info("Done.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--world", default="art_world", help="Gazebo world name")
    parser.add_argument("--side", type=float, default=0.8, help="Square side length (m)")
    parser.add_argument("--speed", type=float, default=0.2, help="Forward speed (m/s)")
    parser.add_argument("--turn", type=float, default=1.0, help="Turn speed (rad/s)")
    parser.add_argument("--ink-dt", type=float, default=0.12, help="Seconds between ink dots")
    parser.add_argument("--no-ink", action="store_true", help="Drive only, no ink")
    args, _ = parser.parse_known_args()

    rclpy.init()
    node = DrawSquare(args)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
