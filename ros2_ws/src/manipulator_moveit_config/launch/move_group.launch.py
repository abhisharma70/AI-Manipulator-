import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder

def generate_launch_description():
    pkg_desc = get_package_share_directory('manipulator_description')
    xacro_file = os.path.join(pkg_desc, 'urdf', 'manipulator.urdf.xacro')

    moveit_config = (
        MoveItConfigsBuilder('manipulator', package_name='manipulator_moveit_config')
        .robot_description(file_path=xacro_file)
        .robot_description_semantic(file_path='config/manipulator.srdf')
        .robot_description_kinematics(file_path='config/kinematics.yaml')
        .joint_limits(file_path='config/joint_limits.yaml')
        .planning_pipelines(pipelines=['ompl'])
        .trajectory_execution(file_path='config/moveit_controllers.yaml')
        .to_moveit_configs()
    )

    move_group_params = moveit_config.to_dict()
    move_group_params['use_sim_time'] = True

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[move_group_params],
    )

    return LaunchDescription([
        move_group_node
    ])
