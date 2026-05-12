#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool


def get_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class DriveCircle(Node):
    def __init__(self):
        super().__init__("drive_circle")

        self.pub_twist = self.create_publisher(TwistStamped, "/diff_drive_controller/cmd_vel", 10)
        self.pub_pen = self.create_publisher(Bool, "/pen_down", 10)
        self.sub = self.create_subscription(Odometry, "/diff_drive_controller/odom", self.on_odom, 10)

        self.target_yaw = 2.0 * math.pi
        self.total_yaw = 0.0
        self.last_yaw = None
        self.done = False
        self.linear_speed = 0.12
        self.angular_speed = 0.24

    def cmd(self, linear, angular):
        t = TwistStamped()
        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "base_link"
        t.twist.linear.x = float(linear)
        t.twist.angular.z = float(angular)
        self.pub_twist.publish(t)

    def on_odom(self, msg):
        if self.done:
            return

        current_yaw = get_yaw(msg.pose.pose.orientation)

        if self.last_yaw is None:
            self.last_yaw = current_yaw
            return

        delta = current_yaw - self.last_yaw
        while delta < -math.pi:
            delta += 2.0 * math.pi
        while delta > math.pi:
            delta -= 2.0 * math.pi

        self.total_yaw += abs(delta)
        self.last_yaw = current_yaw

        remaining = self.target_yaw - self.total_yaw

        if remaining <= 0.05:
            self.cmd(0.0, 0.0)
            self.pub_pen.publish(Bool(data=False))
            self.done = True
            self.get_logger().info("Circle complete.")
        else:
            self.pub_pen.publish(Bool(data=True))
            self.cmd(self.linear_speed, self.angular_speed)


def main(args=None):
    rclpy.init(args=args)
    node = DriveCircle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd(0.0, 0.0)
        node.pub_pen.publish(Bool(data=False))
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()