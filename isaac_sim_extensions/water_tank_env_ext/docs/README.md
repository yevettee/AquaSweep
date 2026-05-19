# water.tank.env

AquaSweep environment extension: a cylindrical water tank (5 m diameter ×
1.2 m height) plus an OceanSim-wrapped underwater camera for visual
turbidity (Clear / Medium / Turbid).

## Buttons

- **LOAD**: Builds a fresh stage with the tank + water.
- **RESET**: Returns the scene to its post-load state.
- **RUN / STOP**: Plays/pauses the timeline and renders the underwater
  camera each physics step. A separate UW_Camera viewport window displays
  the turbidity-applied frame.

## Prerequisites

The `OceanSim` extension (and `isaacsim.ros2.bridge` for its rclpy import)
must be enabled. Launch Isaac Sim with the ROS2 env vars set:

```bash
export ROS_DISTRO=humble
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/exts/isaacsim.ros2.bridge/humble/lib"
```
