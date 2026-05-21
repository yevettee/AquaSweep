# AquaSweep Dashboard (`dashboard_ext`)

Isaac Sim UI extension that subscribes to per-tank `TankStatus` / `RobotStatus` topics and sends `CleanFloor` action goals. Eight tank panels are shown in a 2×4 grid.

## ROS2 topic / action naming

| Resource | Name pattern |
|----------|----------------|
| Tank status | `/aqua/tank_{id}/status` (`aqua_interfaces/TankStatus`) |
| Robot status | `/aqua/tank_{id}/robot_status` (`aqua_interfaces/RobotStatus`) |
| Clean floor | `/aqua/tank_{id}/clean_floor` (`aqua_interfaces/CleanFloor`) |

`{id}` is `1` … `8`. Change `TANK_COUNT` in `ui_dashboard_python/ros_config.py` and `aqua_dashboard/ros_topics.py` together.

## 1. Build workspace and run mock telemetry

```bash
cd /path/to/AquaSweep/water_ws
colcon build --packages-select aqua_interfaces aqua_dashboard
source /path/to/AquaSweep/water_ws/scripts/source_ros_terminal.sh
ros2 run aqua_dashboard mock_telemetry_node
```

> `~/.bashrc`에 `ISAAC_ROS2_BRIDGE/lib`가 있으면 `source install/setup.bash` 만으로는 `ros2`가 깨질 수 있습니다. 반드시 `source_ros_terminal.sh` 를 쓰세요.

Leave this terminal running. It publishes dummy status at 1 Hz and hosts `CleanFloor` action servers for all tanks.

## 2. Verify ROS2 (optional, second terminal)

```bash
source /path/to/AquaSweep/water_ws/install/setup.bash
ros2 topic echo /aqua/tank_1/status --once
ros2 action list | grep clean_floor
```

## 3. Launch Isaac Sim with ROS2 bridge

Match the environment used by `water_tank_env_ext` (Humble + Isaac `isaacsim.ros2.bridge` libs):

```bash
export ROS_DISTRO=humble
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/exts/isaacsim.ros2.bridge/humble/lib"
source /path/to/AquaSweep/water_ws/install/setup.bash
```

Enable the extension:

```bash
# 이 머신에는 isaacsim CLI가 없습니다. isaac-sim.sh 를 사용하세요:
~/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/isaac-sim.sh \
  --ext-folder /path/to/AquaSweep/isaac_sim_extensions \
  --enable dashboard_ext

# 또는 래퍼 스크립트:
/path/to/AquaSweep/isaac_sim_extensions/scripts/launch_dashboard.sh
```

Open **AquaSweep Dashboard** from the toolbar. The **ROS2** frame should show `ROS2 connected`. Expand tank panels to see live fields; press **START** to send a `CleanFloor` goal (mock node logs the goal and reports progress in the UI).

## Troubleshooting

- **ROS2 unavailable** in the dashboard: Isaac was started without sourcing `water_ws/install/setup.bash`, or `aqua_interfaces` is not on `PYTHONPATH`.
- **No tank data (all dashes)**: mock node is not running, or `ROS_DOMAIN_ID` / DDS settings differ between processes.
- **CleanFloor server not available**: start `mock_telemetry_node` before pressing START.

## Implementation layout

| File | Role |
|------|------|
| `ui_dashboard_python/ros_config.py` | Topic/action names, `TANK_COUNT` |
| `ui_dashboard_python/ros_bridge.py` | `rclpy` subscriptions, action clients, background spin |
| `ui_dashboard_python/ui_builder.py` | 8-tank UI and refresh loop |
| `water_ws/.../mock_telemetry_node.py` | Temporary publisher + action server |
