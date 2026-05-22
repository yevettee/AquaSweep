# Changelog

## [0.4.4] - 2026-05-22

### 변경사항
- `sturgeon_spawner.TARGET_LENGTH_M`: 0.90 → **1.0 m**
  - 양식장 청소 시연 영상용 — 1 m급 철갑상어로 통일

### 현재 구현 단계
- 신규 spawn 시 모든 sturgeon이 ~1 m 자연 길이로 스케일 적용
- 기존 인접 모듈/시스템 동작 변경 없음

### 알려진 이슈 / 미완
- `_RADIUS_MAX = TANK_RADIUS - 1.0 = 3.0 m` 인접 margin은 그대로 — 1 m 사이즈로 커진 만큼 풀 벽 충돌 빈도 증가 가능 (관찰 후 margin 재조정 검토)
- v0.4.3 이전 알려진 이슈 그대로 유지

## [0.4.3] - 2026-05-20

### 변경사항
- `scripts/add_aquasweep_attrs.py` 복원 (integration_yun 브랜치 누락분)
  - 파일은 v0.3.1 CHANGELOG에 도입 명시돼있으나 `1차 통합본` 머지 시점에 working tree에서 누락
  - `origin/yun`에서 그대로 가져옴 (수정 없음)
  - 로봇 USD에 `aquasweep:*` custom attribute + PhysX mass를 박는 CLI 유틸 — `physics_applier.discover_bodies()`의 reader 측과 짝을 이룸

### 통합 작업 컨텍스트 (integration_yun)
- yun 브랜치 분석 결과 cherry-pick 후보 4개 중 1개만 채택:
  - ✅ `add_aquasweep_attrs.py` — physics_applier 시스템의 writer 측 도구로 명백히 보완적
  - ❌ `buoyancy.py` — 현 `physics_applier._compute_buoyancy()`가 per-body half_height 지원하므로 중복
  - ❌ `fluid_forces.py` — `aquasweep:*` 속성 기반 시스템과 경쟁 구현 (글로벌 상수 vs per-body USD attr)
  - ❌ `WaterTankScenario` 리팩터링 — OceanSim camera 제거가 핵심이었으나 OceanSim 유지 결정으로 스킵

### 현재 구현 단계
- integration_yun = main(`수조 색깔 및 재질 변경` + `1차 통합본`) + add_aquasweep_attrs 도구
- OceanSim 통합 / debris_env_ext / perception_node 모두 유지
- 수조 8 m 직경, water level 1.2 m는 main 시점에 이미 동일

### 알려진 이슈 / 미완
- v0.4.2 이전 알려진 이슈 그대로 유지
- integration_yun 브랜치 upstream 미설정 — push 시 `git push -u origin integration_yun` 필요

## [0.4.2] - 2026-05-19

### 변경사항
- Unused 자산 제거:
  - `src/assets/robots/underwater_robot_v1.usd` (19 MB) — `underwater_robot_camera_v1.usd`로 대체됨
  - `src/assets/scenes/water_tank.usd` — `build_scene.py` 삭제 후 재생성 불가, ext가 procedural rebuild만 함

### Dead code 점검 결과
- water_tank_env_ext 모든 모듈 사용 중 (`JETBOT_PRIM_PATH`, `_camera_parent_path`, OceanSim 관련 변수 모두 v0.4.0에서 제거 완료)
- 옛 water_tank_env 패키지의 buoyancy/drag/ground_effect는 physics_applier가 sys.path 통해 import 중
- ROS2 메타(package.xml/setup.py)는 향후 ROS2 노드 대비 유지

### 현재 구현 단계
- 코드 dead 없음, 자산 깔끔
- 우리 영역 (water_tank_env_ext + 공유 assets) 정리 완료

### 알려진 이슈 / 미완
- 지명님 영역 `dingo_transformed_tracked.usd`는 새 USD로 대체됐지만 이전 파일 그대로 — 지명님 결정 필요
- v0.4.x 이전 알려진 이슈 그대로 유지

## [0.4.1] - 2026-05-19

### 변경사항
- 수조 dimension 확장:
  - `TANK_RADIUS`: 2.5 → 4.0 m (내부 직경 5 m → 8 m)
  - `TANK_INNER_Z`: 1.2 → 1.5 m
  - `WATER_LEVEL`: 1.0 → 1.2 m
- 로봇 부력 튜닝 (시각 검증 위해 알짜 부력 작게):
  - `underwater_robot_camera_v1.usd`: volume 0.025 → **0.036 m³**, cd_linear 추가 = **200**
  - ρV/m = 0.625 → **0.900** (알짜 -39N, 가속도 -0.98 m/s²)
  - 바닥 도달 시간 ~2초 → 부력 작용 시각 확인 가능

