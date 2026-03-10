import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg = "artbot_sim"
    share = get_package_share_directory(pkg)

    world_path = os.path.join(share, "worlds", "art_world.sdf")
    xacro_path = os.path.join(share, "urdf", "artbot.urdf.xacro")
    config_file = os.path.join(share, "config", "circle_control.yaml")

    # Process Xacro dynamically
    robot_description_xml = xacro.process_file(
        xacro_path,
        mappings={"ros2_control_yaml": config_file},
    ).toxml()

    gz = ExecuteProcess(cmd=["gz", "sim", "-r", world_path], output="screen")

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_description_xml}, {"use_sim_time": True}],
    )

    # CRITICAL FIX: Explicitly bridge the odometry topic so drive_circle.py can see it
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/model/artbot/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/diff_drive_controller/cmd_vel_unstamped@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/pen_down@std_msgs/msg/Bool]gz.msgs.Boolean"
        ],
        output="screen"
    )

    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-topic", "robot_description",
            "-name", "artbot",
            "-allow_renaming", "false",
            "-world", "art_world",
            "-x", "0.0", "-y", "0.0", "-z", "0.05",
        ],
    )

    diff_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=["diff_drive_controller", "--controller-manager", "/controller_manager"],
    )

    js_spawner = Node(
        package="controller_manager",
        executable="spawner",
        output="screen",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    ink = Node(
        package='artbot_sim',
        executable='ink_spawner.py',
        name='ink_spawner',
        remappings=[
            ('/model/artbot/odometry', '/diff_drive_controller/odom')
        ]
    )

    drive = Node(
        package=pkg,
        executable="drive_circle.py",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    # Sequential Loading Logic
    after_spawn = RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[diff_spawner]))
    after_diff = RegisterEventHandler(OnProcessExit(target_action=diff_spawner, on_exit=[js_spawner]))
    after_js = RegisterEventHandler(
        OnProcessExit(target_action=js_spawner, on_exit=[ink, drive])
    )

    return LaunchDescription([
        gz, rsp, bridge, spawn,
        after_spawn, after_diff, after_js
    ])
