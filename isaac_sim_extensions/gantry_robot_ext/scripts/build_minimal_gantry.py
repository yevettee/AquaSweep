# Isaac Sim Script Editor — one line:
# exec(open("/home/rokey/AquaSweep/isaac_sim_extensions/gantry_robot_ext/scripts/build_minimal_gantry.py").read())
#
# Extension이 로드되지 않은 환경에서도 직접 실행 가능한 standalone 버전.

import sys, os
_pkg = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
if _pkg not in sys.path:
    sys.path.insert(0, _pkg)

from gantry_robot_python.gantry_builder import build
import omni.usd

build(omni.usd.get_context().get_stage())
print("[GantryRobot] 빌드 완료 — PLAY 누르면 동작")
