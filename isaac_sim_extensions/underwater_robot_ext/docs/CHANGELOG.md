# Changelog

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
