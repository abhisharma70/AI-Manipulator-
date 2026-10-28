import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    pkg_manipulator_description = get_package_share_directory('manipulator_description')
    pkg_manipulator_gazebo = get_package_share_directory('manipulator_gazebo')
    pkg_manipulator_control = get_package_share_directory('manipulator_control')
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    world_path = os.path.join(pkg_manipulator_gazebo, 'worlds', 'manipulator_tabletop.sdf')
    controllers_yaml = os.path.join(pkg_manipulator_control, 'config', 'ros2_controllers.yaml')
    bridge_config = os.path.join(pkg_manipulator_gazebo, 'config', 'gz_bridge.yaml')
    xacro_file = os.path.join(pkg_manipulator_description, 'urdf', 'manipulator.urdf.xacro')

    robot_description = ParameterValue(
        Command(['xacro ', xacro_file, ' controllers_yaml:=', controllers_yaml]),
        value_type=str
    )

    # Robot State Publisher
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True
        }]
    )

    # Gazebo Sim
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items()
    )

    # Spawn Entity into Gazebo
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'manipulator',
            '-topic', 'robot_description',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.0'
        ],
        output='screen'
    )

    # Gazebo-ROS Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{'config_file': bridge_config}],
        output='screen'
    )

    # ── Chained spawner sequence ──────────────────────────────────────────────
    # Step 1: joint_state_broadcaster (must come first — publishes /joint_states
    #         which robot_state_publisher needs to build the TF tree)
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager', '/controller_manager',
            '--switch-timeout', '30.0',
        ],
        output='screen'
    )

    # Step 2: arm_controller — launched only after joint_state_broadcaster exits
    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'arm_controller',
            '--controller-manager', '/controller_manager',
            '--switch-timeout', '30.0',
        ],
        output='screen'
    )

    # Step 3: gripper_controller — launched only after arm_controller exits
    gripper_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'gripper_controller',
            '--controller-manager', '/controller_manager',
            '--switch-timeout', '30.0',
        ],
        output='screen'
    )

    # Event handlers to enforce sequential spawning
    spawn_arm_after_jsb = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[arm_controller_spawner],
        )
    )

    spawn_gripper_after_arm = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=arm_controller_spawner,
            on_exit=[gripper_controller_spawner],
        )
    )

    return LaunchDescription([
        gz_sim,
        robot_state_publisher_node,
        spawn_robot,
        bridge,
        joint_state_broadcaster_spawner,
        spawn_arm_after_jsb,
        spawn_gripper_after_arm,
    ])
