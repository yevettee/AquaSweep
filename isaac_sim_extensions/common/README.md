- **문제의 원인(참고)**
    - Issacsim 의 내부 python 은 3.11, ROS2 는 3.10.
    - Issacsim 에서 rclpy 를 랩핑해서 사용하도록 설정하면 ROS2 의 aqua_interfaces(3.10으로 빌드)가 import 되지 않음

<aside>
📌

**아래 경로를 기준으로 세팅된 가이드이니 참고 부탁드립니다**

1. ~/AquaSweep/water_ws/src 구조로 ros2 workspace 를 관리하고 있을 때
2. ~/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/isaac-sim.sh 로 issacsim 을 실행하고 있을 때
</aside>

## 1. 최초 세팅 (한 번만)

```bash
sudo apt install ros-humble-desktop   # 또는 ros-humble-ros-base

# Isaac Sim 설치 경로는 팀원마다 다를 수 있습니다.
# 아래 `ISAAC_ROS2_BRIDGE`만 본인 경로에 맞게 바꿉니다.

export ISAAC_ROS2_BRIDGE="$HOME/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/exts/isaacsim.ros2.bridge/humble"

export ISAAC_PYTHON="$(find "$HOME/.cache/packman" -path '*/python/bin/python3' 2>/dev/null | head -1)"
$ISAAC_PYTHON --version   # Python 3.11.x 확인
```

## 2. AquaSweep/isaac_sim_extension/ 에 추가 및 압축 해제

ws_2/woody 브랜치를 pull 해와도 OK

```
AquaSweep/
	ㄴ isaac_sim_extenions/
		 ㄴ common/ *추가
			 ㄴ __init__.py *추가 
			 ㄴ ros_isaac_env.py *추가	 
```

[common.zip](attachment:4ab435eb-f95f-4c61-8a2c-0b8f34d7be80:common.zip)

## 3. AquaSweep/water_ws/ 에 추가 및 압축 해제

```
AquaSweep/
	ㄴ water_ws/
		ㄴ build_isaac/ *추가
		ㄴ install_isaac/  *추가 
```

[build_isaac.zip](attachment:471ceb54-f799-499c-9704-599bc59f30a6:build_isaac.zip)

[install_isaac.zip](attachment:4e6ed6bf-2d76-4850-925c-243112ef8071:install_isaac.zip)

## 4. AquaSweep/water_ws/scripts 에 추가

ws_2/woody 브랜치를 pull 해와도 OK

```
AquaSweep/
	ㄴ water_ws/
		 ㄴ scripts/
			 ㄴ install_aqua_interfaces_for_isaac.sh	 
```

[install_aqua_interfaces_for_isaac.sh](attachment:9d5e004f-0d6d-45bd-81a7-e08bd96bac4c:install_aqua_interfaces_for_isaac.sh)

## 5. ~/.bashrc 에 추가

<aside>
📌

**isaac을 실행했던 terminal 에서 일반 ROS2 노드를 실행할 수 없습니다. 새로운 터미널에서 ros2 run 해야합니다.**

</aside>

```bash
# ROS2 환경 설정
export AQUASWEEP_ROOT="$HOME/AquaSweep"
export ISAAC_ROS2_BRIDGE="$HOME/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/exts/isaacsim.ros2.bridge/humble"
export ROS_DISTRO=humble
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# source humble 먼저
source /opt/ros/humble/setup.bash
[[ -f "$AQUASWEEP_ROOT/water_ws/install/setup.bash" ]] && \
  source "$AQUASWEEP_ROOT/water_ws/install/setup.bash"

# isaac alias 수정
alias isaac='\
  export LD_LIBRARY_PATH="$ISAAC_ROS2_BRIDGE/lib:${LD_LIBRARY_PATH:-}" && \
  source "$AQUASWEEP_ROOT/water_ws/install/setup.bash" 2>/dev/null; \
  "$HOME/dev_ws/isaac_sim/isaacsim/_build/linux-x86_64/release/isaac-sim.sh"'
```

<aside>
📌

**aqua_interfaces 타입을 추가하거나 필드를 수정했을 때 특 스크립트를 실행해야합니다. 편의를 위해 ~/.bashrc 에 아래와 같이 alias를 등록해주세요**

</aside>

```bash
# aqua_interfaces 패키지 수정 후 반드시 실행
alias ai='$AQUASWEEP_ROOT/water_ws/scripts/install_aqua_interfaces_for_isaac.
```

## 6. extension 세팅

rclpy 모듈을 사용해야하는 모든 extension 에 반드시 아래 가이드를 따라 적용해주시면 좋을 것 같아요. 

**(1) extension.toml 에 반드시 포함**

```toml
[dependencies]
"isaacsim.ros2.bridge" = {}
```

**(2) ROS 를 사용하는 파일 최상단에 추가** 

```toml
import sys
from pathlib import Path

_common = Path(__file__).resolve().parents[2] / "common"  # depth는 extension 구조에 맞게 조정
if str(_common) not in sys.path:
    sys.path.insert(0, str(_common))

from ros_isaac_env import configure_isaac_ros_env, purge_stale_ros_modules, AQUA_INTERFACES_INSTALL_HINT
```

**(3) 주의: 파일 최상단에 `import rclpy` 절대 금지**

- on_startup, 버튼 콜백, start() 같은 ROS 켤 때는 import 해도 OK