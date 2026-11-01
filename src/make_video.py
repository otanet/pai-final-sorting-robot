# make_video.py : 提出用動画（1分〜3分、1920x1080）を組み立てる
#   OP → 表紙 → 課題 → 構成 → Genesis の実行 → 評価 → ROS 2 + Gazebo の実行 → 予備実験 → まとめ → ED
# 使い方: python src/make_video.py   （outputs/ に素材があること）
import json
import os
import sys

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = "outputs"
YT = os.path.join("..", "■YouTubeでの動画提出_PAI最終課題_usagisan2020")
SLIDE = os.path.join("..", "■レポート（PDF形式）_説明資料_PAI最終課題_usagisan2020.pdf", "PAI応用1_最終課題_スライド.jpg")
DST = f"{OUT}/PAI最終課題_usagisan2020.mp4"
W, H, FPS = 1920, 1080, 30
F_B = "C:/Windows/Fonts/YuGothB.ttc"
F_M = "C:/Windows/Fonts/YuGothM.ttc"
OLIVE, DARK = (177, 175, 143), (30, 30, 30)
font = lambda size, bold=False: ImageFont.truetype(F_B if bold else F_M, size)


class Writer:
    def __init__(self, path):
        self.c = av.open(path, "w")
        self.s = self.c.add_stream("libx264", rate=FPS)
        self.s.width, self.s.height, self.s.pix_fmt = W, H, "yuv420p"
        self.s.options = {"crf": "20"}
        self.n = 0

    def put(self, img, times=1):
        fr = av.VideoFrame.from_ndarray(np.ascontiguousarray(np.asarray(img)[..., :3]).astype(np.uint8), format="rgb24")
        for _ in range(times):
            for p in self.s.encode(fr):
                self.c.mux(p)
            self.n += 1

    def close(self):
        for p in self.s.encode():
            self.c.mux(p)
        self.c.close()


def fit(img, w=W, h=H, bg=(0, 0, 0)):
    im = Image.fromarray(np.asarray(img)[..., :3]) if not isinstance(img, Image.Image) else img
    s = min(w / im.width, h / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), bg)
    canvas.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return canvas


def wrap(text, width):
    """全角を1、半角を0.55として width 文字ぶんで折り返す。英数字のかたまり（92%、SO-101 など）は途中で切らない"""
    import re
    tokens = re.findall(r"[A-Za-z0-9.%+\-_/:]+|.", text)
    lines, cur, n = [], "", 0.0
    for tok in tokens:
        w = sum(0.55 if ord(ch) < 128 else 1.0 for ch in tok)
        if n + w > width and cur:
            lines.append(cur)
            cur, n = "", 0.0
        cur += tok
        n += w
    return lines + [cur] if cur else lines


def card(title, bullets=(), image=None, kicker=""):
    """講座のスライドに合わせた白地＋オリーブ色の帯のカード"""
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 24, H], fill=OLIVE)
    if kicker:
        d.text((90, 60), kicker, font=font(30), fill=(120, 118, 90))
    d.text((90, 105), title, font=font(60, True), fill=DARK)
    d.line([(90, 200), (W - 90, 200)], fill=OLIVE, width=4)
    x_text = 110
    y = 250
    if image is not None:
        pic = Image.open(image).convert("RGB")
        box_w = 960 if bullets else W - 180
        pic = fit(pic, box_w, H - 330, bg=(255, 255, 255))
        im.paste(pic, (W - box_w - 70 if bullets else 90, 240))
    side = image is not None          # 図があるときは左の列（約 750px）に収まるように折り返す
    width, size = (21, 34) if side else (44, 40)
    for b in bullets:
        lines = wrap(b, width)
        for k, ln in enumerate(lines):
            d.text((x_text, y), ("・" if k == 0 else "　") + ln, font=font(size), fill=DARK)
            y += int(size * 1.45)
        y += 16
    d.text((90, H - 60), "Physical AI 応用編1 最終課題 / usagisan2020", font=font(24), fill=(150, 150, 150))
    return im


