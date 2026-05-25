# AquaSweep 최근 업데이트 (2026년 5월)

## 개요

이 문서는 최근 주요 변경사항을 정리합니다. 각 변경사항의 상세 내용은 해당 섹션을 참조하세요.

---

## 1. Fish Detection Node - YOLO 기반으로 교체

### 변경 내용
- 기존 OpenCV 기반 탐지에서 **YOLOv8 학습 모델** 기반으로 전환
- 다중 detector 지원: `yolo`, `opencv`, `sam2`, `yoloworld`
- Global camera 모드 지원으로 성능 최적화 (렌더패스 7개 → 1개)

### 주요 파일
- `water_ws/src/aqua_detection/aqua_detection/fish_detection_node.py`
- `water_ws/src/aqua_detection/aqua_detection/fish_detectors/`
  - `fish_yolo_detector.py` (권장)
  - `fish_opencv_detector.py`
  - `fish_sam2_detector.py`

### 사용법

```bash
# YOLO 모드 (권장)
ros2 run aqua_detection fish_detection_node --ros-args \
    --params-file src/aqua_detection/config/fish_detection_params.yaml

# 명시적 파라미터 지정
ros2 run aqua_detection fish_detection_node --ros-args \
    -p detector_type:=yolo \
    -p use_global_camera:=true
```

### 토픽
| 모드 | 입력 | 출력 |
|------|------|------|
| Global | `/global/top_img_raw` (2560x1920) | `/pool_N/status`, `/pool_N/top_img_det` |
| Per-Pool | `/pool_N/top_img_raw` (640x480) | `/pool_N/status`, `/pool_N/top_img_det` |

> **상세 문서**: `water_ws/src/aqua_detection/README.md`

---

## 2. AquaSweep Extension - LOAD/RUN/RESUME 기능 추가

### 변경 내용
Isaac Sim의 `aquasweep_ext` UI에서 시뮬레이션 제어 기능이 강화되었습니다.

#### World Controls
- **LOAD**: 씬 로드 (수조, 로봇, 철갑상어, 카메라 등)
- **RUN/STOP**: 시뮬레이션 시작/정지 (타임라인 play/pause)
- **RESET**: 시나리오 초기화

#### Sturgeon Animation
- **RESUME/PAUSE** 토글 버튼
- 청소 작업 시 성능 최적화를 위해 애니메이션 일시정지 가능
- ROS2 서비스로도 제어 가능:
  - `/sturgeon/pause`
  - `/sturgeon/resume`

#### Robot Activation
- **Pool 1~7** 개별 활성화/비활성화 토글
- 각 로봇의 ActionGraph를 필요 시에만 생성하여 성능 최적화
- ROS2 서비스로도 제어 가능:
  - `/{pool_id}/activate_robot`
  - `/{pool_id}/deactivate_robot`

#### Top Camera
- **START/STOP PUBLISHING** 토글
- Per-pool 카메라 토픽 발행 제어

### 주요 파일
- `isaac_sim_extensions/aquasweep_ext/aquasweep_python/ui_builder.py`
- `isaac_sim_extensions/aquasweep_ext/aquasweep_python/sturgeon_animation_service.py`
- `isaac_sim_extensions/aquasweep_ext/aquasweep_python/robot_activation_service.py`

### ROS2 Services 정리

| 서비스 | 타입 | 설명 |
|--------|------|------|
| `/sturgeon/pause` | `std_srvs/srv/Trigger` | 철갑상어 애니메이션 일시정지 |
| `/sturgeon/resume` | `std_srvs/srv/Trigger` | 철갑상어 애니메이션 재개 |
| `/{pool_id}/activate_robot` | `std_srvs/srv/Trigger` | 로봇 ActionGraph 생성 |
| `/{pool_id}/deactivate_robot` | `std_srvs/srv/Trigger` | 로봇 ActionGraph 제거 |

---

## 3. Dashboard GUI - aqua_dashboard 패키지로 분리

### 변경 내용
기존 Isaac Sim extension 내의 대시보드 기능이 독립 ROS2 패키지로 분리되었습니다.

