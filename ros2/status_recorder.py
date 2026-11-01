#!/usr/bin/env python3
# status_recorder.py : /instruction・/plan・/status を時刻つきでファイルに記録する（動画の字幕に使う）
import json
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class Recorder(Node):
    def __init__(self, path):
        super().__init__("status_recorder")
        self.f = open(path, "a", encoding="utf-8")
        for topic in ("instruction", "plan", "status"):
            self.create_subscription(String, topic, lambda m, t=topic: self.write(t, m.data), 10)

    def write(self, topic, data):
        self.f.write(json.dumps({"t": time.time(), "topic": topic, "data": data}, ensure_ascii=False) + "\n")
        self.f.flush()


def main():
    rclpy.init()
    rclpy.spin(Recorder(sys.argv[1] if len(sys.argv) > 1 else "/work/outputs/gazebo/status.jsonl"))


if __name__ == "__main__":
    main()
