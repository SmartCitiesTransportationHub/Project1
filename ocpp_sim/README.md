# OCPP 1.6 攻防仿真台（论文图16/17/A1 的实测来源）

真实 OCPP 1.6-J 消息（`ocpp` 库）经真实 websocket 在一个 CSMS 与 57 个充电桩客户端之间交换；
按 2025-12-05 的真实会话回放（16–22 时）。离散虚拟时钟（1 分钟步进）与墙钟解耦。
A3 后台沦陷攻击（SetChargingProfile=0 / RemoteStopTransaction 扇出）；后台侧检测器
（指令速率 + 规模×节律功率一致性）；遏制（指令限速 / 告警后隔离恢复）。

运行（需先把数据目录指给 AMB_DATA）：
    pip install "ocpp>=2.0" "websockets>=12,<14" pandas numpy matplotlib
    AMB_DATA=/path/to/supp PYTHONPATH=. python3 run_matrix.py    # -> results.json
    AMB_DATA=/path/to/supp PYTHONPATH=. python3 make_sim_figs.py # -> fig17_matrix/fig18_latency/figA1

实测要点：隔离把被发现前残余受控电量从 ~2100 kWh 降至 ~6–10 kWh（>99%）；
规模×节律一致性检测器约 1 分钟捕获速率检测漏掉的隐蔽慢速攻击；仅检测/仅限速几乎不减损失；
4 次良性回放误报 0。
