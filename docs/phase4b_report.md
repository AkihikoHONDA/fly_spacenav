# Phase 4B report — Stylized Fly Pilot + articulated forelegs

実施日: 2026-09-12 JST。**proceduralなA/B/Cを生成し、指定のVariant Bを既定としてRerunへ統合した。左右前脚の2-link IKが保存済み操縦桿へ追従する。** Phase 4Aを含む旧成果は保持し、制御・学習・HCW・fixed sensor camera・Phase 3 test結果は変更していない。

## GeneratorとA/B/C

[generator](../assets/fly_pilot_phase4b/generate_stylized_fly.py)はBlender Pythonでsphere、ellipsoid、cylinderを生成する。外部ハエasset、写実texture、生成AI mesh、画像からの復元は使わない。頭、胸部、腹部、左右の大きな目、小さなハイライト、2枚の翼、固定middle/rear legs、coxa、可動front legsを構成した。体毛・複眼facet・鋭い口器・idle motionは追加していない。

[design_params.json](../assets/fly_pilot_phase4b/design_params.json)だけで3案を切り替える。Blenderの同じ3/4 orthographic camera、照明、neutral poseで960×720 PNGを生成した。

![A/B/C comparison](evidence_phase4b/design_comparison.png)

[A原寸](evidence_phase4b/design_A.png) ／ [B原寸](evidence_phase4b/design_B.png) ／ [C原寸](evidence_phase4b/design_C.png)

| 寸法（display units） | A conservative | B mascot・既定 | C extra playful |
|---|---:|---:|---:|
| head diameter基準 | 0.85 | 1.0625 | 1.12 |
| eye diameter基準 | 0.37 | 0.4625 | 0.49 |
| thorax length / width | 1.00 / 0.72 | 0.95 / 0.80 | 0.85 / 0.84 |
| abdomen length / width | 1.25 / 0.58 | 1.10 / 0.64 | 1.00 / 0.68 |
| wing length / width | 1.45 / 0.54 | 1.25 / 0.60 | 1.20 / 0.62 |
| leg radius | 0.050 | 0.060 | 0.062 |

BはA比で頭・目を25%大きくし、胴体を丸め、翼を短くした。Cはさらに胴を詰めるが、小サイズではB/Cの差は控えめ。Aは体節が読みやすく、Bは顔が読みやすい。これらは見た目の観察であり、人間の「怖さ」を測った実験ではない。追加の装飾案へ広げず、ユーザー指定のBで完成させた。

色は温かい茶色系のbody、明るめの脚、赤橙色の目、淡いgray-blueの翼。テクスチャなし、roughness 0.7、metallic 0。翼alphaは0.65。実Rerunでは重なりによって白く不透明に近く見える箇所がある。Blender比較PNGとRerunの照明は同一ではない。

bodyは27 named objects、4,014 vertices、7,920 triangles。B bodyと左右6 limb assetsの合計は292,056 bytes。default body SHA-256:
`2ce65cc1d8aedcc07b74525c01033d2e46380c97526b2603ef0a17571b220174`。
[全資産manifest](../assets/fly_pilot_phase4b/manifest.json)にSHA・設定・Blender版を保存した。

標準GLB exporterの内部dedup順序、Blender tessellation順序・法線丸め差による非決定性を除くため、object順、polygon開始頂点、fan triangulation、triangle順、normal集計、accessor順を固定したGLB writerをgeneratorに含めた。別プロセス・一時ディレクトリへの再生成で**A/B/C bodyと全segmentのバイトSHA一致**を確認した。既存Blender 4.0.2を使用し、新規ツール導入はない。

## 前脚hierarchyとIK

body、翼、middle/rear legsはstatic。前脚は左右それぞれproximal origin、local +Z方向のupper/lower、footを分離したGLBで構成する。上腕・下腕の長さはともに**0.62**。初期値に対しupperだけ約7%延長、lowerは同じ。異なる長さによる内側の到達不能域を避け、実ログの小さな肩近傍targetにも届くようにした表示上の寸法選択である。

~~~text
shoulder/coxa anchor
  upper rotation
    upper mesh
    lower translation (0,0,0.62) + relative rotation
      lower mesh
      foot translation (0,0,0.62)
        contact-tip mesh
~~~

肩はL=(0.12,0.63,1.16)、R=(0.12,-0.13,1.16)。指令から得たgrip centerへ、stick軸に直交するlocal横方向に±0.11のoffsetを加えて左右targetを分ける。ノブ半径0.13に対する説明用contact tipで、接触力学はない。

[IK実装](../src/flyrendezvous/ik_phase4b.py)は解析的2-link解。S→T方向に対して固定の下向きpoleを射影し、余弦定理で肘位置を決める。到達距離は `[abs(L1-L2)+eps, L1+L2-eps]` にclamp。link長や指令を変形しない。肘の曲がり側を毎frame任意に選ばず、同じpoleから決めるため、seek順序にも依存しない。