### 현재 구현 단계
- 수조 8 m 직경, 1.5 m 높이, water level 1.2 m로 확장
- 부력 균형이 더 자연스러워짐 — 천천히 가라앉으면서 drag으로 종단속도 안정

### 알려진 이슈 / 미완
- 메모리(`project_water_tank`)의 수조 사양 갱신 필요 (직경 5 m → 8 m)
- v0.4.0 이전 알려진 이슈 그대로 유지

## [0.4.0] - 2026-05-19

### 변경사항 (Breaking)
- **OceanSim UW_Camera 통합 제거** — 로봇 USD에 자체 카메라(RealSense stereo + camera)가 박혀있어 별도 UW_Camera 생성 불필요
  - `scenario.py` 단순화: UW_Camera lifecycle 제거, physics applier만 담당
  - `ui_builder.py`에서 Turbidity 드롭다운 + OceanSim CollapsableFrame 제거
  - `oceansim_camera.py` 모듈 삭제
  - `oceansim_configs/water_*.yaml` 삭제
  - `extension.toml`의 `OceanSim` dependency 제거 + description/keywords 갱신
- 새 로봇 USD(`underwater_robot_ext/data/underwater_robot_camera_v1.usd`)에 attr 적용
  - mass=40 kg, volume=0.025 m³, ρV/m=0.625 (SINK)
  - AABB가 v1보다 큰 0.62×0.69×0.29 (카메라 frame 포함)

### 현재 구현 단계
- water.tank.env가 환경(tank/water/lighting) + 매 step 부력/항력만 담당
- 카메라/시각화는 로봇 USD가 직접 책임
- 시나리오 D 워크플로우 단순화:
  1. `isaac --ext-folder ~/water_ws/src/isaac_sim_extensions`
  2. `water.tank.env` LOAD
  3. Content 패널에서 로봇 USD reference (`underwater_robot_camera_v1.usd` 또는 `underwater_robot_v1.usd`)
  4. `water.tank.env` 다시 LOAD (physics_applier 재 discover)
  5. RUN → 로봇 가라앉음 + 청소 카메라는 USD 자체 카메라 활용

### 알려진 이슈 / 미완
- Turbidity 효과(OceanSim) 부활은 별도 작업 — USD의 기존 camera prim에 OceanSim wrap 가능한지 조사 필요
- v0.3.x 이전 알려진 이슈 그대로 유지

## [0.3.2] - 2026-05-19

### 변경사항
- `physics_applier.py`의 sys.path 주입 경로 버그 수정 — `..` 4단계 → 3단계
- 잘못된 경로 진단을 위해 디렉터리 존재 체크 + 명확한 ImportError 메시지 추가

### 알려진 이슈 / 미완
- v0.3.1의 미완 항목 그대로 유지

### 영향
- 이전 버전(0.3.0, 0.3.1)에서 ext가 `ModuleNotFoundError: No module named 'water_tank_env'`로 startup 실패. 0.3.2에서 해결

## [0.3.1] - 2026-05-19

### 변경사항
- JetbotMock 빌드 로직 완전 제거 (사용자 결정 — 진짜 로봇 USD로만 검증)
  - `scene_builders.build_jetbot_mock` 함수 삭제
  - `ui_builder._setup_scene`에서 호출 제거
  - `ui_builder._camera_parent_path` fallback: `/World/JetbotMock` → `/World`
  - `scenario.DEFAULT_CAMERA_PARENT_PATH`: `/World/JetbotMock` → `/World`
- `scripts/add_aquasweep_attrs.py` 신설 — 로봇 USD에 `aquasweep:*` custom attribute + PhysX mass 박는 utility
  - `--mass`, `--volume`, `--half-height`, `--cd-linear`, `--cd-angular`, `--added-mass` 옵션
  - `--dry-run`으로 미리 ρV/m 비율 + FLOAT/NEUTRAL/SINK 판정 확인
  - 백업 파일(`*.bak`) 자동 생성 (gitignore됨)
- 받은 `assets/robots/underwater_robot_v1.usd`에 attr 적용
  - mass = 40 kg (USD에 0이 박혀있어 PhysX 동작 불안정 → 갱신)
  - volume = 0.025 m³, half_height = 0.115 m
  - ρV/m = 0.625 → 바닥 안착 (양식장 바닥 청소 로봇 목표 동작)

### 현재 구현 단계
- 환경 ext + 부력 통합 + 로봇 USD에 attr 박힌 상태
- 시나리오 C(받은 USD로 부력 검증) 즉시 실행 가능
- 사용 워크플로우:
  1. `isaac --ext-folder ~/water_ws/src/isaac_sim_extensions`
  2. `water.tank.env` LOAD
  3. Content 패널에서 `assets/robots/underwater_robot_v1.usd` reference
  4. `water.tank.env` 다시 LOAD (physics_applier 재 discover)
  5. RUN → 로봇이 바닥에 안착

