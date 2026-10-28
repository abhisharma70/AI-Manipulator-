# AI-Based Robotic Manipulator Simulation

An autonomous perception-guided pick-and-place robotic manipulator simulation using ROS 2 Jazzy and Gazebo Sim.

---

## Workspace Structure

```
/home/student/Robotics_Proj/ros2_ws/
└── src/
    ├── manipulator_description/     # URDF, Xacro kinematics, sensors & RViz visualization
    ├── manipulator_gazebo/          # Gazebo world, physics, spawners, and ROS-Gazebo bridge
    ├── manipulator_control/         # ros2_control hardware configurations and controllers
    ├── manipulator_moveit_config/   # MoveIt 2 SRDF, OMPL kinematics and collision config
    ├── manipulator_perception/      # AI/Vision node: HSV color segmentation, centroid & 3D pose
    └── manipulator_bringup/         # Pick-and-place state machine and top-level bringup launch
```

---

## Prerequisites & Installation

If `colcon` is not yet installed in your terminal, run:
```bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions ros-jazzy-moveit ros-jazzy-ros-gz
```

---

## Build & Source

From the workspace root:
```bash
cd /home/student/Robotics_Proj/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

---

## Execution Modes

### 1. View Robot Model & Kinematic Tree in RViz2
```bash
ros2 launch manipulator_description view_robot.launch.py
```

### 2. Launch Physics Simulation in Gazebo
```bash
ros2 launch manipulator_gazebo manipulator_gazebo.launch.py gui:=false
```
The default server-only mode avoids GUI graphics issues in virtual machines. To open the Gazebo window on a machine with working 3D acceleration, pass `gui:=true`.

### 3. Run Autonomous Pick-and-Place (Full System Bringup)
```bash
ros2 launch manipulator_bringup bringup.launch.py gui:=false
```
Pass `gui:=true` to display Gazebo when 3D acceleration is available.
This launches:
- Gazebo Sim with tabletop environment and target pick cube
- Robot state publisher & TF tree
- Hardware controllers (`joint_state_broadcaster`, `arm_controller`, `gripper_controller`)
- MoveIt 2 `move_group`
- AI perception node detecting the target 3D pose
- Autonomous pick-and-place state machine orchestrator
