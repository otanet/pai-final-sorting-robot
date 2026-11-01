#!/bin/bash
# record_demo.sh : Gazebo の画面を録画しながら、日本語の指示を1つ送って仕分けを実行する
# 使い方（コンテナの中で、planner_node.py と sorter_node.py を起動しておく）:
#   bash /work/ros2/record_demo.sh "青と赤は左、黄色は右に仕分けて" gz_demo_1
source /opt/ros/humble/setup.bash
source /home/ubuntu/airobot_ws/install/setup.bash
export DISPLAY=${DISPLAY:-:0}
INST="$1"; NAME="${2:-gz_demo}"; OUT=/work/outputs/gazebo
cd /work/ros2 && python3 gz_scene.py > /dev/null      # ブロックを最初の位置に置き直す
sleep 3
python3 status_recorder.py $OUT/$NAME.jsonl &
REC=$!
# Gazebo の 3D 表示の部分（1500x880）だけを録画する
ffmpeg -loglevel error -y -f x11grab -framerate 15 -video_size 1500x880 -i :0.0+0,160 \
       -c:v libx264 -preset veryfast -pix_fmt yuv420p $OUT/$NAME.mp4 &
FF=$!
echo "{\"t\": $(date +%s.%N), \"topic\": \"record_start\", \"data\": \"\"}" >> $OUT/$NAME.jsonl
sleep 3
ros2 topic pub --once -w 2 /instruction std_msgs/msg/String "{data: '$INST'}" > /dev/null
# 「完了」か「何もしません」が出るまで待つ（最大 6 分）
for i in $(seq 360); do
  grep -q -E '"完了"|何もしません' $OUT/$NAME.jsonl && break; sleep 1
done
sleep 3
kill -INT $FF; wait $FF; kill $REC
echo "recorded $OUT/$NAME.mp4"
