# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 topic/action naming (keep in sync with dashboard_ext ui_dashboard_python/ros_config.py)."""

TANK_COUNT = 8


def _tank_prefix(tank_id: int) -> str:
    return f"/aqua/tank_{tank_id}"


def tank_status_topic(tank_id: int) -> str:
    return f"{_tank_prefix(tank_id)}/status"


def tank_robot_status_topic(tank_id: int) -> str:
    return f"{_tank_prefix(tank_id)}/robot_status"


def tank_clean_floor_action(tank_id: int) -> str:
    return f"{_tank_prefix(tank_id)}/clean_floor"


def tank_ids() -> range:
    return range(1, TANK_COUNT + 1)
