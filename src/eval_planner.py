# eval_planner.py : 指示 -> 手順 の変換の正しさを、LLM の大きさ（0.5B / 1.5B）で比べる
# 使い方: python src/eval_planner.py   （結果は outputs/planner_eval.json）
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from planner import plan

R, B, G, Y = "red", "blue", "green", "yellow"
L, Rt = "left", "right"
# (指示, 正解の手順) 。正解は順番を問わない集合で比べる
CASES = [
    ("赤いブロックを左のトレイに入れて", {(R, L)}),
    ("緑のブロックを右に置いて", {(G, Rt)}),
    ("青は左、黄色は右に仕分けて", {(B, L), (Y, Rt)}),
    ("赤と緑を両方とも右のトレイへ", {(R, Rt), (G, Rt)}),
    ("黄色いのを左に片付けてください", {(Y, L)}),
    ("全部のブロックを左のトレイに集めて", {(R, L), (B, L), (G, L), (Y, L)}),
    ("黄色以外のブロックを右のトレイに入れて", {(R, Rt), (B, Rt), (G, Rt)}),
    ("信号機の色のブロック（赤・黄・緑）を左に", {(R, L), (Y, L), (G, L)}),
    ("赤と黄色は右、青と緑は左に分けて", {(R, Rt), (Y, Rt), (B, L), (G, L)}),
    ("青いブロックだけ右に動かして、ほかは触らないで", {(B, Rt)}),
    ("トマトと同じ色のブロックを左へ", {(R, L)}),
    ("晴れた空と同じ色のブロックを右へ", {(B, Rt)}),
]
MODELS = ["Qwen/Qwen2.5-0.5B-Instruct", "Qwen/Qwen2.5-1.5B-Instruct"]

if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    report = {}
    for m, pv in [(m, pv) for pv in ("v1", "v2") for m in MODELS]:
        key = f"{m.split('/')[-1]} / prompt {pv}"
        rows, t0 = [], time.time()
        for inst, gt in CASES:
            steps, raw = plan(inst, m, pv)
            got = {(s["object"], s["place"]) for s in steps}
            rows.append({"instruction": inst, "ok": got == gt, "plan": steps, "raw": raw,
                         "truth": sorted(gt)})
            print(f"[{key}] {'OK ' if got == gt else 'NG '} {inst} -> {sorted(got)}", flush=True)
        acc = sum(r["ok"] for r in rows) / len(rows)
        report[key] = {"accuracy": acc, "sec_per_instruction": (time.time() - t0) / len(rows), "rows": rows}
        print(f"==> {key}: 正解率 {acc * 100:.0f}%  ({report[key]['sec_per_instruction']:.1f} 秒/指示)", flush=True)
    json.dump(report, open("outputs/planner_eval.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
