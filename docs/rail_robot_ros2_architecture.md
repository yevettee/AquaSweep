# Rail Robot ROS2 통신 아키텍처

원형 레일 협동로봇 (`rail_robot_ext/`)의 Isaac Sim + ROS2 통신 구조 설계 문서입니다.

---

## 1. 접근법 비교

### 방법 1: OmniGraph Action Graph API (단순함)

Isaac Sim의 내장 ROS2 브릿지 노드를 사용하여 **코드 없이 GUI로 설정** 가능합니다.

| 장점 | 단점 |
|------|------|
| 코드 최소화 (노드 연결만 하면 됨) | Custom message (aqua_interfaces) 지원 제한 |
| Isaac Sim 물리 타이밍과 자동 동기화 | 복잡한 로직은 Python 노드 추가 필요 |
| GUI에서 시각적으로 데이터 흐름 확인 가능 | |

### 방법 2: Pure Python rclpy (현재 프로젝트 패턴)

기존 `underwater_robot_ext`와 동일한 패턴입니다.

| 장점 | 단점 |
|------|------|
| aqua_interfaces 커스텀 메시지 완벽 지원 | 더 많은 코드 작성 필요 |
| 기존 코드와 일관성 유지 | 스레드 관리 필요 |
| 복잡한 로직 구현 용이 | |

### 권장: 하이브리드 (Action Graph + Python)

**단순한 것은 Action Graph**, **복잡한 것은 Python**으로 분리합니다.

---

## 2. Action Graph 구조

```
/World/Pools/Pool_1/RailRobot_1/ActionGraph
├── OnPlaybackTick (Trigger)
│
├── ROS2 Context (ROS2ContextNode)
│
├── [Joint State Publisher] ─────────────────────────
│   ├── Articulation State (OgnIsaacArticulationState)
│   │   └── Joint names, positions, velocities
│   └── ROS2 Publish Joint State (OgnROS2PublishJointState)
│       └── Topic: /rail_robot_1/joint_states
│
├── [Joint Command Subscriber] ──────────────────────
│   ├── ROS2 Subscribe Joint State (OgnROS2SubscribeJointState)
│   │   └── Topic: /rail_robot_1/joint_commands
│   └── Articulation Controller (OgnIsaacArticulationController)
│       └── 7축 (rail + 6DOF) 제어
│
└── [Transform Publisher] ───────────────────────────
    ├── Isaac Read Prim (위치/자세 읽기)
    └── ROS2 Publish Transform (OgnROS2PublishTransformTree)
        └── Frame: rail_robot_1/base_link
```

---

## 3. 파일 구조

```
rail_robot_ext/
├── config/
│   └── extension.toml
├── data/
│   └── rail_cobot.usda          # 7축 로봇 USD (Revolute + 6DOF)
├── docs/
│   └── README.md
└── rail_robot_python/
    ├── __init__.py
    ├── extension.py
    ├── ui_builder.py
    ├── global_variables.py
    ├── scenario.py              # 레일 이동 + 암 제어 로직
    ├── joint_state_bridge.py    # ROS2 joint state pub/sub
    └── action_graph_builder.py  # OG 노드 프로그래밍 생성
```

---

## 4. ROS2 토픽 설계

| Topic | Direction | Message Type | 내용 |
|-------|-----------|--------------|------|
| `/rail_robot_1/joint_states` | Publish | `sensor_msgs/JointState` | 7축 현재 상태 |
| `/rail_robot_1/joint_commands` | Subscribe | `sensor_msgs/JointState` | 7축 목표 위치 |
| `/rail_robot_1/status` | Publish | `aqua_interfaces/RobotStatus` | 로봇 상태 |
| `/rail_robot_1/rail_angle` | Publish | `std_msgs/Float64` | 레일 각도 (rad) |

---

## 5. 핵심 코드

### 5.1 Action Graph Builder (GUI 없이 프로그래밍 방식)

