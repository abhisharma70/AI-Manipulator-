# AI Agent Context File: AI-Based Robotic Manipulator Simulation

> **Purpose for AI Agents:** This document serves as the absolute source of truth for AI agents (coding assistants, autonomous developers, and system architects) interacting with or contributing to this project. Read this file carefully to understand system boundaries, tech stack, architecture, hardware virtualizations, and implementation workflows.

---

## 1. Executive Summary & Project Identification

* **Project Title:** AI-Based Robotic Manipulator Simulation Using ROS 2 and Gazebo
* **Domain:** Autonomous Robotics, Computer Vision, Kinematics & Motion Planning
* **Primary Objective:** Design, simulate, and validate an autonomous robotic manipulator arm capable of perception-guided pick-and-place operations inside a high-fidelity 3D physics environment before hardware deployment.
* **Target OS/Environment:** Ubuntu Linux (running within an Oracle VirtualBox Hypervisor)

---

## 2. Technology Stack & Environment Configuration

### 2.1 Stack Overview
```
+-----------------------------------------------------------------------+
|                         APPLICATION LAYER                             |
|               AI Perception & Trajectory Planning                     |
|         (PyTorch/OpenCV/YOLO + MoveIt 2 Kinematics Node)              |
+-----------------------------------------------------------------------+
                                   |
                                   v (ROS 2 Topics / Services / Actions)
+-----------------------------------------------------------------------+
|                         MIDDLEWARE LAYER                              |
|                    ROS 2 (Robot Operating System)                     |
|           DDS Communication, URDF Parsing, Controller Manager          |
+-----------------------------------------------------------------------+
                                   |
                                   v (ros2_control / Gazebo Plugins)
+-----------------------------------------------------------------------+
|                         SIMULATION LAYER                              |
|                          Gazebo Simulator                             |
|               3D Physics (ODE/Bullet), Sensors, Rendering             |
+-----------------------------------------------------------------------+
                                   |
                                   v (System Calls)
+-----------------------------------------------------------------------+
|                      HOST & VIRTUALIZATION LAYER                      |
|                  Ubuntu Linux OS on Oracle VirtualBox                 |
+-----------------------------------------------------------------------+
```

### 2.2 Core Components & Dependencies

1. **Host Virtualization:** Oracle VirtualBox
   * **Target Guest OS:** Ubuntu 22.04 LTS (Jammy Jellyfish) or 24.04 LTS
   * **Recommended VM Allocations for AI Agents to Assume:**
     * CPU Cores: $\ge 4$ cores (Nested Virtualization enabled)
     * RAM: $\ge 8192\text{ MB}$ ($8\text{ GB}$) minimum; $16\text{ GB}$ recommended
     * Video Memory: $128\text{ MB}$ with 3D Acceleration enabled
     * Storage: $50\text{ GB}$ Dynamic Allocation

2. **Middleware:** ROS 2 (Humble Hawksbill / Iron Irwini / Jazzy Jalisco)
   * **Communication Standard:** Data Distribution Service (DDS)
   * **Key Packages:** `rclpy`, `rclcpp`, `geometry_msgs`, `sensor_msgs`, `moveit2`, `ros2_control`

3. **Simulator:** Gazebo (Gazebo Classic or Ignition / Gazebo Harmonic)
   * **Role:** Physics calculation, collision detection, sensor simulation (RGB-D cameras, LiDAR, joint state publishers).

4. **AI & Vision Module:**
   * **Frameworks:** Python 3.x, OpenCV, PyTorch / TensorFlow, NumPy
   * **Core Capabilities:** 2D/3D Object detection, point cloud segmentation, pose estimation ($6\text{ DoF}$ pose estimation for target objects).

---

## 3. Project Architecture & Subsystems

### 3.1 Subsystem Breakdown

#### A. Virtual Machine Environment Setup
* **Responsibility:** Isolates software dependencies from host system; provides stable Linux environment for ROS 2 and Gazebo build toolchains (`colcon`).

#### B. Robot Description & Kinematics (URDF/Xacro)
* **Responsibility:** Defines link geometry, visual/collision meshes, inertia tensors, and joint limits ($N$-Degrees of Freedom).
* **Kinematics:** Defines forward and inverse kinematics dynamics via MoveIt 2 or custom analytic solvers.

