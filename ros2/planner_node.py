#!/usr/bin/env python3
# planner_node.py : /instruction（日本語の指示）を受け取り、LLM で手順を作って /plan に JSON で出す
# 計画の中身は Genesis 版と同じ src/planner.py を使う（同じ AI を、ROS 2 のノードとして組み込む）
import json
import os
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import planner  # noqa: E402


class PlannerNode(Node):
    def __init__(self):
        super().__init__("planner_node")
        self.model = self.declare_parameter("model", "Qwen/Qwen2.5-1.5B-Instruct").value
        self.pub = self.create_publisher(String, "plan", 10)
        self.status = self.create_publisher(String, "status", 10)
        self.create_subscription(String, "instruction", self.on_instruction, 10)
        planner._load(self.model)                     # 起動時にモデルを読み込んでおく
        self.get_logger().info(f"準備完了（{self.model}）")

    def on_instruction(self, msg):
        self.get_logger().info(f"指示: {msg.data}")
        self.status.publish(String(data=f"LLM が計画中: 「{msg.data}」"))
        steps, raw = planner.plan(msg.data, self.model)
        self.get_logger().info(f"LLM の出力: {raw} -> 手順 {steps}")
        self.pub.publish(String(data=json.dumps({"instruction": msg.data, "steps": steps}, ensure_ascii=False)))


def main():
    rclpy.init()
    rclpy.spin(PlannerNode())


if __name__ == "__main__":
    main()