### 알려진 이슈 / 미완
- 카메라 attach 대상 prim: 현재 `/World/Jetbot` fixed lookup. 받은 USD의 root path가 `/Root/dingo/base_link`이라 자동 attach 안 됨 → 카메라는 `/World` fallback (World 원점). 향후 prim path 발견 로직 개선 필요
- 실기 검증 미완 — GUI에서 시나리오 C 전체 흐름 확인 대기
- volume 추정값 0.025 m³ — 실제 mesh 충진율은 다를 수 있음. RUN 후 동작 보고 `--volume`으로 재튜닝 필요할 수 있음
- v0.2.x 이전 알려진 이슈 그대로 유지

## [0.3.0] - 2026-05-19

### 변경사항
- **부력/항력/지면효과/AddedMass ext 통합** — 매 physics step 자동 적용
  - `physics_applier.py` 신설 — stage 순회 + `aquasweep:volume` 가진 rigid body 자동 발견
  - buoyancy/drag/ground_effect 모듈은 옛 `water_tank_env/` 패키지에서 sys.path 주입으로 import
  - per-body 상태 캐시(prev_velocity, AddedMass, Drag 인스턴스)
- `scenario.py`에 WaterPhysicsApplier 통합
  - `setup_scenario(stage=...)`에서 LOAD 시 한 번 discover_bodies
  - `update_scenario(step)`에서 매 step `apply(dt)`
- `scene_builders.build_jetbot_mock`에 PhysX 통합 (검증용 baseline)
  - `RigidBodyAPI` + `CollisionAPI` + `MassAPI(2.0kg)`
  - `aquasweep:volume`(0.0032 m³), `aquasweep:half_height`(0.05 m) custom attr
  - ρV/m ≈ 1.6 → 부력 작용 시 수면으로 떠올라 시각 검증 가능

### 사용 가이드 (지명님 / 로봇 USD 작성자용)
USD에 다음 custom attribute를 박으면 환경 ext가 자동으로 부력/항력 적용:

| 키 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| `aquasweep:volume` | float | ✅ | — | 로봇 부피 (m³). 부력 계산용 |
| `aquasweep:half_height` | float | ❌ | 0.15 | 로봇 반높이 (m). 부분 잠김 보간용 |
| `aquasweep:cd_linear` | float | ❌ | 10.0 | 선형 항력 계수 |
| `aquasweep:cd_angular` | float | ❌ | 5.0 | 회전 항력 계수 |
| `aquasweep:added_mass` | float | ❌ | 0.5 | 추가질량 계수 |

prim에 `UsdPhysics.RigidBodyAPI`도 같이 박혀있어야 작동.

### 현재 구현 단계
- 환경 ext가 water 안 rigid body에 부력/항력 자동 적용 가능
- JetbotMock으로 시각 검증 가능 (RUN → 떠오르는지 확인)
- 진짜 로봇은 USD에 `aquasweep:volume` 박혀있어야 동작

### 알려진 이슈 / 미완
- 실기 검증 미완 — GUI에서 LOAD → RUN 으로 JetbotMock이 떠오르는지 확인 대기
- `Buoyancy` 클래스가 내부 half-height를 하드코딩(0.15)해서 `_compute_buoyancy` 헬퍼로 wrap. 원본 모듈 수정하지 않음
- physics_applier는 LOAD 시점에 한 번 discover. RUN 중 stage에 prim 추가/제거 시 재 LOAD 필요
- v0.2.x 이전 알려진 이슈 그대로 유지

## [0.2.2] - 2026-05-19

### 변경사항
- 옛 ROS2 standalone 패키지(`water_tank_env/water_tank_env/`)에서 ext가 대체한 파일 제거:
  - `physics.py` (새 buoyancy/drag/ground_effect 모듈이 대체)
  - `test_water.py` (구버전 `omni.isaac.core` API + 외부 path 하드코딩, dead code)
  - `build_scene.py` (ext의 `scene_builders.py` procedural rebuild가 대체)
  - `run_oceansim.py`, `run_oceansim.sh` (ext의 LOAD/RUN이 대체)
  - `oceansim_camera.py`, `oceansim_configs/*.yaml`, `params.py` (모두 ext 안에 동일/대체본 존재)
- 옛 패키지에 남은 자산: `buoyancy.py`, `drag.py`, `ground_effect.py` (팀원 제공, ext 통합 예정) + ROS2 메타(`package.xml`, `setup.py` 등)

### 현재 구현 단계
- 코드 트리에서 dead code 정리 완료 (보수적 시나리오 — Tier 2 standalone 러너만 삭제)
- ROS2 패키지 메타는 향후 ROS2 노드 추가 가능성 고려해 유지

