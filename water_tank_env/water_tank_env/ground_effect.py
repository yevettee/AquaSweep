"""
ground_effect.py
----------------
지면 효과(Ground Effect) 계산 모듈

원리:
    로봇이 바닥 가까이에서 수평으로 움직이면,
    로봇과 바닥 사이의 좁은 틈에서 물이 빠져나가기 어려워
    추가 저항이 발생한다.

    바닥 청소로봇은 항상 바닥 근처에 있으므로 중요한 효과.
"""

import numpy as np


class GroundEffect:

    def __init__(
        self,
        influence_height: float = 0.10,
        max_extra_factor: float = 0.5,
    ):
        """
        Args:
            influence_height : 지면 효과가 시작되는 높이 (m). 기본 10cm
            max_extra_factor : 최대 추가 저항 비율 (0.5 = 항력이 최대 50% 증가)
        """
        self.influence_height = influence_height
        self.max_extra_factor = max_extra_factor

    def compute(
        self,
        robot_pos_z: float,
        floor_z: float,
        linear_velocity: np.ndarray,
        base_drag_coeff: float,
    ) -> np.ndarray:
        """
        지면 효과로 인한 추가 항력을 계산한다.

        Args:
            robot_pos_z     : 로봇의 z 좌표 (m)
            floor_z         : 수조 바닥의 z 좌표 (m)
            linear_velocity : 현재 로봇의 선속도 (m/s)
            base_drag_coeff : 기본 항력 계수 (drag.py에서 사용한 값)

        Returns:
            extra_drag_force: 추가 항력 벡터 (N)
                              수평(x, y) 방향만 적용 (바닥과 수직 방향은 제외)
        """
        height_above_floor = robot_pos_z - floor_z

        # 지면 효과 범위 밖이면 추가 저항 없음
        if height_above_floor >= self.influence_height:
            return np.zeros(3)

        # 바닥에 가까울수록 효과가 커짐 (선형 보간)
        # height=0       → factor = max_extra_factor (최대)
        # height=영향범위 → factor = 0 (없음)
        closeness = 1.0 - (height_above_floor / self.influence_height)
        extra_factor = self.max_extra_factor * closeness

        # 수평 속도에만 적용 (z는 0으로)
        horizontal_velocity = np.array([
            linear_velocity[0],
            linear_velocity[1],
            0.0
        ])

        extra_drag = -extra_factor * base_drag_coeff * horizontal_velocity

        return extra_drag
