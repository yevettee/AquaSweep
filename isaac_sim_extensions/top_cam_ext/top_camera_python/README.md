# Top Camera Extension (top_cam_ext)

AquaSweep 시뮬레이션 환경의 상부 카메라 이미지를 ROS2로 퍼블리싱하는 Isaac Sim 확장입니다.

## 사용법

Isaac Sim 실행 시 다음 플래그 사용:
```bash
--ext-folder {path_to_ext_folder} --enable top.camera
```

또는 Isaac Sim 내 Extensions 창에서 `top.camera` 검색 후 활성화.

## 파일 구조

### 핵심 파일

| 파일 | 설명 |
|------|------|
| `extension.py` | Isaac Sim 확장 진입점. 툴바 메뉴, 윈도우 생성, 라이프사이클 관리 |
| `ui_builder.py` | UI 패널 구성 및 버튼 핸들러. 카메라 탐색, 그래프 빌드/중지 |
| `global_variables.py` | 확장 설정값 (토픽명, 해상도, 카메라 필터 등) |
| `camera_discovery.py` | Stage에서 TopCamera 프림 탐색 (per-pool + global) |
| `ros_graph_builder.py` | OmniGraph 생성/해제. ROS2 Image 퍼블리싱 설정 |

### 스크립트 파일 (Script Editor용)

| 파일 | 설명 |
|------|------|
| `collect_yolo_standalone.py` | YOLO 학습용 데이터셋 수집 스크립트. Replicator bbox annotator 사용. Script Editor에서 직접 실행 가능 |
| `debug_bbox_annotator.py` | Replicator bbox annotator 디버그용. 여러 semantic labeling 방식 테스트 |

## UI 기능

### 1. Top Cameras
- **Discover cameras**: Stage에서 `/World/Pools/Pool_N/TopCamera` 탐색

### 2. Global Camera (권장)
- **Build global camera graph**: `/World/GlobalTopCamera` → `/global/top_img_raw` (1920x1440)
- 단일 카메라로 전체 풀 촬영. GPU 렌더 패스 86% 절감

### 3. Per-Pool Publishing
- Pool 1~7 개별 선택 가능
- **Build selected cameras**: 선택된 풀 카메라 → `/pool_N/top_img_raw` (640x480)

## ROS2 토픽

| 토픽 | 메시지 타입 | 해상도 |
|------|------------|--------|
| `/global/top_img_raw` | `sensor_msgs/Image` | 1920x1440 |
| `/pool_N/top_img_raw` | `sensor_msgs/Image` | 640x480 |

## YOLO 데이터셋 수집

Script Editor에서 `collect_yolo_standalone.py` 실행:

```python
exec(open("/path/to/collect_yolo_standalone.py").read())
```

설정값은 파일 상단의 `CONFIG` 섹션에서 수정:
- `OUTPUT_DIR`: 출력 디렉토리
- `NUM_FRAMES`: 수집할 프레임 수
- `POOLS_TO_COLLECT`: 수집할 풀 ID 목록

## Fish Status Classification (Suspicious vs Alive)

YOLO는 물고기 **bbox 감지**만 담당. 상태 분류(suspicious/alive)는 `SimpleFishStatusClassifier`에서 수행.

### 분류 로직 (OpenCV 기반)

| 피처 | Weight | Threshold | 의미 |
|------|--------|-----------|------|
| **bg_contrast** | 40% | > 30.0 | 배경(물)과 밝기 차이 |
| **water_similarity** | 25% | < 0.3 | 물색 유사 픽셀 비율 |
| **HSV bimodal** | 15% | value_std > 40 or sat_std > 30 | 색상 분산 |
| **velocity** | 20% | < 0.02 | 상대 속도 |

> Score > 0.5 → **suspicious**, ≤ 0.5 → **alive**

### Contrast 계산 (OpenCV)

```python
# 1. HSV 변환
hsv = cv2.cvtColor(fish_image, cv2.COLOR_BGR2HSV)
fish_v = np.mean(hsv[:, :, 2])  # V = brightness

# 2. 배경 영역 HSV 평균 (bbox 주변 margin)
bg_hsv = cv2.cvtColor(bg_region, cv2.COLOR_BGR2HSV)
bg_v = np.mean(bg_hsv[:, :, 2][mask])  # fish 영역 제외

# 3. Contrast = |fish_v - bg_v|
bg_contrast = abs(fish_v - bg_v)
```

### 왜 Contrast가 핵심인가?

- **Alive**: 물속에 있어 물과 색상이 비슷 → 낮은 contrast
- **Suspicious (죽음/병)**: 수면에 떠서 푸른 물과 대비가 큼 → 높은 contrast

### 설정 파일

파라미터는 `fish_detection_params.yaml`에서 수정:

```yaml
classifier:
  contrast_threshold: 30.0
  water_similarity_threshold: 0.3
  value_std_threshold: 40.0
  saturation_std_threshold: 30.0
  velocity_threshold: 0.02
  velocity_weight: 0.20
```
