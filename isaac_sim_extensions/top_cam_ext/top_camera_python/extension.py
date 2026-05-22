# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import omni.ext
import omni.timeline
import omni.physx
import numpy as np
import carb
import time
from .ros_bridge import RosBridge


def _suppress_noise_warnings():
    """Isaac Sim 내부에서 발생하는 매 프레임 노이즈 경고를 억제한다.

    대상:
      - isaacsim.core.simulation_manager.plugin: 'No adjacent samples' 경고
      - omni.usd: USD material binding 반복 경고
      - omni.fabric.plugin: bucket id 관련 경고
      - usdrt.population.plugin, omni.kit.window.collection.collection_watch 등
    """
    try:
        import omni.log
        for _ch in (
            "isaacsim.core.simulation_manager.plugin",
            "omni.usd",
            "omni.fabric.plugin",
            "omni.kit.window.collection.collection_watch",
            "usdrt.population.plugin",
        ):
            omni.log.set_level(omni.log.Level.Error, channel=_ch)
    except Exception:
        pass

    try:
        import carb.settings
        settings = carb.settings.get_settings()
        # carb 로그 설정을 통해 강제로 채널 레벨을 Error로 변경
        settings.set("/log/channels/isaacsim.core.simulation_manager.plugin", "Error")
        settings.set("/log/channels/omni.usd", "Error")
        settings.set("/log/channels/omni.fabric.plugin", "Error")
        settings.set("/log/channels/omni.kit.window.collection.collection_watch", "Error")
        settings.set("/log/channels/usdrt.population.plugin", "Error")
    except Exception:
        pass

    carb.log_warn("[top_cam_ext] 노이즈 경고 채널 억제 적용 완료 (omni.log & carb.settings).")


# ── 수조 좌표 가져오기 (water_tank_env_ext 참조) ─────────────────────────────
def _get_pool_centers():
    """params.POOL_CENTERS를 동적으로 가져온다 (import 실패 시 빈 리스트)."""
    try:
        import sys
        from pathlib import Path
        _common = Path(__file__).resolve().parents[2] / "water_tank_env_ext"
        if str(_common) not in sys.path:
            sys.path.insert(0, str(_common))
        from water_tank_env_python import params
        return list(params.POOL_CENTERS)
    except Exception as e:
        carb.log_warn(f"[top_cam_ext] POOL_CENTERS import 실패, 기본값 사용: {e}")
        return [(-12.75, -5.0)]  # Pool_1만이라도 동작


class TopCamExtension(omni.ext.IExt):
    def on_startup(self, ext_id: str):
        self._bridge = RosBridge()
        self._physx_sub = None
        self._cameras = {}        # {pool_id: Camera}
        self._last_capture_time = 0.0
        self._pool_centers = _get_pool_centers()

        # 1. 메인 재생(Run) 감지를 위한 타임라인(Timeline) 전역 이벤트 후킹
        self._timeline = omni.timeline.get_timeline_interface()
        stream = self._timeline.get_timeline_event_stream()
        self._timeline_sub = stream.create_subscription_to_pop(self._on_timeline_event)

        # ── 노이즈 경고 억제 (모듈 레벨 함수 호출) ──────────────────────────
        _suppress_noise_warnings()

        carb.log_warn(f"[top_cam_ext] Extension loaded: {len(self._pool_centers)}개 수조 감지. Run 대기 중.")

    def on_shutdown(self):
        self._stop_system()
        self._timeline_sub = None
        # 싱글톤 리셋: hot reload 시 새 인스턴스가 생성되도록 보장
        import threading as _threading
        RosBridge._instance = None
        RosBridge._singleton_lock = _threading.Lock()

    def _on_timeline_event(self, event):
        # 2. 다른 확장앱에서 Play 버튼을 누르더라도 즉시 감지하여 자동 실행
        if event.type == int(omni.timeline.TimelineEventType.PLAY):
            carb.log_warn("[top_cam_ext] Timeline PLAY 감지됨. 탑캠 자동 시작 및 ROS 브릿지 연결!")
            self._start_system()
        elif event.type == int(omni.timeline.TimelineEventType.STOP):
            carb.log_warn("[top_cam_ext] Timeline STOP 감지됨. 탑캠 시스템 중지.")
            self._stop_system()

    def _start_system(self):
        num_pools = len(self._pool_centers)
        self._bridge.start(num_pools=num_pools)
        self._setup_cameras()

        # 3. 매 물리 프레임마다 카메라 캡처를 실행하도록 구독
        self._physx_sub = omni.physx.get_physx_interface().subscribe_physics_step_events(self._on_physics_step)

    def _stop_system(self):
        # Isaac Sim 5.x: 구독 객체를 None으로 설정하면 자동 해제됨 (RAII 패턴)
        if self._physx_sub is not None:
            self._physx_sub = None
        self._bridge.stop()
        self._cameras = {}

    def _setup_cameras(self):
        """각 수조(Pool_N) 위에 이미 build_top_cameras()로 생성된 USD 카메라를 
        Isaac Sim Camera 센서로 래핑한다."""
        try:
            from omni.isaac.sensor import Camera
            import omni.usd

            stage = omni.usd.get_context().get_stage()

            for pool_id, (cx, cy) in enumerate(self._pool_centers, start=1):
                # build_top_cameras()가 이미 생성한 카메라 경로
                cam_path = f"/World/Pools/Pool_{pool_id}/TopCamera"

                # USD에 카메라가 없으면 직접 생성 (폴백)
                if not stage.GetPrimAtPath(cam_path).IsValid():
                    from pxr import UsdGeom
                    UsdGeom.Camera.Define(stage, cam_path)
                    carb.log_warn(f"[top_cam_ext] Pool_{pool_id}: TopCamera가 USD에 없어 직접 생성.")

                # Isaac Sim Camera 센서로 래핑 및 절대 높이 Z = 12.0 강제 적용
                camera = Camera(
                    prim_path=cam_path,
                    name=f"top_cam_{pool_id}",
                    resolution=(1280, 720),
                )
                camera.initialize()
                camera.set_world_pose(position=np.array([cx, cy, 12.0]))
                self._cameras[pool_id] = camera
                carb.log_warn(f"[top_cam_ext] Pool_{pool_id} TopCamera 절대높이 Z=12.0 강제 설정 완료. (센터: {cx:.1f}, {cy:.1f})")

            carb.log_warn(f"[top_cam_ext] 총 {len(self._cameras)}개 카메라 초기화 완료.")
        except Exception as e:
            carb.log_error(f"[top_cam_ext] Camera Setup Failed: {e}")

    def _on_physics_step(self, dt):
        if not self._cameras:
            return

        current_time = time.time()
        # 0.2초 (5Hz) 간격으로 프레임 캡처 제한 (Readback 버틀넥 제거)
        if current_time - self._last_capture_time < 0.2:
            return

        for pool_id, camera in self._cameras.items():
            try:
                frame = camera.get_rgba()
                if frame is not None and frame.shape[0] > 0:
                    self._bridge.publish_frame(frame, pool_id=pool_id)
            except Exception:
                # 렌더 엔진 초기화 전에 발생하는 간헐적 None 에러 무시
                pass

        self._last_capture_time = current_time


Extension = TopCamExtension