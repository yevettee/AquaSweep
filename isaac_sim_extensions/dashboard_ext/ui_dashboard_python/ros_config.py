# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 topic/action naming for the AquaSweep dashboard (keep in sync with aqua_dashboard/ros_topics.py)."""

POOL_COUNT = 8

def pool_status_topic(pool_id: int) -> str:
    return f"/pool_{pool_id}/status"


def pool_robot_status_topic(pool_id: int) -> str:
    return f"/under_robot_{pool_id}/status"


def pool_clean_floor_action(pool_id: int) -> str:
    return f"/pool_{pool_id}/clean_floor"


def pool_ids() -> range:
    return range(1, POOL_COUNT + 1)


# Aliases for backward compatibility
tank_status_topic = pool_status_topic
tank_robot_status_topic = pool_robot_status_topic
tank_clean_floor_action = pool_clean_floor_action
tank_ids = pool_ids
TANK_COUNT = POOL_COUNT
