# Phase 4A report — Fly Pilot View

実施日: 2026-09-11。**固定姿勢の外部ハエ＋実コマンドに同期する操縦桿（Mode A）を実装・実行・検証した。** DemoとAnalysisのRRD、実Rerunスクリーンショット、14.63秒のMP4を保存した。制御側の変更・再推論・新規実験は0。Phase 3のapproach 8/8、near 2/4をそのまま保持する。

## 採用モデルと取得

採用は指定された第2候補 **Low Poly House Fly (Diptera)**、作者 **Glowbox 3D**。[元モデル](https://sketchfab.com/3d-models/low-poly-house-fly-diptera-2baa84955f704a4091a274ef4acec24a)、[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。

第一候補の[CadNav Fly Insect Rig](https://www.cadnav.com/3d-models/model-45541.html)を先に調べた。掲載情報はMaya .mb、rigged、Non-commercial。ダウンロードはHTTP 403、Maya importerもないため、指定どおりSketchfabへ切り替えた。Sketchfabの公開metadataは取得できたが、download APIはHTTP 401だった。

同じ指定モデルを明示的にクレジットしている[Aden Princeの公開プロジェクト](https://sites.google.com/uic.edu/cs428-adenprince/project-2)から取得した。元URL・作者・ライセンスへのリンクが掲載されている。[公開リポジトリの固定commit](https://github.com/adenprince/cs428-project-2/tree/c6f45eaee28e6ab5e41e5df8f49fd83d7e3ffc9d)から、ハエ1モデルとテクスチャ3枚のみを保持した。第三のモデルは採用していない。認証制限を回避する取得は行っていない。

| 保存物 | 内容 |
|---|---|
| assets/fly_pilot/Fly Old.blend | 採用した再配布元のoriginal filename |
| assets/fly_pilot/fly_pilot.glb | 変換済み・テクスチャ内蔵、516,688 bytes |
| assets/fly_pilot/manifest.json | 元URL、commit、全ファイルSHA-256、変換設定 |
| assets/fly_pilot/README.md | attribution、利用条件、変換手順 |
| sketchfab_metadata.json / redistribution_credit.html | 公開仕様・帰属の取得証拠 |
| blend_inspection.json | Blender内のメッシュ・リグ確認 |

元Blend SHA-256: `0915127a23fb91ec00b7ca1a60142a37168de2860c4646cc4c616aba0eab42e4`  
GLB SHA-256: `ffb17ff193d3459ba7ac5ec8d073ba4a7402ce6cc774151e6a8eb7a7496ed62e`

**出典確認の限界:** 再配布者は指定モデルURLを明記しており、三角形数は掲載値と同じ1,736。一方、Blendは924頂点、Sketchfab掲載値は908頂点である。公式ZIPとのバイナリ同一性までは確認できない。この差を隠して「公式原本そのもの」とは扱わない。先に確認した翼分割版は採用せず削除した。

元ページにはNoAIの記載もある。本作業は決定的な形式変換と3D説明表示に限定し、生成AIによる資産生成・学習には使用しない。配布・発表資料でも作者、元URL、CC BY 4.0とこの出典メモを保持する。

## 変換と固定姿勢

WSLへBlender 4.0.2を導入した。既存学習用venvは変更せず、変換時にそのNumPyを参照した。外部BlendのPython自動実行は無効化した。GLB exporterの任意Draco圧縮は未導入のため無圧縮で出力した。

元world形状へ一様140倍、X軸-25°、Z軸+90°の剛体回転、台座への平行移動を適用した。これは**説明模型だけの座標**であり、HCW・カメラ・FAFB14.1座標とは無関係。原形の頂点変形はしない。元base-color textureを再接続し、roughness 0.7、metallic 0の単純な材質とした。normal/roughnessの原画像は記録として保持したが表示には使わない。

メッシュ1個、armature 0。前脚だけを安定して動かすには新規riggingが必要なため、許可された固定姿勢を採用した。胴体・翼・脚は静止し、前方の操縦桿だけが動く。固定脚はノブを連続的に把持しない。接触や力学が成立しているという表現はしない。

## 信号・座標・normalization

入力は元のonce-only held-outログの **u_applied**。生のreadout出力u_rawや教師コマンドへの差替えはしない。Orbitの加速度矢印と同じ配列・同じsampleを用いる。

物理LVLHのxは外向き、yは軌道進行方向。Cartesian表示は:

~~~text
a_disp = [-a_y, a_x]          # right / up
u = clip(a_disp / 0.005, -1, 1)  # 各軸、表示専用
tip_xy = base_xy + 0.55 * u
tip_z = base_z + sqrt(1.2² - |0.55*u|²)
base = [0.65, 0.25, 0.18]
~~~

操縦桿長は一定1.2 display units。a_ref=0.005 m/s²は既存の適用加速度制限に合わせた表示基準で、制御を変更しない。test_00の最大絶対成分は0.00480729 m/s²、追加の表示clipは0/439。表示対象全777 sampleでも範囲外clipは0。dead zone、平滑化、架空の揺れは追加していない。

Pilotは固定の真上視点、position=[0.65,0.25,3.8]、look_target=[0.65,0.25,0]、up=+Y。**光軸を支点へ合わせる**ことで、中立の見かけのずれを防ぐ。開発時、光軸が支点から外れると高さによる遠近視差で小さな左指令が右に見える問題を実画面で発見し修正した。投影の中立・符号・平行性もテストした。

画面上はOrbitと同じ[-a_y,-a_x]方向、**左=+along-track、下=中心天体方向**。強いコマンドほど操縦桿が大きく傾くが、遠近投影された長さはm/s²の線形目盛ではない。正確な成分は常時併記する数値を読む。センサーカメラ・Brainの既存視点は変更していない。

| test_00 | sample | a_disp X | a_disp Y | 観察 |
|---|---:|---:|---:|---|
| initial 0 s | 0 | 0 | 0 | 支点中央 |
| early 20 s | 40 | +0.00141477 | +0.00427493 | 右上へ大きく傾く |
| braking 85 s | 170 | -0.00056090 | -0.00072195 | 左下へ小さく傾く |
| near/hold 219 s | 438 | -0.00018555 | -0.00015738 | 左下のごく小さな偏位 |

単位m/s²。holdでも保存指令は厳密なゼロではないため、ゼロに見せる加工はしていない。

## GUIと実画面

Demo上段は大きなOrbitとBrainを維持。下段はsensor、T2/T4a/T5d maps、Fly Pilot、5-type barsとcompact status。Pilotには台座、固定ハエ、procedural base/shaft/grip、平面方向ガイド、加速度数値を表示する。Analysisには詳細グラフと右視葉の拡大を残し、Pilotも追加した。

画面の短文は「Illustrative control view; not biological motor output.」「Joystick follows learned 2D translational command.」。詳細免責を画面に詰め込まず、READMEと本報告に置いた。ハエ模型と脳内の36実測神経形態は別の意味を持つ。

以下は**実Rerun native rendererから取得した画面**。合成イメージではない。

### Early approach — 20 s
![early](evidence_phase4a/demo_early.png)

### Braking — 85 s
![braking](evidence_phase4a/demo_braking.png)

### Near / hold — 219 s
![hold](evidence_phase4a/demo_hold.png)

[Initial](evidence_phase4a/demo_initial.png)、[Analysis](evidence_phase4a/analysis_early.png)、[全画面のsample・時刻・SHA記録](evidence_phase4a/screenshots_demo.json)。

## 動画・playback

- [MP4](../outputs/phase4a/mp4/phase4a_test00.mp4): H.264、1600×1000、30 fps、439 frames、14.633 s、1,091,783 bytes。
- [Animated WebP](../outputs/phase4a/demo_test00.webp): 74実Rerun capture、14.633 s。
- 元test_00の0〜219 sを15倍速。6 sampleごとのcaptureと最終sampleを用い、間のフレームはholdする。神経活動・コマンドの補間はしない。
- 実Rerunでseek、play、pause、末尾保持を確認。連続play中の9枚も保存し、時間が前進して219 sへ到達することを確認した。
- WebP全74枚を復号し、ハッシュ・duration・source対応を検証。MP4全439枚を復号し、PTS 0〜438、time base 1/30、元captureとのPSNR最小40.38 dBを確認。
- Windows GUIの手動マウス操作・発表用PC上の実時間FPSは未測定。native headless software rendererの実再生・capture検証である。

[動画検証](../outputs/phase4a/mp4/verification.json)、[フレームmanifest](../outputs/phase4a/video_manifest_demo.json)、[WebP検証](../outputs/phase4a/video_review.json)。

## 検証と制御不変

| 検証 | 結果 |
|---|---|
| 非GPUテスト全体 | **130 passed、GPU integration 2 deselected** |
| Phase 4A固有 | 9 passed: 方向、0、clip、長さ、保存信号、資産、遠近投影 |
| Pilot RRD照合 | Demo/Analysis各777 sample、shaft/grip/矢印/数値を元ログと照合 |
| asset load | RRD内GLB blob SHAがファイルと一致 |
| 既存描画データ | Brainを含む441 component streams、53,977 valuesがPhase 3Wと厳密一致 |
| 過去保存物 | **2,769 filesのSHA-256不変**、README/projectは旧本文を残して追記 |
| Phase 3結果 | approach **8/8**、near **2/4**を固定 |
| 新規推論・再学習・制御実験 | **0** |

[回帰検証JSON](../outputs/phase4a/regression.json)、[Pilot検証JSON](../outputs/phase4a/pilot_verification.json)。nearの既知失敗2例への調整は一切行っていない。

## 描画負荷とMode比較

同じ2240×1400、native software renderer。値はIPC・readback・PNG書出しを含む観測で、GPU FPSの比較ではない。

| 指標 | Phase 3W multi | Phase 4A Demo |
|---|---:|---:|
| RRD bytes | 8,225,775 | 8,711,413 |
| 起動からfirst seek（2秒待機含む） | 2.401 s | 2.405 s |
| screenshot RPC中央値 | 0.516 s | 0.516 s |
| viewer RSS | 871,996 kB | 880,556 kB |
| viewer peak RSS | 884,180 kB | 887,468 kB |
| 74枚video capture | 56.46 s | 56.64 s |

RRDは約5.9%増、RSSは約1%増。この条件では追加負荷は小さい。ハエassetはstaticで一度だけ記録し、毎sample更新するのは操縦桿と数値だけ。

Mode Aは実装・検証済み。実コマンドを読み取りやすく、追従脚を生物学的運動と誤解させにくい。一方、固定脚がノブを保持しないため演出上の限界はある。Mode Bの前脚追従は未実装・未比較で、見栄えや負荷の実測値を捏造しない。新しいrigging作業を追加せず、同期表示の成立を優先した。

## 再生・再現コマンド

WSLのプロジェクトルートで実行:

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4a/demo.rrd --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4a/analysis.rrd --bind 127.0.0.1

# 保存ログから表示のみ再生成
.venv/bin/python -m flyrendezvous.viewer_phase4a

# 必要な場合のみ資産再変換
blender --background --disable-autoexec --python-exit-code 1 --python scripts/convert_fly_phase4a.py

# 検証
.venv/bin/python -m pytest tests -m "not integration"
.venv/bin/python scripts/verify_phase4a_regression.py
.venv/bin/python scripts/verify_phase4a_pilot.py
.venv/bin/python scripts/capture_phase4a.py --mode demo --video
.venv/bin/python scripts/capture_phase4a.py --mode analysis
.venv/bin/python scripts/review_phase4a_video.py
.venv/bin/python scripts/export_phase4a_mp4.py
~~~

RRDを再生成した場合はcaptureと動画も作り直す。資産だけを再変換した場合もハッシュを検証する。動画exportは既存.tools/video/pythonのffmpeg 7.0.2を再利用した。

## README・残る制約・推奨

READMEへ「presentation layer」「biological motor outputではない」「u_appliedとの同期」「固定姿勢」「モデルの帰属・利用条件」「制御結果不変」を追記した。外部house-fly模型は実測神経形態ではなく、Drosophilaの運動器検証モデルでもない。FAFB14.1の脳内形態、全45,669 model cellsの計算、type aggregate activityの意味は従来どおりである。

残る制約は、前脚把持なし、単純材質、真上視点による立体感の弱さ、公式ZIPとの原本一致未確認、Windows発表環境でのFPS未測定。OrbitとBrainを優先したためPilotは補助サイズであり、大会場ではAnalysisの大きなPilotも利用できる。

**SpaceROS勉強会のmain Demoへ補助パネルとして採用を推奨する。** 「ハエが生物学的に操縦している」のではなく「画像入力から得た学習器の実指令を模型で説明している」と紹介する。Phase 4Aで停止し、flybody、MuJoCo、筋・運動神経モデル、新規制御実験へ進まない。
