# sim.py : Genesis 上の「仕分け台」（Franka・色付きブロック・左右のトレイ・カメラ2台）
# 「左」「右」は、動画のカメラ（ロボットの正面）から見た向き。左のトレイは y < 0 側にある。
import numpy as np
import genesis as gs

CUBE = 0.04                      # ブロックの一辺 [m]
COLORS = {                       # 名前: RGB
    "red": (0.85, 0.12, 0.12),
    "blue": (0.12, 0.25, 0.85),
    "green": (0.12, 0.65, 0.20),
    "yellow": (0.92, 0.80, 0.10),
}
TRAYS = {                        # 名前: (中心 x, 中心 y), 見た目の色
    "left": ((0.45, -0.36), (0.75, 0.75, 0.80)),
    "right": ((0.45, 0.36), (0.55, 0.45, 0.35)),
}
TRAY_SIZE = 0.18
WORK_X, WORK_Y = (0.36, 0.62), (-0.18, 0.18)   # ブロックを置く範囲


def to_np(x):
    return x.cpu().numpy() if hasattr(x, "cpu") else np.asarray(x)


def random_layout(seed, names=tuple(COLORS)):
    """ブロックが重ならないように、作業範囲にランダムに置く（seed で再現できる）"""
    rng = np.random.default_rng(seed)
    pts = []
    while len(pts) < len(names):
        p = np.array([rng.uniform(*WORK_X), rng.uniform(*WORK_Y)])
        if all(np.linalg.norm(p - q) > 0.09 for q in pts):
            pts.append(p)
    return {n: (float(p[0]), float(p[1])) for n, p in zip(names, pts)}


_READY = False


class SortingScene:
    def __init__(self, layout, video_res=(960, 540), top_res=(640, 480)):
        global _READY
        if not _READY:
            gs.init(backend=gs.cpu, logging_level="warning")
            _READY = True
        self.scene = gs.Scene(sim_options=gs.options.SimOptions(dt=0.01),
                              vis_options=gs.options.VisOptions(segmentation_level="entity"),
                              show_viewer=False)
        self.scene.add_entity(gs.morphs.Plane())
        for name, ((x, y), color) in TRAYS.items():    # トレイ（薄い板。当たり判定なし）
            self.scene.add_entity(gs.morphs.Box(size=(TRAY_SIZE, TRAY_SIZE, 0.002), pos=(x, y, 0.001),
                                                fixed=True, collision=False),
                                  surface=gs.surfaces.Default(color=color))
        self.cubes = {}
        for name, (x, y) in layout.items():
            self.cubes[name] = self.scene.add_entity(gs.morphs.Box(size=(CUBE,) * 3, pos=(x, y, CUBE / 2)),
                                                     surface=gs.surfaces.Default(color=COLORS[name]))
        self.franka = self.scene.add_entity(gs.morphs.MJCF(file="xml/franka_emika_panda/panda.xml"))
        # 認識用: ほぼ真上から見るカメラ / 動画用: ロボットの正面から見るカメラ
        self.top = self.scene.add_camera(res=top_res, pos=(0.47, 0.0, 1.25), lookat=(0.48, 0.0, 0.0), fov=50, GUI=False)
        self.view = self.scene.add_camera(res=video_res, pos=(1.55, 0.0, 1.05), lookat=(0.30, 0.0, 0.28), fov=55, GUI=False)
        self.scene.build()
        self.arm = Arm(self)

    def cube_pos(self, name):
        return to_np(self.cubes[name].get_pos())

    def in_tray(self, name, tray):
        (x, y), _ = TRAYS[tray]
        p = self.cube_pos(name)
        return abs(p[0] - x) < TRAY_SIZE / 2 and abs(p[1] - y) < TRAY_SIZE / 2 and p[2] < CUBE

    def where(self, name):
        for t in TRAYS:
            if self.in_tray(name, t):
                return t
        return None

    def top_image(self, seg=False):
        out = self.top.render(rgb=True, segmentation=seg)
        return (np.asarray(out[0], dtype=np.uint8), np.asarray(out[2]) if seg else None)


class Arm:
    """Franka を pick / place で動かす（関節空間の直線補間＋IK）。動画用のフレームも記録する"""
    GRASP = 0.11      # hand リンクと指先の距離
    LIFT = 0.22

    def __init__(self, s, record_every=4):
        self.s, self.f = s, s.franka
        self.motors, self.fingers = np.arange(7), np.arange(7, 9)
        self.ee = self.f.get_link("hand")
        self.down = np.array([0, 1, 0, 0])
        self.f.set_dofs_kp(np.array([4500, 4500, 3500, 3500, 2000, 2000, 2000, 100, 100]))
        self.f.set_dofs_kv(np.array([450, 450, 350, 350, 200, 200, 200, 10, 10]))
        self.f.set_dofs_force_range(np.array([-87, -87, -87, -87, -12, -12, -12, -100, -100]),
                                    np.array([87, 87, 87, 87, 12, 12, 12, 100, 100]))
        q0 = np.array([0, -0.6, 0, -2.4, 0, 1.9, 0.79, 0.04, 0.04])
        self.f.set_dofs_position(q0)
        self.f.control_dofs_position(q0)
        self.record = False
        self.record_every = record_every
        self.frames, self.caption, self._n = [], [], 0

    def step(self, n=1):
        for _ in range(n):
            self.s.scene.step()
            self._n += 1
            if self.record and self._n % self.record_every == 0:
                self.frames.append((np.asarray(self.s.view.render()[0], dtype=np.uint8), list(self.caption)))

    def move_to(self, pos, steps=100):
        q_goal = to_np(self.f.inverse_kinematics(link=self.ee, pos=np.array(pos, dtype=float), quat=self.down))
        q_now = to_np(self.f.get_dofs_position())
        for i in range(1, steps + 1):
            self.f.control_dofs_position((q_now + (q_goal - q_now) * i / steps)[:7], self.motors)
            self.step()
        self.step(25)

    def open(self):
        self.f.control_dofs_position(np.array([0.04, 0.04]), self.fingers)
        self.step(50)

    def close(self):
        self.f.control_dofs_force(np.array([-2.0, -2.0]), self.fingers)
        self.step(70)

    def pick(self, x, y, z=CUBE / 2):
        self.open()
        self.move_to((x, y, z + self.LIFT))
        self.move_to((x, y, z + self.GRASP), steps=70)
        self.close()
        self.move_to((x, y, z + self.LIFT), steps=70)

    def place(self, x, y, z=CUBE / 2):
        self.move_to((x, y, z + self.LIFT))
        self.move_to((x, y, z + self.GRASP + 0.02), steps=70)
        self.open()
        self.move_to((x, y, z + self.LIFT), steps=60)

    def home(self):
        self.move_to((0.40, 0.0, 0.45), steps=80)
