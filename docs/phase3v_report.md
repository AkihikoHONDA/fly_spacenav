# FlyRendezvous Phase 3V 実装・実行・検証報告

2026-09-11。**T2・T4a・T5dの実測代表形態を同じFAFB14.1座標のBrain Viewに表示し、保存済みPhase 3応答に同期して明るさを変えるDemoを完成した。** T4a消失を再現できる旧viewerの末尾RESETを修正した。単体106件、両RRD各777フレームの数値照合、3局面以上の実撮影、WebP/MP4復号検証を実施。旧成果1,297ファイルはSHA一致。制御・readout・HCW・sensor camera・test結果は変更していない。

[Demo実画面](evidence_phase3v/demo_hold.png) ／ [14.633秒MP4](../outputs/phase3v/mp4/phase3v_test00.mp4) ／ [Demo RRD](../outputs/phase3v/phase3v_demo.rrd) ／ [Analysis RRD](../outputs/phase3v/phase3v_analysis.rrd)

## 1. T4aが見えていなかった原因の切り分け

旧outputs/phase3/phase3_demo.rrdを読み、既定blueprintと実画面を再確認した。

| 確認項目 | 結果 |
|---|---|
| T4a morphology entity | /brain/representativeに**777時点**、829頂点／828枝を記録済み |
| anatomy context | ME_R/LOP_R、左側ME/LO/LOP、FB/EBの**7 entity**を記録済み |
| Brain View | blueprintに**T4a接写とFAFB14.1 contextの2つの3D view**。両者のorigin=/brain |
| visibility | 通常時の既定queryにはT4aが含まれる。**最終試行後のClearで消える** |
| opacity | 777時点の形態色のalphaは全て255。透明度0が原因ではない |
| camera framing / panel size | 全体視点では1細胞が小さく、接写も画面幅の約18%へ分割されていた |
| coordinate scale | 元nmを0.001倍してµm。背景も同じ。桁違い・独自位置合わせはない |
| draw order | 3Dの深度描画で、特別な前面化はない。通常サンプルで枝が見えることを実描画確認。全消失は深度順ではなくClearで再現した |
| contrast | 低応答時の細い枝と中立背景は判別しにくい。消失バグとは別の可読性問題 |

**再現した直接原因は、最後の試行にもRESETを出していたこと。** 旧RRDの末尾408.5秒ではT4a・sensor・maps・軌跡がClearされ、脳背景だけが残る。次の試行がないのに「independent next episode」の状態で終わっていた。

[旧RRD entity確認](../outputs/phase3v/phase3_existing_entities.json)、[実blueprint内容](../outputs/phase3v/old_brain_blueprint.txt)、[旧版撮影記録](evidence_phase3v/screenshots_baseline.json)。ユーザーが当時開いていたrecording・時刻・保存済みGUI設定そのものは取得していないので、その画面がこの末尾状態だったとは断定しない。ただし、同じ「脳背景はあるが形態がない」状態を既定RRDだけで再現した。

![旧Phase 3の末尾：背景だけが残る](evidence_phase3v/baseline_terminal.png)

### 修正

Phase 3Vでは、独立試行**間**のRESETだけ残し、最後の試行の後にはClearを出さない。末尾408.0秒の最後の観測を保持する。末尾のtest_09は既知の失敗試行で、成功へ見せ替えてはいない。

![Phase 3Vの末尾：3形態と最終観測を保持](evidence_phase3v/demo_terminal.png)

旧Phase 3のコード・RRD・報告は履歴として保存し、修正版はviewer_phase3v.py、outputs/phase3vに分離した。READMEの先頭を最新版Demoへの入口に変更し、異なる旧RRDを開く混乱を減らした。

## 2. 実測形態の取得と来歴

新規取得は**T2 1本、T5d 1本のみ**。T4aはPhase 1Bの既存ファイルをそのまま再利用。Tm3/L2の形態や同型の複数代表は取得していない。

| type | FlyWire root ID | side | 頂点／枝 | cell_class |
|---|---|---|---|---|
| T2 | 720575940608937923 | right | 1099 / 1098 | ME>LO |
| T4a | 720575940605852192 | right | 829 / 828 | ME>LOP |
| T5d | 720575940623043327 | right | 631 / 630 | LO>LOP |

