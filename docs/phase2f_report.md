# FlyRendezvous Phase 2F 実施報告

**追加対応済み：[約14秒のMP4](../outputs/phase2f/mp4/phase2f_test00.mp4)。ユーザー承認後にffmpegを導入して生成・検証した。詳細は末尾の追記。**

実施日：2026-09-11（JST）。**保存ログのみで5型のbar/map、T4aのabsolute/relative比較、実Rerun再生と14.066秒の実描画アニメーションを作成した。** 旧成果460ファイルは不変。追加形態取得・学習・新しい制御実験は0件。

結論は、**T4aには固定relative尺度を採用する価値がある。5型のbarを残し、retinotopic mapも最終画面へ残すことを推奨する。一方、5型すべての3D代表形態を増やす必要性は低い。追加するならまずT2、T5dは説明目的次第、Tm3/L2はbar/mapを優先する。** 最終採否はユーザー判断である。

単体84件と表示・動画の照合は通過した。既知のGPU prefix再現比較は今回も1件失敗し、閾値を緩和していない。

## 成果を見る

- [14.066秒の実描画アニメーション（WebP）](../outputs/phase2f/phase2f_test00.webp)
- [主成果：phase2f.rrd](../outputs/phase2f/phase2f.rrd)
- [approach画面](evidence_phase2f/approach.png)／[braking画面](evidence_phase2f/braking.png)／[hold画面](evidence_phase2f/hold.png)
- [元test_00のraw/relative時系列PDF](evidence_phase2f/raw_relative_timeseries.pdf)
- [全指標CSV](../outputs/phase2f/motion_metrics.csv)／[試行別・局面別JSON](../outputs/phase2f/motion_metrics.json)

![5型のbar/mapと同じT4a形態の2尺度比較](evidence_phase2f/braking.png)

上段はPhase 2E向きの軌道、実sensor image、5本のbar、同じT4a形態のMode A/B。中央はT2/Tm3/T4a/T5d/L2の5枚のmap、下段はraw RMS・qの時系列と時刻・凡例。神経mapはモデル内のretinotopic格子であり、実脳のXYZ配置ではない。

## 1. 固定したもの・データの範囲

HCW、target、goal、camera、checkpoint、readout、split、成功条件、Phase 2 test成績を維持した。軌道表示は引き続きX=-y、Y=x（上向き正）、Rerun描画座標は[-y,-x]。画像・mapへ軌道の回転を適用していない。

| 用途 | 使用データ | 範囲 |
|---|---|---|
| RMS p05/p95、q時間指標、静的test_00時系列 | 元学習器test_00〜test_11 | 12試行、全4,077フレーム、制御中3,837フレーム |
| map尺度・空間変化、Rerun | 既存の全細胞応答付きreplay test_00/test_05 | 422＋470＝892フレーム、制御中852フレーム |
| アニメーション | 上記replay test_00 | 物理0〜210.5秒の観測を表示、最終状態時刻211秒 |
| GPU回帰テスト | 既存テストの短い実モデル推論 | 表示データや学習へは追加しない |

元testの12本には全型RMS/meanがあるが、細胞別の全応答は保存されていない。**mapの尺度・空間指標は全12本を評価したものではなく、既存replayの2本に限定**する。不足分の推論は行わなかった。replayと元testの既知の微小な差を同一データとして扱わず、それぞれの時刻・baseline・応答を使った。

表示用にT2/Tm3/T4a/T5d/L2の各721細胞を抽出した。元の計算対象は45,669細胞、readoutは57型×16 binのまま。真のstateは既存ログの局面分類・軌道描画にだけ用い、新たな制御入力には使っていない。

## 2. 固定尺度の定義

### activity barとT4a relative色

灰色reset後の各細胞baselineとの差Δvから型全体RMSを取る。元testの**制御中だけ**を使い、試行iの各フレームに重み1/(12 N_i)を付けた混合経験分布の逆CDFからp05_jとp95_jを求めた。各試行の総重みは常に1/12である。長い試行が支配する単純な全フレーム結合でも、試行別percentileの中央値でもない。

**q_j(t)=clip((RMS_j(t)−p05_j)/(p95_j−p05_j),0,1)**。

