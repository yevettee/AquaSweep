import sys
from pathlib import Path

# 형제 extension 디렉터리를 sys.path에 추가해 하위 모듈을 직접 임포트할 수 있게 한다.
# 반드시 from .extension import * 보다 먼저 실행돼야 한다 — extension.py가
# ui_builder.py 를 import하면서 형제 모듈을 importlib로 끌어오기 때문이다.
_exts_dir = Path(__file__).resolve().parents[2]
for _name in ("water_tank_env_ext", "debris_env_ext", "underwater_robot_ext", "rail_robot_ext"):
    _p = str(_exts_dir / _name)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from .extension import *  # noqa: E402, F401  — Kit's IExt discovery requires this
