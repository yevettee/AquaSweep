# Changelog

## [1.1.0] - 2026-05-22
### Added
- Discover-and-publish pipeline mirroring under_cam_ext, selecting
  per-pool top-down cameras (positive token filter on "top*camera").
- Single OmniGraph fanning `OnPlaybackTick` to one
  `IsaacCreateRenderProduct` + `ROS2CameraHelper` per pool, publishing
  raw `sensor_msgs/Image` to `/pool_{N}/top_img_raw`.
- UI panel with Discover / Build / Stop buttons and live status.

### Removed
- NVIDIA scenario template (`scenario.py`).

## [1.0.1] - 2025-01-21
### Changed
- Update extension description and add extension specific test settings


## [0.1.0] - 2026-05-21

### Added

- Initial version of top.camera Extension