#### C. Gazebo Physics & Sensor Simulation
* **Responsibility:** Simulates physical properties (mass, friction, gravity) and sensor outputs (camera frames via `sensor_msgs/msg/Image`, depth maps via `sensor_msgs/msg/PointCloud2`).

#### D. ROS 2 Middleware & Control Nodes
* **Responsibility:** Central nervous system. Publishes joint states (`/joint_states`), controls trajectories (`/joint_trajectory_controller`), and subscribes to sensor feedback.

#### E. AI Manipulation & Perception Pipeline
* **Responsibility:** Process visual input $\rightarrow$ Estimate 3D bounding box / object pose $(x, y, z, r, p, y)$ $\rightarrow$ Generate target end-effector goal $\rightarrow$ Send action trajectory to ROS 2 controller.

---

## 4. Workflows & Execution Pipelines

### 4.1 Pick-and-Place Execution Sequence

```
[Gazebo Simulator] ---> (RGB-D Camera Data) ---> [Perception Node (AI)]
                                                           |
                                                           v
                                                (Object Pose Estimation)
                                                           |
                                                           v
[ROS 2 Controllers] <--- (Trajectory Plan) <--- [MoveIt 2 / Kinematics]
        |
        v
[Gazebo Actuators] ---> (Physical Movement & Gripper Closing)
```

1. **Environment Initialization:** Launch ROS 2 nodes and spawn manipulator URDF into Gazebo environment.
2. **Perception Feed:** Camera node streams live visual feeds over ROS 2 topics.
3. **AI Inference:** Object recognition node detects target object, calculates precise 3D spatial coordinates relative to the base reference frame (`base_link`).
4. **Path Planning:** Target coordinates are sent to MoveIt 2 planner to calculate obstacle-free collision path.
5. **Execution:** Trajectory points are sent to controller actuators (`ros2_control`), executing smooth movement and end-effector/gripper activation.

---

## 5. Guidelines for AI Agents Working on This Project

When generating code, refactoring files, or solving bugs for this repository, AI agents MUST follow these constraints:

### 5.1 ROS 2 Conventions
* **Coding Style:** Follow `PEP 8` for Python nodes (`rclpy`) and `Google C++ Style Guide` for C++ nodes (`rclcpp`).
* **Node Architecture:** Always use object-oriented ROS 2 nodes (inherit from `rclpy.node.Node` or `rclcpp::Node`). Avoid monolithic scripts.
* **Topic/Service/Action Naming:** Use clean snake_case conventions (e.g., `/manipulator/camera/image_raw`, `/manipulator/plan_trajectory`).
* **Build System:** Write standard `package.xml` and `CMakeLists.txt` (C++) or `setup.py` (Python) adhering strictly to `colcon build`.

### 5.2 Gazebo & Simulation Standards
* **URDF/Xacro:** Ensure all links have `<inertial>`, `<visual>`, and `<collision>` tags defined accurately.
* **Physics Stability:** Keep inertia tensors physically realistic; unphysical inertia values cause simulation jittering inside Gazebo.
* **Plugins:** Use standardized ROS 2 Gazebo plugins (`gazebo_ros2_control`, `gazebo_ros_camera`).

### 5.3 VirtualBox & Resource Optimization
* **Performance Considerations:** Gazebo requires significant GPU rendering. When recommending scripts or configurations, account for potential VM performance overhead (e.g., recommend appropriate image resolution like $640 \times 480$ for AI vision models to reduce latency).

---

## 6. Prompting Guide & Instructions for the User

To instruct an AI agent effectively using this document, attach or paste this markdown file into your chat session and use explicit directives such as:

* *"Using the project architecture defined in `robotics_project_context.md`, generate a ROS 2 Python node that subscribes to `/camera/image_raw` and performs object detection with OpenCV."*
* *"Based on `robotics_project_context.md`, write a Xacro file for a 3-DOF robotic arm compatible with Gazebo physics."*
* *"Provide a step-by-step shell script to configure ROS 2 dependencies on Ubuntu inside VirtualBox as specified in Section 2."*