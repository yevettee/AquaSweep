# 원형 수조 청소용 협동로봇 연구

8m 직경 원형 수조 벽면 청소를 위한 협동로봇 선정 및 Isaac Sim 구현 방안 연구 문서입니다.

## 1. 협동로봇 크기 및 가격대 분석

### 8m 직경 수조 청소를 위한 핵심 고려사항

- **벽면 도달 범위**: 로봇이 레일에 장착되어 수조 가장자리를 따라 이동하므로, 로봇 팔의 reach는 벽면 높이(약 1.5m)를 커버할 수 있으면 충분
- **청소 도구 무게**: 브러시/흡입 장치 등 end-effector 무게 (보통 3-10kg)
- **청소 효율성**: 팔 길이가 길수록 한 위치에서 더 넓은 면적 청소 가능

### 협동로봇 주요 옵션 비교

| 모델 | Reach (도달거리) | Payload | 가격대 (암 단독, 1대) | 적합도 |
|------|-----------------|---------|----------------------|--------|
| **UR5e** | 850mm | 5kg | $30,000–$45,000 | △ 작은 편, 도달거리 부족 |
| **UR10e** | 1,300mm | 12.5kg | $45,000–$60,000 | ◎ 가성비 우수 |
| **UR16e** | 900mm | 16kg | $57,000–$65,000 | △ 무거운 도구용, reach 짧음 |
| **UR20** | 1,750mm | 25kg | $65,000–$85,000 | ◎ 넓은 커버리지 |
| **UR30** | 1,300mm | 35kg | $70,000–$90,000 | △ 고하중 특화 |
| **FANUC CRX-10iA/L** | 1,418mm | 10kg | ~$50,000 | ◎ IP67 방수 우수 |
| **FANUC CRX-20iA/L** | 1,418mm | 20kg | ~$55,000 | ◎ 방수 + 높은 payload |
| **FANUC CRX-30iA** | 1,756mm | 30kg | ~$61,000 | ◎ 가장 긴 reach |
| **Doosan M1013** | 1,300mm | 10kg | $30,000–$40,000 | ○ 저가형 대안 |

### 추천 옵션

#### Option A: 비용 효율형 (UR10e / CRX-10iA/L)

- **도달거리**: ~1.3m → 1.5m 벽면 충분히 커버
- **가격**: $45,000–$55,000/대
- **장점**: 검증된 생태계, 풍부한 부품/지원
- **단점**: 한 위치당 청소 면적 좁음 → 더 많은 이동 필요

#### Option B: 효율 극대화형 (UR20 / CRX-30iA)

- **도달거리**: ~1.75m → 더 넓은 면적 한번에 청소
- **가격**: $65,000–$85,000/대
- **장점**: 적은 이동으로 빠른 청소, 미래 확장성
- **단점**: 초기 비용 높음

#### Option C: 수중환경 최적화 (FANUC CRX-20iA/L)

- **도달거리**: 1,418mm
- **방수 등급**: IP67
- **가격**: ~$55,000/대
- **장점**: 수조 환경에 가장 적합한 방수 등급, 물이 튀거나 습한 환경에서 안정적

### 로봇 크기 표준

협동로봇은 보통 **reach 기준**으로 분류됩니다:

- **소형**: 500–850mm (UR3e, UR5e)
- **중형**: 900–1,400mm (UR10e, UR16e, CRX-10iA/L, CRX-20iA/L)
- **대형**: 1,500mm+ (UR20, CRX-25iA, CRX-30iA)

수조 벽면 높이 1.5m를 고려하면, **중형 (1.3m reach) 이상**이면 충분합니다.

### 추가 비용 고려사항

| 항목 | 예상 비용 |
|------|----------|
| End-of-arm tooling (청소 도구) | $5,000–$15,000 |
| Integration (설치/통합) | $10,000–$35,000 |
| Training (교육) | $2,000–$5,000 |
| Maintenance (3년) | $2,000–$5,000 |
| **3년 TCO (Total Cost of Ownership)** | **$65,000–$100,000** |

---

## 2. Isaac Sim 원형 레일 구현 방법

### 방법 A: Revolute Joint (회전 조인트) - 권장

수조 중심을 기준으로 회전하는 방식입니다.

#### 구조

```
/World
  /Tank_Center (수조 중심 anchor)
    └─ RevoluteJoint (Z축 회전)
        └─ /RailCarriage (캐리지)
            └─ /Cobot_Base
                └─ 6-DOF Arm Joints
```

#### 장점

- 자연스러운 원형 모션
- 레일 경로 자체를 물리 시뮬레이션할 필요 없음
- 각도 제어가 직관적 (0°–360°)

#### 구현 단계

1. 수조 중심에 빈 Xform 생성 (Tank_Center)
2. Tank_Center와 RailCarriage 사이에 **Revolute Joint** 추가
3. Joint의 **Axis = Z** (수직 회전축)
4. Joint에 **Angular Drive** 추가 (position/velocity 제어용)
5. Carriage에 로봇 암 마운트

#### 코드 예시: RevoluteJoint 생성

