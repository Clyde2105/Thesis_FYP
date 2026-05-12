#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Bool
import time
import math
import threading

class StarDrawer(Node):
    def __init__(self):
        super().__init__('star_drawer')
        self.publisher_ = self.create_publisher(TwistStamped, '/diff_drive_controller/cmd_vel', 10)
        self.pen_pub = self.create_publisher(Bool, '/pen_down', 10)
        
        self.side_length = 1.0 
        self.linear_speed = 0.2 
        self.angular_speed = 0.4 
        self.pen_offset = 0.20 
        
        self.move_duration = self.side_length / self.linear_speed
        self.offset_duration = self.pen_offset / self.linear_speed
        
        # A 5-pointed star requires turning 144 degrees (4*pi/5 radians)
        self.turn_angle = (4 * math.pi) / 5
        self.turn_duration = self.turn_angle / self.angular_speed

        self.thread = threading.Thread(target=self.draw_star)
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

    def draw_star(self):
        while self.get_clock().now().nanoseconds == 0: time.sleep(0.1)
        self.sim_sleep(10.0)
        
        for _ in range(5): # 5 points!
            # Draw line
            self.pen_pub.publish(Bool(data=True)); self.sim_sleep(0.5)
            self.move(self.linear_speed, 0.0, self.move_duration); self.sim_sleep(0.5)
            self.pen_pub.publish(Bool(data=False)); self.sim_sleep(0.5)
            
            # Compensate for 144-degree corner
            self.move(self.linear_speed, 0.0, self.offset_duration); self.sim_sleep(0.5)
            self.move(0.0, self.angular_speed, self.turn_duration); self.sim_sleep(0.5)
            self.move(-self.linear_speed, 0.0, self.offset_duration); self.sim_sleep(0.5)

        self.get_logger().info('Star complete! You did it!')

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(StarDrawer())
    rclpy.shutdown()

if __name__ == '__main__':
    main()