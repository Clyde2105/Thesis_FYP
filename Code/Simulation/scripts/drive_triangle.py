#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import Bool
import time
import math
import threading

class TriangleDrawer(Node):
    def __init__(self):
        super().__init__('triangle_drawer')
        self.publisher_ = self.create_publisher(TwistStamped, '/diff_drive_controller/cmd_vel', 10)
        self.pen_pub = self.create_publisher(Bool, '/pen_down', 10)
        
        self.side_length = 1.0  
        self.linear_speed = 0.2 
        self.angular_speed = 0.4 
        
        # Pen offset from center of rotation based on your spawner script
        self.pen_offset = 0.20 
        
        self.move_duration = self.side_length / self.linear_speed
        self.offset_duration = self.pen_offset / self.linear_speed
        
        # 120-degree turn
        self.turn_angle = (2 * math.pi) / 3 
        self.turn_duration = self.turn_angle / self.angular_speed

        self.thread = threading.Thread(target=self.draw_triangle)
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

    def draw_triangle(self):
        while self.get_clock().now().nanoseconds == 0:
            time.sleep(0.1)

        self.get_logger().info('Waiting 10 SIMULATED seconds for Gazebo controllers to settle...')
        self.sim_sleep(10.0)
        
        self.get_logger().info('Starting to draw equilateral triangle...')
        
        for i in range(3):
            # 1. PEN DOWN
            self.get_logger().info(f'Drawing leg {i+1}: Lowering pen...')
            self.set_pen(True)
            self.sim_sleep(0.5) 

            # 2. MOVE FORWARD (Draw the line)
            self.get_logger().info(f'Drawing leg {i+1}: Moving Forward...')
            self.publish_continuously(self.linear_speed, 0.0, self.move_duration)
            self.sim_sleep(0.5) 

            # 3. PEN UP
            self.get_logger().info(f'Drawing leg {i+1}: Lifting pen...')
            self.set_pen(False)
            self.sim_sleep(0.5)

            # 4. COMPENSATE: Move forward so center of rotation is on the corner
            self.get_logger().info(f'Drawing leg {i+1}: Aligning center to corner...')
            self.publish_continuously(self.linear_speed, 0.0, self.offset_duration)
            self.sim_sleep(0.5)

            # 5. TURN
            self.get_logger().info(f'Drawing leg {i+1}: Turning 120 degrees...')
            self.publish_continuously(0.0, self.angular_speed, self.turn_duration)
            self.sim_sleep(0.5) 

            # 6. COMPENSATE: Reverse so pen is exactly on the corner again
            self.get_logger().info(f'Drawing leg {i+1}: Reversing pen back to corner...')
            self.publish_continuously(-self.linear_speed, 0.0, self.offset_duration)
            self.sim_sleep(0.5)

        self.get_logger().info('Triangle complete!')

def main(args=None):
    rclpy.init(args=args)
    node = TriangleDrawer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

if __name__ == '__main__':
    main()