# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 topic/action naming for the AquaSweep dashboard (keep in sync with aqua_dashboard/ros_topics.py)."""

TANK_COUNT = 8

def tank_status_topic(tank_id: int) -> str:
    return f"/tank_{tank_id}/status"


def tank_robot_status_topic(tank_id: int) -> str:
    return f"/under_robot_{tank_id}/status"


def tank_clean_floor_action(tank_id: int) -> str:
    return f"/tank_{tank_id}/clean_floor"


def tank_ids() -> range:
    return range(1, TANK_COUNT + 1)
