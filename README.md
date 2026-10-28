# ROS 2 Manipulator Pick-and-Place Simulation

A ROS 2 Jazzy and Gazebo Sim project for a five-joint manipulator with a parallel gripper. The full bringup launches the simulated tabletop scene, controllers, camera-based target detection, MoveIt 2, and an autonomous pick-and-place sequence.

## Features

- Gazebo Sim tabletop world with a red target cube and destination bin
- Xacro robot description with camera and gripper
- `ros2_control` arm and gripper trajectory controllers
- Camera-based target detection and 3D position estimation
- MoveIt 2 planning configuration
- Automated pick-and-place orchestration
- Per-run telemetry image generated from the launch log

## Requirements

- Ubuntu with ROS 2 Jazzy
- Gazebo Sim and `ros_gz`
- MoveIt 2
- `colcon`
- Python 3, OpenCV, and NumPy

Install the ROS and system dependencies with:

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-moveit \
  ros-jazzy-ros-gz \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers \
  ros-jazzy-controller-manager \
  ros-jazzy-gz-ros2-control \
  python3-colcon-common-extensions \
  python3-opencv \
  python3-numpy
```

## Run the Full Simulation

From the repository root:

```bash
./run_simulation.sh
```

The script checks its dependencies, builds the workspace, sources the ROS environment, and launches the full system with the Gazebo GUI. In virtual machines or environments with unreliable 3D acceleration, run headless instead:

```bash
./run_simulation.sh --headless
```

The simulation log is written to `simulation_run.log`. When the launch process exits, the script generates or replaces `simulation_telemetry.png` with target-position samples, sequence progress, controller status, and the run result. The generated image is ignored by Git.

To stop a run normally, use `Ctrl+C` in the terminal running the script. Avoid force-quitting the terminal if you want the telemetry image generated on exit.

## Build and Launch Manually

```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch manipulator_bringup bringup.launch.py gui:=false
```

Set `gui:=true` to open Gazebo's graphical interface when 3D acceleration is available.

## Workspace Packages

| Package | Purpose |
| --- | --- |
| `manipulator_description` | Xacro robot model, camera, gripper, and RViz description |
| `manipulator_gazebo` | Gazebo world, simulation launch, and ROS-Gazebo bridge configuration |
| `manipulator_control` | `ros2_control` hardware and controller configuration |
| `manipulator_moveit_config` | MoveIt 2 planning, kinematics, and controller configuration |
| `manipulator_perception` | Image-based target detection and 3D pose estimation |
| `manipulator_bringup` | Full-system launch and pick-and-place orchestrator |

## Telemetry Report

`generate_telemetry_image.py` reads `simulation_run.log` and writes `simulation_telemetry.png` in the repository root. It can also be run directly:

```bash
python3 generate_telemetry_image.py
```

Optional paths can be supplied with `--log PATH` and `--output PATH`. The report summarizes values present in the text log; it does not record continuous joint-state telemetry.
