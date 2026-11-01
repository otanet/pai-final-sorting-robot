#!/bin/bash
# start_gazebo.sh : 講義の Docker イメージの中で、CRANE+ V2 の Gazebo を起動して仕分けの机を用意する
# 使い方（コンテナの中で、ubuntu ユーザで）: bash /work/ros2/start_gazebo.sh
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
export DISPLAY=${DISPLAY:-:0}
mkdir -p /work/outputs/gazebo
ros2 launch crane_plus_gazebo crane_plus_with_table.launch.py > /work/outputs/gazebo/launch.log 2>&1 &
# コントローラが動き出すまで待つ
until grep -q "Configured and activated.*crane_plus_gripper_controller" /work/outputs/gazebo/launch.log 2>/dev/null; do sleep 2; done
sleep 5
pkill -x rviz2          # 動画には Gazebo の画面だけを使う
cd /work/ros2 && python3 gz_scene.py
echo "Gazebo ready"
