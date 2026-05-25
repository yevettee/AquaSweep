# AquaSweep Fish Detection

ROS2 기반 물고기 탐지 노드. Isaac Sim top camera 이미지를 구독하여 YOLO/OpenCV로 물고기와 이물질을 탐지합니다.

## 빠른 시작

### 1. Isaac Sim 준비

1. Isaac Sim 실행 후 **aquasweep_ext** → LOAD 클릭
2. **top.camera** 확장 열기
3. 카메라 모드 선택 (아래 참고)
4. Play 시작

### 2. Detection Node 실행

```bash
cd ~/AquaSweep/water_ws
source install/setup.bash
```

---

## 카메라 모드

### Global Camera (권장)

**장점**: 1개 렌더패스로 성능 좋음 (7개 → 1개)

**Isaac Sim 설정**:
- top.camera → "Build global camera graph" 클릭

**ROS2 실행**:
```bash
ros2 run aqua_detection fish_detection_node --ros-args \
    --params-file src/aqua_detection/config/fish_detection_params.yaml
```

또는 명시적으로:
```bash
ros2 run aqua_detection fish_detection_node --ros-args \
    -p detector_type:=yolo \
    -p use_global_camera:=true
```

**토픽**:
- 입력: `/global/top_img_raw` (2560x1920)
- 출력: `/pool_N/status`, `/pool_N/top_img_det` (N=1~7)

---

### Per-Pool Camera (개별 풀)

**장점**: 각 풀마다 독립적인 고해상도 이미지

**Isaac Sim 설정**:
- top.camera → 원하는 풀 체크박스 선택
- "Build selected cameras" 클릭

**ROS2 실행**:
```bash
ros2 run aqua_detection fish_detection_node --ros-args \
    --params-file src/aqua_detection/config/fish_detection_params.yaml \
    -p use_global_camera:=false
```

또는:
```bash
ros2 run aqua_detection fish_detection_node --ros-args \
    -p detector_type:=yolo \
    -p use_global_camera:=false
```

**토픽**:
- 입력: `/pool_N/top_img_raw` (640x480, N=1~7)
- 출력: `/pool_N/status`, `/pool_N/top_img_det`

---

## Detector 종류

| detector_type | 설명 | 속도 | 정확도 |
|---------------|------|------|--------|
| `yolo` | YOLOv8 학습 모델 (권장) | 빠름 | 높음 |
| `opencv` | 전통적 CV (adaptive threshold) | 매우 빠름 | 보통 |
| `sam2` | SAM2 zero-shot segmentation | 느림 | 높음 |
| `yoloworld` | YOLO-World open-vocab | 보통 | 보통 |

---

## 주요 파라미터

`config/fish_detection_params.yaml` 참고:

```yaml
fish_detection_node:
  ros__parameters:
    detector_type: "yolo"        # yolo, opencv, sam2, yoloworld
    use_global_camera: true      # true: global, false: per-pool
    num_pools: 7
    debug_visualization: true    # /pool_N/top_img_det 발행
```

---

## 디버깅

### 토픽 확인
```bash
# 이미지 토픽 확인
ros2 topic list | grep img

# 메시지 수신 확인
ros2 topic hz /global/top_img_raw
ros2 topic hz /pool_1/top_img_raw
```

### 디버그 이미지 보기
```bash
# rqt_image_view로 detection 결과 확인
ros2 run rqt_image_view rqt_image_view
# /pool_1/top_img_det 선택
```

### 로그 확인
```bash
# Detection node 로그에서 첫 이미지 수신 확인
# "first image received" 메시지가 나와야 정상
```

---

## 트러블슈팅

### 이미지가 안 들어올 때
1. Isaac Sim이 Play 상태인지 확인
2. `ROS_DOMAIN_ID` 동일한지 확인 (Isaac Sim 시작 전 export 필요)
3. top.camera에서 카메라 그래프가 빌드되었는지 확인

### FPS가 낮을 때
1. Global camera 모드 사용 (렌더패스 86% 감소)
2. `PUBLISH_STEP_INTERVAL` 증가 (`ros_graph_builder.py`)
3. 해상도 낮추기 (`global_variables.py`)

---

## 파일 구조

```
aqua_detection/
├── config/
│   └── fish_detection_params.yaml   # 파라미터 설정
├── aqua_detection/
│   ├── fish_detection_node.py       # 메인 노드
│   └── fish_detectors/
│       ├── fish_yolo_detector.py    # YOLO detector
│       ├── fish_opencv_detector.py  # OpenCV detector
│       └── fish_sam2_detector.py    # SAM2 detector
└── README.md
```
