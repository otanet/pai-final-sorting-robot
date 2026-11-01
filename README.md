# 言葉で頼むと仕分けるロボット（Physical AI 応用編1 最終課題）

日本語の指示（例:「青は左、黄色は右に仕分けて」）を、ロボットが自分で手順に分けて実行します。

- **計画**: LLM（Qwen2.5-1.5B-Instruct、ローカル推論・API キー不要）が、指示を手順の JSON に変換
- **認識**: オープン語彙の物体検出 OWLv2 が、真上カメラの画像からブロックを名前で見つけ、ホモグラフィで床の座標に変換
- **動作**: アームが逆運動学で「つかむ → 運ぶ → 置く」
- 同じ計画を、講義で使った2つのシミュレータで動かしました
  - **Genesis**（Franka、4色のブロック）… 配置を変えて 40 回評価
  - **ROS 2 Humble + Gazebo**（CRANE+ V2、講義の Docker イメージ）… `planner_node` と `sorter_node` を自作

## 結果

- LLM の計画の正解率（指示 12 個、1.5B）: プロンプト v1 67% → v2 92%
- LLM の計画の正解率（0.5B）: v1 42% → v2 67%
- Genesis での仕分けの成功率（40 回）: 72.5%（計画が正しかった 30 回では 97%）
- 位置の推定誤差（OWLv2 + ホモグラフィ）: 平均 2.3 mm、最大 12 mm
- ROS 2 + Gazebo: 「赤は右、青は左のトレイに仕分けて」を完了

失敗の内訳: 11 回のうち 10 回は「黄色以外のブロックを右に」で LLM が手順を誤ったもの、1 回は緑のブロックがアームの陰になり検出できなかったもの。

## ファイル構成

```
src/
  sim.py            Genesis の仕分け台（Franka・ブロック・トレイ・カメラ2台）と pick/place
  perception.py     OWLv2 による検出と、ホモグラフィ（画素 → 床の座標）
  planner.py        LLM で指示 → 手順（JSON）。プロンプト v1 / v2 と検証
  eval_planner.py   LLM の大きさ（0.5B/1.5B）× プロンプト（v1/v2）で正解率を比較
  run.py            demo（動画3本）/ eval（4指示 × 10配置 = 40回）
  make_figures.py   グラフと構成図
  make_video.py     提出用動画（OP・ED つき、1920x1080、1〜3分）
ros2/
  start_gazebo.sh   講義の Docker の中で CRANE+ V2 の Gazebo を起動し、机を用意
  gz_scene.py       ブロックとトレイを置く（何度でも置き直せる）
  planner_node.py   /instruction → LLM → /plan
  sorter_node.py    /plan → 逆運動学 → ros2_control（FollowJointTrajectory）
  status_recorder.py, record_demo.sh   録画と字幕用の記録
report/
  build_report.js   説明資料（PowerPoint）を作るスクリプト
outputs/            評価結果（JSON）・図・動画
```

## 動かし方

### Genesis 版（Windows / Linux、CPU で可）

```bash
pip install -r requirements.txt
python src/eval_planner.py      # LLM の比較（outputs/planner_eval.json）
python src/run.py demo          # デモ動画3本（outputs/demo_*.mp4）
python src/run.py eval 10       # 40 回の評価（outputs/sim_eval.json）
python src/make_figures.py
```

初回は Hugging Face から Qwen2.5-0.5B/1.5B-Instruct と OWLv2 をダウンロードします。

### ROS 2 + Gazebo 版（講義の Docker イメージ）

```bash
docker run -d --name pai_final -p 6081:80 --shm-size=1g -v "$(pwd):/work" airobotbook/ros2-desktop-ai-robot-book-humble:latest
# ブラウザで http://localhost:6081 を開くと画面が見えます
docker exec -u root pai_final pip3 install transformers==4.46.3 "accelerate<1.2"
docker exec -u ubuntu -e DISPLAY=:0 pai_final bash /work/ros2/start_gazebo.sh
docker exec -d -u ubuntu pai_final bash -lc "source /opt/ros/humble/setup.bash; source ~/airobot_ws/install/setup.bash; cd /work/ros2; python3 planner_node.py"
docker exec -d -u ubuntu pai_final bash -lc "source /opt/ros/humble/setup.bash; source ~/airobot_ws/install/setup.bash; cd /work/ros2; python3 sorter_node.py"
docker exec -u ubuntu -e DISPLAY=:0 pai_final bash /work/ros2/record_demo.sh "赤は右、青は左のトレイに仕分けて" gz_demo_1
```

## 工夫した点

1. **失敗の分析からプロンプトを改善**: v1 の失敗（連想「トマトと同じ色」、否定「黄色以外」）を見て、規則と例を追加。例にはテストと同じ言葉を使わないようにした。
2. **再現できる評価**: 配置を seed で固定し、指示 4 種 × 配置 10 種で成功率を数えた（第2回講義の考え方）。
3. **安全のための検証**: LLM の出力から、存在しない色・トレイや重複を捨ててから実行する。
4. **同じ計画を ROS 2 のノードに**: 計画（`src/planner.py`）を共通にし、Genesis と Gazebo（ROS 2）の両方で使った。

## ライセンスと利用したもの

- このリポジトリのコード: MIT License（`LICENSE`）
- Genesis（Apache-2.0）、Qwen2.5（Apache-2.0）、OWLv2（Apache-2.0）、Franka のモデル（Genesis 同梱）
- CRANE+ V2 の逆運動学は『ROS 2とPythonで作って学ぶAIロボット入門 改訂第2版』の `crane_plus_commander/kinematics.py`（講義の Docker イメージ内）を import して使用
- 動画の OP・ED と表紙のスライドは講座から提供されたもの
