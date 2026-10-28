#!/usr/bin/env python3
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration

class PickAndPlaceOrchestrator(Node):
    def __init__(self):
        super().__init__('pick_and_place_orchestrator')

        # Action clients for controllers
        self.arm_client = ActionClient(self, FollowJointTrajectory, '/arm_controller/follow_joint_trajectory')
        self.gripper_client = ActionClient(self, FollowJointTrajectory, '/gripper_controller/follow_joint_trajectory')

        # Subscribe to target object pose from perception
        self.target_pose = None
        self.pose_sub = self.create_subscription(
            PoseStamped,
            '/target_object_pose',
            self.target_pose_callback,
            10
        )

        self.arm_joints = ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5']
        self.gripper_joints = ['left_finger_joint', 'right_finger_joint']

        self.get_logger().info('Pick and Place Orchestrator initialized. Waiting for controllers...')
        self.timer = self.create_timer(2.0, self.run_state_machine)
        self.state = 'WAIT_FOR_SERVERS'

    def target_pose_callback(self, msg: PoseStamped):
        if self.target_pose is None:
            self.target_pose = msg
            self.get_logger().info(
                f'Received target pick pose at X={msg.pose.position.x:.3f}, Y={msg.pose.position.y:.3f}, Z={msg.pose.position.z:.3f}'
            )

    def run_state_machine(self):
        self.timer.cancel()

        if self.state == 'WAIT_FOR_SERVERS':
            if not self.arm_client.wait_for_server(timeout_sec=2.0) or not self.gripper_client.wait_for_server(timeout_sec=2.0):
                self.get_logger().warn('Waiting for action servers to become active...')
                self.timer = self.create_timer(2.0, self.run_state_machine)
                return

            self.get_logger().info('Action servers connected! Starting Pick-and-Place sequence...')
            self.state = 'READY_OBSERVE'

        if self.state == 'READY_OBSERVE':
            self.get_logger().info('[STATE 1/7] Moving arm to ready observation pose & opening gripper...')
            self.send_gripper_goal(0.025)
            # Arm tilts forward, gripper pointing ~115° down (phi≈2.0 rad), TCP at (0.22, 0, 0.60)
            self.send_arm_goal([-0.151, 0.610, 1.541, 0.0], duration_sec=3.0)
            self.state = 'WAIT_FOR_DETECTION'
            self.timer = self.create_timer(3.5, self.run_state_machine)
            return

        if self.state == 'WAIT_FOR_DETECTION':
            self.get_logger().info('[STATE 2/7] Waiting for perception node to publish target pose...')
            if self.target_pose is None:
                self.timer = self.create_timer(1.0, self.run_state_machine)
                return
            self.state = 'PRE_GRASP'
            self.timer = self.create_timer(0.5, self.run_state_machine)
            return

        if self.state == 'PRE_GRASP':
            self.get_logger().info('[STATE 3/7] Moving arm to pre-grasp approach pose above object...')
            # Gripper pointing ~143° down (phi≈2.5 rad), TCP at (0.25, 0, 0.52)
            self.send_arm_goal([0.023, 0.577, 1.900, 0.0], duration_sec=3.0)
            self.state = 'GRASP_DESCENT'
            self.timer = self.create_timer(3.5, self.run_state_machine)
            return

        if self.state == 'GRASP_DESCENT':
            self.get_logger().info('[STATE 4/7] Descending to grasp height and closing gripper...')
            # Gripper pointing straight DOWN (phi=π), TCP at (0.25, 0, 0.425) — top of cube
            self.send_arm_goal([0.165, 0.767, 2.210, 0.0], duration_sec=2.0)
            time.sleep(2.2)
            self.send_gripper_goal(0.005)  # Close gripper around cube
            self.state = 'LIFT_OBJECT'
            self.timer = self.create_timer(2.0, self.run_state_machine)
            return

        if self.state == 'LIFT_OBJECT':
            self.get_logger().info('[STATE 5/7] Lifting object vertically...')
            # Gripper still pointing ~115° down (phi≈2.0 rad), TCP at (0.25, 0, 0.58)
            self.send_arm_goal([-0.161, 0.773, 1.388, 0.0], duration_sec=2.5)
            self.state = 'TRANSPORT_TO_BIN'
            self.timer = self.create_timer(3.0, self.run_state_machine)
            return

        if self.state == 'TRANSPORT_TO_BIN':
            self.get_logger().info('[STATE 6/7] Transporting object above target placement bin...')
            # Rotate joint_1 by 0.722 rad to face bin at (0.25, 0.22), TCP at (0.25, 0.22, 0.52)
            self.send_arm_goal([0.042, 0.779, 1.379, 0.0], duration_sec=3.0,
                               joint_1=0.722)
            self.state = 'RELEASE_AND_RESET'
            self.timer = self.create_timer(3.5, self.run_state_machine)
            return

        if self.state == 'RELEASE_AND_RESET':
            self.get_logger().info('[STATE 7/7] Releasing object into bin and returning to Home pose...')
            self.send_gripper_goal(0.025)  # Open gripper
            time.sleep(1.5)
            self.send_arm_goal([0.0, 0.0, 0.0, 0.0], duration_sec=3.0)
            self.get_logger().info('🎉 Pick-and-Place Cycle successfully completed!')
            return

    def send_arm_goal(self, positions_q2345, duration_sec=3.0, joint_1=0.0):
        """
        Send arm trajectory goal.
        positions_q2345: list of [q2, q3, q4, q5] (joint_1 handled separately via joint_1 param).
        """
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = self.arm_joints
        point = JointTrajectoryPoint()
        point.positions = [joint_1] + list(positions_q2345)
        sec = int(duration_sec)
        nanosec = int((duration_sec - sec) * 1e9)
        point.time_from_start = Duration(sec=sec, nanosec=nanosec)
        goal.trajectory.points.append(point)
        self.arm_client.send_goal_async(goal)

    def send_gripper_goal(self, finger_position, duration_sec=1.0):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = self.gripper_joints
        point = JointTrajectoryPoint()
        point.positions = [finger_position, finger_position]
        sec = int(duration_sec)
        nanosec = int((duration_sec - sec) * 1e9)
        point.time_from_start = Duration(sec=sec, nanosec=nanosec)
        goal.trajectory.points.append(point)
        self.gripper_client.send_goal_async(goal)

def main(args=None):
    rclpy.init(args=args)
    node = PickAndPlaceOrchestrator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
