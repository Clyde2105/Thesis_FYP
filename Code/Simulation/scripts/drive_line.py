#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Bool
import time
import threading

class LineDrawer(Node):
    def __init__(self):
        super().__init__('line_drawer')
        self.publisher_ = self.create_publisher(TwistStamped, '/diff_drive_controller/cmd_vel', 10)
        self.pen_pub = self.create_publisher(Bool, '/pen_down', 10)
        
        self.line_length = 0.5  # Meters
        self.linear_speed = 0.2 # Meters per second
        self.move_duration = self.line_length / self.linear_speed

        self.thread = threading.Thread(target=self.draw_line)
        self.thread.start()

    def cmd_vel(self, linear_x, angular_z):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "base_link"
        msg.twist.linear.x = float(linear_x)
        msg.twist.angular.z = float(angular_z)
        self.publisher_.publish(msg)

    def publish_continuously(self, linear_x, angular_z, duration_sec):
        start_time = self.get_clock().now()
        target_time = start_time + rclpy.duration.Duration(seconds=duration_sec)
        
        while self.get_clock().now() < target_time:
            self.cmd_vel(linear_x, angular_z)
            time.sleep(0.05)
            
        self.cmd_vel(0.0, 0.0)

    def sim_sleep(self, duration_sec):
        start_time = self.get_clock().now()
        target_time = start_time + rclpy.duration.Duration(seconds=duration_sec)
        while self.get_clock().now() < target_time:
            time.sleep(0.05)

    def set_pen(self, is_down):
        msg = Bool()
        msg.data = is_down
        self.pen_pub.publish(msg)

    def draw_line(self):
        while self.get_clock().now().nanoseconds == 0:
            time.sleep(0.1)

        self.get_logger().info('Waiting 10 SIMULATED seconds for Gazebo controllers to settle...')
        self.sim_sleep(10.0)
        
        self.get_logger().info('Starting to draw a straight line...')
        
        # 1. PEN DOWN
        self.get_logger().info('Lowering pen...')
        self.set_pen(True)
        self.sim_sleep(0.5) 

        # 2. MOVE FORWARD
        self.get_logger().info(f'Moving Forward for {self.line_length} meters...')
        self.publish_continuously(self.linear_speed, 0.0, self.move_duration)
        self.sim_sleep(0.5) 

        # 3. PEN UP
        self.get_logger().info('Lifting pen...')
        self.set_pen(False)
        self.sim_sleep(0.5)

        self.get_logger().info('Line complete!')

def main(args=None):
    rclpy.init(args=args)
    node = LineDrawer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()