[公式annotationの固定commit](https://github.com/flyconnectome/flywire_annotations/tree/8587524c1748ce5ef2080822a2fc890fc03bf597)のキャッシュをSHA確認して再利用した。各型についてcell_typeが完全一致しside=rightの最初の行を選択。T2を別型から推定せず、T5をT5dへ読み替えていない。

- annotation commit: 8587524c1748ce5ef2080822a2fc890fc03bf597
- annotation SHA-256: 9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be
- dataset: FlyWire female FAFB、materialization **783**
- source: [fafbsegが公開する取得API](https://fafbseg-py.readthedocs.io/en/latest/source/generated/fafbseg.flywire.get_skeletons.html)と同じ個別precomputed skeleton配布経路
- [T2個別形態](https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783/720575940608937923)
- [T5d個別形態](https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783/720575940623043327)

形態SHA-256：

- T2: aa1ab497abb0dea7633944f5cf09ac413528d3266dfe2ad58ccf13fa561d2de3
- T4a: 636df53b81276202a6209a128f5e7636141e14cd44eb094c3f9fff9402877858
- T5d: b3e2457d6ab57c6a6317818eef8c434390ab8934625c20367dbddc7c7ff796e0

[全来歴・annotation原行・座標範囲・SHA](anatomy_mapping_phase3v.json)、[取得処理](../scripts/fetch_phase3v_morphologies.py)。公開EM再構成由来のスケルトンであり、生成した架空の樹状形態ではない。連結木・finite座標・辺端点・SWCへの往復を検証し、元の辺を修復・追加していない。SWC検証中のfloat32参照計算による丸め差は、元変換と同じfloat64で比較するよう修正し、許容差を緩めず1B同様の1e-6 µmで確認した。

### 利用条件と引用

[FlyWire利用条件](https://flywire.ai/tos)は編集・注釈をCC-BY-NC 4.0としている。関連する[Schlegelのバルク配布](https://zenodo.org/records/10877326)にはCC-BY 4.0が示されるが、今回の個別endpoint infoには独立したライセンス欄がない。両者を来歴に残し、個別endpointへ広い再配布許諾を推定しない。今回の取得・表示はローカルで行い、外部公開はしていない。

[固定版READMEの推奨引用](https://raw.githubusercontent.com/flyconnectome/flywire_annotations/8587524c1748ce5ef2080822a2fc890fc03bf597/README.md)に従う帰属：

- FlyWire Consortium / Dorkenwald et al. (2024), Neuronal wiring diagram of an adult brain, [DOI](https://doi.org/10.1038/s41586-024-07558-y)
- Schlegel et al. (2024), Whole-brain annotation and multi-connectome cell typing of Drosophila, [DOI](https://doi.org/10.1038/s41586-024-07686-5)
- Matsliah et al. (2024), Neuronal parts list and wiring diagram for a visual system, [DOI](https://doi.org/10.1038/s41586-024-07981-1)
- Berg et al. (2025), Sexual dimorphism in the complete connectome of the Drosophila male central nervous system, [DOI](https://doi.org/10.1101/2025.10.09.680999)
- 背景：Jenett et al.、JFRC2／fafbseg。従来の[資産manifest](assets_manifest.json)を保持。

## 3. 座標整合とBrain View

3形態のsourceは**FAFB14.1・nm**。配布infoのidentity transformは既存T4aのものと一致し、背景も[FAFB14.1](https://fafbseg-py.readthedocs.io/en/latest/source/generated/fafbseg.flywire.get_neuropil_volumes.html)。全てnm→µmの0.001倍のみで表示した。見た目合わせの移動・回転・非一様scale・左右反転はない。型ごとに別空間へ退避する必要はなかった。

Brain Viewは**右視葉のME_R/LO_R/LOP_Rを文脈として見る固定視点**。全脳を俯瞰する視点ではない。元meshの三角形辺を中立色[42,49,62]・0.22 UI-point線で表示し、不透明な面による枝の遮蔽を避けた。3形態は各1 entity、全枝同じ色、線幅2.8 UI points。画面上の線幅を読みやすくしたもので、神経突起の実太さを表すものではない。背景8領域をRRDに保持し、主Brain Viewには右3領域を表示する。

表示用EyeControlsはposition=(810,86,183)、look_target=(708,298,180)、up=(0,0,1)。これは観客用の固定視点で、**制御入力の完全固定sensor cameraは変更していない**。個別root IDをFlyvis cell_indexに割り当てず、モデルの左右も未割当。

## 4. Activity coloringとmapの役割

保存された同型721モデル細胞について、RMS=sqrt(mean((activity_i−baseline_i)²))を計算する。Phase 3のtrain24＋validation6の**control periods・試行等重み**からtest前に固定されたp05/p95を、そのまま再利用・再計算照合した。

~~~text
q = clip((RMS - p05)/(p95 - p05), 0, 1)
RGB(type, q) = round(base_RGB(type) * (0.35 + 0.65*q))
~~~

| type | 固定p05 | 固定p95 | q=1のRGB |
|---|---|---|---|
| T2 | 0.203869 | 1.128422 | [255, 166, 65] |
| T4a | 0.094231 | 0.182648 | [80, 175, 255] |
| T5d | 0.064431 | 0.130871 | [245, 100, 225] |

色系統に生物学的意味はなく、typeを見分けるためだけのorange／blue／magenta。q=0でも形態を見失わないよう35%の明るさ下限を設けた。**この下限は表示上の目印であり、活動の追加ではない。** qは型自身の固定した通常範囲内での応答レベルだけを表し、type間の絶対活動比較・発火率・mVではない。q=0でもraw RMSは非ゼロになり得る。raw RMSは5-type barの数値とAnalysis系列に残した。

画面の短い凡例は次の内容：

~~~text
Representative morphologies
Color intensity = within-type relative response
No one-to-one mapping to Flyvis model cells
~~~

実画面では同じ短文をBrain View直下にまとめて表示する。長い免責文はREADMEと本報告へ移した。

| 表示 | 伝える内容 |
|---|---|
| Brain View | どのtypeのモデル群が反応しているかを、実測された代表形態と解剖背景の中で示す |
| Retinotopic map | そのtype内部で視野のどこに対応するモデル格子細胞が、どの符号・大きさで変化したかを示す |

mapは型全体RMSを一色で塗らず、細胞別のsigned Δvを保持。Phase 3で非testから固定した型別±limitをそのまま使う。異なる型の色強度の絶対比較はしない。

## 5. GUI layout

Demo上段はorbitとBrainを約1:1.25で並べ、高さの約68%を使う。下段にsensor、T2/T4a/T5d maps、中小の5型barsとcompact status。詳細グラフはDemoから外し、Analysisへ配置した。

Analysisは3形態Brain View、全5型map（Tm3/L2を含む）、raw/q、加速度、goal誤差、速度、時刻対応を保持。Tm3/L2はbar/mapのままで形態はない。

![Phase 3V Demo：3形態＋脳背景＋保持局面](evidence_phase3v/demo_hold.png)

## 6. Playbackと実スクリーンショット

既存の成功approach **test_00** を再生した。元testを再計算せず、同じbaseline・応答・画像・状態・適用加速度を使用する。物理0.5秒と神経0.01秒の対応、15倍再生を維持。3型のbrightnessは以下の実値に対応する。

| type | 局面／時刻 | raw RMS | q | 実RRDのRGB |
|---|---|---|---|---|
| T2 | early approach / 20.0 s | 0.236140 | 0.034904 | [95, 62, 24] |
| T2 | braking / 85.0 s | 0.411852 | 0.224955 | [127, 82, 32] |
| T2 | near/hold / 219.0 s | 0.917910 | 0.772310 | [217, 141, 55] |
| T4a | early approach / 20.0 s | 0.093359 | 0.000000 | [28, 61, 89] |
| T4a | braking / 85.0 s | 0.123272 | 0.328451 | [45, 99, 144] |
| T4a | near/hold / 219.0 s | 0.138608 | 0.501905 | [54, 118, 172] |
| T5d | early approach / 20.0 s | 0.067712 | 0.049380 | [94, 38, 86] |
| T5d | braking / 85.0 s | 0.078776 | 0.215902 | [120, 49, 110] |
| T5d | near/hold / 219.0 s | 0.113305 | 0.735606 | [203, 83, 186] |

![early approach](evidence_phase3v/demo_early.png)

![braking](evidence_phase3v/demo_braking.png)

![near/hold](evidence_phase3v/demo_hold.png)

各形態がearlyでは暗く、braking〜holdで明るくなることを実画面で確認した。T4aのqはT2/T5dと同一ではない。全枝同色のまま緩やかに変わり、架空のspikeや枝内伝播は加えていない。保持では実応答の変化も小さくなる。初期・diagonal・末尾の追加画面も保存した。

[撮影・seek/play/pause記録](evidence_phase3v/screenshots_demo.json)、[Analysis実画面](evidence_phase3v/analysis_braking.png)、[定量検証](../outputs/phase3v/verification.json)。

### 動画

[WebP](../outputs/phase3v/phase3v_test00.webp)はnative Rerunの6サンプルごとの画面と最終サンプル、74枚、1600×1000、14,633 ms。全74枚を復号し、各元PNG SHA・フレーム期間・連続playを照合した。

[MP4](../outputs/phase3v/mp4/phase3v_test00.mp4)は同じ実フレームを既存ffmpegでH.264/yuv420pへ変換。30 fps、439フレーム、14.633333秒。撮影間は同じ画像を保持し、形態・活動を補間していない。全439フレームを復号して元画像と比較し、時刻PTSとdurationを検証した。詳細なPSNRとSHAは[MP4検証](../outputs/phase3v/mp4/verification.json)。

実画面はnative Rerun headless/software rasterizer。実際のplay/seek/pauseと連続再生を検証したが、Windows GUIの人手マウス操作、プロジェクターでの視認性、実時間GUI性能は未検証。

## 7. Test・不変性

| 検証 | 結果 |
|---|---|
| 単体 | **106/106通過**（既存96＋新規10） |
| 追加検証内容 | exact type・元座標と接続・3本限定・固定色系統・明るさ単調性と下限・不正入力・非test尺度・末尾Clear回帰 |
| 旧RRD診断 | T4a777時点、背景7 entity、2つの3D view、alpha255、末尾消失を実画面で再現 |
| 新RRD数値照合 | Demo/Analysis各**777フレーム**。3形態全2,556枝・RGB・ラベル位置、背景、5 maps、bars、画像・軌道・v/a・系列・時刻 |
| 校正 | train+validation30試行のp05/p95を再計算し、test開始前の固定SHAと一致 |
| 動画 | WebP74/74枚、MP4全439枚復号、元PNG照合、PTS確認 |
| 旧成果 | **1,297/1,297 SHA一致**。制御・readout・HCW・camera・test・旧コード／報告／証拠・形態を保持 |
| 新しい推論／制御実験 | **0 / 0** |
| GPU統合 | 今回は未実行（2件をdeselect）。表示のみの変更で新規推論は行わない。既知のPhase 3 prefix再現性失敗は未解決のまま |

Phase 3 testは**接近8/8・near2/4**、nearのFOV外1・timeout1という既知結果のまま。3V RRDはtest_00、test_08、test_09の保存記録を使うが、新しいtest評価ではない。near失敗へreadoutを合わせていない。将来の改善は別Phase・新splitとする。

[unit log](../outputs/phase3v/unit-tests.log)、[Demo RRD照合](../outputs/phase3v/rrd_audit_demo.json)、[Analysis RRD照合](../outputs/phase3v/rrd_audit_analysis.json)、[不変性・定量確認](../outputs/phase3v/verification.json)、[保護対象SHA](../outputs/phase3v/prior_hashes.json)。

## 8. 再生・再検証

WSLプロジェクトルートから最新版を開く。--newは他のRerunウィンドウへの接続を避けるための新規viewer指定。

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3v/phase3v_demo.rrd --new --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3v/phase3v_analysis.rrd --new --bind 127.0.0.1
~~~

0〜219秒は成功approach。20秒、85秒、219秒を比べると3形態の変化が分かる。試行間にはRESETがあり、最後の観測は保持される。

~~~bash
OPENBLAS_NUM_THREADS=4 .venv/bin/python -m pytest tests -m 'not integration'
.venv/bin/python scripts/verify_phase3v.py
.venv/bin/python scripts/verify_phase3v_rrd.py
.venv/bin/python scripts/review_phase3v_video.py
~~~

再生成は既存ログだけを使う：

~~~bash
.venv/bin/python scripts/fetch_phase3v_morphologies.py
RERUN_ANALYTICS_ENABLED=false .venv/bin/python -m flyrendezvous.viewer_phase3v
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3v.py --baseline
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3v.py --video
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3v.py --mode analysis
.venv/bin/python scripts/verify_phase3v_rrd.py
.venv/bin/python scripts/verify_phase3v.py
.venv/bin/python scripts/review_phase3v_video.py
.venv/bin/python scripts/export_phase3v_mp4.py
~~~

取得スクリプトは既存manifestがあればSHA確認だけを行い、追加細胞を取らない。RRD再生成後はSHAが変わるため撮影・動画も再生成する。

## 9. 終了条件と制約

6終了条件を満たした。脳背景とT4a、3つのexact型実測代表、実RMS/qとの同期、mapとの役割区別、制御不変、READMEの意味説明を確認した。

ただし、**3形態は表示した実測細胞自身の活動ではない**。Flyvis細胞との一対一対応なし、同型モデル群の集約値、枝内伝播なし。Flyvisは3型だけでなく全45,669モデル細胞を計算している。モデルと実測の左右対応も未割当。右視葉を拡大した文脈表示であり、全脳の神経活動表示ではない。

3Vでは追加した2形態以外の取得、再学習、新しい接近方向、gaze control、sensor方向変更、target/goal変更、Tm3/L2形態、同型複数代表、枝内伝播、ハエ型機体、photorealistic asteroid、ROS/MuJoCoへ進んでいない。ここで終了する。
