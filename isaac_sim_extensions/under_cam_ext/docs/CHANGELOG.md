# Changelog

## [1.1.0] - 2026-05-22
### Added
- Discover-and-publish pipeline: stage traversal finds every under-water
  camera (skipping top/realsense/stereo helpers) and groups them by
  pool id parsed from the prim path.
- Single OmniGraph that fans `OnPlaybackTick` out to one
  `IsaacCreateRenderProduct` + `ROS2CameraHelper` per pool, publishing
  raw `sensor_msgs/Image` to `/pool_{N}/under_img_raw`.
- UI panel with Discover / Build / Stop buttons and live status.
- Standalone verification script under `verify/verify_under_cam_pipeline.py`.

### Removed
- NVIDIA scenario template (`scenario.py`).

## [1.0.1] - 2025-01-21
### Changed
- Update extension description and add extension specific test settings


## [0.1.0] - 2026-05-21

### Added

- Initial version of under.camera Extension
