import os

import omni.ext
from isaacsim.examples.browser import get_instance as get_browser_instance
from isaacsim.examples.interactive.base_sample import BaseSampleUITemplate

from water_robot.robot_controller import WaterTankJetbotSample


class WaterTankJetbotExtension(omni.ext.IExt):
    """Examples Browser에 JetBot 샘플을 등록."""

    def on_startup(self, ext_id: str):
        self.example_name = "Water Tank Jetbot Cleaner"
        self.category = "Water Robot Examples"

        ui_kwargs = {
            "ext_id": ext_id,
            "file_path": os.path.abspath(__file__),
            "title": "Water Tank Jetbot Cleaner",
            "doc_link": "https://docs.omniverse.nvidia.com/isaacsim/latest/ros2_tutorials/python_scripting/index.html",
            "overview": "JetBot differential drive: tank-width strips, 90° turns, one round trip.",
            "sample": WaterTankJetbotSample(),
        }

        ui_handle = BaseSampleUITemplate(**ui_kwargs)

        get_browser_instance().register_example(
            name=self.example_name,
            execute_entrypoint=ui_handle.build_window,
            ui_hook=ui_handle.build_ui,
            category=self.category,
        )

        return

    def on_shutdown(self):
        # 확장 종료 순서상 Examples Browser 모델이 먼저 비워지면 KeyError 난다. 무시하면 된다.
        try:
            get_browser_instance().deregister_example(name=self.example_name, category=self.category)
        except KeyError:
            pass

        return


# 일부 Kit 빌드는 모듈 최상단의 `Extension` 이름으로 IExt 구현체를 찾는다.
Extension = WaterTankJetbotExtension
