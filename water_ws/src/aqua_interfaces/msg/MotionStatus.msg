# 모션 진행 상태 (step_sync 대체)
uint8 IDLE=0
uint8 RUNNING=1
uint8 PAUSED=2
uint8 DONE=3

uint8 state               # 현재 상태
float32 progress          # 진행률 (0.0 ~ 1.0)
uint32 current_step       # 현재 step 번호
uint32 total_steps        # 전체 step 수
string phase              # 현재 단계 (spiral, wall_follow, return 등)