p05/p95は一度算出して[display_scales.json](../outputs/phase2f/display_scales.json)に保存し、全フレーム・両replayで固定した。qは「その型自身の今回のtest範囲に対してどの程度か」であり、percentile rankそのものではない。**q=0は活動ゼロではなくp05以下、q=1はp95以上**を意味する。raw RMSを各barに常時併記した。発火率や型間の絶対活動比較には使わない。

dynamic rangeが1×10⁻⁸以下なら増幅せずq=0.5の中立値にし、scaleのrelative_valid=falseで未成立を記録する実装とテストを追加した。今回の5型は全て十分なrangeがあり、有効であった。毎フレームの正規化はない。

### signed retinotopic map

色は細胞別Δvを青（負）・白（ゼロ）・赤（正）で表示する。全細胞応答を持つ2本のreplayについて、各試行の総重みを1/2とし、制御中の全選択細胞の|Δv|からp99を求めてlimit_jとした。各型の[-limit_j,+limit_j]に固定し、範囲外をclipする。

型ごとにlimitが異なるので、**同じ赤の強さを異なる型の絶対活動量として比較できない**。各mapのタイトルに固定limitを表示し、共通凡例にも明記した。今回、clipされる細胞×フレームは各型とも約1%。model cell_indexとu/vを保持し、空間平均した色をmapへ塗ってはいない。

モデル格子の周辺には画像前処理・視野境界に伴う応答も見える。特に周辺の赤青帯を、そのまま対象物の位置や解剖学的な境界と解釈しない。

## A. T4aのraw尺度とrelative尺度で何が変わったか

Mode AはPhase 1B/2と同じRMS 0..0.22、Mode Bは固定p05..p95を同じ青→黄paletteへ写像する。**同じ実測T4a ID 720575940605852192、同じ828枝、同じ時点の721モデル細胞RMS**を別の比較ビューで表示した。実測形態は1種類・1細胞のままであり、脳内に代表細胞を増殖・配置したわけではない。

T4aのp05=0.089184、p95=0.117017、range=0.027833。clipされない区間の色の傾きは従来の約**7.90倍**になる。実活動を大きくしたのではなく、限られた実変化を固定した表示範囲へ広げた。

![元test_00のraw・q・T4a palette比較](evidence_phase2f/raw_relative_timeseries.png)

上2段は5型のraw RMSとq、下段はT4aのpalette位置。全区間を共通物理時間軸で示した。初期観測も図には含めるが、尺度校正・主要指標には含めない。開始直後の大きな応答やrelative色の飽和は、記録された入力立ち上がり応答を表示したもので、人工的なspike演出ではない。

実アニメーションの22.5→90→195物理秒を復号して見ると、Mode Aは淡い色のまま変化が小さく、Mode Bは青→中間色→黄への変化を読み取りやすい。形態の形や枝内分布が変化するわけではなく、全枝同じ一色が変化する。

以下は**制御期間のRRDへ渡した8-bit RGB色値**の変化で、レンダリング後の画素や生物の電位単位ではない。

| replay | Mode | RGB成分の変化幅 | 隣接フレームで色値が変わった割合 |
|---|---|---|---:|
| test_00 | absolute | [21.0, 11.0, 11.0] | 13.2% |
| test_00 | relative | [152.0, 78.0, 78.0] | 47.6% |
| test_05 | absolute | [25.0, 12.0, 12.0] | 11.8% |
| test_05 | relative | [180.0, 93.0, 93.0] | 41.6% |


relativeでも、0.5物理秒刻みの全フレームで色が変わるわけではない。両modeとも色差の中央値は0だった。長い区間の変化を見やすくする効果であり、枝内を光が走る・連続発火するという表現は行っていない。

## B. 5型のbar/mapは区別できるか

barは型名・固定色・q数値・raw RMSを併記し、5型を同時に追える。ただしrelative barの時間経過はかなり似ており、barだけで各型の機能を識別するのは難しい。raw RMSではT2/L2が比較的大きく、Tm3/T4a/T5dの変化は共通活動尺度で小さく見えるが、relativeでは5型とも変化が分かる。

mapにはbarと異なる情報がある。実描画では次の違いを確認した。

