// build_report.js : 説明資料（PowerPoint）を作る。数値は outputs/*.json から読む
// 使い方: cd report && node build_report.js   → 説明資料_PAI最終課題_usagisan2020.pptx
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.join(__dirname, "..");
const OUT = path.join(ROOT, "outputs");
const SLIDE_BG = path.join(ROOT, "..", "■レポート（PDF形式）_説明資料_PAI最終課題_usagisan2020.pdf", "PAI応用1_最終課題_スライド.jpg");
const planEval = JSON.parse(fs.readFileSync(path.join(OUT, "planner_eval.json"), "utf8"));
const simAll = JSON.parse(fs.readFileSync(path.join(OUT, "sim_eval.json"), "utf8"));
const sim = simAll.summary;
const planOk = simAll.episodes.filter((e) => e.plan_ok);
const okGivenPlan = planOk.filter((e) => e.success).length / planOk.length;   // 計画が正しかった回の成功率
const o = sim._overall;
const acc = (k) => Math.round(planEval[k].accuracy * 100);
const A = {
  s05v1: acc("Qwen2.5-0.5B-Instruct / prompt v1"), s15v1: acc("Qwen2.5-1.5B-Instruct / prompt v1"),
  s05v2: acc("Qwen2.5-0.5B-Instruct / prompt v2"), s15v2: acc("Qwen2.5-1.5B-Instruct / prompt v2"),
};
const pct = (x) => `${Math.round(x * 100)}%`;

// 色は講座のスライド（オリーブ色）に合わせる
const COL = { olive: "8C8A6A", oliveL: "B1AF8F", tint: "F4F3EC", dark: "222222", mid: "5A5A5A", blue: "2E5E8C", red: "B03A2E", white: "FFFFFF" };
const FONT = "Yu Gothic";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 inch
pres.title = "説明資料_PAI最終課題_usagisan2020";
pres.author = "usagisan2020";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: COL.white },
  objects: [
    { text: { text: "Physical AI 応用編1 最終課題 / usagisan2020", options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: "8A8A8A", fontFace: FONT } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "8A8A8A", fontFace: FONT },
  placeholders: [],
});

function title(slide, kicker, text) {
  slide.addText(kicker, { x: 0.6, y: 0.35, w: 12, h: 0.35, fontSize: 14, color: COL.olive, bold: true, isTextBox: true, margin: 0 });
  slide.addText(text, { x: 0.6, y: 0.7, w: 12.1, h: 0.75, fontSize: 32, color: COL.dark, bold: true, isTextBox: true, margin: 0 });
}

function cardBox(slide, x, y, w, h, head, body, opts = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: opts.fill || COL.tint }, line: { color: opts.fill || COL.tint } });
  slide.addText(head, { x: x + 0.25, y: y + 0.18, w: w - 0.5, h: 0.45, fontSize: 18, bold: true, color: opts.headColor || COL.dark, isTextBox: true, margin: 0 });
  slide.addText(body.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < body.length - 1 } })),
    { x: x + 0.25, y: y + 0.7, w: w - 0.5, h: h - 0.85, fontSize: 14, color: COL.dark, valign: "top", paraSpaceAfter: 6, isTextBox: true, margin: 0 });
}

function stat(slide, x, y, w, big, label, color) {
  slide.addText(big, { x, y, w, h: 0.95, fontSize: 48, bold: true, color: color || COL.olive, isTextBox: true, margin: 0 });
  slide.addText(label, { x, y: y + 0.95, w, h: 0.5, fontSize: 13, color: COL.mid, isTextBox: true, margin: 0 });
}

function image(slide, file, x, y, w, h, caption) {
  slide.addImage({ path: file, x, y, w, h, sizing: { type: "contain", w, h } });
  if (caption) slide.addText(caption, { x, y: y + h + 0.05, w, h: 0.35, fontSize: 11, color: COL.mid, isTextBox: true, margin: 0 });
}

// 1. 表紙（講座のスライドを背景に使う）
{
  const s = pres.addSlide();
  s.background = { path: SLIDE_BG };
  s.addText("言葉で頼むと仕分けるロボット", { x: 0.6, y: 4.7, w: 6.0, h: 0.65, fontSize: 28, bold: true, color: COL.dark, isTextBox: true, margin: 0 });
  s.addText([{ text: "LLM の計画 × オープン語彙の物体検出", options: { breakLine: true } }, { text: "Genesis / ROS 2 + Gazebo" }], { x: 0.6, y: 5.35, w: 5.6, h: 0.65, fontSize: 15, color: "444444", isTextBox: true, margin: 0 });
  s.addText("omnicampus: usagisan2020", { x: 0.6, y: 6.05, w: 5.6, h: 0.35, fontSize: 13, color: "666666", isTextBox: true, margin: 0 });
}

