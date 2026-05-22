# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""ROS2 topic/action/service naming for the AquaSweep dashboard (keep in sync with aqua_dashboard/ros_topics.py)."""

POOL_COUNT = 7


def pool_status_topic(pool_id: int) -> str:
    return f"/pool_{pool_id}/status"


def pool_robot_status_topic(pool_id: int) -> str:
    return f"/under_robot_{pool_id}/status"


def pool_top_cam_det_topic(pool_id: int) -> str:
    return f"/pool_{pool_id}/top_img_det"


def pool_under_cam_det_topic(pool_id: int) -> str:
    return f"/pool_{pool_id}/under_img_det"


def pool_clean_floor_action(pool_id: int) -> str:
    return f"/pool_{pool_id}/clean_floor"


def pool_start_clean_floor_service(pool_id: int) -> str:
    return f"/pool_{pool_id}/start_clean_floor"


def planner_start_service() -> str:
    return "/planner/start"


def planner_pause_service() -> str:
    return "/planner/pause"


def pool_ids() -> range:
    return range(1, POOL_COUNT + 1)


# Aliases for backward compatibility
tank_status_topic = pool_status_topic
tank_robot_status_topic = pool_robot_status_topic
tank_clean_floor_action = pool_clean_floor_action
tank_ids = pool_ids
TANK_COUNT = POOL_COUNT
