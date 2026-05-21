# Dashboard
현재 dashboard node 및 dashboard ext 가 만들어져있긴 한데 아래 낸용 바탕으로 고도화. planner node 와 상호작용 하므로 참고 

### Wireframe

- 상단 헤더: 좌측 AquaSweep 우측 시작 버튼. 클릭 시 /planner/start 서비스 요청
- 2 * 2 grid 로 pool(+robot) 정보 포함.
- pool_1, under_robot_1 은 한 세트임.
- /pool_{id}/top_cam_det, /pool_{id}/under_cam_det 구독해서 detection 된 이미지 표시
- top_cam_det 아래에는 /pool_1/status 표시
- under_cam_det 아래에는 /under_robot_1/status 표시
- 각 pool(+robot) 은 개별적인 시작 버튼을 가짐. 이 시작 버튼은 /pool_{id}/start_clean_floor 서비스 요청.

### Rendering Conditions

- 각 pool(+robot) 은 드롭다운으로 가리지 말 것.
- 전체 시작 버튼의 경우 작업이 진행 중일 때는 전체 시작 버튼 및 개별 버튼 클릭 불가
- 개별 시작 버튼의 경우 해당 pool_id의 작업이 진행 중일 때는 개별 버튼 클릭 불가


# Planner node
- dashboard node 로부터 /planner/start 요청을 받는다.
    - 요청을 받으면 /pool_{id}/status 를 구독해서 fish_count == 0 인 것들만 청소를 시작한다. 이때 controller 노드에게 모든 pool_{id} 에 대해 controller 노드에게 send_goal (CleanFloor.action) 하게 된다.
- dashboard node 로부터 /pool_{id}/start_clean_floor 요청을 받는다.
    - 요청을 받으면 해당 pool_{id} 에 대해 controller 노드에게 send_goal (CleanFloor.action) 한다. 


# 작업 주의사항
- 현재 실제 발행이 안되고 있어서 mock data 가 필요함. 그런데 아예 mock 통신용 노드를 만들기보단 상수로 채워서 하면 좋겠음. (혹은 다른 간단한 방식 제안. 아예 사용되는 많은 통신에 대해 mock package를 따로 만들어도 됨. 그리고 mock pkg 에는 README.md 에 이건 실 개발용이 아니라 테스트용임을 명시)
- controller node 쪽 로직은 절대 수정하지마. 다른 개발자가 작업중이라 충돌 생김. 연결이 애매하면 일단 명시만 해두어도 OK. 


# Ros2 통신 entity 및 네이밍 참고
/home/woody/AquaSweep/docs/ROS2 Communication Guide 367f3b5807d480ffb41ad03b647ad3f3.md