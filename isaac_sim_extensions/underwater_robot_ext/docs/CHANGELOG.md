# Changelog

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
