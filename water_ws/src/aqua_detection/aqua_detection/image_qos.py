"""QoS profiles for camera image subscriptions."""

from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)


def image_subscription_qos(reliability: str = 'best_effort', depth: int = 10) -> QoSProfile:
    """Build QoS for Isaac Sim /pool_N/top_img_raw subscribers.

    Isaac Sim ROS2CameraHelper defaults to RELIABLE + keepLast(10).
    For live vision, BEST_EFFORT + small depth is preferred (drop stale frames).
    """
    normalized = reliability.lower()
    if normalized in ('best_effort', 'sensor', 'sensor_data'):
        policy = ReliabilityPolicy.BEST_EFFORT
    elif normalized == 'reliable':
        policy = ReliabilityPolicy.RELIABLE
    else:
        return qos_profile_sensor_data

    return QoSProfile(
        reliability=policy,
        history=HistoryPolicy.KEEP_LAST,
        depth=depth,
        durability=DurabilityPolicy.VOLATILE,
    )
