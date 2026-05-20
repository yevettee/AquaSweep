#!/usr/bin/env bash
# Build aqua_interfaces for Isaac Sim Python 3.11 and install into isaacsim.ros2.bridge.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WS="$ROOT/water_ws"

ISAAC_PY="${ISAAC_PYTHON:-}"
if [[ -z "$ISAAC_PY" ]]; then
  ISAAC_PY="$(find "$HOME/.cache/packman" -path '*/python/bin/python3' 2>/dev/null | head -1 || true)"
fi
if [[ -z "$ISAAC_PY" || ! -x "$ISAAC_PY" ]]; then
  echo "Set ISAAC_PYTHON to Isaac Sim python3 (Kit python/bin/python3)." >&2
  exit 1
fi

ISAAC_BRIDGE="${ISAAC_ROS2_BRIDGE:-$HOME/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/exts/isaacsim.ros2.bridge/humble}"
if [[ ! -d "$ISAAC_BRIDGE/rclpy/rclpy" ]]; then
  echo "Isaac ROS2 bridge not found at: $ISAAC_BRIDGE" >&2
  exit 1
fi

echo "Using Isaac Python: $ISAAC_PY"
"$ISAAC_PY" --version

ISAAC_SITE="$("$ISAAC_PY" -c 'import site; print(site.getsitepackages()[0])')"
"$ISAAC_PY" -m pip install -q empy==3.3.4 catkin_pkg lark-parser packaging numpy
cp -r /opt/ros/humble/lib/python3.10/site-packages/ament_package "$ISAAC_SITE/"

source /opt/ros/humble/setup.bash
export PYTHONPATH="/opt/ros/humble/lib/python3.10/site-packages:/opt/ros/humble/local/lib/python3.10/dist-packages"
export LD_LIBRARY_PATH="$ISAAC_BRIDGE/lib:${LD_LIBRARY_PATH:-}"

cd "$WS"
colcon build --packages-select aqua_interfaces \
  --build-base build_isaac \
  --install-base install_isaac \
  --allow-overriding aqua_interfaces \
  --cmake-args \
    -DPYTHON_EXECUTABLE="$ISAAC_PY" \
    -DPython3_EXECUTABLE="$ISAAC_PY"

PY311_PKG="$WS/install_isaac/aqua_interfaces/lib/python3.11/site-packages/aqua_interfaces"
LIB_DIR="$WS/install_isaac/aqua_interfaces/lib"
DEST_RCLPY="$ISAAC_BRIDGE/rclpy/aqua_interfaces"
DEST_LIB="$ISAAC_BRIDGE/lib"

rm -rf "$DEST_RCLPY"
cp -r "$PY311_PKG" "$DEST_RCLPY"
cp "$LIB_DIR"/libaqua_interfaces*.so "$DEST_LIB/"

echo "Installed aqua_interfaces (py3.11) to:"
echo "  $DEST_RCLPY"
echo "  $DEST_LIB"
