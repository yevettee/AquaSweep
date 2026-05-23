# 📓 학습 기술 노트 (Tech Notes)

AquaSweep 수중 비전 프로젝트 고도화를 수행하며 습득한 컴퓨터 비전 핵심 개념과 Isaac Sim 5.1 & ROS 2 연동 최적화 핵심 노하우를 정리한 학습 기술 노트입니다.

---

## 💡 1. 실무 비전 핵심 기법 (OpenCV 패턴)

### ① 조명 불균형의 최종 병기: 조명 평탄화 (Illumination Normalization)
* **원리**: 실내 수조 중앙의 초강력 하이라이트(빛 번짐)가 존재할 때, 단순한 임계값 적용은 언제나 실패합니다. 이때 이미지를 거대 가우시안 블러(`151x151` 홀수 커널) 처리하면 배경의 전반적인 **조도 맵(Illumination Map)**만 남길 수 있습니다.
* **수식**:
  $$\text{Corrected} = \frac{\text{Original}}{\text{IllumMap}} \times 255$$
* 이 나눗셈 연산(`cv2.divide`)을 통해 수조 중앙의 흰색 번짐과 구석진 곳의 어두운 편차가 수학적으로 평평하게 상쇄되어 균일 조도의 이미지로 보정됩니다.

### ② 윤곽 복원의 마법: 적응형 이진화 (Adaptive Thresholding)
* **가장 중요한 교훈**: 피사체의 크기(두께)보다 이진화의 **블록 사이즈(`BlockSize`)**가 현격하게 작으면 피사체 내부에 구멍이 숭숭 뚫리는 공동화 현상이 생깁니다.
* **설계 규칙**: 객체 실루엣 두께보다 확연히 넓은 초대형 블록 격자 크기(`151x151` 등)를 지정하면 흐릿하게 번진 대형 어종(Sturgeon)의 몸통도 빈 틈 없이 단 한 덩어리로 온전히 포획해 낼 수 있습니다.

---

## 🚀 2. Isaac Sim 5.1 & ROS 2 최적화 노하우

### ① 비전 캡처 주기 제한을 통한 시스템 프레임 레이트 보존
* GPU에서 렌더링된 물리 화면을 CPU 호스트 메모리로 긁어오는 **Readback** 연산은 Isaac Sim의 대표적인 자원 버틀넥(Bottleneck) 중 하나입니다.
* `subscribe_physics_step_events`에서 매 물리 프레임마다 즉시 프레임을 긁지 않고, 시간차 측정 오프셋을 두어 **`5Hz (0.2초 주기)`**로 읽기 제한을 걸어줌으로써, 시뮬레이션의 물리 연산 프레임(FPS)이 반토막 나는 자원 병목을 완벽히 해결하고 매끄러운 다중 수조 뷰포트를 확보했습니다.

### ② 싱글톤 ROS 브릿지 설계의 중요성
* Isaac Sim의 `extension.py`와 `ui_builder.py` 및 각종 뷰포트들이 각각 ROS Bridge 인스턴스를 무분별하게 다중 생성하면 `rclpy.init()` 이중 선언 및 Publisher Context 무효화 에러로 세그멘테이션 폴트(Segfault) 크래시가 상시 발생합니다.
* 파이썬의 스레드 락(`threading.Lock`)을 활용한 **Thread-Safe 싱글톤(Singleton)** 패턴으로 `RosBridge`를 구축하고, Timeline STOP 감지 시 rclpy 컨텍스트 및 FastRTPS 공유 메모리를 안전하게 소거(`_cleanup_rclpy_context`)해야만 런타임 누수 없는 극도의 라이프사이클 안정성을 보장할 수 있습니다.
