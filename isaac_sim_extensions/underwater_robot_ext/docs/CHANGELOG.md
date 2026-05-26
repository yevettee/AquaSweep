# Changelog

## [1.2.0] - 2026-05-26
### Changed
- `HIPPO_USD_FILENAME`: `hippo_v1_black_eyes.usdz` → `hippo_v1_lite.usdz` (7대 모두 자동 적용).
- 캐터필러 트랙 시각 최적화: 1,032개 Mesh prim + 1,034 머티리얼 → **1개 메시 + 단일 머티리얼** (Blender Decimate ratio 0.05).
  - face 수 2,108,236 → 105,411 (-95%), draw call 폭발 해소.
  - 새 USD: `data/hippo_v1_lite.usd` (편집용) + `hippo_v1_lite.usdz` (런타임 self-contained 31MB).
  - 트랙은 `data/caterpillar_decimate005_clean.usd` 를 reference 로 참조.

### Removed (in hippo_v1_lite)
- `/Root/GroundPlane` (CollisionMesh + CollisionPlane) — 7대 spawn 시 유령 충돌면이 같이 끌려오던 문제 해결.
- `/Root/hippo/base_link/under_cam` 하위 시각 자식 (`Model`, `Lens`, `OmniverseKitViewportCameraMesh`) — under_cam Camera prim 자체는 유지.

### Added
- `underwater_robot_python/bake_visual_wheels.py` — VisualWheels 서브트리 → 단일 Mesh 베이크 (asset-prep).
- `underwater_robot_python/clean_decimated_usd.py` — Blender export 후처리 (scaffolding 제거 + Y-up 회전 제거 + metersPerUnit 통일).
- `underwater_robot_python/usd_mesh_to_obj.py` — USD Mesh → OBJ 추출 (외부 DCC 핸드오프용).

## [1.1.0] - 2026-05-22
### Changed
- 우리 개조 로봇 이름을 **dingo → hippo** 로 통일 (Clearpath Dingo-D 플랫폼 기반).
  - 새 USD: `data/hippo_v1.usd` (v1 base를 flatten 후 cleanup +
    카메라 위치/이름 고정 + 본체 핑크 + realsense/lidar 진짜 제거).
  - 기존 `data/underwater_robot_camera_v1.usd` 는 호환을 위해 유지.
- 모듈 rename:
  - `dingo_physics_sanitize.py` → `hippo_physics_sanitize.py`
  - `verify_dingo_usd.py` → `verify_hippo_usd.py`
  - `prepare_dingo_usd_on_stage()` → `prepare_hippo_usd_on_stage()`
- `global_variables.py`:
  - `DINGO_USD_FILENAME` → `HIPPO_USD_FILENAME` (구 이름은 alias 로 유지)
  - `DINGO_WHEEL_RADIUS_M/BASE_M` → `HIPPO_WHEEL_*` (구 이름은 alias 로 유지)
  - `ROBOT_PRIM_PATH = "/World/Dingo"` → `"/World/Hippo"`
  - `DEBUG_TRAIL_CURVE_PRIM_PATH = ".../DingoCenterTrail"` → `HippoCenterTrail`
- `aquasweep_ext/ui_builder.py`: 7-pool spawn 시 scene name `dingo_{i}` → `hippo_{i}`,
  `PRIMARY_ROBOT_SCENE_NAME = "hippo_1"`.
- `top_cam_ext`의 `EXCLUDE_TOKENS` 에 `/hippo/` 추가 (legacy `/dingo/` 도 유지).

### Removed
- `_disable_default_cameras()` + `DEFAULT_CAMERAS_TO_DISABLE` 상수 —
  `hippo_v1.usd` 가 flatten 결과로 realsense/viewport gizmo 가 진짜 제거된
  상태라 런타임에 deactivate 할 prim 이 없음 (dead code).

## [1.0.4] - 2026-05-20
### Changed
- `data/underwater_robot_camera_v1.usd`에 `aquasweep:*` custom attribute 적용 (v0.4.1 튜닝값 재현)
  - `aquasweep:volume = 0.036` m³ (AABB 자동값 0.122는 카메라 프레임 포함으로 과대평가 → 명시 오버라이드)
  - `aquasweep:half_height = 0.1432` m
  - `aquasweep:cd_linear = 200` N·s/m
  - 결과: ρV/m = **0.900** → SINK (알짜 -39 N, ~0.98 m/s² 감속 → 천천히 가라앉음)
- 적용 도구: `scripts/add_aquasweep_attrs.py` (water_tank_env_ext v0.4.3에서 복원)
- 백업: `data/underwater_robot_camera_v1.usd.bak` (스크립트 자동 생성, gitignore 누락 → 수동 처리 필요)

### 알려진 이슈 / 미완
- integration_yun 브랜치 .gitignore 부재 → `*.bak`, `__pycache__/*.pyc` 등이 untracked로 표시. 별도 PR로 .gitignore 추가 권장
- 실기 검증 미완 — Isaac Sim에서 LOAD → RUN으로 천천히 가라앉는지 확인 필요

## [1.0.3] - 2026-05-19
### Changed
- 기본 로봇을 JetBot → extension `data/dingo_transformed_tracked.usd` (Clearpath Dingo + VisualWheels) 로 교체, 균일 스케일 제거
- 차동 모델·나선 간격·질량 상수를 Dingo 측정값 및 Dingo-D 스펙(9.1 kg)에 맞춤
### Removed
- JetBot 외부 트랙 USD 레퍼런스용 `track_visual_attach` — Dingo USD 내장 `VisualWheels` 와 충돌·중복 방지
### Fixed
- Load 시 `VisualWheels` 체인 물리만 비활성화 (`prepare_dingo_usd_on_stage`) — 계층은 USD 편집본 사용

## [1.0.2] - 2026-05-18
### Added
- JetBot 휠 링크 아래에 트랙 비주얼 USD 를 선택적으로 레퍼런스로 붙이는 `track_visual_attach` (data/track_visuals 또는 AQUASWEEP_* 환경 변수)

### Changed
- 원형 수조(직경 5m 가정) 나선형 시나리오: 반경 방향 스텝 후 고정 반지름 `R_target` 을 유지하며 CCW 한 바퀴를 반복하는 FSM (`scenario.py`)
- JetBot 약 40cm 스케일을 위한 USD 균일 스케일 및 차동 휠 파라미터 정합 (`global_variables`, `ui_builder`)

## [1.0.1] - 2025-01-21
### Changed
- Update extension description and add extension specific test settings


## [0.1.0] - 2026-05-17

### Added

- Initial version of underwater.robot Extension
