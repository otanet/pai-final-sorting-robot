#!/usr/bin/env python3
# sorter_node.py : /plan（JSON の手順）を受け取り、Gazebo 上の CRANE+ V2 でブロックを左右のトレイへ運ぶ
# - 逆運動学: 教科書（AIロボット入門 第6章）の crane_plus_commander/kinematics.py
# - 動作: ros2_control の FollowJointTrajectory アクション（アーム・グリッパ）
# - ブロックの位置: Gazebo 版ではシミュレータに置いた既知の位置を使う（認識は Genesis 版で評価）
import json
import os
import sys
import time
from math import radians

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import String
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from crane_plus_commander.kinematics import inverse_kinematics, joint_in_range, GRIPPER_MIN, GRIPPER_MAX

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gz_scene import CUBES, TRAYS, CUBE  # noqa: E402

ARM = ["crane_plus_joint1", "crane_plus_joint2", "crane_plus_joint3", "crane_plus_joint4"]
HOME = [0.0, -1.16, -2.01, -0.73]
Z_GRASP, Z_ABOVE = CUBE / 2 + 0.002, 0.075        # 土台から見た手先の高さ [m]
JA = {"red": "赤", "blue": "青", "green": "緑", "yellow": "黄色", "left": "左", "right": "右"}


def solve(x, y, z):
    """手先を (x, y, z) へ。真下向き（-90°）から少しずつ起こして、解ける姿勢を探す"""
    for deg in range(-90, -25, 5):
        q = inverse_kinematics([x, y, z, radians(deg)], elbow_up=True)
        if q is not None and all(joint_in_range(q)):
            return q
    return None


class Sorter(Node):
    def __init__(self):
        super().__init__("sorter_node")
        self.arm = ActionClient(self, FollowJointTrajectory, "/crane_plus_arm_controller/follow_joint_trajectory")
        self.hand = ActionClient(self, FollowJointTrajectory, "/crane_plus_gripper_controller/follow_joint_trajectory")
        self.status = self.create_publisher(String, "status", 10)
        self.create_subscription(String, "plan", self.on_plan, 10)
        self.arm.wait_for_server()
        self.hand.wait_for_server()
        self.slots = {"left": 0, "right": 0}
        self.queue = []
        self.get_logger().info("準備完了")

    def say(self, text):
        self.get_logger().info(text)
        self.status.publish(String(data=text))

    def _send(self, client, names, q, sec):
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = names
        pt = JointTrajectoryPoint(positions=[float(v) for v in q])
        pt.time_from_start = Duration(sec=int(sec), nanosec=int((sec % 1) * 1e9))
        goal.trajectory.points = [pt]
        fut = client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, fut)
        res = fut.result().get_result_async()
        rclpy.spin_until_future_complete(self, res)
        time.sleep(0.3)

    def move(self, x, y, z, sec=2.0):
        q = solve(x, y, z)
        if q is None:
            self.say(f"手が届きません: ({x:.2f}, {y:.2f}, {z:.2f})")
            return False
        self._send(self.arm, ARM, q, sec)
        return True

    def gripper(self, closed):
        self._send(self.hand, ["crane_plus_joint_hand"], [GRIPPER_MAX - 0.25 if closed else GRIPPER_MIN], 1.0)

    def on_plan(self, msg):
        self.queue.append(json.loads(msg.data))

    def loop(self):
        if not self.queue:
            return
        p = self.queue.pop(0)
        steps = p["steps"]
        self.slots = {"left": 0, "right": 0}
        if not steps:
            self.say("LLM の手順が空のため、何もしません")
            return
        self.say("LLM の手順: " + "、".join(f"{JA[s['object']]}→{JA[s['place']]}" for s in steps))
        for k, s in enumerate(steps):
            if s["object"] not in CUBES:
                self.say(f"{JA[s['object']]}のブロックはこの机にありません")
                continue
            (x, y), _ = CUBES[s["object"]]
            (tx, ty), _ = TRAYS[s["place"]]
            ty += (-0.025 if self.slots[s["place"]] % 2 == 0 else 0.025)
            self.slots[s["place"]] += 1
            self.say(f"実行中 {k + 1}/{len(steps)}: {JA[s['object']]}のブロックを{JA[s['place']]}のトレイへ")
            self.gripper(False)
            self.move(x, y, Z_ABOVE)
            self.move(x, y, Z_GRASP, 1.5)
            self.gripper(True)
            self.move(x, y, Z_ABOVE, 1.5)
            self.move(tx, ty, Z_ABOVE)
            self.move(tx, ty, Z_GRASP + 0.01, 1.5)
            self.gripper(False)
            self.move(tx, ty, Z_ABOVE, 1.5)
        self._send(self.arm, ARM, HOME, 2.0)
        self.say("完了")


def main():
    rclpy.init()
    node = Sorter()
    while rclpy.ok():          # アクションの完了待ちで spin するので、rclpy.spin() ではなく自前のループにする
        rclpy.spin_once(node, timeout_sec=0.2)
        node.loop()


if __name__ == "__main__":
    main()