// 2. 課題の概要と目的
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "1. 課題の概要と目的", "日本語の指示どおりに、ロボットがブロックを仕分ける");
  cardBox(s, 0.6, 1.6, 5.9, 1.45, "課題", ["「青は左、黄色は右に仕分けて」のような指示を受け、ロボットが自分で手順に分けて実行する"]);
  cardBox(s, 0.6, 3.15, 5.9, 1.7, "目的", ["人が言葉で頼むだけで仕分けや片付けができる、作業ロボットの基本の形を作る", "成功率を数字で測り、どこで失敗するかを確かめる"]);
  cardBox(s, 0.6, 4.95, 5.9, 1.95, "講義との関係", ["第2回: seed を固定した評価と記録", "第4・5回: ROS 2 のトピック・アクション、CRANE+ V2", "第6回: OSS（Genesis・Qwen・OWLv2）を組み合わせて公開"]);
  image(s, path.join(OUT, "shots", "genesis_demo1.png"), 6.85, 1.7, 5.9, 3.32, "Genesis 版の実行画面（左: 正面カメラ、右: 真上カメラと OWLv2 の検出結果）");
}

// 3. システム構成
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "2. システムの構成", "指示 → LLM（計画）→ OWLv2（認識）→ アーム（動作）");
  image(s, path.join(OUT, "fig_system.png"), 0.9, 1.65, 11.5, 4.86);
  s.addText("AI は推論のみで使用（学習なし）。LLM・検出器ともローカルの CPU で動き、API キーは不要", { x: 0.9, y: 6.55, w: 11.5, h: 0.35, fontSize: 13, color: COL.mid, isTextBox: true, margin: 0 });
}

// 4. 使用ツールと AI
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "3. 使用したツールと AI", "講義のシミュレータ2つと、公開されている AI モデル2つ");
  cardBox(s, 0.6, 1.7, 5.95, 2.4, "Genesis 1.4.5（講義のシミュレータ）", ["Franka アーム・4色のブロック・左右のトレイ", "真上カメラと正面カメラ（動画用）", "配置を seed で変えて 40 回評価"]);
  cardBox(s, 6.8, 1.7, 5.95, 2.4, "ROS 2 Humble + Gazebo（講義の Docker）", ["airobotbook/ros2-desktop-ai-robot-book-humble", "CRANE+ V2・ros2_control・教科書の逆運動学", "planner_node と sorter_node を自作"]);
  cardBox(s, 0.6, 4.3, 5.95, 2.4, "LLM: Qwen2.5-Instruct（0.5B / 1.5B）", ["日本語の指示 → 手順の JSON（few-shot）", "存在しない色・トレイは検証で捨てる", "プロンプト v1 / v2 で比較"]);
  cardBox(s, 6.8, 4.3, 5.95, 2.4, "物体検出: OWLv2（オープン語彙）", ["「a red cube」のように名前で検出（学習なし）", "ホモグラフィで画素 → 床の座標", "較正の再投影誤差は平均 0.7 mm"]);
}

// 5. Genesis 版の動作
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "4. Genesis 版の動作", "LLM の手順どおりに、Franka が左右のトレイへ運ぶ");
  image(s, path.join(OUT, "shots", "genesis_demo1.png"), 0.6, 1.7, 5.95, 3.35, "指示「青は左、黄色は右に仕分けて」→ 手順「青→左、黄色→右」");
  image(s, path.join(OUT, "shots", "genesis_demo2_end.png"), 6.8, 1.7, 5.95, 3.35, "指示「信号機の色のブロック（赤・黄・緑）を左に」→ 3個を左へ（成功）");
  s.addText([
    { text: "流れ: ", options: { bold: true } },
    { text: "① 真上カメラの画像を1枚撮る → ② OWLv2 で4色の位置を推定 → ③ LLM の手順の順に「つかむ → 運ぶ → 置く」→ ④ シミュレータの位置で成功を判定" },
  ], { x: 0.6, y: 5.6, w: 12.15, h: 0.9, fontSize: 15, color: COL.dark, isTextBox: true, margin: 0, valign: "top" });
}