| 型 | 今回の実mapで見える特徴 | 一色のtype aggregateから増える情報 |
|---|---|---|
| T2 | 中心付近の正応答領域が広がる | 応答がどの格子細胞に分布するか |
| Tm3 | 中心の正応答と周辺の弱い負応答。T2に似た経過 | 正負・周辺の違いはあるが、同時表示の追加情報は控えめ |
| T4a | 中心付近に正負が隣接した配置 | 正負の相殺と配置をRMS一色からは読み取れない |
| T5d | T4aとは異なる正負の配置・広がり | 型全体RMSが似ていても空間パターンは異なる |
| L2 | 中心付近の負応答領域が広がる | T2の正応答との符号の違いを明確に示せる |

これは今回の画像・単一モデル・記録での観察である。方向選択性の新しい検証や、T4a/T5dのsuffixと画面方向の対応付けは行っていない。機能や因果的重要度を、このmapだけから断定しない。

## C. 動いて見える型と、ほぼ一定に見える区間

**relative barでは全5型が接近後半〜制動で動いて見える。全区間で一定だった型はない。** T4a形態の従来absolute色はほぼ一定に見えやすく、relative化で改善した。保持区間では全5型とも変化が小さく、短い動画ではほぼ止まった状態に近く見える。これは表示が停止したのではなく、記録された神経活動変化も小さいためである。

mapはT4a/T5dの正負配置の違いが特に分かりやすい。T2/Tm3/L2も中心領域の広がりが変化し、型全体を一色で示す場合より多くの情報を保持している。ただし見かけの拡大・移動は緩やかで、派手な高速運動ではない。

初期の低応答区間ではbarがclipされる。replay test_00の制御期間でp05未満だった割合はT2 **15.4%**、Tm3 **16.4%**、T4a **11.2%**、T5d **19.7%**、L2 **15.7%**。この区間でもraw RMSは非ゼロでmapに応答がある。**barだけでは弱い応答変化を取りこぼすため、raw値とmapを残す**ことを推奨する。12試行の混合分布の尺度なので、各個別試行・replayで必ず5%ずつclipされるわけではない。

局面はPhase 2Eのstate/commandルールを再利用した。observationを分離し、near_holdは位置誤差<0.25 m・速度<0.01 m/s、brakingは高x側でvx<0かつapplied ax>0、残りの高x側の接近をapproachとする。局面分類は表示解析専用である。制動時の活動変化には、対象の見かけサイズ等の変化も同時に含まれる。

## D. 動きの定量評価

p05/p95は12試行等重みの混合分布。qの時間標準偏差と|Δq|/0.5秒は各試行の制御期間で計算して12試行の中央値を取った。reset境界をまたぐ差分は使わない。値は**物理秒**あたりで、再生秒や神経秒ではない。

| 型 | raw p05 | raw p95 | raw range | q時間std | abs(Δq)/秒 median | abs(Δq)/秒 p95 |
|---|---:|---:|---:|---:|---:|---:|
| T2 | 0.178737 | 0.457773 | 0.279035 | 0.2239 | 0.003665 | 0.007088 |
| Tm3 | 0.049631 | 0.099162 | 0.049531 | 0.2425 | 0.003628 | 0.007731 |
| T4a | 0.089184 | 0.117017 | 0.027833 | 0.1929 | 0.003111 | 0.021731 |
| T5d | 0.061589 | 0.085156 | 0.023567 | 0.2253 | 0.003241 | 0.014411 |
| L2 | 0.143051 | 0.248423 | 0.105372 | 0.2571 | 0.003899 | 0.005473 |


局面中央値は、3局面とも5標本以上ある同じ9試行（test_00〜07、test_10）に限定し、試行内中央値→試行間中央値とした。残り3試行も通常の時間指標・尺度校正には含む。

| 型 | approach median q | braking median q | near_hold median q |
|---|---:|---:|---:|
| T2 | 0.1053 | 0.5468 | 0.7679 |
| Tm3 | 0.1031 | 0.5720 | 0.8153 |
| T4a | 0.1512 | 0.5858 | 0.7088 |
| T5d | 0.1345 | 0.6028 | 0.8345 |
| L2 | 0.1093 | 0.6117 | 0.8727 |