初期の横向きpoleではnear trialの急な指令変化で曲げ方向が反転することをテストで発見した。下向きpoleへ修正後、全trial内の隣接bend方向の内積最小値は**0.47794 > 0**。フレーム間の枝選択反転はない。実表示777 sampleでは到達clamp **0**、合計1,554脚先がtargetへ到達。範囲外・ゼロ距離・特異方向は別の合成unit inputでclampと有限解を検証した。これは新しい制御実験ではない。

Rerun内の実際の親子matrixからforward kinematicsを再計算し、元ログから独立に算出したtargetとの最大誤差は**7.90×10⁻⁸ display units**。接続・長さ・rotationの直交性・static assetのblob SHAも確認した。[RRD検証](../outputs/phase4b/pilot_verification.json)。

## 同期信号と視点

信号はPhase 4Aと同じ**保存済みu_applied、同一sample、同一時刻**。映像用の別指令、teacher、u_raw、平滑化、idle animationへ差し替えていない。

~~~text
a_disp = [-a_y, a_x]
u = clip(a_disp / 0.005, -1, 1)
tip_xy = base_xy + 0.55 * u
tip_z = base_z + sqrt(1.2² - |0.55*u|²)
base = [0.65, 0.25, 0.18]
~~~

joystick base/shaft/grip、台座、加速度arrow、範囲枠の記録値は**Phase 4Aと完全一致**。変化したのはbody asset、前脚、Pilot専用cameraとガイド・説明である。

Pilot cameraはposition=(1.35,-1.95,3.85)、look_target=(-0.15,0.25,1.05)、up=+Zの固定3/4視点。センサーカメラとBrain cameraは変更しない。斜め視点ではZ高さとXY方向が投影上で混ざり、neutralの直立stickも斜めに見える。従って3Dの画面角度をそのままOrbitの2D角度と同一視しない。

小さな**Command XY guide**は `[u_x,-u_y]` をそのまま描画し、Orbitと厳密に同方向。左=+along-track、下=中心天体方向と明記した。3D投影でも正負の単軸指令で当該左右・上下成分が逆転しないことをテストした。定量的な方向・強さはguideとm/s²数値で読む。bodyの傾き、羽ばたき、呼吸などは追加していない。

## Demo・実画面・Phase 4Aとの比較

Orbit/Brainの大きさ、sensor、T2/T4a/T5d maps、5-type bars、compact statusの大枠を維持した。Pilot内だけを3Dと小guide＋短文へ配置した。Analysisにも同じBとIKを表示する。

表示文:
- Joystick: learned 2D command.
- Forelegs: illustrative IK, not biological motor output.
- X/Y成分とguide方向。

![Actual Demo, 20 s](evidence_phase4b/demo_early.png)

| 局面 | 時刻 / sample | a_disp X / Y (m/s²) | 実Rerun証拠 |
|---|---|---|---|
| neutral | 0 s / 0 | 0 / 0 | [demo_neutral.png](evidence_phase4b/demo_neutral.png) |
| early approach | 20 s / 40 | +0.00141477 / +0.00427493 | [demo_early.png](evidence_phase4b/demo_early.png) |
| braking | 85 s / 170 | -0.00056090 / -0.00072195 | [demo_braking.png](evidence_phase4b/demo_braking.png) |
| near/hold | 219 s / 438 | -0.00018555 / -0.00015738 | [demo_hold.png](evidence_phase4b/demo_hold.png) |

4時点でforelegの接続とgripへの追従を目視確認し、全時点の数値は上記FKで検証した。hold指令は非ゼロのため、小さな偏位もそのまま残す。neutralの肘は下へ曲がり、指令に応じて伸縮せず角度だけが変わる。[Analysis実画面](evidence_phase4b/analysis_early.png)。

![Phase 4A versus Phase 4B](evidence_phase4b/phase4a_vs_phase4b.png)

比較は両方の20 s・2240×1400実スクリーンショットから、同じ505×425 pixel領域を無拡縮で切り出した。[元画像・crop・SHA](evidence_phase4b/comparison.json)。

| 観点 | Phase 4A | Phase 4B |
|---|---|---|
| 親しみやすさ | 黒い実物寄りbodyと細脚 | 丸い茶色bodyと大きな目で標本らしさが弱い |
| 小サイズの形 | 翼は明瞭、body詳細は暗い | 顔・翼・太い脚の区別がつきやすい |
| 操作の説明 | 固定脚はノブを追わない | 左右脚先がノブに追従する |
| 指令方向 | 真上視点で直感的 | 3D単独では劣る。guide・数値併用で明確 |
| 破綻・制約 | 関節animationなし | 接続・長さ・反転は検証済み。遮蔽や自己接触回避は未解決 |

Bの方が全て優れるとは結論しない。4Bはキャラクターと操作の説明を改善し、4Aは直接的な方向表示に利点がある。遠側の脚や目の一部は視点・姿勢により隠れる。常に6本全ての輪郭が完全に分離するとは保証しない。

## 動画とplayback

[Demo MP4](../outputs/phase4b/mp4/phase4b_test00.mp4)はH.264、1600×1000、30 fps、439 frames、**14.633秒**、1,108,290 bytes。[WebP](../outputs/phase4b/demo_test00.webp)も保存した。

