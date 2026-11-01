# run.py : 「日本語の指示 -> LLM で手順 -> OWLv2 で物体の位置 -> Franka で仕分け」を Genesis で実行する
# 使い方:
#   python src/run.py demo   … 動画用に3つの指示を実行（outputs/demo_*.mp4）
#   python src/run.py eval   … 4つの指示 × 10配置 = 40回を実行して成功率を出す（outputs/sim_eval.json）
import json
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import perception
import planner
from sim import COLORS, CUBE, TRAYS, SortingScene, random_layout, to_np
from planner import COLORS_JA

OUT = "outputs"
SLOTS = [(-0.045, -0.045), (0.045, -0.045), (-0.045, 0.045), (0.045, 0.045)]   # トレイ内の置き場所
Q0 = np.array([0, -0.6, 0, -2.4, 0, 1.9, 0.79, 0.04, 0.04])
LLM = os.environ.get("LLM", "Qwen/Qwen2.5-1.5B-Instruct")
TRAY_JA = {"left": "左", "right": "右"}


def _font(size):
    for c in ["C:/Windows/Fonts/meiryo.ttc", "C:/Windows/Fonts/msgothic.ttc",
              "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"]:
        if os.path.exists(c):
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


F_BIG, F_MID = _font(30), _font(24)


def save_mp4(frames, path, fps=30):
    """PyAV で H.264 の mp4 に保存する（外部の ffmpeg を起動しないので、バックグラウンド実行でも動く）"""
    import av
    with av.open(path, "w") as c:
        st = c.add_stream("libx264", rate=fps)
        st.height, st.width = frames[0].shape[:2]
        st.pix_fmt = "yuv420p"
        for f in frames:
            for pkt in st.encode(av.VideoFrame.from_ndarray(np.ascontiguousarray(f), format="rgb24")):
                c.mux(pkt)
        for pkt in st.encode():
            c.mux(pkt)


def plan_text(steps):
    return "、".join(f"{COLORS_JA[s['object']]}→{TRAY_JA[s['place']]}" for s in steps) or "（手順なし）"


def compose(view, top, lines):
    """1280x720 の1コマ: 左上に正面カメラ、右上に真上カメラ（検出結果）、下に字幕"""
    canvas = Image.new("RGB", (1280, 720), (18, 24, 38))
    canvas.paste(Image.fromarray(view).resize((853, 480)), (0, 0))
    canvas.paste(Image.fromarray(top).resize((427, 320)), (853, 0))
    d = ImageDraw.Draw(canvas)
    d.text((865, 330), "真上カメラ + OWLv2 の検出結果", font=F_MID, fill=(180, 200, 230))
    d.text((865, 365), "（認識はこの画像で1回だけ行う）", font=_font(20), fill=(140, 155, 180))
    for i, t in enumerate(lines):
        d.text((24, 500 + i * 52), t, font=F_BIG if i == 0 else F_MID, fill=(255, 255, 255) if i == 0 else (215, 225, 240))
    return np.array(canvas)