map指標は全細胞応答付きreplay 2本の制御期間を対象に、各試行で計算して中央値を取る。空間stdはフレームごとの細胞間標準偏差の時間中央値。Δmapは隣接フレームの細胞別Δv差のRMSを0.5秒で割ったもの。さらに各フレームの空間平均を引いた「centered pattern」差も求め、一様な活動レベル変化だけで空間変化を主張しないようにした。

| 型 | fixed ±limit | 空間std中央値 | Δmap/秒 median | Δmap/秒 p95 | centered pattern/秒 median |
|---|---:|---:|---:|---:|---:|
| T2 | 1.558635 | 0.299259 | 0.001793 | 0.003694 | 0.001710 |
| Tm3 | 0.379396 | 0.073239 | 0.000505 | 0.001259 | 0.000494 |
| T4a | 0.399239 | 0.102592 | 0.001051 | 0.002491 | 0.001050 |
| T5d | 0.341085 | 0.074767 | 0.000841 | 0.001792 | 0.000841 |
| L2 | 0.872026 | 0.194967 | 0.001511 | 0.002955 | 0.001492 |


mapのfixed limitで割ってclipした表示信号についても差分を保存した。

| 型 | normalized map変化/秒 median | normalized map変化/秒 p95 |
|---|---:|---:|
| T2 | 0.001143 | 0.002367 |
| Tm3 | 0.001320 | 0.003157 |
| T4a | 0.002217 | 0.005559 |
| T5d | 0.002315 | 0.005055 |
| L2 | 0.001732 | 0.003386 |


T4a/T5dはraw活動が小さくても、表示尺度上のパターン変化はT2/Tm3より大きい値だった。これを異なる型の絶対電位変化や重要度の比較には使わない。test_00のnear_holdでは表示信号の変化率中央値がT2 0.000271、Tm3 0.000368、T4a 0.000830、T5d 0.000731、L2 0.000496 /物理秒まで小さくなる。[局面別詳細](../outputs/phase2f/replay_visibility.json)

## 動画・実再生での確認方法

Rerunのseek、play、pauseを実行し、native headlessレンダラーでapproach/braking/holdを撮影した。さらにplay状態を継続して進む画面を取得し、表示時刻52.5秒付近から118.5、181.5、210.5秒までの進行を確認した。画像取得の前後時刻は[screenshots.json](evidence_phase2f/screenshots.json)と[video_manifest.json](../outputs/phase2f/video_manifest.json)に残した。

アニメーションは同じRRDの実描画2240×1400から作成した。replay test_00の3サンプルおきと最終サンプル、計142枚を使い、1600×1000のanimated WebPへ保存した。基本100 ms、末尾33 msのフレーム期間で**14,066 ms（約15倍再生）**。形態や活動の補間・架空フレーム・halo・bloom・枝内伝播は加えていない。

全142フレームを復号し、合計時間、各元PNGのSHA、全隣接画像の変化を検証した。復号後の22.5・90・195秒相当の画面も目視確認した。全画面の隣接差には軌道・時刻・画像も含まれるため、それだけを神経活動の変化証拠にはせず、上記の型別・map指標とRRD照合を併用した。[動画検証](../outputs/phase2f/video_review.json)

**MP4は作成していない。** 既存環境にffmpeg/ffprobeやPython動画エンコーダーがなく、browser操作ツールも接続時のsandboxメタデータエラーで利用できなかった。大規模な動画フレームワークは追加せず、既存Pillow/libwebpで動画補助成果を作った。主成果は操作可能なRRDである。ブラウザ内でのWebP再生やWindows GUIの滑らかさは未検証。native headlessの連続再生と実フレーム列を確認したが、実時間GUI描画性能や人による識別率の実験とは区別する。

## E. 次の3D代表形態・bar/mapの判断