def band(frame, lines, speed_note=""):
    """映像の下に字幕の帯をつける（映像は上の 1920x900 に収める）"""
    im = fit(frame, W, 900, bg=(18, 24, 38))
    canvas = Image.new("RGB", (W, H), (18, 24, 38))
    canvas.paste(im, (0, 0))
    d = ImageDraw.Draw(canvas)
    for i, t in enumerate(lines[:2]):
        d.text((40, 918 + i * 66), t, font=font(44 if i == 0 else 38, i == 0), fill=(255, 255, 255) if i == 0 else (215, 225, 240))
    if speed_note:
        d.rounded_rectangle([W - 330, 20, W - 20, 90], 14, fill=(0, 0, 0))
        d.text((W - 175, 55), speed_note, font=font(36, True), fill=(255, 220, 80), anchor="mm")
    return canvas


def frames_of(path):
    with av.open(path) as c:
        v = c.streams.video[0]
        fps = float(v.average_rate)
        for f in c.decode(v):
            yield float(f.pts * v.time_base), f.to_ndarray(format="rgb24"), fps


def play(w, path, speed=1.0, t0=0.0, t1=1e9, deco=lambda t, img: fit(img)):
    """path の [t0, t1) を speed 倍速で書き出す。deco(元の時刻, 画像) で字幕などを付ける"""
    emitted, start = 0, None
    for t, img, fps in frames_of(path):
        if t < t0:
            continue
        if t >= t1:
            break
        start = t if start is None else start
        target = int(round((t - start + 1 / fps) / speed * FPS))
        if emitted >= target:
            continue
        out = deco(t, img)
        w.put(out, target - emitted)
        emitted = target


def gazebo_segment(w):
    path = f"{OUT}/gazebo/gz_demo_1.mp4"
    ev = [json.loads(l) for l in open(f"{OUT}/gazebo/gz_demo_1.jsonl", encoding="utf-8")]
    t_rec = next(e["t"] for e in ev if e["topic"] == "record_start")
    inst = next(e["data"] for e in ev if e["topic"] == "instruction")
    t_plan = next(e["t"] for e in ev if e["topic"] == "plan") - t_rec
    st = [(e["t"] - t_rec, e["data"]) for e in ev if e["topic"] == "status"]
    plan_txt = next((s for _, s in st if s.startswith("LLM の手順")), "")

    def status_at(t):
        cur = ""
        for ts, s in st:
            if ts <= t:
                cur = s
        return cur

    head = f"ROS 2 + Gazebo（CRANE+ V2）  指示: 「{inst}」"
    play(w, path, 1.0, 0, 6, lambda t, im: band(im, [head, status_at(t) or "指示を /instruction トピックに送信"]))
    wait = t_plan - 6
    w.put(band(next(frames_of(path))[1], [head, f"planner_node（LLM）が計画中 … 約 {wait:.0f} 秒かかるため省略"], "省略"), FPS * 3)
    play(w, path, 2.0, t_plan - 1, 1e9, lambda t, im: band(im, [head, f"{plan_txt}  ／  {status_at(t)}"], "2倍速"))


