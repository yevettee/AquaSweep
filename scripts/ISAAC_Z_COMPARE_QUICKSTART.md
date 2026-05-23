# Isaac Sim — RUN SCENARIO 전후 로봇/바퀴 Z 비교 (빠른 실행)

`compare_z_run_scenario.py`로 **로봇 루트 Z**와 **왼쪽 바퀴 collision Z**(중심·최저점)를 RUN 전후에 찍고 차이를 봅니다.

| 비교 항목 | aquasweep_ext (7 pools) | 단일 pool / 단일 로봇 |
|-----------|-------------------------|------------------------|
| Extension | **AquaSweep** (`aquasweep_ext`) | **underwater.robot** (`underwater_robot_ext`) + 선택: **water.tank.env** |
| LOAD 결과 | Pool_1…7 + `hippo_1`…`hippo_7` | `/World/Hippo` 1대 (또는 Tank만 로드 후 로봇 1대) |
| 스크립트 | 아래 **Case A** | 아래 **Case B** |

---

## 0. Script Editor에 스크립트 올리기 (한 번만)

1. Isaac Sim → **Window → Script Editor**
2. 아래 **단축 로드** 한 줄 실행 (또는 파일 전체 붙여넣기)

```python
exec(open("/home/woody/AquaSweep/scripts/compare_z_run_scenario.py").read())
```

성공 시 콘솔: `[compare_z] loaded. Helpers: snap_before(), ...`

> 경로가 다르면 `open("...")` 안의 절대 경로만 본인 워크스페이스에 맞게 수정하세요.

---

## Case A — aquasweep_ext, **모든 pool** LOAD

### 준비

1. Extension Manager에서 **AquaSweep** (`aquasweep_ext`) Enable
2. AquaSweep 패널 → **LOAD** (7 pools + 7 hippos)
3. Script Editor에서 `exec(open(...compare_z_run_scenario.py).read())` 실행

### RUN 전후 Z 측정 (3단계)

```python
# 1) RUN 누르기 전 (타임라인 정지, LOAD 직후)
snap_before("A: all pools, before RUN")

# 2) UI에서 Run Scenario → RUN, 2~3초 대기 (로봇이 바닥에 안착할 때까지)

# 3) RUN 후
snap_after("A: all pools, after RUN")
compare_saved()
```

### 특정 pool만 숫자로 보고 싶을 때

```python
before = snap("before", robot_ids=[1])
# ... RUN ...
after = snap("after", robot_ids=[1])
compare(before, after)
```

`robot_ids=[1]` → Pool_1만. `[1, 5]` → 1번·5번만 비교.

---

## Case B — **특정 pool / 단일 로봇**만

### B-1. underwater.robot 단독 (pool USD 없음)

1. **underwater.robot** extension Enable
2. **LOAD** → `/World/Hippo` 에 로봇 1대
3. Script Editor:

```python
exec(open("/home/woody/AquaSweep/scripts/compare_z_run_scenario.py").read())
snap_before("B: single Hippo, before RUN")
# UI Run Scenario → RUN, 2~3초
snap_after("B: single Hippo, after RUN")
compare_saved()
```

`discover_robots()`가 `World/Hippo` 한 줄만 출력하면 정상입니다.

### B-2. 수조 1개 + 로봇 (water.tank.env + underwater.robot)

1. **water.tank.env** → LOAD (건물·7 pools 생성, 로봇 없음)
2. **underwater.robot** → LOAD (`/World/Hippo` — pool 안이 아닌 월드 루트)
3. 위와 동일하게 `snap_before` / RUN / `snap_after` / `compare_saved`

> Pool_1 **안**에 로봇을 넣은 멀티풀 배치와 비교하려면 Case A를 쓰고 `robot_ids=[1]`로 필터하세요.

---

## 출력 읽는 법

`compare_saved()` 는 **세 블록**을 출력합니다.

1. **BEFORE (pre-RUN)** — RUN 누르기 전 스냅샷만  
2. **AFTER (post-RUN)** — RUN 후 스냅샷만  
3. **BEFORE vs AFTER vs CHANGE** — 한 줄에 `bef` / `aft` / `Δ` 나란히

| 열 | 의미 |
|----|------|
| `robot_Z` | articulation 루트 (`hippo`) 월드 Z |
| `wheel_ctr` | 바퀴 collision 실린더 **중심** Z |
| `wheel_low` | 바퀴 **최저점** Z |
| `gap_floor` | `wheel_low - 0` (building floor top). **음수 = 바닥 관통** |
| `status` | `PENETRATE` / `on floor` / `floating` |
| `Δ` (CHANGE 표) | **after − before** (양수 = RUN 후 더 위로) |

**해석 힌트**

- AFTER 표만 보면 7풀이 숫자가 같아 보여도, CHANGE 표의 `bef` 열이 풀마다 다르면 RUN 전에는 달랐던 것  
- AFTER `gap_floor < 0` → 스폰/PhysX 튜닝 필요 (`ROBOT_SPAWN_Z_M` 올리기 등)

---

## 관련 진단 스크립트 (같은 폴더)

| 파일 | 용도 |
|------|------|
| `compare_z_run_scenario.py` | **RUN 전후 Z diff** (이 문서) |
| `check_wheel_transform_detail.py` | 바퀴 transform 체인 (hippo 경로로 수정 필요 시 `dingo`→`hippo`) |
| `check_wheel_floor_contact.py` | 바닥과 바퀴 gap |
| `check_pool_floor_z.py` | Pool Xform / 로봇 Z 요약 |
| `check_spawn_z.py` | `ROBOT_SPAWN_Z_M` 메모리 값 확인 |
| `test_wheel_diagnosis.py` | World.scene / DOF / DriveAPI |

구 스크립트는 prim 이름이 `dingo`인 경우가 있습니다. 현재 AquaSweep은 **`hippo`** 입니다. `compare_z_run_scenario.py`는 둘 다 자동 탐색합니다.

---

## 한 줄 치트시트

```python
# 로드
exec(open("/home/woody/AquaSweep/scripts/compare_z_run_scenario.py").read())

# 측정 루프
snap_before(); input("UI에서 RUN 후 Enter...") or None; snap_after(); compare_saved()
```

Script Editor REPL에 `input()`이 없으면 RUN 누른 뒤 수동으로 `snap_after(); compare_saved()` 만 실행하면 됩니다.
