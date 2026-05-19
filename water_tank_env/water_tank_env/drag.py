"""
drag.py
-------
항력(Drag) + 추가질량(Added Mass) 계산 모듈

항력 원리:
    물속에서 움직이면 속도에 비례하는 반대 방향 힘이 생긴다.
    공식: F_drag = -Cd × velocity

추가질량 원리:
    물속에서 가속하면 주변 물도 같이 끌고가야 해서 실제보다 무겁게 느껴진다.
    공식: F_added = -Ca × ρ × V × acceleration
"""

import numpy as np


WATER_DENSITY = 1000.0  # kg/m³


class Drag:

    def __init__(
        self,
        linear_drag_coeff: float = 10.0,
        angular_drag_coeff: float = 5.0,
    ):
        """
        Args:
            linear_drag_coeff : 선형 이동 항력 계수 (클수록 더 느리게 이동)
            angular_drag_coeff: 회전 항력 계수 (클수록 회전이 더 느림)
        """
        self.Cd_linear  = linear_drag_coeff
        self.Cd_angular = angular_drag_coeff

    def compute(
        self,
        linear_velocity: np.ndarray,
        angular_velocity: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        항력을 계산한다.

        Args:
            linear_velocity : 선속도 [vx, vy, vz] (m/s)
            angular_velocity: 각속도 [wx, wy, wz] (rad/s)

        Returns:
            linear_drag_force : 선형 항력 벡터 (N)
            angular_drag_torque: 회전 항력 토크 (N·m)
        """
        # 속도 반대 방향으로 힘 적용
        # 빠를수록 저항도 커짐
        linear_drag_force   = -self.Cd_linear  * linear_velocity
        angular_drag_torque = -self.Cd_angular * angular_velocity

        return linear_drag_force, angular_drag_torque


class AddedMass:

    def __init__(
        self,
        robot_volume: float,
        added_mass_coeff: float = 0.5,
    ):
        """
        Args:
            robot_volume     : 로봇 부피 (m³)
            added_mass_coeff : 추가질량 계수 (구형=0.5, 납작한형=0.1~0.3)
                               모델링 담당에게 형태에 맞는 값 확인
        """
        self.robot_volume     = robot_volume
        self.added_mass_coeff = added_mass_coeff

        # 추가질량 = Ca × ρ × V
        self._added_mass = added_mass_coeff * WATER_DENSITY * robot_volume

    def compute(self, linear_acceleration: np.ndarray) -> np.ndarray:
        """
        추가질량 힘을 계산한다.

        Args:
            linear_acceleration: 선형 가속도 [ax, ay, az] (m/s²)

        Returns:
            force: 추가질량 힘 벡터 (N)
        """
        # 가속 방향의 반대로 힘이 작용 (관성처럼 느껴지는 효과)
        force = -self._added_mass * linear_acceleration
        return force

    def update_volume(self, new_volume: float):
        """로봇 부피가 바뀔 경우 재계산"""
        self.robot_volume = new_volume
        self._added_mass  = self.added_mass_coeff * WATER_DENSITY * new_volume