### 알려진 이슈 / 미완
- 부력/항력 모듈 ext 통합 미완 — `Episode`/scenario에 매 step callback 등록 필요
- `src/assets/scenes/water_tank.usd` 재생성 도구(`build_scene.py`) 삭제됨 → 향후 필요 시 ext의 `scene_builders.py`를 standalone에서 호출하는 짧은 스크립트로 재생성
- v0.2.x 이전 알려진 이슈 그대로 유지

## [0.2.1] - 2026-05-19

### 변경사항
- `src/assets/` 공유 자산 폴더 신설 (git tracking)
  - `src/assets/robots/underwater_robot_v1.usd` — 팀원 제공 로봇 USD (지명님 ext의 NVIDIA Jetbot 교체용)
  - `src/assets/scenes/water_tank.usd` — 기존 `~/water_ws/scenes/`에서 이동
- `build_scene.py`의 `USD_OUTPUT_PATH`를 새 경로(`src/assets/scenes/`)로 갱신

### 현재 구현 단계
- 로봇 USD가 git 추적 영역에 들어와 팀 공유 가능
- 지명님 ext에서 path만 새 위치로 교체하면 로봇 USD 사용 가능 (지명님 영역 작업)

### 알려진 이슈 / 미완
- 지명님 ext(`underwater_robot_ext/.../ui_builder.py:174-178`)의 NVIDIA Jetbot path 교체 미완 — 지명님 브랜치에서 처리 필요
- USD 파일 크기 증가 시 git LFS 도입 고려 필요 (현재는 일반 add)
- v0.2.0의 알려진 이슈는 모두 그대로 유지 (실기 검증, RectLight 방향 등)

## [0.2.0] - 2026-05-19

### 변경사항
- `_setup_scene`에서 `create_new_stage()` 제거 — `underwater.robot` extension과 stage 공유 가능 (우리 LOAD가 양보)
- `/World/Jetbot` 존재 시 `JetbotMock` 빌드 skip, camera prim path 동적 선택 (`/World/Jetbot/Camera_Sensor` vs `/World/JetbotMock/Camera_Sensor`)
- 모든 scene 빌드 함수(`add_lighting`, `build_tank`, `build_water`, `build_jetbot_mock`)에 idempotent skip 추가 — 재 LOAD 시 `AddRotateXYZOp` 등 충돌 없음
- Turbidity 드롭다운 버그 수정 — 존재하지 않는 `set_populate_fn_to_scroll_for_all_items()` 호출 제거
- Turbidity 변경 시 자동으로 UW_Camera 재생성 (RUN 상태 보존, RESET 불필요)
- Water material 색조 변경: `(0.18, 0.45, 0.65)` 푸른빛 → `(0.10, 0.50, 0.40)` 양식장 청록, opacity 0.30 → 0.35
- Lighting 보강: 단일 DistantLight → `/World/Lighting` 그룹 아래 3종 세트
  - `Sun` (DistantLight, 차가운 흰빛 #E8F4FF, intensity 800)
  - `CeilingLight` (RectLight 2.5×2.5m, #E8F4FF, intensity 5000, 천장 z=3.0)
  - `UnderwaterAccent` (SphereLight, 청록 #00CFAA, intensity 300, 수중 z=0.3)
- Turbidity yaml 9-float 재튠: 양식장 청록(#00A86B) 톤 + 거리 갭 확대 (atten_coeff R 채널 강화)

### 현재 구현 단계
- water.tank.env extension: LOAD / RUN-STOP / RESET / Turbidity 즉시 적용 모두 동작
- underwater.robot과 stage 공유 가능 (워크플로우: 지명님 LOAD → 우리 LOAD)
- 양식장 분위기 1차 적용 (water teal tint + 실내 양식장 조명 컨셉)
- 카메라가 진짜 JetBot 아래에 자동 attach (지명님 ext 공동 활성화 시)

### 알려진 이슈 / 미완
- 반대 순서 LOAD(우리 → 지명님) 시 지명님 코드의 `create_new_stage()`가 우리 prim wipe — 운영적으로 "지명님 먼저 LOAD" 권장
- OceanSim 5.1-rc 호환성: 가끔 `omni.graph.image.core` scheduler에서 segfault (Isaac Sim 5.1-rc.19 vs OceanSim 4.5 타깃 차이)
- UsdLux.RectLight emission 방향이 USD 빌드에 따라 +Z일 수 있음 — 천장 light가 위로 비추면 회전 추가 필요 (실기 확인 대기)
- 원통 수조 3개 정삼각형 배치 미완 (현재 1개만)
- 실기 검증 미완: LOAD→RUN→Turbidity 토글 전체 플로우 사용자 GUI 확인 대기

## [0.1.0] - 2026-05-18
- Initial extension: cylindrical water-tank scene + OceanSim UW_Camera scenario.
