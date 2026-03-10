import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg_name = 'artbot_sim'
    pkg_share = get_package_share_directory(pkg_name)

    # 1) Process URDF (xacro arg passed here)
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    ros2_control_yaml = os.path.join(pkg_share, 'config', 'ros2_control.yaml')

    doc = xacro.process_file(xacro_file, mappings={
        'ros2_control_yaml': ros2_control_yaml,
    })
    robot_description = {'robot_description': doc.toxml()}

    # 2) Start Gazebo
    world_path = os.path.join(pkg_share, 'worlds', 'art_world.sdf')
    gazebo = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_path],
        output='screen'
    )

    # 3) Cleanup (remove leftover models if they exist)
    remove_artbot = ExecuteProcess(
        cmd=['gz', 'model', '--remove', '--model-name', 'artbot'],
        output='screen'
    )
    remove_artbot0 = ExecuteProcess(
        cmd=['gz', 'model', '--remove', '--model-name', 'artbot_0'],
        output='screen'
    )

    # 4) Robot State Publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[robot_description, {'use_sim_time': True}]
    )

    # 5) Bridge (Clock)
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock]'
        ],
        output='screen'
    )


    # 6) Spawn Robot (NO allow_renaming --> prevents artbot_0)
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'artbot',
            '-world', 'art_world',
            '-x', '0.0', '-y', '0.0', '-z', '0.05'
        ],
        output='screen'
    )

    # 7) Controllers
    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_controller"],
        output="screen",
    )

    joint_broad_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        output="screen",
    )

    spawn_controllers_after_robot = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_entity,
            on_exit=[joint_broad_spawner, diff_drive_spawner],
        )
    )

    return LaunchDescription([
        gazebo,
        node_robot_state_publisher,
        bridge,

        # cleanup first, then spawn
        remove_artbot,
        remove_artbot0,
        spawn_entity,

        spawn_controllers_after_robot,
    ])
