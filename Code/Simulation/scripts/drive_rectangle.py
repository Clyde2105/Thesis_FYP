#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Bool
import time
import math
import threading

class RectangleDrawer(Node):
    def __init__(self):
        super().__init__('rectangle_drawer')
        self.publisher_ = self.create_publisher(TwistStamped, '/diff_drive_controller/cmd_vel', 10)
        self.pen_pub = self.create_publisher(Bool, '/pen_down', 10)
        
        self.linear_speed = 0.2 
        self.angular_speed = 0.4 
        self.pen_offset = 0.20 
        
        self.offset_duration = self.pen_offset / self.linear_speed
        self.turn_duration = (math.pi / 2) / self.angular_speed # 90 degrees

        self.thread = threading.Thread(target=self.draw_rectangle)
        self.thread.start()

    def move(self, linear_x, angular_z, duration_sec):
        msg = TwistStamped()
        msg.header.frame_id = "base_link"
        msg.twist.linear.x, msg.twist.angular.z = float(linear_x), float(angular_z)
        
        target = self.get_clock().now() + rclpy.duration.Duration(seconds=duration_sec)
        while self.get_clock().now() < target:
            msg.header.stamp = self.get_clock().now().to_msg()
            self.publisher_.publish(msg)
            time.sleep(0.05)
        self.publisher_.publish(TwistStamped()) # Stop

    def sim_sleep(self, duration_sec):
        target = self.get_clock().now() + rclpy.duration.Duration(seconds=duration_sec)
        while self.get_clock().now() < target: time.sleep(0.05)

    def draw_rectangle(self):
        while self.get_clock().now().nanoseconds == 0: time.sleep(0.1)
        self.sim_sleep(10.0)
        
        sides = [1.0, 0.5, 1.0, 0.5] # Length, Width, Length, Width
        
        for distance in sides:
            move_duration = distance / self.linear_speed
            
            # Draw line
            self.pen_pub.publish(Bool(data=True)); self.sim_sleep(0.5)
            self.move(self.linear_speed, 0.0, move_duration); self.sim_sleep(0.5)
            self.pen_pub.publish(Bool(data=False)); self.sim_sleep(0.5)
            
            # Compensate for 90-degree corner
            self.move(self.linear_speed, 0.0, self.offset_duration); self.sim_sleep(0.5)
            self.move(0.0, self.angular_speed, self.turn_duration); self.sim_sleep(0.5)
            self.move(-self.linear_speed, 0.0, self.offset_duration); self.sim_sleep(0.5)

        self.get_logger().info('Rectangle complete!')

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(RectangleDrawer())
    rclpy.shutdown()

if __name__ == '__main__':
    main()