```python
from pxr import UsdPhysics, Gf

# Tank center와 carriage 선택 후
joint = UsdPhysics.RevoluteJoint.Define(stage, "/World/Tank/CircularRailJoint")
joint.CreateBody0Rel().SetTargets(["/World/Tank/Center"])
joint.CreateBody1Rel().SetTargets(["/World/Tank/RailCarriage"])
joint.CreateAxisAttr("Z")

# Angular Drive 추가 (위치 제어)
drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
drive.CreateDampingAttr().Set(10000.0)
drive.CreateStiffnessAttr().Set(100000.0)
drive.CreateTargetPositionAttr().Set(0.0)  # 각도 목표값 (degrees)
```

### 방법 B: Prismatic Joint (직선 조인트) + 외부 변환

제안받은 7축 prismatic 방식입니다.

#### 구조

- 로봇 베이스에 Prismatic Joint 추가
- 직선 거리를 원형 경로로 매핑

#### 단점

- 원형 레일에는 부자연스러움
- 호(arc) 길이 ↔ 각도 변환 필요
- 물리 시뮬레이션 복잡

### 방법 C: Kinematic Motion (비물리적 애니메이션)

물리 시뮬레이션 없이 Transform 직접 제어:

```python
import math
from pxr import UsdGeom, Gf

def update_carriage_position(stage, time, angular_velocity, tank_radius=4.0):
    """수조 중심 기준 캐리지 회전
    
    Args:
        stage: USD stage
        time: 현재 시뮬레이션 시간 (초)
        angular_velocity: 각속도 (rad/s)
        tank_radius: 수조 반경 (m), 기본값 4.0m
    """
    carriage = stage.GetPrimAtPath("/World/Tank/RailCarriage")
    xf = UsdGeom.Xformable(carriage)
    
    angle = time * angular_velocity  # rad
    
    x = tank_radius * math.cos(angle)
    y = tank_radius * math.sin(angle)
    yaw_deg = math.degrees(angle) + 90  # 로봇이 벽면을 향하도록
    
    xf.AddTranslateOp().Set(Gf.Vec3d(x, y, 0))
    xf.AddRotateZOp().Set(yaw_deg)
```

#### 장점

- 구현 간단
- 레일 물리 시뮬레이션 불필요

#### 단점

- 물리적 상호작용 불가 (충돌 감지 등)
- RL 학습에 사용하려면 Articulation 필요

### 추천 접근법: Revolute Joint + 6-DOF Arm

기존 프로젝트 구조(`params.py`의 `POOL_CENTERS`)를 활용한 구현:

```
/World/Pools/Pool_1
    /CircularRail          ← 빈 Xform (수조 중심에 위치)
        └─ RevoluteJoint   ← Z축 회전 (7축 역할)
            └─ /Carriage   ← 레일 위 이동체
                └─ /Cobot  ← 6축 협동로봇 (UR10e URDF/USD)
                    └─ /EndEffector (청소 도구)
```

이 구조의 장점:

1. RevoluteJoint의 target position을 조절해 캐리지를 수조 둘레로 이동
2. 6축 Cobot이 벽면 위아래로 end-effector 이동
3. Isaac Sim의 Articulation Controller로 모든 7축 동시 제어 가능

---

## 3. 핵심 구성요소 상세 설명

### 3.1 Revolute Joint Prim

#### 정의

**Revolute Joint**는 USD Physics에서 제공하는 **회전 관절**입니다. 두 개의 강체(Rigid Body)를 연결하고, 하나의 축을 중심으로 **회전만 허용**합니다.

#### 역할 (원형 레일 맥락에서)

```
수조 중심 (고정점)
      │
      │  ← Revolute Joint (Z축 회전)
      │
      ▼
   Carriage (회전하는 물체)
```

#### 주요 속성

| 속성 | 설명 |
|------|------|
| **Body0** | 고정된 기준점 (수조 중심) |
| **Body1** | 회전하는 대상 (캐리지) |
| **Axis** | 회전축 (Z = 수직축 → 수평면에서 회전) |
| **Lower/Upper Limit** | 회전 범위 제한 (예: -180° ~ 180°) |
| **Drive** | 모터처럼 목표 각도/속도로 구동 |

#### 실제 동작

- Body0(수조 중심)는 **월드에 고정**
- Body1(캐리지)는 **Z축을 중심으로 회전**
- Angular Drive를 통해 **목표 각도를 설정**하면 물리 엔진이 캐리지를 그 각도로 이동시킴

```python
# 예: 캐리지를 90도 위치로 이동
drive.CreateTargetPositionAttr().Set(90.0)  # degrees
```

#### Revolute vs Prismatic 비교

| Joint 종류 | 움직임 | 원형 레일 적합성 |
|-----------|--------|-----------------|
| **Prismatic** | 직선 이동 | ❌ 원형 경로에 부자연스러움 |
| **Revolute** | 회전 | ✅ 수조 중심 기준 자연스러운 원형 이동 |

---

### 3.2 RailCarriage (레일 캐리지)

#### 정의

