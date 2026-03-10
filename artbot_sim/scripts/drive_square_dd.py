#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool

def get_yaw(q):
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

class DriveSquare(Node):
    def __init__(self):
        super().__init__("drive_square_dd")
        
        self.pub_twist = self.create_publisher(Twist, "/diff_drive_controller/cmd_vel_unstamped", 10)
        self.pub_stamped = self.create_publisher(TwistStamped, "/diff_drive_controller/cmd_vel", 10)
        self.pub_pen = self.create_publisher(Bool, "/pen_down", 10)
        self.sub = self.create_subscription(Odometry, "/model/artbot/odometry", self.on_odom, 10)

        # 4 Corners: (1,0) -> (1,1) -> (0,1) -> (0,0)
        self.goals = [(1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
        self.goal_idx = 0
        self.state = "TURN"
        self.timer_wait = 0
        self.prev_dist = 999.9
        
        # --- ULTRA PRECISION SETTINGS ---
        self.YAW_TOLERANCE = 0.01   # 0.5 degrees (Tight, but allows settling)
        self.DIST_TOLERANCE = 0.008 # 0.8 cm (Must hit the absolute bullseye)
        self.MAX_SPEED = 0.25       # Moderate cruise speed
        self.MIN_SPEED = 0.02       # Ant speed for final 5cm
        self.TURN_SPEED_LIMIT = 0.2 # Slow turn to prevent skidding/swinging

    def cmd(self, v, w):
        t = Twist()
        t.linear.x = float(v)
        t.angular.z = float(w)
        self.pub_twist.publish(t)
        
        ts = TwistStamped()
        ts.header.stamp = self.get_clock().now().to_msg()
        ts.twist = t
        self.pub_stamped.publish(ts)

    def on_odom(self, msg):
        # 1. Global Stop Check
        if self.goal_idx >= 4:
            self.cmd(0.0, 0.0)
            self.pub_pen.publish(Bool(data=False))
            return

        # 2. Wait Timer (Pause for physics to settle)
        if self.timer_wait > 0:
            self.timer_wait -= 1
            self.cmd(0.0, 0.0)
            return

        # 3. Calculate Position & Error
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        yaw = get_yaw(msg.pose.pose.orientation)

        gx, gy = self.goals[self.goal_idx]
        dx = gx - x
        dy = gy - y
        dist = math.sqrt(dx*dx + dy*dy)
        wanted_yaw = math.atan2(dy, dx)
        err_yaw = wanted_yaw - yaw

        while err_yaw > math.pi: err_yaw -= 2.0 * math.pi
        while err_yaw < -math.pi: err_yaw += 2.0 * math.pi

        # 4. State Machine
        if self.state == "TURN":
            self.pub_pen.publish(Bool(data=False)) # Pen UP
            self.prev_dist = 999.9

            if abs(err_yaw) < self.YAW_TOLERANCE:
                self.get_logger().info(f"Aligned. Dist to Go: {dist:.4f}m")
                self.state = "DRIVE"
                self.timer_wait = 30 # Wait 1s before driving
            else:
                # Gentle Turn P-Controller
                w = 0.8 * err_yaw
                w = max(min(w, self.TURN_SPEED_LIMIT), -self.TURN_SPEED_LIMIT)
                
                # Min rotation speed to overcome friction
                if abs(w) < 0.05: w = 0.05 if w > 0 else -0.05
                self.cmd(0.0, w)

        elif self.state == "DRIVE":
            self.pub_pen.publish(Bool(data=True)) # Pen DOWN

            # HIT CHECK: 0.8cm tolerance OR overshot while very close
            if dist < self.DIST_TOLERANCE or (dist > self.prev_dist and dist < 0.03):
                self.get_logger().info(f"Corner {self.goal_idx} Hit! (Err: {dist:.4f}m)")
                self.goal_idx += 1
                self.state = "TURN"
                self.timer_wait = 30 # Stop and settle
            
            elif abs(err_yaw) > 0.1: # If we drift > 5 degrees
                self.get_logger().info("Drift detected! Re-aligning...")
                self.state = "TURN"
            
            else:
                # Speed Control
                if dist > 0.15:
                    speed = self.MAX_SPEED
                else:
                    # Linear ramp down, but clamp to MIN_SPEED so we don't stall
                    speed = max(self.MIN_SPEED, dist * 0.8)

                # Heading Correction (P-Control)
                correction = err_yaw * 1.5
                self.cmd(speed, correction)
                self.prev_dist = dist

def main():
    rclpy.init()
    node = DriveSquare()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()