class Runner:
    def __init__(self):
        self.s = SortingScene(random_layout(0))
        self.arm = self.s.arm
        self.H = self.calibrate()
        self.plans = {}

    def reset(self, layout):
        for n, (x, y) in layout.items():
            self.s.cubes[n].set_pos(np.array([x, y, CUBE / 2]))
            self.s.cubes[n].set_quat(np.array([1.0, 0, 0, 0]))
        self.s.franka.set_dofs_position(Q0)
        self.s.franka.control_dofs_position(Q0)
        self.arm.step(30)

    def calibrate(self):
        """カメラ較正: 既知の位置に置いたブロックの「画像上の位置（セグメンテーションの重心）」と
        「床の座標」を対応させてホモグラフィを求める（AI は使わない、一度だけの準備）"""
        samples = []
        for seed in (100, 101, 102):
            lay = random_layout(seed)
            self.reset(lay)
            _, seg = self.s.top_image(seg=True)
            offset = 1 if (seg == len(self.s.scene.entities)).any() else 0
            for n, ent in self.s.cubes.items():
                vs, us = np.nonzero(seg == ent.idx + offset)
                p = self.s.cube_pos(n)
                samples.append((us.mean(), vs.mean(), p[0], p[1]))
        H = perception.calibrate(samples)
        err = [np.hypot(*(np.array(perception.pixel_to_world(H, u, v)) - (x, y))) for u, v, x, y in samples]
        print(f"較正: {len(samples)} 点, 再投影誤差 平均 {np.mean(err) * 1000:.1f} mm", flush=True)
        np.save(f"{OUT}/calib.npy", H)
        return H

    def get_plan(self, instruction):
        if instruction not in self.plans:
            t = time.time()
            self.plans[instruction] = (*planner.plan(instruction, LLM), time.time() - t)
        return self.plans[instruction]

    def episode(self, instruction, truth, seed, record=False, title=""):
        layout = random_layout(seed)
        self.reset(layout)
        steps, raw, t_llm = self.get_plan(instruction)
        top, _ = self.s.top_image()
        t = time.time()
        found = perception.detect(top, list(COLORS))
        t_det = time.time() - t
        top_vis = perception.draw(top, found)
        loc_err = {}
        for n, (u, v, *_ ) in found.items():
            x, y = perception.pixel_to_world(self.H, u, v)
            loc_err[n] = float(np.hypot(x - layout[n][0], y - layout[n][1]))
        frames = []
        if record:
            self.arm.frames = []
            self.arm.record = True
        counts = {"left": 0, "right": 0}
        for k, st in enumerate(steps):
            n = st["object"]
            head = f"指示: 「{instruction}」"
            cap = [head, f"LLM の手順: {plan_text(steps)}",
                   f"実行中 {k + 1}/{len(steps)}: {COLORS_JA[n]}のブロックを{TRAY_JA[st['place']]}のトレイへ"]
            self.arm.caption = cap
            if n not in found:
                print(f"  {n} が見つからない", flush=True)
                continue
            x, y = perception.pixel_to_world(self.H, *found[n][:2])
            (tx, ty), _ = TRAYS[st["place"]]
            sx, sy = SLOTS[counts[st["place"]] % 4]
            counts[st["place"]] += 1
            self.arm.pick(x, y)
            self.arm.place(tx + sx, ty + sy)
        self.arm.caption = [f"指示: 「{instruction}」", f"LLM の手順: {plan_text(steps)}", "完了。結果を確認"]
        self.arm.home()
        self.arm.record = False
        where = {n: self.s.where(n) for n in COLORS}
        want = {o: p for o, p in truth}
        success = all(where[n] == want.get(n) for n in COLORS)   # 指示どおり＆ほかは動かしていない
        plan_ok = {(s["object"], s["place"]) for s in steps} == set(truth)
        res = dict(instruction=instruction, seed=seed, plan=steps, plan_ok=plan_ok, success=success,
                   where=where, loc_err_mm={k: v * 1000 for k, v in loc_err.items()},
                   detected=sorted(found), t_llm=t_llm, t_detect=t_det)
        if record:
            mark = "成功" if success else "失敗"
            for img, cap in self.arm.frames:
                frames.append(compose(img, top_vis, cap))
            final = compose(self.arm.frames[-1][0], top_vis,
                            [f"指示: 「{instruction}」", f"LLM の手順: {plan_text(steps)}",
                             f"結果: {mark}（各ブロックの位置: " + "、".join(
                                 f"{COLORS_JA[n]}={TRAY_JA.get(where[n], '机')}" for n in COLORS) + "）"])
            frames += [final] * 45
            path = f"{OUT}/{title}.mp4"
            save_mp4(frames, path)
            res["video"] = path
            print(f"  動画: {path} ({len(frames) / 30:.1f} 秒)", flush=True)
        return res


DEMOS = [  # (指示, 正解, 配置の seed)
    ("青は左、黄色は右に仕分けて", [("blue", "left"), ("yellow", "right")], 7),
    ("信号機の色のブロック（赤・黄・緑）を左に", [("red", "left"), ("yellow", "left"), ("green", "left")], 3),
    ("トマトと同じ色のブロックを左へ", [("red", "left")], 11),   # LLM が失敗する例（考察用）
]
EVAL = [
    ("赤いブロックを左のトレイに入れて", [("red", "left")]),
    ("青は左、黄色は右に仕分けて", [("blue", "left"), ("yellow", "right")]),
    ("信号機の色のブロック（赤・黄・緑）を左に", [("red", "left"), ("yellow", "left"), ("green", "left")]),
    ("黄色以外のブロックを右のトレイに入れて", [("red", "right"), ("blue", "right"), ("green", "right")]),
]

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"
    r = Runner()
    results = []
    if mode == "demo":
        for i, (inst, truth, seed) in enumerate(DEMOS):
            print(f"[demo {i + 1}] {inst}", flush=True)
            res = r.episode(inst, truth, seed, record=True, title=f"demo_{i + 1}")
            print("  ", {k: res[k] for k in ("plan", "success", "where")}, flush=True)
            results.append(res)
        json.dump(results, open(f"{OUT}/demo_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    else:
        n_seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        for inst, truth in EVAL:
            for seed in range(n_seeds):
                res = r.episode(inst, truth, seed)
                results.append(res)
                print(f"{'OK ' if res['success'] else 'NG '} seed={seed} {inst} plan_ok={res['plan_ok']} "
                      f"err={ {k: round(v) for k, v in res['loc_err_mm'].items()} }", flush=True)
        summary = {}
        for inst, _ in EVAL:
            rs = [x for x in results if x["instruction"] == inst]
            summary[inst] = {"success_rate": sum(x["success"] for x in rs) / len(rs), "n": len(rs),
                             "plan_ok": all(x["plan_ok"] for x in rs)}
        errs = [v for x in results for v in x["loc_err_mm"].values()]
        summary["_overall"] = {"success_rate": sum(x["success"] for x in results) / len(results), "n": len(results),
                               "loc_err_mean_mm": float(np.mean(errs)), "loc_err_max_mm": float(np.max(errs)),
                               "detect_rate": float(np.mean([len(x["detected"]) == 4 for x in results])),
                               "t_detect_mean_s": float(np.mean([x["t_detect"] for x in results])),
                               "llm": LLM}
        print(json.dumps(summary, ensure_ascii=False, indent=1), flush=True)
        json.dump({"summary": summary, "episodes": results}, open(f"{OUT}/sim_eval.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
