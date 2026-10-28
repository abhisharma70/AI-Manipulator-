#!/usr/bin/env bash

# ==============================================================================
# AI-Based Robotic Manipulator Simulation - All-in-One Build & Run Script
# ==============================================================================

set -eo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

WORKSPACE_DIR="/home/student/Robotics_Proj/ros2_ws"
ROS_DISTRO_PATH="/opt/ros/jazzy"
GUI_MODE="true"

if [ "$#" -gt 1 ]; then
    echo "Usage: $0 [--gui|--headless]" >&2
    exit 2
fi

case "${1:-}" in
    ""|--gui) ;;
    --headless) GUI_MODE="false" ;;
    *)
        echo "Usage: $0 [--gui|--headless]" >&2
        exit 2
        ;;
esac

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}  AI Robotic Manipulator Simulation Launch Sequence  ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Check for ROS 2 Installation
if [ ! -f "${ROS_DISTRO_PATH}/setup.bash" ]; then
    echo -e "${RED}[ERROR] ROS 2 Jazzy not found at ${ROS_DISTRO_PATH}.${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4] Checking and installing missing dependencies...${NC}"
MISSING_PKGS=()

# Check key packages
dpkg -s ros-jazzy-ros2-control >/dev/null 2>&1 || MISSING_PKGS+=("ros-jazzy-ros2-control")
dpkg -s ros-jazzy-ros2-controllers >/dev/null 2>&1 || MISSING_PKGS+=("ros-jazzy-ros2-controllers")
dpkg -s ros-jazzy-controller-manager >/dev/null 2>&1 || MISSING_PKGS+=("ros-jazzy-controller-manager")
dpkg -s ros-jazzy-gz-ros2-control >/dev/null 2>&1 || MISSING_PKGS+=("ros-jazzy-gz-ros2-control")
dpkg -s python3-colcon-common-extensions >/dev/null 2>&1 || MISSING_PKGS+=("python3-colcon-common-extensions")
dpkg -s python3-opencv >/dev/null 2>&1 || MISSING_PKGS+=("python3-opencv")

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing packages detected: ${MISSING_PKGS[*]}${NC}"
    echo -e "${YELLOW}Installing missing dependencies (requires sudo)...${NC}"
    sudo apt update
    sudo apt install -y "${MISSING_PKGS[@]}"
else
    echo -e "${GREEN}All required packages are installed.${NC}"
fi

# 2. Source ROS 2 Base
echo -e "${GREEN}[2/4] Sourcing ROS 2 Jazzy environment...${NC}"
source "${ROS_DISTRO_PATH}/setup.bash"

# 3. Clean and Build Workspace
echo -e "${GREEN}[3/4] Building ROS 2 Workspace in ${WORKSPACE_DIR}...${NC}"
cd "${WORKSPACE_DIR}"
colcon build --symlink-install

# 4. Source Workspace Overlay
source "${WORKSPACE_DIR}/install/setup.bash"

echo -e "${GREEN}[4/4] Launching Gazebo, Controllers, Perception & State Machine...${NC}"
echo -e "${BLUE}----------------------------------------------------${NC}"
echo -e "${YELLOW}Activity Logs will stream below:${NC}"
echo -e "${GREEN}Gazebo GUI: ${GUI_MODE}${NC}"
echo -e "${BLUE}----------------------------------------------------${NC}"

# Execute top-level bringup and tee logs to simulation_run.log
LOG_FILE="/home/student/Robotics_Proj/simulation_run.log"
REPORT_SCRIPT="/home/student/Robotics_Proj/generate_telemetry_image.py"

generate_telemetry_report() {
    if [ -f "${LOG_FILE}" ]; then
        python3 "${REPORT_SCRIPT}" --log "${LOG_FILE}" || \
            echo -e "${RED}[WARN] Telemetry image generation failed.${NC}" >&2
    fi
}

trap generate_telemetry_report EXIT

echo -e "${GREEN}Logging output to console and ${LOG_FILE}...${NC}"
ros2 launch manipulator_bringup bringup.launch.py "gui:=${GUI_MODE}" 2>&1 | tee "${LOG_FILE}"
