#!/usr/bin/env python3
# gz_scene.py : Gazebo（Ignition）の机の上に、色付きブロック3つと左右のトレイ（目印）を置く
# 「左」「右」は、ロボットの正面のカメラから見た向き（左のトレイは y < 0 側）
import subprocess

TABLE_Z = 1.015                      # 机の天板の高さ（CRANE+ の土台と同じ高さ）
CUBE = 0.025
# CRANE+ V2 は腕が短い（真下向きでつかめるのは土台から約 0.17m まで）ので、その内側に置く
# グリッパの指はブロックの向きに合わせて回らず、開くと隣のブロックに当たるので、
# 土台から見た角度が小さく、互いに離れた2か所に置く（3個目を中央に置くと、つかむときに崩れた）
CUBES = {"red": ((0.15, 0.06), "0.85 0.1 0.1 1"),
         "blue": ((0.15, -0.06), "0.1 0.2 0.85 1")}
TRAYS = {"left": ((0.03, -0.15), "0.8 0.8 0.85 1"), "right": ((0.03, 0.15), "0.55 0.45 0.35 1")}


def cube_sdf(name, rgba):
    m, i = 0.01, 0.01 * CUBE ** 2 / 6
    return f"""<sdf version='1.6'><model name='{name}'><link name='link'>
<inertial><mass>{m}</mass><inertia><ixx>{i}</ixx><iyy>{i}</iyy><izz>{i}</izz></inertia></inertial>
<collision name='c'><geometry><box><size>{CUBE} {CUBE} {CUBE}</size></box></geometry>
<surface><friction><ode><mu>2.0</mu><mu2>2.0</mu2></ode></friction></surface></collision>
<visual name='v'><geometry><box><size>{CUBE} {CUBE} {CUBE}</size></box></geometry>
<material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material></visual></link></model></sdf>"""


def tray_sdf(name, rgba):
    return f"""<sdf version='1.6'><model name='{name}'><static>true</static><link name='link'>
<visual name='v'><geometry><box><size>0.09 0.09 0.002</size></box></geometry>
<material><ambient>{rgba}</ambient><diffuse>{rgba}</diffuse></material></visual></link></model></sdf>"""


def spawn(name, sdf, x, y, z):
    subprocess.run(["ros2", "run", "ros_gz_sim", "create", "-world", "default", "-name", name,
                    "-string", sdf, "-x", str(x), "-y", str(y), "-z", str(z)], check=True,
                   stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    # 元のワールドの木のブロックと、前回置いたものを消す（何度でも置き直せるように）
    for old in ["wood_cube_5cm", "tray_left", "tray_right", "red", "blue", "yellow"]:
        subprocess.run(["ign", "service", "-s", "/world/default/remove", "--reqtype", "ignition.msgs.Entity",
                        "--reptype", "ignition.msgs.Boolean", "--timeout", "3000",
                        "--req", f'name: "{old}" type: MODEL'], stdout=subprocess.DEVNULL)
    for n, ((x, y), c) in TRAYS.items():
        spawn(f"tray_{n}", tray_sdf(f"tray_{n}", c), x, y, TABLE_Z + 0.001)
    for n, ((x, y), c) in CUBES.items():
        spawn(n, cube_sdf(n, c), x, y, TABLE_Z + CUBE / 2 + 0.005)
    # GUI のカメラをロボットの正面・斜め上へ
    subprocess.run(["ign", "service", "-s", "/gui/move_to/pose", "--reqtype", "ignition.msgs.GUICamera",
                    "--reptype", "ignition.msgs.Boolean", "--timeout", "3000",
                    "--req", "pose: {position: {x: 0.32, y: 0.0, z: 1.27}, orientation: {x: -0.3420, y: 0.0, z: 0.9397, w: 0.0}}"])
    # ↑ yaw 180°（ロボットの方を向く）と pitch 40°（見下ろす）を合成した姿勢
    print("scene ready")
