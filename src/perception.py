# perception.py : 真上カメラの画像から、名前で指定したブロックを見つけて床の座標に変換する
# - 検出: OWLv2（オープン語彙の物体検出。学習なし・推論のみ）
# - 画素 -> 床の座標: ホモグラフィ（床は平面なので 3x3 行列1つで変換できる）
import numpy as np
import torch
from PIL import Image

QUERY = {"red": "a red cube", "blue": "a blue cube", "green": "a green cube", "yellow": "a yellow cube"}
_MODEL = {}


def _owl():
    if not _MODEL:
        from transformers import Owlv2Processor, Owlv2ForObjectDetection
        name = "google/owlv2-base-patch16-ensemble"
        _MODEL["proc"] = Owlv2Processor.from_pretrained(name)
        _MODEL["model"] = Owlv2ForObjectDetection.from_pretrained(name).eval()
    return _MODEL["proc"], _MODEL["model"]


def detect(img, names, thr=0.1):
    """{名前: (u, v, score, (x1, y1, x2, y2))}。名前ごとに一番スコアの高い枠を返す"""
    proc, model = _owl()
    inp = proc(text=[[QUERY[n] for n in names]], images=Image.fromarray(img), return_tensors="pt")
    with torch.no_grad():
        out = model(**inp)
    S = max(img.shape[:2])                     # OWLv2 は正方形にパディングして推論する
    res = proc.post_process_grounded_object_detection(out, threshold=thr, target_sizes=torch.tensor([[S, S]]))[0]
    found = {}
    for s, l, b in zip(res["scores"].tolist(), res["labels"].tolist(), res["boxes"].tolist()):
        n = names[l]
        if n not in found or s > found[n][2]:
            found[n] = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, s, tuple(b))
    return found


def calibrate(samples):
    """samples: [(u, v, x, y), ...] からホモグラフィを求める（最小二乗, DLT）"""
    A = []
    for u, v, x, y in samples:
        A.append([u, v, 1, 0, 0, 0, -x * u, -x * v, -x])
        A.append([0, 0, 0, u, v, 1, -y * u, -y * v, -y])
    _, _, vt = np.linalg.svd(np.asarray(A, dtype=float))
    H = vt[-1].reshape(3, 3)
    return H / H[2, 2]


def pixel_to_world(H, u, v):
    p = H @ np.array([u, v, 1.0])
    return float(p[0] / p[2]), float(p[1] / p[2])


def draw(img, found, color=(255, 230, 0)):
    from PIL import ImageDraw
    im = Image.fromarray(img.copy())
    d = ImageDraw.Draw(im)
    for n, (u, v, s, (x1, y1, x2, y2)) in found.items():
        d.rectangle([x1, y1, x2, y2], outline=color, width=3)
        d.text((x1, max(0, y1 - 14)), f"{n} {s:.2f}", fill=color)
    return np.array(im)
