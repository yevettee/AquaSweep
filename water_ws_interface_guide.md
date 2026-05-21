# Interfaces

### Naming Rules

통신 name 과 prim_path 를 유사도 높게 관리해야함  

- pool_1, 2, 3, …
- under_robot_1, 2, 3 …
- rail_robot_1, 2, 3 …

```
# prim 예시

- world
    - ground
    - pools
        - pool_1
            - water
            - under_robot_1
                - base_link
                - under_cam_1
            - top_cam_1
    - rails
        - rail_1
            - rail_robot_1
```

### Built-in

- **geometry_msgs/msg/Twist (로봇 제어)**
    - /under_robot_1/cmd_vel
    
    | 필드 | 타입 | 설명 |
    | --- | --- | --- |
    | linear | geometry_msgs/Vector3 | 선속도 (m/s)
    • x: 전진/후진
    • y: 좌우 (Diff Drive는 보통 0)
    • z: 상하 (보통 0) |
    | angular | geometry_msgs/Vector3 | 각속도 (rad/s)
    • x, y: roll/pitch (보통 0)
    • z: yaw 회전 (가장 중요) |
- **sensor_msgs/msg/JointState (각 관절(바퀴) 센서값)**
    - /under_robot_1/joint_state
    - /rail_robot_1/joint_state
    
    | 필드 | 타입 | 설명 |
    | --- | --- | --- |
    | name | string[] | joint 이름 배열 (예: ["left_wheel", "right_wheel"]) |
    | position | float64[] | 각 joint 위치 (rad 또는 meter) |
    | velocity | float64[] | 각 joint 속도 (rad/s 또는 m/s) |
    | effort | float64[] | 각 joint 토크/힘 (Nm 또는 N) — **외력·부하 측정에 중요** |
- **sensor_msgs/msg/Image (카메라 이미지 발행)**
    - /pool_1/under_img_raw
    - /pool_1/under_img_det
    - /pool_1/top_img_raw
    - /pool_1/top_img_det
    
    | 필드 | 타입 | 설명 |
    | --- | --- | --- |
    | height | uint32 | 이미지 높이 (픽셀) |
    | width | uint32 | 이미지 너비 (픽셀) |
    | encoding | string | "rgb8", "bgr8", "mono8", "16UC1" 등 |
    | is_bigendian | uint8 | 0 = little endian (대부분), 1 = big endian |
    | step | uint32 | 한 줄(row)의 바이트 길이 |
    | data | uint8[] | 실제 이미지 데이터 (1차원 배열) |
- **sensor_msgs/msg/Imu (로봇 센서의 관성 추정값)**
    - /under_robot_1/imu
    
    | 필드 | 타입 | 설명 |
    | --- | --- | --- |
    | orientation | geometry_msgs/Quaternion | 자세 (x,y,z,w) |
    | orientation_covariance | float64[9] | 자세 공분산 (신뢰도) |
    | angular_velocity | geometry_msgs/Vector3 | 각속도 (rad/s) |
    | angular_velocity_covariance | float64[9] | 각속도 공분산 |
    | linear_acceleration | geometry_msgs/Vector3 | 선가속도 (m/s²) |
    | linear_acceleration_covariance | float64[9] | 선가속도 공분산 |
- **nav_msgs/msg/Odometry (로봇 전체의 위치,자세,속도 추정값)**
    - /under_robot_1/odom
    
    | 필드 | 타입 | 설명 |
    | --- | --- | --- |
    | child_frame_id | string | "base_link" (로봇 본체 프레임) |
    | pose | geometry_msgs/PoseWithCovariance | 위치 + 방향 + 공분산
    (position.x, y, orientation.z/yaw가 핵심) |
    | twist | geometry_msgs/TwistWithCovariance | 현재 속도 + 공분산
    (linear.x, angular.z가 핵심) |
- **nav_msgs/msg/Path** (나중에 planner 고도화 할 때)
    - /under_robot_1/planned_path
    
    | 필드 | 타입 | 설명 |
    | --- | --- | --- |
    | poses | geometry_msgs/PoseStamped[] | **PoseStamped 배열** (경로상의 waypoint들) |

### Custom

aqua_interfaces/

- **msg/**
    - **RobotStatus**
        - /under_robot_1/status
            - state (e.g. IDLE, RUNNING, PAUSED, DISCHARGED..)
            - battery_level: (0~1)
            - collision_force: (N)
    - **poolStatus**
        - /pool_1/status
            - pollution_level
            - fish_type
            - fish_count
            - fish_count_suspicious
    - **poolPhysicalVariables**
        - /pool_1/physical_variables
            - buoyancy
            - drag
            - lift
            - viscosity
- **action/**
    - **CleanFloor**
        - /under_robot_1/clean_floor
    - **CleanWall**
        - /rail_robot_1/clean_wall