元の0〜219 sを15倍速で表示。実Rerunを6 sample間隔＋最終sampleで74回captureし、間の画像はholdする。架空の中間pose・指令・活動を補間しない。通常のRRD playbackでは元777 sampleすべてのtransformを利用する。

native Rerunでseek/play/pause/terminal保持を確認し、連続play中の9 captureで219 s到達を確認。WebP全74枚のハッシュ・durationを照合。MP4全439枚を復号し、PTS 0〜438、time base 1/30、元画像とのPSNR最小40.34 dBを確認した。[動画manifest](../outputs/phase4b/video_manifest_demo.json)、[MP4検証](../outputs/phase4b/mp4/verification.json)、[WebP検証](../outputs/phase4b/video_review.json)。

## Testsとregression

| 検証 | 結果 |
|---|---|
| 非GPU全体 | **144 passed、integration 2 deselected** |
| Phase 4B固有 | **14 passed** |
| generator | A/B/Cと6 segmentを別プロセスで再生成、GLB SHA一致 |
| IK | 長さ保持、内外clamp、有限解、neutral、全ログのbend連続性 |
| camera/guide | 正負単軸の投影符号、Orbitと同じ平面成分 |
| 実RRD | 各777 sample、左右1,554脚先、7 static asset blobs |
| 従来表示 | 441 streams / 53,977 valuesがPhase 4Aと完全一致 |
| 旧成果 | **2,913ファイルのSHA不変** |
| Phase 3 test | approach **8/8**、near **2/4**のまま |
| 新推論・再学習・新制御実験 | **0** |

[regression.json](../outputs/phase4b/regression.json)。README/projectは旧本文を保持して追記した。near失敗2例の調整、test条件変更、HCW更新はない。GPU制御の再試験は今回の範囲外として行っていない。

## 描画・再生コスト

同じ2240×1400 native headless software renderer。capture時間はIPC/readback/PNG書出しを含み、発表PCのGPU FPSを表すものではない。

| 指標 | Phase 4A Demo | Phase 4B Demo |
|---|---:|---:|
| RRD bytes | 8,711,413 | 8,623,356 |
| 起動からfirst seek（2秒待機含む） | 2.405 s | 2.401 s |
| screenshot RPC中央値 | 0.516 s | 0.522 s |
| viewer RSS | 880,556 kB | 894,528 kB |
| peak RSS | 887,468 kB | 907,200 kB |
| 74枚capture所要時間 | 56.64 s | 57.24 s |

関節transformは増えるが、テクスチャ不要の小さいassetによりRRDは約1%小さくなった。RSSは約1.6%増。この測定では大幅な負荷増は見られない。Windows GUIの手動操作・実時間FPSは未測定。

## 再現・再生

WSLのプロジェクトルートで実行:

~~~bash
# 同じA/B/CとBの分割GLB、比較用PNGを生成
blender --background --disable-autoexec --python-exit-code 1 --python assets/fly_pilot_phase4b/generate_stylized_fly.py

# 元ログだけでDemo/Analysisを生成
.venv/bin/python -m flyrendezvous.viewer_phase4b

# GUI再生
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4b/demo.rrd --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4b/analysis.rrd --bind 127.0.0.1

# 検証・動画・比較
.venv/bin/python -m pytest tests -m "not integration"
.venv/bin/python scripts/verify_phase4b_regression.py
.venv/bin/python scripts/verify_phase4b_pilot.py
.venv/bin/python scripts/capture_phase4b.py --mode demo --video
.venv/bin/python scripts/capture_phase4b.py --mode analysis
.venv/bin/python scripts/compare_phase4b.py
.venv/bin/python scripts/review_phase4b_video.py
.venv/bin/python scripts/export_phase4b_mp4.py
~~~

モデル・RRDを変更した場合はcapture/videoも再生成する。ffmpegは既存.tools/video/pythonを再利用。generatorの再現性テストはBlenderを使用するが、Flyvisの推論やGPU学習は行わない。

## 限界と勉強会への推奨

**Phase 4BのB＋IK＋平面guideを、SpaceROS内部勉強会の補助Pilotとして採用を推奨する。** A/Cは人間レビュー用に保存した。4Aも比較用にそのまま残した。

このbodyはproceduralな説明用stylized modelで、actual fly anatomyではない。前脚はjoystick targetに対するillustrative IKであり、Flyvisが脚関節角を出しているわけではない。motor neuron、muscle、body/contact physics、操作力の再現ではない。脳内で表示する実測T2/T4a/T5d形態とは意味が異なる。

残る視覚的問題は遠側脚の遮蔽、翼の白さ、自己接触回避なし、3D投影単独での方向の読みづらさ。関節上限や生物学的妥当性は検証していない。美観を理由に別デザインや全身運動へ拡張せず、Bの完成と証拠保存で終了する。Phase 4C、flybody、NeuroMechFly、MuJoCo、新制御実験へは進まない。
