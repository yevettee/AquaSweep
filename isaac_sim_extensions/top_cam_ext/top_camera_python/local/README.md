# Local Script Editor tools (not in git)

Isaac Sim **Window → Script Editor** 에서 `exec(open("...").read())` 로 실행합니다.

| Script | Purpose |
|--------|---------|
| `collect_yolo_obb_standalone.py` | Write OBB dataset to `water_ws/src/aqua_detection/dataset_obb/` |
| `debug_obb_visualization.py` | Single-frame OBB overlay → `aqua_detection/debug_obb_viz.png` |

Paths in each file’s `CONFIGURATION` block can be edited for your machine.
