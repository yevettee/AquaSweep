"""Isaac Sim 콘솔에서 실행하는 바퀴 직접 제어 테스트.

사용법:
1. Isaac Sim에서 AquaSweep 확장 로드 후 LOAD → RUN
2. Script Editor (Window → Script Editor) 열기
3. 이 파일 내용 붙여넣고 실행 (Ctrl+Enter)

테스트 결과:
- 로봇이 움직이면 → ActionGraph 문제 (767749b 방식으로 변경 필요)
- 로봇이 안 움직이면 → 물리/USD 설정 문제
"""

from isaacsim.core.api.world import World
from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController
import numpy as np

# Dingo-D 파라미터 (global_variables.py에서)
WHEEL_RADIUS = 0.049
WHEEL_BASE = 0.4523

# 테스트할 로봇 번호 (1-7)
TEST_ROBOT_IDS = [1, 5]  # 안 움직이는 1번과 잘 움직이는 5번 비교

# 테스트 속도
LINEAR_VEL = 0.5   # m/s
ANGULAR_VEL = 0.3  # rad/s


def test_direct_wheel_control():
    world = World.instance()
    if world is None:
        print("[TEST] World not initialized. Run LOAD first.")
        return
    
    controllers = {}
    robots = {}
    
    for robot_id in TEST_ROBOT_IDS:
        scene_name = f"dingo_{robot_id}"
        try:
            robot = world.scene.get_object(scene_name)
            if robot is None:
                print(f"[TEST] Robot {scene_name} not found")
                continue
            robots[robot_id] = robot
            
            controller = DifferentialController(
                name=f"test_diff_{robot_id}",
                wheel_radius=WHEEL_RADIUS,
                wheel_base=WHEEL_BASE,
            )
            controller.reset()
            controllers[robot_id] = controller
            print(f"[TEST] Robot {robot_id} ready: {scene_name}")
        except Exception as e:
            print(f"[TEST] Error loading robot {robot_id}: {e}")
    
    if not robots:
        print("[TEST] No robots loaded. Check scene names.")
        return
    
    # 바퀴 속도 계산
    wheel_actions = controllers[list(controllers.keys())[0]].forward(
        command=[LINEAR_VEL, ANGULAR_VEL]
    )
    print(f"[TEST] Wheel actions for v={LINEAR_VEL}, omega={ANGULAR_VEL}: {wheel_actions}")
    
    # 직접 바퀴 제어 적용
    for robot_id, robot in robots.items():
        try:
            robot.apply_wheel_actions(wheel_actions)
            print(f"[TEST] Applied wheel actions to robot {robot_id}")
        except Exception as e:
            print(f"[TEST] Error applying to robot {robot_id}: {e}")
    
    print("\n[TEST] 완료! 로봇이 움직이는지 확인하세요.")
    print("       - 움직이면: ActionGraph 문제 → 767749b 방식으로 변경")
    print("       - 안 움직이면: 물리/USD 설정 문제")


# 실행
test_direct_wheel_control()
