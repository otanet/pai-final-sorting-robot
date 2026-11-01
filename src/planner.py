# planner.py : 日本語の指示を、ロボットが実行できる手順（JSON）に変換する
# LLM（Qwen2.5-Instruct。ローカルで推論、API キー不要）に few-shot で JSON を書かせ、
# 存在しない色やトレイを含む手順は捨てる（安全のための検証）。
import json
import re
import torch

COLORS_JA = {"red": "赤", "blue": "青", "green": "緑", "yellow": "黄色"}
SYSTEM = """あなたはロボットアームの作業計画係です。机の上には red, blue, green, yellow の4つのブロックと、
left（左）と right（右）の2つのトレイがあります。ユーザーの日本語の指示を、実行する手順の JSON 配列に変換してください。
各要素は {"object": 色, "place": "left" または "right"} です。動かさないブロックは含めません。
JSON 配列だけを出力し、説明は書かないでください。"""
FEWSHOT = [
    ("赤いブロックを左のトレイに入れて", '[{"object": "red", "place": "left"}]'),
    ("青と黄色を右に片付けて", '[{"object": "blue", "place": "right"}, {"object": "yellow", "place": "right"}]'),
]
# v2: 失敗の分析（「〜以外」と、色を連想させる言葉）をもとに、規則と例を足したプロンプト。
# 例にはテストの指示（eval_planner.py）と同じ言葉は使わない。
SYSTEM_V2 = SYSTEM + """
規則:
- 「〜以外」は、その色を除いた残りすべての色を意味します。
- 物の名前で色を表すときは、その物の代表的な色に置き換えます（例: バナナ→yellow、葉っぱ→green、海→blue、いちご→red）。
- 「AとBは右、CとDは左」のように複数のまとまりがあるときは、それぞれの色に正しいトレイを対応させます。"""
FEWSHOT_V2 = FEWSHOT + [
    ("赤以外のブロックを左に集めて", '[{"object": "blue", "place": "left"}, {"object": "green", "place": "left"}, {"object": "yellow", "place": "left"}]'),
    ("バナナと同じ色のブロックを右へ", '[{"object": "yellow", "place": "right"}]'),
    ("緑と青は右、赤は左に分けて", '[{"object": "green", "place": "right"}, {"object": "blue", "place": "right"}, {"object": "red", "place": "left"}]'),
]
PROMPTS = {"v1": (SYSTEM, FEWSHOT), "v2": (SYSTEM_V2, FEWSHOT_V2)}
_LLM = {}


def _load(model_id):
    if model_id not in _LLM:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(model_id)
        import transformers
        kw = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"   # 版による引数名の違い
        model = AutoModelForCausalLM.from_pretrained(model_id, **{kw: torch.float32}).eval()
        _LLM[model_id] = (tok, model)
    return _LLM[model_id]


def plan(instruction, model_id="Qwen/Qwen2.5-1.5B-Instruct", prompt="v2"):
    """戻り値: (手順のリスト, LLM の生の出力)"""
    tok, model = _load(model_id)
    system, fewshot = PROMPTS[prompt]
    msgs = [{"role": "system", "content": system}]
    for q, a in fewshot:
        msgs += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
    msgs.append({"role": "user", "content": instruction})
    inp = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
    with torch.no_grad():
        out = model.generate(**inp, max_new_tokens=120, do_sample=False)
    raw = tok.decode(out[0, inp["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return validate(raw), raw


def validate(raw):
    """JSON を取り出し、知らない色・トレイ・重複を除く"""
    m = re.search(r"\[.*\]", raw, re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        return []
    steps, seen = [], set()
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        o, p = str(it.get("object", "")).lower(), str(it.get("place", "")).lower()
        if o in COLORS_JA and p in ("left", "right") and o not in seen:
            steps.append({"object": o, "place": p})
            seen.add(o)
    return steps