```python
# action_graph_builder.py
"""Action Graph를 코드로 생성하여 ROS2 브릿지 설정."""

import omni.graph.core as og
from omni.isaac.core_nodes import IsaacCoreNodesExtension


def create_rail_robot_action_graph(
    robot_prim_path: str,
    robot_name: str = "rail_robot_1",
    graph_path: str = None,
) -> og.Graph:
    """레일 로봇용 ROS2 Action Graph 생성.
    
    Args:
        robot_prim_path: 로봇 Articulation root prim 경로
        robot_name: ROS2 토픽 prefix
        graph_path: Action Graph prim 경로 (None이면 자동 생성)
    
    Returns:
        생성된 OmniGraph
    """
    if graph_path is None:
        graph_path = f"{robot_prim_path}/ActionGraph"
    
    # Action Graph 생성
    keys = og.Controller.Keys
    (graph, nodes, _, _) = og.Controller.edit(
        {"graph_path": graph_path, "evaluator_name": "execution"},
        {
            keys.CREATE_NODES: [
                ("OnPlaybackTick", "omni.graph.action.OnPlaybackTick"),
                ("ROS2Context", "omni.isaac.ros2_bridge.ROS2Context"),
                
                # Joint State Publisher
                ("ArticulationState", "omni.isaac.core_nodes.IsaacArticulationState"),
                ("JointStatePub", "omni.isaac.ros2_bridge.ROS2PublishJointState"),
                
                # Joint Command Subscriber
                ("JointStateSub", "omni.isaac.ros2_bridge.ROS2SubscribeJointState"),
                ("ArticulationController", "omni.isaac.core_nodes.IsaacArticulationController"),
            ],
            keys.SET_VALUES: [
                # Articulation 대상 설정
                ("ArticulationState.inputs:robotPath", robot_prim_path),
                ("ArticulationController.inputs:robotPath", robot_prim_path),
                
                # 토픽 이름 설정
                ("JointStatePub.inputs:topicName", f"/{robot_name}/joint_states"),
                ("JointStateSub.inputs:topicName", f"/{robot_name}/joint_commands"),
                
                # 7축 조인트 이름 (예시)
                ("ArticulationController.inputs:jointNames", [
                    "rail_revolute",       # 레일 회전 (7축)
                    "shoulder_pan_joint",  # 6축 암
                    "shoulder_lift_joint",
                    "elbow_joint",
                    "wrist_1_joint",
                    "wrist_2_joint",
                    "wrist_3_joint",
                ]),
            ],
            keys.CONNECT: [
                # 실행 흐름
                ("OnPlaybackTick.outputs:tick", "ArticulationState.inputs:execIn"),
                ("OnPlaybackTick.outputs:tick", "JointStateSub.inputs:execIn"),
                
                # Joint State Publish
                ("ArticulationState.outputs:jointNames", "JointStatePub.inputs:jointNames"),
                ("ArticulationState.outputs:jointPositions", "JointStatePub.inputs:jointPositions"),
                ("ArticulationState.outputs:jointVelocities", "JointStatePub.inputs:jointVelocities"),
                ("ArticulationState.outputs:execOut", "JointStatePub.inputs:execIn"),
                
                # Joint Command → Controller
                ("JointStateSub.outputs:jointNames", "ArticulationController.inputs:jointNames"),
                ("JointStateSub.outputs:jointPositions", "ArticulationController.inputs:positionCommand"),
                ("JointStateSub.outputs:execOut", "ArticulationController.inputs:execIn"),
                
                # ROS2 Context 공유
                ("ROS2Context.outputs:context", "JointStatePub.inputs:context"),
                ("ROS2Context.outputs:context", "JointStateSub.inputs:context"),
            ],
        },
    )
    
    return graph
```

### 5.2 Pure Python ROS2 Bridge (커스텀 메시지용)