def main():
    os.makedirs(OUT, exist_ok=True)
    plan_ev = json.load(open(f"{OUT}/planner_eval.json", encoding="utf-8"))
    sim_all = json.load(open(f"{OUT}/sim_eval.json", encoding="utf-8"))
    sim = sim_all["summary"]
    plan_ok = [e for e in sim_all["episodes"] if e["plan_ok"]]
    ok_given_plan = sum(e["success"] for e in plan_ok) / len(plan_ok)
    acc = {k: v["accuracy"] * 100 for k, v in plan_ev.items()}
    o = sim["_overall"]
    w = Writer(DST)

    play(w, f"{YT}/PAI応用1_最終課題_OP.mp4")
    # 表紙: 講座のスライドの左下に題名を重ねる
    cover = Image.open(SLIDE).convert("RGB").resize((W, H))
    d = ImageDraw.Draw(cover)
    d.text((88, 690), "言葉で頼むと仕分けるロボット", font=font(56, True), fill=DARK)
    d.text((90, 770), "LLM の計画 × オープン語彙の物体検出", font=font(32), fill=(70, 70, 70))
    d.text((90, 815), "Genesis / ROS 2 + Gazebo", font=font(32), fill=(70, 70, 70))
    d.text((90, 870), "omnicampus: usagisan2020", font=font(28), fill=(110, 110, 110))
    w.put(cover, FPS * 5)
    w.put(card("どんな課題か", [
        "日本語の指示（例:「青は左、黄色は右に仕分けて」）を、ロボットが自分で手順に分けて実行する",
        "目的: 人が言葉で頼むだけで、物流や片付けの仕分けができるロボットの基本を作る",
        "講義のツール（Genesis、ROS 2 + Gazebo の CRANE+ V2）で動かし、成功率を数字で確かめる",
    ], kicker="1. 課題と目的"), FPS * 8)
    w.put(card("システムの構成", [], image=f"{OUT}/fig_system.png", kicker="2. 仕組み"), FPS * 8)

    for i, label in [(1, "Genesis（Franka）デモ1"), (2, "Genesis（Franka）デモ2")]:
        play(w, f"{OUT}/demo_{i}.mp4")
    play(w, f"{OUT}/demo_3.mp4")
    w.put(card("失敗から改善へ: プロンプト v2", [
        "失敗の例: 「トマトと同じ色」→ LLM が手順を出せなかった（連想）",
        "「黄色以外」→ 緑だけを選んだ（否定）",
        "対策: 規則（「〜以外」・物の名前→色）と、テストとは別の例を3つ追加",
        f"結果（1.5B）: 正解率 {acc['Qwen2.5-1.5B-Instruct / prompt v1']:.0f}% → {acc['Qwen2.5-1.5B-Instruct / prompt v2']:.0f}%",
    ], image=f"{OUT}/fig_planner.png", kicker="3. 工夫した点"), FPS * 10)
    w.put(card("Genesis での成功率（配置を変えて 40 回）", [
        f"全体の成功率: {o['success_rate'] * 100:.1f}%（{o['n']} 回）",
        f"位置の推定誤差: 平均 {o['loc_err_mean_mm']:.1f} mm（最大 {o['loc_err_max_mm']:.0f} mm）",
        f"LLM の計画が正しかった {len(plan_ok)} 回に限ると: {ok_given_plan * 100:.0f}%",
        "失敗の多くは「黄色以外」の計画の誤り。1回はアームの陰でブロックが見えなかった",
    ], image=f"{OUT}/fig_success.png", kicker="4. 評価"), FPS * 10)

    w.put(card("同じ計画を ROS 2 + Gazebo で", [
        "講義の Docker イメージ（ROS 2 Humble・Ignition Gazebo・CRANE+ V2）で実行",
        "ノード: /instruction → planner_node（LLM）→ /plan → sorter_node",
        "sorter_node は教科書の逆運動学と ros2_control のアクションでアームを動かす",
        "※ Gazebo 版のブロックの位置はシミュレータの既知の値（認識は Genesis 版で評価）",
    ], kicker="5. ROS 2 + Gazebo"), FPS * 8)
    gazebo_segment(w)

    w.put(card("予備実験（Colab / MuJoCo）", [
        "A01: TurtleBot3 が YOLO で物体を見つけて追従",
        "A02: UR アームが、名前で指定した物体を OWLv2 で探して運ぶ",
        "→ A02 の「名前で物体を探す」を、今回の認識部分に発展させた",
    ], kicker="6. これまでの取り組み"), FPS * 5)
    play(w, f"{YT}/a01_yolo_follow_20261031.mp4", 3.0, 0, 30,
         lambda t, im: band(im, ["予備実験 A01: TurtleBot3 + YOLO 追従（MuJoCo）", ""], "3倍速"))
    play(w, f"{YT}/a02_pick_by_name_20261031.mp4", 1.0, 0, 13.5,
         lambda t, im: band(im, ["予備実験 A02: 名前で指定した物体を拾う（OWLv2 + MuJoCo）", ""]))

    w.put(card("まとめと今後", [
        f"言葉の指示 → LLM の計画 → 物体検出 → アーム、を1つにつなぎ、Genesis で成功率 {o['success_rate'] * 100:.1f}%（計画が正しければ {ok_given_plan * 100:.0f}%）",
        f"プロンプトの改善で、LLM の計画の正解率を {acc['Qwen2.5-1.5B-Instruct / prompt v1']:.0f}% → {acc['Qwen2.5-1.5B-Instruct / prompt v2']:.0f}% に上げた",
        "同じ計画を ROS 2 のノードにして、Gazebo の CRANE+ V2 でも実行できた",
        "今後: Gazebo 側にもカメラと物体検出を入れる／実機 CRANE+ V2・SO-101 で試す",
    ], kicker="7. まとめ"), FPS * 9)
    play(w, f"{YT}/PAI応用1_最終課題_ED.mp4")
    w.close()
    print(f"{DST}: {w.n / FPS:.1f} 秒")
    assert 60 <= w.n / FPS <= 180, "長さが 1〜3 分の範囲外です"


if __name__ == "__main__":
    main()
