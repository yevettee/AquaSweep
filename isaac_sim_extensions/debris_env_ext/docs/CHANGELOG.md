# Changelog

## [0.2.2] - 2026-05-27

### 변경사항
- 스폰 풀: `DEBRIS_SPAWN_POOLS` = [1, 2, 3, 6, 7] (`params.py` / `global_variables.py`)
- 풀당 개수: 30~50 (`DEBRIS_COUNT_MAX` 70 → 50)
- `DebrisSystem.pool_counts`: `dict[int, int]` (1-based pool ID)
- `DebrisScenario.pool_counts()` — 읽기 API
- `pool_indices`로 spawn/clear (전체 7풀 enumerate 제거)

## [0.2.1] - 2026-05-24

### 변경사항
- `DEBRIS_RADIUS`: 0.05 → **0.03 m** (직경 10 cm → 6 cm). top camera 시야 기준 픽셀 면적 약 0.36×로 감소

### 후속 검토 필요
- `aqua_detection/top/detection_node.py`의 debris 면적 필터(15 ≤ area ≤ 500 px @ 3× upscale) — radius 0.05 기준이라 0.03에서 하한 조정 필요 가능
- PhysX particle contact_offset/rest_offset이 radius에 비례 자동 적용되므로 별도 튜닝 불필요

## [0.2.0] - 2026-05-22

### 변경사항
- Debris 시각 파라미터 일괄 조정:
  - `DEBRIS_RADIUS`: 0.015 → **0.05 m** (5 cm radius, 10 cm diameter)
  - 풀별 debris 개수: 고정 10 → **random 30~70 per pool** (`rng.integers(lo, hi+1)` 풀마다 추첨)
  - 색상: brown↔black per-particle 랜덤 그라데이션 제거 → **단색 `#221911`** (near-black dark brown, constant interp)
- API 변경 (breaking):
  - `DebrisSystem.__init__(count=int, ...)` → `__init__(count_range=(min,max), ...)`
  - `DebrisScenario.setup_scenario(count=int, ...)` → `setup_scenario(count_range=(min,max), ...)`
  - `global_variables.DEBRIS_COUNT(=10)` 삭제 → `DEBRIS_COUNT_MIN(=30)` / `DEBRIS_COUNT_MAX(=70)`
- UI 갱신: `Count` 단일 IntDrag → `Count Min` / `Count Max` 두 IntDrag
- `_add_particles_at`가 풀별 count를 인자로 받도록 시그니처 변경 (`count: int` 추가)
- `_apply_material_to`의 per-vertex displayColor 생성 로직 → constant interp 단일 Vec3f로 단순화

### 호출자 영향
- `aquasweep_ext/aquasweep_python/ui_builder.py`도 같이 갱신 (Count Min/Max 패널 + `count_range` 호출). 누락 시 `TypeError: unexpected keyword argument 'count'`

### 현재 구현 단계
- 풀당 30~70 debris가 단일 dark-brown 색으로 스폰. 5 cm radius로 시각적으로 또렷
- aquasweep / debris.env 두 ext 모두 새 UI 반영

### 알려진 이슈 / 미완
- Radius 0.05로 키운 만큼 PhysX particle contact_offset/rest_offset 자동 비례(`radius * 1.5/1.0/0.5`)되지만 풀 직경 대비 충돌 거동 미검증 — RUN 후 거동 이상하면 radius 또는 offset 비율 재튜닝 필요
- UI Count Min > Max 입력 시 코드 내부에서 swap만 함 (사용자에게 경고 없음)

## [0.1.0] - 2026-05-19

### Added
- Initial port of DebrisSystem from standalone `water_debris_env` module.
- Isaac Sim Extension framework wrapper (extension.py, ui_builder.py, scenario.py).
- UI controls: debris count, radius, spawn / clear buttons.
- GPU PhysX particle system with configurable parameters.