// 6. 工夫: プロンプトの改善
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "5. 工夫した点: 失敗を分析してプロンプトを改善", `1.5B モデルの正解率 ${A.s15v1}% → ${A.s15v2}%`);
  s.addChart(pres.charts.BAR, [{ name: "正解率", labels: ["0.5B v1", "1.5B v1", "0.5B v2", "1.5B v2"], values: [A.s05v1, A.s15v1, A.s05v2, A.s15v2] }], {
    x: 0.6, y: 1.65, w: 6.6, h: 4.9, barDir: "col", chartColors: [COL.oliveL, COL.oliveL, COL.olive, COL.olive],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0\"%\"", dataLabelFontSize: 14, dataLabelColor: COL.dark,
    valAxisMaxVal: 100, valAxisMinVal: 0, valAxisLabelFontSize: 11, catAxisLabelFontSize: 13, valAxisLabelColor: COL.mid, catAxisLabelColor: COL.dark,
    valGridLine: { color: "E5E5E5", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
    showTitle: true, title: "LLM の計画の正解率（日本語の指示 12 個）", titleFontSize: 14, titleColor: COL.dark,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt",
  });
  cardBox(s, 7.5, 1.65, 5.25, 2.25, "v1 での失敗", ["「トマトと同じ色」「晴れた空と同じ色」→ 手順なし（連想ができない）", "「黄色以外」→ 緑だけ（否定の取り違え）"]);
  cardBox(s, 7.5, 4.05, 5.25, 2.5, "v2 での対策", ["規則を追加:「〜以外」は残りすべて、物の名前は代表的な色に置き換える", "例を3つ追加（バナナ・赤以外 など。テストとは別の言葉）", "小さいモデル（0.5B）も 42% → 67%"], { fill: "E9E8DC" });
}

// 7. 評価
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "6. 評価: Genesis で配置を変えて 40 回", "seed を固定した同じ条件で、成功率を数えた");
  stat(s, 0.6, 1.75, 3.0, `${(o.success_rate * 100).toFixed(1)}%`, `全体の成功率（${o.n} 回）`);
  stat(s, 0.6, 3.35, 3.2, `${o.loc_err_mean_mm.toFixed(1)} mm`, `位置の推定誤差の平均（最大 ${Math.round(o.loc_err_max_mm)}mm）`);
  stat(s, 0.6, 4.95, 3.0, pct(okGivenPlan), `計画が正しかった ${planOk.length} 回での成功率`);
  const insts = Object.keys(sim).filter((k) => !k.startsWith("_"));
  s.addChart(pres.charts.BAR, [{ name: "成功率", labels: insts.map((k) => k.replace("のブロック", "")), values: insts.map((k) => Math.round(sim[k].success_rate * 100)) }], {
    x: 4.0, y: 1.65, w: 8.75, h: 4.9, barDir: "bar", chartColors: [COL.olive],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0\"%\"", dataLabelFontSize: 13, dataLabelColor: COL.dark,
    valAxisMaxVal: 120, valAxisMinVal: 0, valAxisMajorUnit: 20, valAxisHidden: true, valAxisLabelFontSize: 11, catAxisLabelFontSize: 12, valAxisLabelColor: COL.mid, catAxisLabelColor: COL.dark,
    valGridLine: { color: "E5E5E5", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false, catAxisOrientation: "maxMin",
    showTitle: true, title: "指示ごとの成功率（各 10 回、LLM は 1.5B・プロンプト v2）", titleFontSize: 14, titleColor: COL.dark,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", titleFontFace: "+mn-lt",
  });
  s.addText("成功の条件: 指示されたブロックが正しいトレイにあり、指示されていないブロックは机の上に残っていること", { x: 0.6, y: 6.6, w: 12.15, h: 0.35, fontSize: 12, color: COL.mid, isTextBox: true, margin: 0 });
}