| 型 | 次に3D形態を追加する価値 | bar/mapでの扱い | 判断理由 |
|---|---|---|---|
| T4a | 取得済みを維持。新規取得不要 | bar＋mapを維持 | relative色で既存形態の時間変化が読みやすくなる。mapの正負配置は別に必要 |
| T2 | **新規追加するなら第一候補、まず1型** | bar＋mapを維持 | 大きいraw変化と分かりやすい領域拡大。ただし3Dで増えるのは主に形態の説明で、活動情報自体はbar/mapに既にある |
| T5d | **条件付き候補** | mapの優先度は高い | T4aと異なるsigned patternを比較できる。ON/OFF系の形態比較を主目的とするなら追加余地。動きを増やす目的だけならmapで十分 |
| Tm3 | いまは追加を優先しない | barを維持。mapは枠があれば | T2に似たbar・中心応答の経過。入力段階の説明はできるが、3D形態を増やす必然性は今回弱い |
| L2 | いまは追加を優先しない | bar＋負応答mapが有用 | 負の中心応答という情報は一色RMS形態では失われる。mapの方が今回の違いを直接示せる |

Phase 2EではT2/Tm3/T5dの取得案を挙げたが、Phase 2Fで同時比較した結果、**3型同時取得を急がずT2から考える**案へ絞る。これは表示の優先順位の見直しで、学習・計算対象から型を除く判断ではない。形態未取得の型について、形状自体の見やすさを評価済みとは言えない。

表示から完全に外す必要がある型は、今回の5型にはない。画面を縮小するなら、まずTm3 mapを省いてbar/時系列に残す。最小3枚ならT2/T4a/T5d、余裕があればL2の負応答mapを足す。今回の判断用RRDは5枚同時表示を維持した。

## F. 次段階でユーザーが決めること

1. **追加形態取得**：必須ではない。形態の説明を増やすならT2 1型から。T5dはT4/T5比較という説明目的が明確な場合に検討する。Tm3/L2はbar/mapを先に活用する。
2. **relative scale採用**：T4aの主表示として条件付きで推奨。固定p05/p95・raw RMS・clipの意味を併記し、absolute尺度も比較手段として残す。別条件を追加しても毎フレーム再校正しない。
3. **retinotopic map採用**：推奨。型aggregateより情報量が多く、正負・位置・広がりを保つ。型別固定scaleを明示し、色強度の型間絶対比較を禁止する。
4. **新しい斜め接近制御問題**：今回の表示検証とは独立した次のユーザー判断。今回の12試行成功や表示成立を、新条件での制御成功として外挿しない。今回、新条件は実施していない。

## 検証結果・保存物

| 検証 | 結果 |
|---|---|
| 既存68＋追加16単体 | **84/84通過** |
| 追加テスト | 型別quantile、trial equal-weight、sample複製不変性、fixed relative/clip、極小range、type選択、fixed signed map、RMS一致、空間平均とpattern変化の分離、時間対応、旧成果不変性 |
| 実RRD照合 | **892フレーム**。5 mapの全色・格子位置、5 barの長さと数値、10系列、T4a両尺度のRGB/828枝、画像・軌道・ベクトル・時刻を元replayから再構成。35 entity path、総22,300行 |
| RRD形式 | `rerun rrd verify` exit 0 |
| 実再生 | seek/play/pause、3局面のスクリーンショット、連続playの画面進行 |
| アニメーション | 142/142フレーム復号、14,066 ms、元PNGと動画のSHA照合 |
| 旧成果 | **460/460 SHA一致**。Phase 1/1B/2/2Eの出力・報告・evidence、設定・旧コード・旧テスト・形態等を保存 |
| 既存GPU統合 | **1/2通過、1/2失敗、skip 0**。既知prefix比較。閾値変更なし、成功するまでの再試行なし |

GPU失敗は `test_phase2_real_images_policy_prefix_and_weight_freeze` の先頭10画像の再実行比較。20成分中1成分が従来のatol=2×10⁻⁷、rtol=2×10⁻⁵を超過し、その差は6.65475×10⁻⁷ m/s²だった。既存stateful checkpointテストは通過した。失敗箇所以降のassertion通過は主張しない。原因特定・閾値緩和・制御変更は今回行わず、Phase 2Eからの既知問題として分離した。[GPU log](../outputs/phase2f/integration-tests.log)