**RailCarriage**는 **레일 위를 이동하는 플랫폼/대차**입니다. 로봇 팔(Cobot)을 탑재하고, Revolute Joint에 의해 수조 둘레를 이동합니다.

#### 역할

```
Revolute Joint
      │
      ▼
┌─────────────────┐
│  RailCarriage   │  ← 이동 플랫폼
│  ┌───────────┐  │
│  │   Cobot   │  │  ← 6축 협동로봇 탑재
│  │  (UR10e)  │  │
│  └───────────┘  │
└─────────────────┘
```

#### 기능

| 기능 | 설명 |
|------|------|
| **로봇 탑재** | 협동로봇의 베이스가 캐리지에 고정됨 |
| **위치 이동** | Revolute Joint에 의해 수조 둘레를 이동 |
| **방향 유지** | 항상 수조 벽면을 향하도록 회전 (로봇이 벽을 바라봄) |
| **강체 역할** | 물리 시뮬레이션에서 Rigid Body로 동작 |

#### USD 계층 구조

```
/World/Pools/Pool_1
    /Center                    ← 빈 Xform (수조 중심, 고정)
    /CircularRailJoint         ← Revolute Joint
        Body0: /World/Pools/Pool_1/Center
        Body1: /World/Pools/Pool_1/RailCarriage
    /RailCarriage              ← 이동 플랫폼 (Rigid Body)
        /CobotBase             ← 로봇 베이스
            /shoulder_link
            /upper_arm_link
            /forearm_link
            /wrist_1_link
            /wrist_2_link
            /wrist_3_link
            /EndEffector       ← 청소 도구
```

#### RailCarriage 물리 속성 설정

```python
from pxr import UsdPhysics

carriage_prim = stage.GetPrimAtPath("/World/Pools/Pool_1/RailCarriage")
UsdPhysics.RigidBodyAPI.Apply(carriage_prim)
UsdPhysics.MassAPI.Apply(carriage_prim).CreateMassAttr().Set(50.0)  # 50kg
```

---

### 3.3 전체 동작 흐름

```
1. ROS2에서 목표 각도 수신 (예: 90°)
          │
          ▼
2. Revolute Joint의 Angular Drive에 목표 설정
          │
          ▼
3. 물리 엔진이 RailCarriage를 회전시킴
          │
          ▼
4. RailCarriage 위의 Cobot도 함께 이동
          │
          ▼
5. Cobot이 벽면을 향한 상태로 청소 작업 수행
```

#### 시각적 다이어그램

```
        수조 (8m 직경)
     ╭───────────────╮
    ╱                 ╲
   │     ○ 중심       │
   │      │           │
   │      │ Revolute  │
   │      │ Joint     │
   │      ▼           │
   │   [Carriage]     │  ← 레일 위 이동
   │   ┌─────┐        │
   │   │Robot│───▶벽  │  ← 로봇이 벽면 청소
   │   └─────┘        │
    ╲                 ╱
     ╰───────────────╯
```

#### 구성요소 역할 요약

| 구성요소 | 타입 | 역할 |
|---------|------|------|
| **Center** | Xform (고정) | 회전의 기준점 (수조 중심) |
| **Revolute Joint** | Physics Joint | 두 물체를 연결하고 회전만 허용 |
| **RailCarriage** | Rigid Body | 로봇을 싣고 레일 위를 이동하는 플랫폼 |
| **Cobot** | Articulation | 캐리지 위에서 벽면 청소 수행 |

---

## 4. 요약

| 항목 | 권장 |
|------|------|
| **로봇 모델** | UR10e (가성비) / FANUC CRX-20iA/L (방수) / UR20 (효율) |
| **가격대** | $45,000–$85,000/대 |
| **Isaac Sim 구현** | **Revolute Joint** (수조 중심 기준 Z축 회전) |
| **7축 개념** | Prismatic보다 Revolute가 원형 경로에 자연스러움 |

---

## 5. 7축 레일 시스템 제조사 참고

실제 하드웨어 구현 시 참고할 수 있는 7축 레일 시스템:

| 제조사 | 제품명 | 특징 |
|--------|--------|------|
| **HepcoMotion** | MHD 7th Axis Track System | 원형/직선 혼합 레이아웃 가능, 최대 136kN 하중 |
| **Thomson** | Movotrak CTU | UR 로봇 전용, 최대 10m 연장, 충돌 감지 내장 |
| **Cobotracks** | Linear Motion Kit (LMK) | UR+ 인증, 최대 50m, 플러그앤플레이 |

---

## 참고 자료

- [Universal Robots 제품 사양](https://www.universal-robots.com/products/)
- [FANUC CRX 시리즈](https://www.fanucamerica.com/products/robots/series/collaborative-robot)
- [Isaac Sim Articulation Tutorial](https://docs.isaacsim.omniverse.nvidia.com/latest/robot_setup_tutorials/tutorial_gui_simple_robot.html)
- [HepcoMotion MHD 7th Axis](https://www.hepcomotion.com/product/curved-rails-and-track-system-components/mhd-7th-axis-track-system/)

---

*문서 작성일: 2026-05-22*
