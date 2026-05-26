# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ActionGraph-based ROS2 cmd_vel controller setup.

Creates an OmniGraph that subscribes to /under_robot_N/cmd_vel and drives
the differential robot using Isaac Sim's built-in nodes. This approach
avoids rclpy import issues by using Isaac Sim's native ROS2 bridge.

Usage:
    from .actiongraph_setup import create_cmd_vel_graph, remove_cmd_vel_graph

    # After robot is loaded on stage:
    create_cmd_vel_graph(
        robot_prim_path="/World/Hippo",
        robot_name="under_robot_1",
        wheel_radius=0.049,
        wheel_base=0.4523,
    )
"""

from typing import Optional

import carb

# Graph path pattern for cmd_vel controllers
GRAPH_PATH_PATTERN = "/World/Graphs/{robot_name}_CmdVelController"


def create_cmd_vel_graph(
    robot_prim_path: str,
    robot_name: str = "under_robot_1",
    wheel_radius: float = 0.049,
    wheel_base: float = 0.4523,
    max_linear_speed: float = 1.0,
    max_angular_speed: float = 2.8,
) -> Optional[str]:
    """Create an ActionGraph for ROS2 cmd_vel subscription and differential drive control.

    Args:
        robot_prim_path: USD prim path to the robot articulation root (e.g., "/World/Hippo")
        robot_name: Robot name used in topic (e.g., "under_robot_1" for /under_robot_1/cmd_vel)
        wheel_radius: Wheel radius in meters
        wheel_base: Distance between wheels in meters
        max_linear_speed: Maximum linear velocity (m/s)
        max_angular_speed: Maximum angular velocity (rad/s)

    Returns:
        Graph prim path if successful, None otherwise
    """
    try:
        import omni.graph.core as og
        from pxr import Usd
        from isaacsim.core.utils.stage import get_current_stage
    except ImportError as e:
        carb.log_error(f"[actiongraph_setup] Failed to import OmniGraph: {e}")
        return None

    graph_path = GRAPH_PATH_PATTERN.format(robot_name=robot_name)
    topic_name = f"/{robot_name}/cmd_vel"

    stage = get_current_stage()
    if stage is None:
        carb.log_error("[actiongraph_setup] No stage available")
        return None

    # Remove existing graph if present
    existing = stage.GetPrimAtPath(graph_path)
    if existing.IsValid():
        carb.log_info(f"[actiongraph_setup] Removing existing graph: {graph_path}")
        stage.RemovePrim(graph_path)

    # Ensure parent prim exists
    graphs_prim = stage.GetPrimAtPath("/World/Graphs")
    if not graphs_prim.IsValid():
        stage.DefinePrim("/World/Graphs", "Scope")

    carb.log_info(
        f"[actiongraph_setup] Creating cmd_vel graph: {graph_path}\n"
        f"  topic: {topic_name}\n"
        f"  robot: {robot_prim_path}\n"
        f"  wheel_radius: {wheel_radius}, wheel_base: {wheel_base}"
    )

    try:
        # Create ActionGraph for ROS2 cmd_vel subscription and differential drive control
        #
        # Correct structure (from Isaac Sim documentation):
        # - All execution-triggered nodes receive tick from OnPlaybackTick IN PARALLEL
        # - Data flows separately between nodes
        #
        # Execution (parallel from OnPlaybackTick):
        #   OnPlaybackTick.tick -> SubscribeTwist.execIn
        #   OnPlaybackTick.tick -> DiffController.execIn
        #   OnPlaybackTick.tick -> ArticulationController.execIn
        #
        # Data flow:
        #   ROS2Context.context -> SubscribeTwist.context
        #   SubscribeTwist.linearVelocity (double3) -> BreakLinear -> x (double) -> DiffController.linearVelocity
        #   SubscribeTwist.angularVelocity (double3) -> BreakAngular -> z (double) -> DiffController.angularVelocity
        #   DiffController.velocityCommand -> ArticulationController.velocityCommand
        #
        keys = og.Controller.Keys
        
        (graph, nodes, _, _) = og.Controller.edit(
            {"graph_path": graph_path, "evaluator_name": "execution"},
            {
                keys.CREATE_NODES: [
                    ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                    ("ROS2Context", "isaacsim.ros2.bridge.ROS2Context"),
                    ("SubscribeTwist", "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                    ("BreakLinear", "omni.graph.nodes.BreakVector3"),
                    ("BreakAngular", "omni.graph.nodes.BreakVector3"),
                    ("DiffController", "isaacsim.robot.wheeled_robots.DifferentialController"),
                    ("ArticulationController", "isaacsim.core.nodes.IsaacArticulationController"),
                ],
                keys.SET_VALUES: [
                    ("SubscribeTwist.inputs:topicName", topic_name),
                    ("DiffController.inputs:wheelRadius", wheel_radius),
                    ("DiffController.inputs:wheelDistance", wheel_base),
                    ("DiffController.inputs:maxLinearSpeed", max_linear_speed),
                    ("DiffController.inputs:maxAngularSpeed", max_angular_speed),
                    ("ArticulationController.inputs:robotPath", robot_prim_path),
                    # Use jointNames instead of jointIndices for explicit mapping
                    ("ArticulationController.inputs:jointNames", ["left_wheel_joint", "right_wheel_joint"]),
                ],
                keys.CONNECT: [
                    # Execution: ALL nodes receive tick from OnPlaybackTick in PARALLEL
                    ("OnPlaybackTick.outputs:tick", "SubscribeTwist.inputs:execIn"),
                    ("OnPlaybackTick.outputs:tick", "DiffController.inputs:execIn"),
                    ("OnPlaybackTick.outputs:tick", "ArticulationController.inputs:execIn"),
                    # Data: ROS2 context
                    ("ROS2Context.outputs:context", "SubscribeTwist.inputs:context"),
                    # Data: Break Twist vectors into scalar components
                    # linearVelocity.x = forward/backward velocity
                    ("SubscribeTwist.outputs:linearVelocity", "BreakLinear.inputs:tuple"),
                    ("BreakLinear.outputs:x", "DiffController.inputs:linearVelocity"),
                    # angularVelocity.z = rotation velocity
                    ("SubscribeTwist.outputs:angularVelocity", "BreakAngular.inputs:tuple"),
                    ("BreakAngular.outputs:z", "DiffController.inputs:angularVelocity"),
                    # Data: Wheel velocities to articulation controller
                    ("DiffController.outputs:velocityCommand", "ArticulationController.inputs:velocityCommand"),
                ],
            },
        )

        carb.log_info(f"[actiongraph_setup] Successfully created cmd_vel graph: {graph_path}")
        return graph_path

    except Exception as e:
        carb.log_error(f"[actiongraph_setup] Failed to create graph: {e}")
        import traceback
        carb.log_error(traceback.format_exc())
        return None


def remove_cmd_vel_graph(robot_name: str = "under_robot_1") -> bool:
    """Remove the cmd_vel ActionGraph for a robot.

    Args:
        robot_name: Robot name used when creating the graph

    Returns:
        True if removed, False otherwise
    """
    try:
        from isaacsim.core.utils.stage import get_current_stage
    except ImportError:
        return False

    graph_path = GRAPH_PATH_PATTERN.format(robot_name=robot_name)
    stage = get_current_stage()

    if stage is None:
        return False

    prim = stage.GetPrimAtPath(graph_path)
    if prim.IsValid():
        stage.RemovePrim(graph_path)
        carb.log_info(f"[actiongraph_setup] Removed graph: {graph_path}")
        return True

    return False


def create_cmd_vel_subscriber_graph(
    robot_name: str = "under_robot_1",
) -> Optional[str]:
    """ROS2 cmd_vel 구독 전용 ActionGraph 생성 (휠 제어 없음).

    SubscribeTwist → BreakLinear/BreakAngular 까지만 구성한다.
    linear.x, angular.z 값은 read_cmd_vel()로 읽는다.
    """
    try:
        import omni.graph.core as og
        from isaacsim.core.utils.stage import get_current_stage
    except ImportError as e:
        carb.log_error(f"[actiongraph_setup] OmniGraph import failed: {e}")
        return None

    graph_path = GRAPH_PATH_PATTERN.format(robot_name=robot_name)
    topic_name = f"/{robot_name}/cmd_vel"

    stage = get_current_stage()
    if stage is None:
        return None

    existing = stage.GetPrimAtPath(graph_path)
    if existing.IsValid():
        stage.RemovePrim(graph_path)

    if not stage.GetPrimAtPath("/World/Graphs").IsValid():
        stage.DefinePrim("/World/Graphs", "Scope")

    try:
        keys = og.Controller.Keys
        og.Controller.edit(
            {"graph_path": graph_path, "evaluator_name": "execution"},
            {
                keys.CREATE_NODES: [
                    ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                    ("ROS2Context",    "isaacsim.ros2.bridge.ROS2Context"),
                    ("SubscribeTwist", "isaacsim.ros2.bridge.ROS2SubscribeTwist"),
                    ("BreakLinear",    "omni.graph.nodes.BreakVector3"),
                    ("BreakAngular",   "omni.graph.nodes.BreakVector3"),
                ],
                keys.SET_VALUES: [
                    ("SubscribeTwist.inputs:topicName", topic_name),
                ],
                keys.CONNECT: [
                    ("OnPlaybackTick.outputs:tick",      "SubscribeTwist.inputs:execIn"),
                    ("ROS2Context.outputs:context",       "SubscribeTwist.inputs:context"),
                    ("SubscribeTwist.outputs:linearVelocity",  "BreakLinear.inputs:tuple"),
                    ("SubscribeTwist.outputs:angularVelocity", "BreakAngular.inputs:tuple"),
                ],
            },
        )
        carb.log_info(f"[actiongraph_setup] cmd_vel subscriber graph created: {graph_path} | topic={topic_name}")
        return graph_path
    except Exception as e:
        carb.log_error(f"[actiongraph_setup] Failed: {e}")
        return None


def read_cmd_vel(robot_name: str = "under_robot_1") -> tuple:
    """ActionGraph 에서 최신 cmd_vel (linear_x, angular_z) 를 읽는다.

    ActionGraph 가 없거나 실패하면 (0.0, 0.0) 반환.
    """
    try:
        import omni.graph.core as og
        graph_path = GRAPH_PATH_PATTERN.format(robot_name=robot_name)
        lx = og.Controller.get(
            og.Controller.attribute(f"{graph_path}/BreakLinear.outputs:x")
        )
        az = og.Controller.get(
            og.Controller.attribute(f"{graph_path}/BreakAngular.outputs:z")
        )
        return float(lx), float(az)
    except Exception:
        return 0.0, 0.0


def graph_exists(robot_name: str = "under_robot_1") -> bool:
    """Check if a cmd_vel graph exists for the given robot.

    Args:
        robot_name: Robot name

    Returns:
        True if graph exists
    """
    try:
        from isaacsim.core.utils.stage import get_current_stage
    except ImportError:
        return False

    graph_path = GRAPH_PATH_PATTERN.format(robot_name=robot_name)
    stage = get_current_stage()

    if stage is None:
        return False

    return stage.GetPrimAtPath(graph_path).IsValid()
