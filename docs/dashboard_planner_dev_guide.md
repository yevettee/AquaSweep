# Dashboard & Planner 개발 가이드

> **구현 상태**: ✅ 완료 (2026-05)
> 
> Dashboard GUI가 `aqua_dashboard` 패키지로 분리되어 구현 완료됨.
> Planner에 Sturgeon/Robot 자동 제어 로직 추가됨.

---

## 패키지 구조

```
water_ws/src/
├── aqua_dashboard/           # Dashboard (분리된 패키지)
│   └── aqua_dashboard/
│       ├── dashboard_node.py # Headless 노드
│       ├── dashboard_gui.py  # PyQt5 GUI
│       └── ros_topics.py     # 토픽/서비스 정의
├── aqua_planner/             # Planner
│   └── aqua_planner/
│       ├── planner_node.py   # 메인 노드
│       └── task_executor.py  # Action 클라이언트
```

---

## Dashboard (aqua_dashboard)

### 실행 방법

```bash
# GUI 대시보드 (PyQt5)
ros2 run aqua_dashboard dashboard_gui

# Headless 노드 (CLI/백엔드용)
ros2 run aqua_dashboard dashboard_node
```

### UI 구성

- **상단 헤더**: "AquaSweep" 로고 + 전체 시작 버튼 (`/planner/start`)
- **그리드 레이아웃**: 7개 풀(+로봇) 정보 표시
  - `pool_1` ~ `pool_7`, 각각 `under_robot_1` ~ `under_robot_7`과 세트
- **카메라 피드**: `/pool_{id}/top_img_det`, `/pool_{id}/under_img_det`
- **상태 표시**: 
  - Top cam 아래: `/pool_{id}/status` (fish_count, pollution_level)
  - Under cam 아래: `/under_robot_{id}/status` (state, battery_level)
- **개별 시작 버튼**: `/{pool_id}/start_clean_floor` 서비스 요청

### UI 동작 조건

- 작업 진행 중일 때 전체 시작 버튼 및 해당 풀 개별 버튼 비활성화
- 드롭다운 없이 모든 풀 정보 동시 표시

### 구독 토픽

| 토픽 | 타입 | 설명 |
|------|------|------|
| `/pool_{id}/status` | `PoolStatus` | 풀 상태 (fish_count, pollution_level) |
| `/under_robot_{id}/status` | `RobotStatus` | 로봇 상태 (state, battery_level) |
| `/pool_{id}/top_img_det` | `Image` | Top 카메라 탐지 이미지 |
| `/pool_{id}/under_img_det` | `Image` | Under 카메라 탐지 이미지 |

### 서비스 클라이언트

| 서비스 | 타입 | 설명 |
|--------|------|------|
| `/planner/start` | `Trigger` | 전체 청소 시작 |
| `/planner/pause` | `Trigger` | 전체 청소 일시정지 |
| `/{pool_id}/start_clean_floor` | `Trigger` | 개별 풀 청소 시작 |

---

## Planner (aqua_planner)

### 실행 방법

```bash
ros2 run aqua_planner planner_node
```

### 제공 서비스

| 서비스 | 설명 |
|--------|------|
| `/planner/start` | fish_count == 0인 모든 풀 청소 시작 |
| `/planner/pause` | 모든 진행 중인 작업 취소 |
| `/{pool_id}/start_clean_floor` | 특정 풀 청소 시작 |

### /planner/start 동작 플로우

```
1. 작업 중복 체크 (이미 실행 중이면 거부)
2. /pool_{id}/status 확인 → fish_count == 0인 풀만 선택
3. /sturgeon/pause 호출 (최초 1회, 성능 최적화)
4. 각 eligible pool에 대해:
   a. /{pool_id}/activate_robot 호출 (ActionGraph 생성)
   b. CleanFloor action 전송
5. 모든 작업 완료 시:
   a. /sturgeon/resume 호출 (애니메이션 재개)
```

### Sturgeon 제어 (자동)

청소 작업 시작 시 철갑상어 애니메이션을 자동으로 일시정지하여 GPU/CPU 부하 감소:
- `_call_sturgeon_pause()`: 청소 시작 전 호출
- `_call_sturgeon_resume()`: 모든 청소 완료 후 호출

### Robot Activation (자동)

청소 대상 로봇의 ActionGraph를 필요 시에만 생성:
- `_call_activate_robot(pool_id)`: 청소 시작 전 호출
- ROS2 cmd_vel 토픽 연결이 이때 활성화됨

### 구독 토픽

| 토픽 | 타입 | 설명 |
|------|------|------|
| `/pool_{id}/status` | `PoolStatus` | 청소 가능 여부 판단 (fish_count) |

### 서비스 클라이언트

| 서비스 | 설명 |
|--------|------|
| `/sturgeon/pause` | 철갑상어 애니메이션 정지 |
| `/sturgeon/resume` | 철갑상어 애니메이션 재개 |
| `/{pool_id}/activate_robot` | 로봇 ActionGraph 생성 |
| `/{pool_id}/deactivate_robot` | 로봇 ActionGraph 제거 |

---

## 관련 문서

- [최근 업데이트](./recent_updates.md)
- [ROS2 Communication Guide](./ROS2%20Communication%20Guide.md)