```python
# joint_state_bridge.py
"""Pure Python ROS2 bridge for rail robot - custom messages + joint states."""

from __future__ import annotations

import math
import threading
from typing import Optional, Tuple

_RailRobotBridge = None


def _ensure_bridge_class() -> bool:
    global _RailRobotBridge
    
    if _RailRobotBridge is not None:
        return True
    
    try:
        from geometry_msgs.msg import Twist
        from sensor_msgs.msg import JointState
        from std_msgs.msg import Float64
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
        
        # aqua_interfaces 커스텀 메시지
        from aqua_interfaces.msg import RobotStatus
        
        _qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
        )
        
        class RailRobotBridge(Node):
            """레일 로봇 ROS2 브릿지 - Pub/Sub 통합."""
            
            def __init__(self, robot_name: str = "rail_robot_1"):
                super().__init__(f"{robot_name}_bridge")
                self._lock = threading.Lock()
                self._robot_name = robot_name
                
                # === 상태 저장 ===
                self._target_positions = [0.0] * 7  # 7축 목표
                self._current_positions = [0.0] * 7
                self._current_velocities = [0.0] * 7
                
                # === Publishers ===
                self._joint_state_pub = self.create_publisher(
                    JointState, f"/{robot_name}/joint_states", 10
                )
                self._rail_angle_pub = self.create_publisher(
                    Float64, f"/{robot_name}/rail_angle", 10
                )
                self._status_pub = self.create_publisher(
                    RobotStatus, f"/{robot_name}/status", 10
                )
                
                # === Subscribers ===
                self._joint_cmd_sub = self.create_subscription(
                    JointState,
                    f"/{robot_name}/joint_commands",
                    self._on_joint_command,
                    _qos,
                )
                
                self._joint_names = [
                    "rail_revolute",
                    "shoulder_pan_joint",
                    "shoulder_lift_joint", 
                    "elbow_joint",
                    "wrist_1_joint",
                    "wrist_2_joint",
                    "wrist_3_joint",
                ]
                
                self.get_logger().info(f"RailRobotBridge started for {robot_name}")
            
            def _on_joint_command(self, msg: JointState) -> None:
                """외부에서 받은 joint 목표값 저장."""
                with self._lock:
                    for i, name in enumerate(msg.name):
                        if name in self._joint_names:
                            idx = self._joint_names.index(name)
                            if i < len(msg.position):
                                self._target_positions[idx] = msg.position[i]
            
            def get_target_positions(self) -> list[float]:
                """현재 목표 joint positions 반환 (physics step에서 호출)."""
                with self._lock:
                    return self._target_positions.copy()
            
            def publish_joint_states(
                self,
                positions: list[float],
                velocities: list[float],
            ) -> None:
                """현재 joint 상태 발행 (physics step에서 호출)."""
                with self._lock:
                    self._current_positions = positions
                    self._current_velocities = velocities
                
                msg = JointState()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.name = self._joint_names
                msg.position = positions
                msg.velocity = velocities
                msg.effort = [0.0] * len(positions)
                self._joint_state_pub.publish(msg)
                
                # 레일 각도만 별도 발행
                rail_msg = Float64()
                rail_msg.data = positions[0] if positions else 0.0
                self._rail_angle_pub.publish(rail_msg)
            
            def publish_status(self, state: int, battery: float = 1.0) -> None:
                """로봇 상태 발행."""
                msg = RobotStatus()
                msg.state = state  # 0=IDLE, 1=RUNNING, 2=PAUSED
                msg.battery_level = battery
                msg.collision_force = 0.0
                self._status_pub.publish(msg)
        
        _RailRobotBridge = RailRobotBridge
        return True
    
    except Exception as e:
        print(f"RailRobotBridge import error: {e}")
        return False


def create_rail_robot_bridge(robot_name: str = "rail_robot_1"):
    """브릿지 노드 생성. configure_isaac_ros_env() + rclpy.init() 후 호출."""
    if not _ensure_bridge_class():
        return None
    return _RailRobotBridge(robot_name)
```

### 5.3 Scenario (물리 제어)

```python
# scenario.py
"""레일 로봇 시나리오 - ROS2 명령 수신 → Articulation 제어."""

import math
from typing import Optional, Tuple

import carb
from pxr import UsdPhysics


class RailRobotScenario:
    """Revolute Joint (레일) + 6DOF 암 통합 제어."""
    
    def __init__(self):
        self._articulation = None
        self._bridge = None
        self._joint_names = [
            "rail_revolute",
            "shoulder_pan_joint",
            "shoulder_lift_joint",
            "elbow_joint", 
            "wrist_1_joint",
            "wrist_2_joint",
            "wrist_3_joint",
        ]
    
    def initialize(self, articulation, physics_dt: float):
        """World 로드 후 초기화."""
        self._articulation = articulation
        self._physics_dt = physics_dt
    
    def set_ros_bridge(self, bridge):
        """ROS2 브릿지 연결."""
        self._bridge = bridge
        carb.log_info("[rail_robot] ROS2 bridge attached")
    
    def on_physics_step(self, step_size: float):
        """매 물리 스텝: ROS2 명령 읽기 → 관절 제어 → 상태 발행."""
        if self._articulation is None or self._bridge is None:
            return
        
        # 1. ROS2에서 목표 위치 가져오기
        target_positions = self._bridge.get_target_positions()
        
        # 2. Articulation 제어 (position control)
        self._articulation.set_joint_positions(target_positions)
        
        # 3. 현재 상태 읽기
        current_positions = self._articulation.get_joint_positions().tolist()
        current_velocities = self._articulation.get_joint_velocities().tolist()
        
        # 4. ROS2로 상태 발행
        self._bridge.publish_joint_states(current_positions, current_velocities)
        self._bridge.publish_status(state=1)  # RUNNING
    
    def get_rail_angle(self) -> float:
        """현재 레일 각도 (rad) 반환."""
        if self._articulation is None:
            return 0.0
        positions = self._articulation.get_joint_positions()
        return float(positions[0]) if len(positions) > 0 else 0.0
```

