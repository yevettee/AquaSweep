# aqua_mock

**WARNING: This package is for TESTING and DEVELOPMENT purposes only.**

This package provides mock ROS2 publishers and services to test the AquaSweep dashboard and planner nodes without requiring Isaac Sim or real robot hardware.

## Purpose

- Publishes simulated `TankStatus` and `RobotStatus` messages
- Publishes placeholder camera detection images (`sensor_msgs/Image`)
- Provides mock `CleanFloor` action servers that simulate cleaning progress
- Allows testing the full dashboard UI and planner logic offline

## Usage

```bash
# Build
cd ~/AquaSweep/water_ws
colcon build --packages-select aqua_mock
source install/setup.bash

# Run mock publisher
ros2 run aqua_mock mock_publisher_node
```

## Published Topics

For each pool (pool_1, pool_2):

| Topic | Type | Description |
|-------|------|-------------|
| `/pool_{id}/status` | `aqua_interfaces/TankStatus` | Pool status with varying fish_count |
| `/under_robot_{id}/status` | `aqua_interfaces/RobotStatus` | Robot status |
| `/pool_{id}/top_img_det` | `sensor_msgs/Image` | Placeholder top camera image |
| `/pool_{id}/under_img_det` | `sensor_msgs/Image` | Placeholder underwater camera image |

## Action Servers

| Action | Description |
|--------|-------------|
| `/pool_{id}/clean_floor` | Mock CleanFloor action server |

## Notes

- The mock `fish_count` cycles between 0 and non-zero values to allow testing the planner's fish_count == 0 filter
- Camera images are solid-color placeholders (different colors per pool)
- CleanFloor actions complete in ~1.2 seconds with progress feedback