// 8. ROS 2 + Gazebo 版
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "7. 同じ計画を ROS 2 + Gazebo（CRANE+ V2）で", "講義の Docker で、自作ノード2つをつないで実行");
  const nodes = [["/instruction", COL.tint], ["planner_node\n（LLM）", "E9E8DC"], ["/plan（JSON）", COL.tint], ["sorter_node\n（逆運動学）", "E9E8DC"], ["ros2_control\nCRANE+ V2", COL.tint]];
  nodes.forEach(([t, c], i) => {
    const x = 0.6 + i * 2.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.7, w: 2.1, h: 0.95, rectRadius: 0.1, fill: { color: c }, line: { color: COL.oliveL } });
    s.addText(t, { x, y: 1.7, w: 2.1, h: 0.95, fontSize: 13, bold: true, align: "center", valign: "middle", color: COL.dark, isTextBox: true, margin: 0 });
    if (i < nodes.length - 1) s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 2.13, y: 2.0, w: 0.34, h: 0.35, fill: { color: COL.olive }, line: { color: COL.olive } });
  });
  image(s, path.join(OUT, "shots", "gazebo_mid.png"), 0.6, 2.95, 5.95, 3.45, "赤を右のトレイへ運ぶ途中");
  image(s, path.join(OUT, "shots", "gazebo_end.png"), 6.8, 2.95, 5.95, 3.45, "指示「赤は右、青は左のトレイに仕分けて」の完了後");
}

// 9. 失敗と考察
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "8. 失敗と考察", "どこで失敗したかを、計画・認識・動作に分けて見る");
  cardBox(s, 0.6, 1.6, 3.9, 2.95, "計画（LLM）", ["v2 でも「黄色以外を右に」を取り違えた（緑だけを選ぶ）", "1.5B の小さいモデルでは否定の扱いが不安定", "対策: 指示の言い換えで確認する／大きいモデルや、否定だけを規則で処理する"], { headColor: COL.red });
  cardBox(s, 4.72, 1.6, 3.9, 2.95, "認識（OWLv2）", ["配置 seed=9 では、緑のブロックがアームの手の真下に隠れて、真上カメラから見えなかった", `4色を検出できた割合 ${pct(o.detect_rate)}（見えていれば位置の誤差は平均 ${o.loc_err_mean_mm.toFixed(1)} mm）`, "対策: 撮影の前にアームをカメラの視野の外へ動かす"], { headColor: COL.red });
  cardBox(s, 8.85, 1.6, 3.9, 2.95, "動作（Gazebo）", ["3個目のブロックを中央に置くと、開いた指が隣に当たって崩れた", "CRANE+ は腕が短く、真下向きでつかめるのは土台から約 0.17 m まで", "対策: 置き方の工夫（今回は2個に）／手首の向きの制御"], { headColor: COL.red });
  image(s, path.join(OUT, "shots", "genesis_demo3_fail.png"), 0.6, 4.7, 3.9, 2.0);
  image(s, path.join(OUT, "shots", "seed9_top.png"), 4.72, 4.7, 3.9, 2.0);
  image(s, path.join(OUT, "shots", "gazebo_fail_3cubes.png"), 8.85, 4.7, 3.9, 2.0);
}

// 10. まとめ
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "9. まとめと今後", "言葉 → 計画 → 認識 → 動作を1つにつないだ");
  stat(s, 0.6, 1.75, 3.6, `${(o.success_rate * 100).toFixed(1)}%`, "Genesis での仕分けの成功率");
  stat(s, 4.5, 1.75, 3.6, `${A.s15v1}→${A.s15v2}%`, "プロンプト改善による LLM の正解率");
  stat(s, 8.4, 1.75, 4.3, "2 つ", "シミュレータ（Genesis / ROS 2 + Gazebo）");
  cardBox(s, 0.6, 3.6, 5.95, 2.6, "わかったこと", ["小さい LLM でも、例と規則を足すと正解率が大きく上がる", `失敗 ${o.n - Math.round(o.success_rate * o.n)} 回のうち ${o.n - Math.round(o.success_rate * o.n) - 1} 回は「計画」の誤り。計画が正しければ成功率 ${pct(okGivenPlan)}`, "同じ計画を ROS 2 のノードにすると、ロボットを替えても使える"]);
  cardBox(s, 6.8, 3.6, 5.95, 2.6, "今後", ["Gazebo 側にもカメラと物体検出を入れる", "実機の CRANE+ V2 や SO-101 で試す", "LLM の手順を実行前に人が確認できる画面を作る"], { fill: "E9E8DC" });
}

pres.writeFile({ fileName: path.join(__dirname, "説明資料_PAI最終課題_usagisan2020.pptx") }).then((f) => console.log("wrote", f));