---

## 6. 통신 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                         ROS2 Network                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ aqua_planner │    │aqua_controller│   │ aqua_dashboard│       │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  /pool_1/clean_wall   /rail_robot_1/    /rail_robot_1/          │
│    (Action)           joint_commands     status                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Isaac Sim                                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                  rail_robot_ext                          │    │
│  │                                                          │    │
│  │  ┌──────────────┐      ┌──────────────────────────┐     │    │
│  │  │ ROS2 Bridge  │◄────►│    RailRobotScenario     │     │    │
│  │  │ (rclpy node) │      │                          │     │    │
│  │  │              │      │  ┌────────────────────┐  │     │    │
│  │  │ Sub:         │      │  │   Articulation     │  │     │    │
│  │  │  joint_cmds ─┼─────►│  │  ┌──────────────┐  │  │     │    │
│  │  │              │      │  │  │rail_revolute │  │  │     │    │
│  │  │ Pub:         │      │  │  │  (7th axis)  │  │  │     │    │
│  │  │  joint_states│◄─────┼──│  └──────────────┘  │  │     │    │
│  │  │  rail_angle  │      │  │  ┌──────────────┐  │  │     │    │
│  │  │  status      │      │  │  │ 6-DOF Cobot  │  │  │     │    │
│  │  └──────────────┘      │  │  │ (UR10e etc)  │  │  │     │    │
│  │                        │  │  └──────────────┘  │  │     │    │
│  │                        │  └────────────────────┘  │     │    │
│  │                        └──────────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  /World/Pools/Pool_1/RailRobot_1                                │
│      └─ RevoluteJoint (rail_revolute)                           │
│          └─ Carriage                                            │
│              └─ Cobot (Articulation Root)                       │
│                  └─ 6 joints (shoulder...wrist)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. 구성요소별 권장 방법

| 구성요소 | 방법 | 이유 |
|---------|------|------|
| **Joint State Pub/Sub** | Action Graph 또는 Python | 표준 메시지, 양쪽 다 가능 |
| **Custom 메시지 (RobotStatus 등)** | Pure Python (rclpy) | aqua_interfaces 지원 필요 |
| **복잡한 로직 (청소 궤적 등)** | Python Scenario | 코드로 제어 필요 |
| **물리 제어** | `Articulation.set_joint_positions()` | Isaac Sim API |

---

## 8. USD Prim 구조 (Revolute Joint 기반)

```
/World/Pools/Pool_1
    /CircularRail              ← 빈 Xform (수조 중심에 위치)
        └─ RevoluteJoint       ← Z축 회전 (7축 역할)
            └─ /Carriage       ← 레일 위 이동체
                └─ /Cobot      ← 6축 협동로봇 (UR10e URDF/USD)
                    └─ /EndEffector (청소 도구)
```

### Revolute Joint 설정 코드

```python
from pxr import UsdPhysics, Gf

# Tank center와 carriage 선택 후
joint = UsdPhysics.RevoluteJoint.Define(stage, "/World/Pools/Pool_1/CircularRailJoint")
joint.CreateBody0Rel().SetTargets(["/World/Pools/Pool_1/Center"])
joint.CreateBody1Rel().SetTargets(["/World/Pools/Pool_1/RailCarriage"])
joint.CreateAxisAttr("Z")

# Angular Drive 추가 (위치 제어)
drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
drive.CreateDampingAttr().Set(10000.0)
drive.CreateStiffnessAttr().Set(100000.0)
drive.CreateTargetPositionAttr().Set(0.0)  # 각도 목표값 (degrees)
```

---

## 참고 자료

- [Isaac Sim ROS2 Bridge](https://docs.isaacsim.omniverse.nvidia.com/latest/ros2_tutorials/ros2_bridge.html)
- [OmniGraph Action Graph](https://docs.isaacsim.omniverse.nvidia.com/latest/omnigraph/index.html)
- [Articulation Controller](https://docs.isaacsim.omniverse.nvidia.com/latest/robot_setup_tutorials/tutorial_gui_simple_robot.html)
- 기존 코드: `underwater_robot_ext/underwater_robot_python/cmd_vel_receiver.py`
- 기존 코드: `dashboard_ext/ui_dashboard_python/ros_bridge.py`

---

*문서 작성일: 2026-05-22*
