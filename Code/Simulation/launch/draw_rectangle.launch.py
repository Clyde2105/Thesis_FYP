#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node
from launch.substitutions import Command

def generate_launch_description():
    pkg = "artbot_sim"
    share = get_package_share_directory(pkg)

    return LaunchDescription([
        Node(package="robot_state_publisher", executable="robot_state_publisher", parameters=[{"use_sim_time": True, "robot_description": Command(["xacro ", os.path.join(share, "urdf", "triangle_bot.xacro"), " ros2_control_yaml:=", os.path.join(share, "config", "triangle_control.yaml")])}]),
        ExecuteProcess(cmd=["ros2", "launch", "ros_gz_sim", "gz_sim.launch.py", f"gz_args:={os.path.join(share, 'worlds', 'art_world.sdf')} -r"]),
        Node(package="ros_gz_bridge", executable="parameter_bridge", arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"]),
        Node(package="ros_gz_sim", executable="create", arguments=["-name", "artbot", "-topic", "robot_description", "-z", "0.1"]),
        
        TimerAction(period=8.0, actions=[ExecuteProcess(cmd=["ros2", "control", "load_controller", "--set-state", "active", "joint_state_broadcaster"])]),
        TimerAction(period=10.0, actions=[ExecuteProcess(cmd=["ros2", "control", "load_controller", "--set-state", "active", "diff_drive_controller"])]),
        
        Node(package=pkg, executable="triangle_ink_spawner.py", parameters=[{"use_sim_time": True}], remappings=[("/model/artbot/odometry", "/diff_drive_controller/odom")]),
        
        # Call the rectangle script
        TimerAction(period=12.0, actions=[Node(package=pkg, executable="drive_rectangle.py", parameters=[{"use_sim_time": True}])])
    ])