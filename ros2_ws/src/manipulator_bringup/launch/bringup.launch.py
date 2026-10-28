import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_manipulator_gazebo = get_package_share_directory('manipulator_gazebo')
    pkg_manipulator_moveit = get_package_share_directory('manipulator_moveit_config')
    gui = LaunchConfiguration('gui')

    # 1. Gazebo simulation launch
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_manipulator_gazebo, 'launch', 'manipulator_gazebo.launch.py')
        ),
        launch_arguments={'gui': gui}.items(),
    )

    # 2. MoveIt move_group node (delayed to allow controllers to register)
    moveit_launch = TimerAction(
        period=6.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_manipulator_moveit, 'launch', 'move_group.launch.py')
                )
            )
        ]
    )

    # 3. Perception node (delayed to allow camera feed to start)
    perception_node = TimerAction(
        period=10.0,
        actions=[
            Node(
                package='manipulator_perception',
                executable='object_detector',
                name='object_detector',
                output='screen',
                parameters=[{'use_sim_time': True}]
            )
        ]
    )

    # 4. Pick-and-Place Orchestrator
    orchestrator_node = TimerAction(
        period=14.0,
        actions=[
            Node(
                package='manipulator_bringup',
                executable='pick_and_place_orchestrator.py',
                name='pick_and_place_orchestrator',
                output='screen',
                parameters=[{'use_sim_time': True}]
            )
        ]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'gui',
            default_value='false',
            description='Start the Gazebo GUI (requires working 3D graphics)',
        ),
        gazebo_launch,
        moveit_launch,
        perception_node,
        orchestrator_node
    ])