### 분리 이유
- Isaac Sim의 rclpy 환경과 충돌 방지
- 독립 프로세스로 실행하여 안정성 향상
- PyQt5 기반 GUI 제공

### 패키지 구조
```
water_ws/src/aqua_dashboard/
├── aqua_dashboard/
│   ├── dashboard_node.py    # Headless 노드 (CLI/백엔드용)
│   ├── dashboard_gui.py     # PyQt5 GUI 애플리케이션
│   └── ros_topics.py        # 토픽/서비스 이름 정의
├── package.xml
└── setup.py
```

### 사용법

```bash
# GUI 대시보드 실행
ros2 run aqua_dashboard dashboard_gui

# Headless 노드 (백엔드/테스트용)
ros2 run aqua_dashboard dashboard_node
```

### 기능
- **실시간 모니터링**: 7개 풀 상태 (물고기 수, 오염도)
- **로봇 상태**: 배터리, 작업 상태 (IDLE/RUNNING/PAUSED/DISCHARGED)
- **카메라 피드**: Top/Under 카메라 이미지 표시
- **제어 버튼**:
  - 전체 시작: `/planner/start`
  - 개별 풀 시작: `/{pool_id}/start_clean_floor`
  - 일시정지: `/planner/pause`

### 구독 토픽
- `/pool_{id}/status` (PoolStatus)
- `/under_robot_{id}/status` (RobotStatus)
- `/pool_{id}/top_img_det` (Image)
- `/pool_{id}/under_img_det` (Image)

---

## 4. Planner Node - 자동 Sturgeon/Robot 제어 로직 추가

### 변경 내용
`/planner/start` 서비스 호출 시 자동으로:
1. **Sturgeon 애니메이션 일시정지** (`/sturgeon/pause`) - 성능 최적화
2. **대상 풀의 로봇 활성화** (`/{pool_id}/activate_robot`)
3. 청소 작업 완료 후 **Sturgeon 애니메이션 재개** (`/sturgeon/resume`)

### 플로우

```
/planner/start 호출
    ├─ fish_count == 0 인 풀만 선택
    ├─ /sturgeon/pause 호출 (최초 1회)
    ├─ 각 eligible pool에 대해:
    │   ├─ /{pool_id}/activate_robot 호출
    │   └─ CleanFloor action 전송
    └─ 모든 작업 완료 시:
        └─ /sturgeon/resume 호출
```

### 주요 파일
- `water_ws/src/aqua_planner/aqua_planner/planner_node.py`

### 서비스 클라이언트
Planner 노드가 호출하는 서비스:
- `/sturgeon/pause`, `/sturgeon/resume`
- `/{pool_id}/activate_robot`, `/{pool_id}/deactivate_robot`

### 제공 서비스
- `/planner/start` - fish_count == 0인 모든 풀 청소 시작
- `/planner/pause` - 모든 진행 중인 작업 취소
- `/{pool_id}/start_clean_floor` - 특정 풀 청소 시작

---

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Isaac Sim                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   aquasweep_ext                              │   │
│  │  ┌─────────────┐  ┌───────────────────┐  ┌───────────────┐  │   │
│  │  │ UI Builder  │  │ SturgeonAnimation │  │    Robot      │  │   │
│  │  │ LOAD/RUN    │  │     Service       │  │  Activation   │  │   │
│  │  │ STOP/RESET  │  │ /sturgeon/pause   │  │   Service     │  │   │
│  │  └─────────────┘  │ /sturgeon/resume  │  │ /pool_N/...   │  │   │
│  │                   └───────────────────┘  └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                         ROS2 Services
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                         ROS2 Nodes                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  aqua_planner │  │ aqua_detect  │  │   aqua_dashboard     │ │
│  │ /planner/start│  │ YOLO/OpenCV  │  │  PyQt5 GUI           │ │
│  │ Auto control  │  │ fish detect  │  │  Pool/Robot monitor  │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

---

## 관련 문서
- [Fish Detection 상세 가이드](../water_ws/src/aqua_detection/README.md)
- [ROS2 Communication Guide](./ROS2%20Communication%20Guide.md)
- [Dashboard/Planner 개발 가이드](./dashboard_planner_dev_guide.md)
