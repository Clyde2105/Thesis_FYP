#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node
from launch.substitutions import Command


def generate_launch_description():
    package_name = "artbot_sim"
    share = get_package_share_directory(package_name)

    xacro_path = os.path.join(share, "urdf", "triangle_bot.xacro")
    config_file = os.path.join(share, "config", "triangle_control.yaml")
    world_path = os.path.join(share, "worlds", "art_world.sdf")

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{
            "use_sim_time": True,
            "robot_description": Command([
                "xacro ", xacro_path, " ros2_control_yaml:=", config_file
            ])
        }],
        output="screen",
    )

    gazebo = ExecuteProcess(
        cmd=[
            "ros2", "launch", "ros_gz_sim", "gz_sim.launch.py",
            f"gz_args:={world_path} -r"
        ],
        output="screen",
    )

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        ],
        output="screen",
    )

    spawn_robot = TimerAction(
        period=3.0,
        actions=[
            Node(
                package="ros_gz_sim",
                executable="create",
                arguments=[
                    "-name", "artbot",
                    "-topic", "robot_description",
                    "-x", "0.0",
                    "-y", "0.0",
                    "-z", "0.2",
                ],
                output="screen",
            )
        ],
    )

    joint_state_broadcaster = TimerAction(
        period=8.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "ros2", "control", "load_controller",
                    "--set-state", "active",
                    "joint_state_broadcaster",
                ],
                output="screen",
            )
        ],
    )

    diff_drive_controller = TimerAction(
        period=10.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    "ros2", "control", "load_controller",
                    "--set-state", "active",
                    "diff_drive_controller",
                ],
                output="screen",
            )
        ],
    )

    ink_spawner = Node(
        package=package_name,
        executable="triangle_ink_spawner.py",
        name="ink_spawner",
        parameters=[{"use_sim_time": True}],
        output="screen",
        remappings=[
            ("/model/artbot/odometry", "/diff_drive_controller/odom"),
        ],
    )

    drive_triangle = TimerAction(
        period=12.0,
        actions=[
            Node(
                package=package_name,
                executable="drive_triangle.py",
                name="drive_triangle",
                parameters=[{"use_sim_time": True}],
                output="screen",
            )
        ],
    )

    return LaunchDescription([
        robot_state_publisher,
        gazebo,
        bridge,
        spawn_robot,
        joint_state_broadcaster,
        diff_drive_controller,
        ink_spawner,
        drive_triangle,
    ])