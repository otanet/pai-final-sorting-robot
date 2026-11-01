# make_figures.py : レポートと動画に使う図を作る（評価結果のグラフ・システム構成図）
# 使い方: python src/make_figures.py   （outputs/planner_eval.json と outputs/sim_eval.json が必要）
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

OUT = "outputs"
FONT = "C:/Windows/Fonts/YuGothM.ttc" if os.path.exists("C:/Windows/Fonts/YuGothM.ttc") else None
FONT_B = "C:/Windows/Fonts/YuGothB.ttc" if os.path.exists("C:/Windows/Fonts/YuGothB.ttc") else FONT
if FONT:
    font_manager.fontManager.addfont(FONT)
    plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()
ACCENT, GRAY, DARK = "#8C8A6A", "#C9C7B5", "#2B2B2B"


def planner_chart():
    rep = json.load(open(f"{OUT}/planner_eval.json", encoding="utf-8"))
    keys = ["Qwen2.5-0.5B-Instruct / prompt v1", "Qwen2.5-1.5B-Instruct / prompt v1",
            "Qwen2.5-0.5B-Instruct / prompt v2", "Qwen2.5-1.5B-Instruct / prompt v2"]
    labels = ["0.5B\nプロンプトv1", "1.5B\nプロンプトv1", "0.5B\nプロンプトv2", "1.5B\nプロンプトv2"]
    vals = [rep[k]["accuracy"] * 100 for k in keys]
    secs = [rep[k]["sec_per_instruction"] for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    bars = ax.bar(labels, vals, color=[GRAY, GRAY, ACCENT, ACCENT], width=0.6)
    for b, v, s in zip(bars, vals, secs):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=15, color=DARK)
        ax.text(b.get_x() + b.get_width() / 2, 4, f"{s:.0f}秒/指示", ha="center", fontsize=10, color="white")
    ax.set_ylim(0, 110)
    ax.set_ylabel("正しい手順を出せた割合 [%]")
    ax.set_title("LLM の計画の正解率（日本語の指示 12 個）", fontsize=14)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_planner.png")
    plt.close(fig)


def success_chart():
    s = json.load(open(f"{OUT}/sim_eval.json", encoding="utf-8"))["summary"]
    insts = [k for k in s if not k.startswith("_")]
    vals = [s[k]["success_rate"] * 100 for k in insts]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    bars = ax.barh([i.replace("のブロック", "") for i in insts][::-1], vals[::-1], color=ACCENT, height=0.55)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.0f}%", va="center", fontsize=13, color=DARK)
    ax.set_xlim(0, 115)
    ax.set_xlabel("成功率 [%]（配置を変えて各 10 回）")
    o = s["_overall"]
    ax.set_title(f"Genesis での仕分けの成功率（全体 {o['success_rate'] * 100:.1f}%、{o['n']} 回）", fontsize=14)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_success.png")
    plt.close(fig)


def system_diagram():
    """システム構成図（指示 → LLM → 手順 → 認識 → 動作）"""
    W, H = 1800, 760
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    fb, fm, fs = ImageFont.truetype(FONT_B, 34), ImageFont.truetype(FONT, 26), ImageFont.truetype(FONT, 22)

    def box(x, y, w, h, title, sub, fill):
        d.rounded_rectangle([x, y, x + w, y + h], 18, fill=fill, outline=DARK, width=2)
        d.text((x + w / 2, y + 42), title, font=fb, fill=DARK, anchor="mm")
        for i, t in enumerate(sub):
            d.text((x + w / 2, y + 92 + i * 34), t, font=fs, fill=DARK, anchor="mm")

    def arrow(x1, y1, x2, y2, label=""):
        d.line([x1, y1, x2, y2], fill=DARK, width=4)
        d.polygon([(x2, y2), (x2 - 18, y2 - 10), (x2 - 18, y2 + 10)], fill=DARK)
        if label:
            d.text(((x1 + x2) / 2, y1 - 22), label, font=fs, fill="#555", anchor="mm")

    y = 90
    box(30, y, 300, 200, "日本語の指示", ["例: 青は左、", "黄色は右に仕分けて"], "#F2F1EA")
    arrow(330, y + 100, 420, y + 100)
    box(420, y, 380, 200, "LLM（計画）", ["Qwen2.5-1.5B-Instruct", "ローカル推論・API キー不要", "few-shot で JSON を出力"], "#E4E2D3")
    arrow(800, y + 100, 890, y + 100)
    box(890, y, 400, 200, "OWLv2（認識）", ["真上カメラの画像から", "名前でブロックを検出", "ホモグラフィで床の座標へ"], "#E4E2D3")
    arrow(1290, y + 100, 1380, y + 100)
    box(1380, y, 390, 200, "アーム（動作）", ["逆運動学で関節角を計算", "つかむ → 運ぶ → 置く", "結果をシミュレータで判定"], "#F2F1EA")
    d.text((W / 2, 380), "同じ「LLM の計画」を、2つの講義ツールで動かす", font=fb, fill=DARK, anchor="mm")
    box(130, 440, 700, 280, "Genesis 版（Franka）", ["4色のブロック・左右のトレイ", "OWLv2 で位置を認識して仕分け", "配置を変えて 40 回評価（成功率）"], "#FFFFFF")
    box(970, 440, 700, 280, "ROS 2 + Gazebo 版（CRANE+ V2）", ["講義の Docker イメージで実行", "/instruction → planner_node → /plan", "→ sorter_node（ros2_control）"], "#FFFFFF")
    im.save(f"{OUT}/fig_system.png")


if __name__ == "__main__":
    planner_chart()
    success_chart()
    system_diagram()
    print("figures saved")