Phase 2の保存済み成績は**接近8/8・近傍4/4成功**のまま。readout SHAは `7cc96bd86ba09fa3b688f7574249fde22abb6ff10a1149f7817832459e407151` で不変。[旧成果開始時ハッシュ](../outputs/phase2f/prior_hashes.json)、[最終検証](../outputs/phase2f/final_checks.json)、[RRD照合](../outputs/phase2f/rrd_audit.json)、[単体log](../outputs/phase2f/unit-tests.log)を保存した。

主要数値は `display_scales.json`、`type_activity.npz`（元12試行）、`test_00_display.npz`／`test_05_display.npz`（5型の細胞別Δv、raw、q、cell_index、u/v、時刻、局面）、`motion_metrics.json/csv`、`replay_visibility.json`。尺度・表示データ・動画に元レコードのSHAを関連付けた。新規依存は追加していない。

## 再現・再生コマンド

WSLの既存プロジェクトルートで、まずRRDを開く：

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase2f/phase2f.rrd --bind 127.0.0.1
```

保存ログのみから再生成する：

```bash
.venv/bin/python scripts/analyze_phase2f.py
.venv/bin/python scripts/plot_phase2f.py
.venv/bin/python -m flyrendezvous.viewer_phase2f
.venv/bin/python scripts/verify_phase2f_rrd.py
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun rrd verify outputs/phase2f/phase2f.rrd
.venv/bin/python scripts/capture_phase2f.py --video
.venv/bin/python scripts/review_phase2f_video.py
.venv/bin/python scripts/verify_phase2f.py
```

`capture_phase2f.py`だけなら静止画と操作確認、`--video`で実描画アニメーションも生成する。動画フレームを作り直さず操作を再確認する場合は`--video --reuse-video`。古いRRDに対する動画の流用を避け、RRDを変更したら`--video`で再生成する。

テスト：

```bash
.venv/bin/python -m pytest tests -m 'not integration'
.venv/bin/python -m pytest tests -m integration
```

今回の表示検証は完了。relative尺度の最終採否・追加形態の取得型・新しい制御問題はユーザー判断として残し、ここで停止する。

## 追加対応：ffmpeg導入とMP4生成

初回報告後、ユーザーからffmpeg等の追加導入許可を受け、**[実描画MP4](../outputs/phase2f/mp4/phase2f_test00.mp4)**を作成した。上記の「MP4未生成」「追加依存なし」は初回実施時の記録である。

[PyPIのimageio-ffmpeg 0.6.0](https://pypi.org/project/imageio-ffmpeg/0.6.0/)のLinux wheelを取得し、公開SHA-256 `c7e46fcec401dd990405049d2e2f475e2b397779df2519b544b8aab515195282` と照合した。同梱ffmpeg 7.0.2をプロジェクト内 `.tools/video/python` へ導入した。学習用venvの既存パッケージやシステムPythonは変更していない。[導入記録](../outputs/phase2f/mp4/tool_install.json)

元のRerun実描画PNG 142枚を再利用し、撮影間隔の3サンプル分は同じ画像を保持する方式で、H.264/yuv420p、1600×1000、30 fps、422フレーム、**14.066667秒、1,901,877 bytes**のMP4を生成した。表示速度は15倍。新しい活動推論・軌道計算・描画演出・フレーム補間は行っていない。

全422フレームをMP4から復号し、対応する元PNGの縮小画像と比較した。全フレームのPSNR最小40.50 dB、平均41.71 dB。PTSは0〜421、time baseは1/30、各フレームdurationは1で一致した。13秒位置の復号画像も目視確認した。これは復号・画質・時刻の検証であり、Windows GUIでの動画プレイヤー操作を追加検証したものではない。[MP4検証JSON](../outputs/phase2f/mp4/verification.json)

Phase 2Fの既存180成果ファイルと、従来の460保護対象ファイルは全てSHA一致。元RRD、WebP、神経活動、制御・学習結果、既知GPUテストの記録は保持した。MP4追加によってPhase 2Fの型選択・relative尺度に関する判断は変更していない。

再生成：

```bash
.venv/bin/python scripts/export_phase2f_mp4.py
```

別の環境で動画ツールも準備する場合は、専用の出力先へ導入する：

```bash
.venv/bin/python -m pip install --no-deps --target .tools/video/python imageio-ffmpeg==0.6.0
```
