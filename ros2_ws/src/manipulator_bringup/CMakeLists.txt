cmake_minimum_required(VERSION 3.8)
project(manipulator_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

install(
  PROGRAMS manipulator_bringup/pick_and_place_orchestrator.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
