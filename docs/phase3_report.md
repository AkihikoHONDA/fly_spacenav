# FlyRendezvous Phase 3 実装・実行・検証報告

2026-09-11。**球形ターゲットへの斜め下側からの画像入力standoff rendezvousは、held-outの接近8/8で成功した。nearは2/4、合計10/12成功で、近傍の頑健性は未達。** 教師は12/12。指定6候補からvalidationだけでモデルを選び、testを一度評価した。test後の再学習・条件緩和・教師救済は行っていない。

[添付指令の保存版](codex_phase3.md)、[固定設定](../configs/phase3.json)、[全評価JSON](../outputs/phase3/evaluation.json)、[集計と失敗診断](../outputs/phase3/summary.json)。

## A. Problem geometry

- 従来と同じ2D HCW。LVLH xは中心天体から外向き、yは軌道進行方向。n=0.0011 s⁻¹、ZOH離散化、物理dt=0.5秒、各軸加速度上限0.005 m/s²。
- 球中心は原点、半径1 m。e_r=(-1,+1)/√2、e_t=(-1,-1)/√2（LVLHで90°反時計回り）。goal=(-3.5355339,+3.5355339) m、目標速度0。中心から5 m、表面から4 mのstandoff pointへ止まる。
- 表示はX=-y、Y=x（上正）、Rerun下正キャンバスには(-y,-x)。goalは左下。target sphere、半径5 mのstandoff circle、選択されたgoalを区別する。
- approach初期位置はr0 e_r+c e_t、r0∈[14,22] m、c∈[-2,2] m。vx/vy各±0.02 m/s。nearはgoalからradial/tangential各±0.5 m、vx/vy各±0.01 m/s。
- collisionは中心距離≤1.25 m、range exitは≥40 m。FOV外・nonfiniteも別理由で終了。
- 成功はgoal誤差<0.25 mかつ速度<0.01 m/sを連続10物理秒（20区間）保持。区間両端の条件を確認。最大400秒。

各試行で一様灰色1神経秒のreset/warmupを行う。最初の10物理秒はu=0だがHCW運動は進む。その後も神経dt=0.01秒、物理／神経時間比50を維持。画像k→更新後神経応答→区間[k×0.5,(k+1)×0.5)の適用加速度を保存する。再生15倍とは別で、ハエの実時間制御を主張しない。

### 球のカメラ投影

64×64、水平FOV設定40°、boresight=-e_r=(+1,-1)/√2を固定。画面右軸は(+1,+1)/√2。追尾・姿勢制御なし。背景0.5、silhouette1.0、8×8サブピクセル面積平均。

**指令の円形silhouetteを、厳密な球の透視投影を包む円として実装した。** 軸外の球の厳密なpinhole silhouetteは楕円なので、円形化は近似である。真の球の水平接線境界を保ち、垂直方向を保守的に広げる。旧diskのfR/xを回転流用していない。

カメラ座標のdepth=z、lateral=l、中心距離=d、球半径=R、f=31.5/tan(20°)として、

~~~text
u_center = 31.5 + f*l*z/(z²-R²)
v_center = 31.5
radius = f*R*sqrt(d²-R²)/(z²-R²)
~~~

bearing βと球の角半径α=asin(R/d)に対するtan(β±α)の中点・半幅から導いた。軸上はfR/√(d²-R²)。z≤R、球内部・背面・nonfiniteはinvalid。画素中心0..63、外縁-0.5..63.5への全包含をFOV gateとする（Phase 2と同じ画素・焦点距離規約）。

独立に球の3D接線円をpinhole投影し、その全体を包むことをテストした。最終teacher gateの円半径／真の楕円短半径の最大比は1.007685（垂直過大分≤0.769%）。abs(bearing)+αは最大17.595°で名目半視野20°にも余裕がある。

## B. Teacher gate

旧Q=diag(0.01,1/9,25,25)、R=diag(40000,40000)をLVLHへそのまま適用した初回は、**approach0/20・near10/10**。接近20試行は全てFOV外終了。y位置誤差をxより強く抑えるため斜め接近軌道が曲がり、球が視野端を越えた。独立角度計算でも確認し、camera sign bugとは扱っていない。

指令でQ/Rが「初期案」とされていることに基づき、**同じQ固有値を接近radial/tangential軸へ回転**した。B=[e_r,e_t]、S=diag(B,B)、Q_new=S Q_old Sᵀ。R・HCW・上限・球・goal・FOV・初期条件・成功条件は維持した。教師の設計変更であり、単なる実装バグ修正とは称さない。初回の設定・LQR・30軌道・失敗結果を保存した。

新goalのu_eq=(-3n²x_goal,0)=(+1.2834×10⁻⁵,0) m/s²、u=u_eq−K(s−s_goal)。y_goal≠0を誤差ベクトルへ反映し、連続／離散の平衡を検証した。回転後は同じseed3100で**approach20/20・near10/10、30/30成功、FOV喪失0、衝突0**。終了44.5〜242.5秒、最小表面距離3.607 m、試行別最大飽和率5.591%。ゲート通過後に神経データ生成・学習へ進んだ。

[初回失敗](../outputs/phase3/phase3a_initial.json)、[最終gate](../outputs/phase3/phase3a.json)、[最終LQR](../outputs/phase3/lqr.json)。

![初回失敗と教師のQ座標系変更](evidence_phase3/teacher_gate_diagnostic.png)

## C. Zero-shotとデータ生成

旧Phase 2 readoutの重み・標準化・出力軸をそのまま使い、新train条件の最初のapproach2本・near2本を診断した。**0/4成功**。approach2本はrange exit、near2本はFOV外。旧readoutは新camera/goalへ転用できなかった。この4本は新testの成績ではなく、validationにも追加していない。旧readout SHAは7cc96bd86ba09fa3b688f7574249fde22abb6ff10a1149f7817832459e407151で不変。[zero-shot](../outputs/phase3/zero_shot.json)

splitを神経データ生成前に固定した。

| split | seed | approach | near | 合計 |
|---|---:|---:|---:|---:|
| train | 3101 | 16 | 8 | 24 |
| validation | 3102 | 4 | 2 | 6 |
| held-out test | 3103 | 8 | 4 | 12 |
| 教師gate（独立） | 3100 | 20 | 10 | 30 |

train/validation教師30本は**30/30成功**し、実画像を状態保持Flyvisへ入力した。全45,669モデル細胞を計算し、非input57型・39,901細胞の4×4符号付きbaseline差poolingで912特徴。input R1..R8の5,768細胞は計算するがreadoutには直接含めない。

T2/Tm3/T4a/T5d/L2の各721細胞応答を全神経試行で保存し、train_00では全45,669細胞応答も保存。計算・学習・表示の対象は別。平均・標準偏差・定数除外はtrain制御期間のみで算出。ラベルは飽和済み教師加速度/a_max。選択モデルは912特徴全てを保持し、学習標本7,817。旧adapter/features/readoutは変更していない。

[data](../outputs/phase3/data.json)、[features](../outputs/phase3/features.json)、[split](../outputs/phase3/splits.json)。

## D. 線形readoutの学習・選択

現時刻のみ／現時刻＋5フレーム前連結、λ=10⁻⁴/10⁻²/1の6候補を学習した。MSEはa_maxで正規化した出力のteacher-forced値で、closed-loop成功数とは別指標。

| 候補 | train MSE | validation MSE | validation成功 | 平均最終誤差 m |
|---|---|---|---|---|
| lag0_lambda0.0001 | 0.000212 | 0.006541 | 6/6 | 0.1932 |
| lag0_lambda0.01 | 0.000837 | 0.002417 | 5/6 | 0.2783 |
| lag0_lambda1 | 0.004393 | 0.005854 | 2/6 | 1.9810 |
| lag5_lambda0.0001 | 0.000132 | 0.012156 | 4/6 | 0.3771 |
| lag5_lambda0.01 | 0.000673 | 0.002207 | 5/6 | 0.8698 |
| lag5_lambda1 | 0.003240 | 0.005141 | 1/6 | 2.4527 |

選択はvalidation閉ループ成功数最大→平均最終位置誤差最小→teacher-forced MSE最小→lag/λ。**lag0、λ=0.0001、validation6/6**を選んだ。MSEだけなら他候補が小さいが、規定どおり閉ループ成功を優先した。

追加教師付け条件「normalized RMSE<0.25かつvalidation成功<6」は不成立で、**追加0 round**。MLP・RL・PCA・新特徴量・非線形readoutは使っていない。[全候補](../outputs/phase3/round0/candidates.json)、[model lock](../outputs/phase3/model_lock.json)、[追加判定](../outputs/phase3/augmentation.json)。

新readout SHA: d6a073fa889447d9b7d4dd25da4b2b590cbc9014071d21015d2f591243e757ee。

## E. Held-out test：学習器自身の閉ループ

モデル固定後、未使用12条件を一度だけ評価した。ImagePolicy.stepの引数はimageだけ。真の状態・速度・時刻・教師ラベルを制御器に渡さず、保存ラベルは評価専用。HCWは学習器の飽和後加速度で更新した。教師軌道をlearnerとして再生する処理や失敗時の教師切替はない。

| controller | approach | near | 全体 | FOV喪失 | 衝突 |
|---|---:|---:|---:|---:|---:|
| 教師（test比較） | 8/8 | 4/4 | 12/12 | 0 | 0 |
| 新Flyvis＋readout | **8/8** | **2/4** | **10/12** | 1 | 0 |

| ID | 区分 | 結果 | 終了 s | 誤差 m | 速度 m/s | 最小表面距離 m | 飽和率 | ∫|a|dt m/s |
|---|---|---|---|---|---|---|---|---|
| test_00 | approach | success | 219.5 | 0.1754 | 0.00608 | 4.1752 | 0.0% | 0.2211 |
| test_01 | approach | success | 222.0 | 0.1748 | 0.00599 | 4.1741 | 4.7% | 0.2522 |
| test_02 | approach | success | 266.0 | 0.1764 | 0.00632 | 4.1764 | 1.2% | 0.2808 |
| test_03 | approach | success | 247.5 | 0.1787 | 0.00612 | 4.1786 | 0.0% | 0.2396 |
| test_04 | approach | success | 252.5 | 0.1761 | 0.00593 | 4.1753 | 0.0% | 0.1809 |
| test_05 | approach | success | 239.5 | 0.1787 | 0.00601 | 4.1785 | 0.0% | 0.1999 |
| test_06 | approach | success | 258.5 | 0.1778 | 0.00605 | 4.1777 | 0.0% | 0.2525 |
| test_07 | approach | success | 250.0 | 0.1748 | 0.00623 | 4.1747 | 0.8% | 0.2277 |
| test_08 | near | success | 84.0 | 0.1720 | 0.00671 | 3.6544 | 0.0% | 0.1566 |
| test_09 | near | field_of_view_exit | 85.0 | 1.0270 | 0.02818 | 3.5558 | 18.0% | 0.2286 |
| test_10 | near | success | 97.5 | 0.2290 | 0.00296 | 3.6823 | 0.0% | 0.1543 |
| test_11 | near | timeout | 400.0 | 1.0882 | 0.01773 | 4.2681 | 3.2% | 0.5500 |

終了時刻は10秒保持を完了した時刻、失敗はabort/timeout時刻。飽和率は制御期間中にいずれかの軸が上限へ達した割合。∫|a|dtは加速度ノルムの時間積分で、燃料消費ではない。全教師試行の同じ指標は[evaluation.json](../outputs/phase3/evaluation.json)に保存した。

learner接近成功時間219.5〜266秒、near成功84〜97.5秒。全12本の最小中心距離4.5558 m、表面距離3.5558 m。接近の平均最終誤差0.1766 m・速度0.00609 m/s。nearは失敗込みで平均誤差0.6290 m・速度0.01389 m/s。全体の平均∫|a|dtは0.24534 m/s、教師0.16635 m/s。ただし終了理由・時間が異なり、公平な燃料効率比較とは扱わない。

補助比較として同じtest_00初期値のu=0軌道も1本保存した（field_of_view_exit、310.5秒）。これは旧readoutのzero-shotとは別の無制御baselineで、モデル選択・成功数に加えていない。

### 失敗理由

- **test_09 / near**：85秒でFOV外。誤差1.0270 m、速度0.02818 m/s。途中で条件内に入ったが最長保持6秒で10秒に届かなかった。最終radial誤差+0.4169 m、tangential誤差−0.9385 mで横ずれが拡大。最後のayは−0.005へ飽和した。
- **test_11 / near**：400秒でtimeout。誤差1.0882 m、速度0.01773 m/s、保持0秒。radial誤差+1.0827 mが主で、停止位置へ収束していない。最後のaxは+0.000157、教師ラベルは−0.000359 m/s²で符号も異なる。

これは保存ログの記述で、唯一の因果機構を特定したとは言わない。nearの汎化不足が残る。testを見た再選択・正規化変更・条件緩和・追加学習はない。

![教師・learner・旧zero-shotの軌道](evidence_phase3/trajectories.png)

![成功1本と失敗2本の教師比較](evidence_phase3/teacher_vs_learner.png)

## F. GUIと神経活動

DemoとAnalysisを別RRDにした。両者は同じ元test_00、test_08、test_09（接近成功・near成功・near失敗）を使い、**各777表示フレーム**。Phase 2と異なり、再生のための制御再推論をしていない。元testの状態・画像・活動・指令をそのまま表示する。最終区間の適用前サンプルまで表示し、完了時刻をstatusに記載。試行間は明示RESETとし補間しない。

Demoは大きな軌道（幅配分43%）、sensor、5型bar、FAFB14.1背景とT4a接写、T2/T4a/T5d map、compact statusを同時表示。初回実画面の脳の見切れを受け、背景カメラだけ引いて全体を収めた。形態座標・寸法・左右・対応は変更しない。Analysisは5型全map、raw/q系列、加速度・goal誤差・速度・時間対応、T4a absolute/relative比較を追加した。真の状態は表示・評価専用。

![Demo: hold直前の実Rerun](evidence_phase3/demo_hold.png)

![Analysis: 実Rerun](evidence_phase3/analysis_braking.png)

### 非testの固定尺度

train+validation教師30本、各試行等重み、制御期間のみからRMSのp05/p95、細胞別|Δv|のp99を計算し、test開始前にSHA固定した。q=clip((RMS−p05)/(p95−p05),0,1)。mapは型別固定±p99。毎フレーム再正規化なし。全5型でrange>10⁻⁸。

| type | p05 RMS | p95 RMS | map固定 ±limit |
|---|---|---|---|
| T2 | 0.203869 | 1.128422 | 2.198860 |
| Tm3 | 0.054679 | 0.220236 | 0.426523 |
| T4a | 0.094231 | 0.182648 | 0.542405 |
| T5d | 0.064431 | 0.130871 | 0.432711 |
| L2 | 0.152498 | 0.497440 | 0.871707 |

[校正元と尺度](../outputs/phase3/display_scales.json)、[test開始lock](../outputs/phase3/test_started.json)。raw RMSをbar数値とAnalysis系列に残す。qや異なる型のmap色強度を、型間の絶対活動比較には使わない。mapは青=負、白=ゼロ、赤=正。

T4aは既存実測1形態（FlyWire783、720575940605852192、右側、829頂点／828枝）。721モデル細胞RMS/qで全枝を同じ色にする。文脈と接写は同じ形態。実細胞自身の活動・個別対応・枝内伝播・発火率ではない。脳背景はFAFB14.1 µm、未割当の中立色。新形態は取得していない。

### 実描画・再生・動画

native Rerunで初期0秒、early20秒、diagonal73秒、braking85秒、hold219秒を撮影し、seek/play/pauseを検証した。Analysis撮影では複数recordingの先頭を参照していた検証コードをactive recording参照へ修正した。要求時刻との一致は緩めていない。

[Demo撮影](evidence_phase3/screenshots_demo.json)、[Analysis撮影](evidence_phase3/screenshots_analysis.json)、[実描画アニメーション](../outputs/phase3/phase3_test00.webp)。

動画はtest_00の6サンプルごとと最終サンプル、74枚のnative画面から作成。1600×1000、14,633 ms、約15倍。74/74フレームを復号し、元PNG SHA、全フレーム期間、連続play4画面と時刻進行を確認した。人工的な神経発光・枝内伝播なし。

実画面では5型barの増減、T2/Tm3の正応答領域、L2の負応答、T4a/T5dの異なる正負配置が見える。suffixと画面運動方向の解剖対応を検証したものではない。保持では変化が小さい。test_00制御期間のT4a RGBが隣接サンプル間に変化した割合はabsolute22.7%、relative43.1%。RGB成分rangeは[41,21,21]と[99,51,51]。relativeで緩やかな色変化を追いやすくなった。脳全体では形態は小さいため接写・mapを併用する。

![raw値と固定relative値](evidence_phase3/activity_summary.png)

Windows GUIのマウス操作、ブラウザ内再生、人の識別率、実時間GUI速度は未検証。native headlessの実描画・操作・復号とは区別する。描画はsoftware rasterizer、推論はRTX5070Ti CUDA。

## G. 検証と旧成果保護

| 検証 | 結果 |
|---|---|
| 単体 | **96/96通過**（旧84＋Phase 3追加12） |
| 追加テスト | goal/表示軸、平衡・Q固有値、球半径・bearing・接線包絡、内部/背面invalid、分割・範囲、collision、教師30軌道、画像限定interface |
| 保存数値監査 | **155試行・51,875ステップ**。初回失敗教師を含め画像・投影・HCW・教師ラベル・readout指令・保持・距離・積分を再計算 |
| 全応答→pooling | train_00の470フレーム、45,669細胞から912特徴を再構成 |
| 標準化・選択・尺度 | train限定標準化、規定6候補選択、非test尺度とtest前SHAが一致 |
| RRD照合 | **各777フレーム**。画像・軌道・v/a・bar・5 map・系列・T4a全828枝と色・脳背景・status/時間を照合 |
| RRD形式 | Demo／Analysisともrerun rrd verify exit0 |
| 実GUI・動画 | 各5局面撮影、seek/play/pause、74/74フレーム復号、連続play4画面 |
| 旧成果 | **681/681 SHA一致**。Phase 1/1B/2/2E/2Fの出力・報告・証拠・旧コード・設定・テスト・形態・checkpointを保持 |
| 既存GPU統合 | **1/2通過、1/2失敗、skip0**。既知prefix比較。閾値変更・成功するまでの再試行なし |

GPU失敗は既存test_phase2_real_images_policy_prefix_and_weight_freeze。先頭10画像の再推論で20成分中4成分が従来atol=2×10⁻⁷、rtol=2×10⁻⁵を超え、違反成分の最大差1.45123028×10⁻⁶ m/s²。失敗箇所以降のassertion通過は主張しない。別のstateful実モデルテストは通過。今回の全神経試行のパラメータbefore/after SHAは独立監査で一致した。GPUの厳密prefix再現性は残る制約である。

[audit](../outputs/phase3/audit.json)、[Demo RRD audit](../outputs/phase3/rrd_audit_demo.json)、[Analysis RRD audit](../outputs/phase3/rrd_audit_analysis.json)、[unit log](../outputs/phase3/unit-tests.log)、[GPU log](../outputs/phase3/integration-tests.log)、[video review](../outputs/phase3/video_review.json)、[旧SHA](../outputs/phase3/prior_hashes.json)。

新規コードはgeometry_phase3.py、phase3_runtime.py、viewer_phase3.pyとPhase 3専用scripts/tests/config。旧HCW/adapter/features/readoutを再利用し旧ファイルは変更していない。README/projectは今回の結果を追記し、過去の個別対応未達・旧test成績は保持した。追加依存・追加形態取得なし。

## H. 再生・検証・残る制約

WSLプロジェクトルート：

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3/phase3_demo.rrd --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3/phase3_analysis.rrd --bind 127.0.0.1
OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/verify_phase3.py
OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/verify_phase3_rrd.py
.venv/bin/python scripts/review_phase3_video.py
OPENBLAS_NUM_THREADS=4 .venv/bin/python -m pytest tests -m 'not integration'
OPENBLAS_NUM_THREADS=4 .venv/bin/python -m pytest tests -m integration
~~~

保存ログだけから図・GUIを再生成：

~~~bash
.venv/bin/python scripts/summarize_phase3.py
RERUN_ANALYTICS_ENABLED=false .venv/bin/python -m flyrendezvous.viewer_phase3
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3.py --mode demo --video
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3.py --mode analysis
.venv/bin/python scripts/review_phase3_video.py
.venv/bin/python scripts/verify_phase3_rrd.py
~~~

実験順序はrun_phase3.py a → zero → b → calibrate_phase3.py → run_phase3.py c → d。a/zero/b/c/dは既存契約・データ・モデル固定・test開始記録があれば再実行を拒否する。既存出力を削除してtestを繰り返すための手順ではない。GUIだけ作り直しても神経・制御実験は増えない。

残る制約は**near2/4失敗**、単一固定Flyvis、既知サイズ・一様球・円形silhouette近似・固定calibration、限定初期範囲、対象自身の重力なし、姿勢なし、実カメラ雑音・遅延なし、接触／着陸なし、時間再尺度化、代表形態の個別対応なし、GPU数値再現性。

接近8条件ではstandoffの成立を示したが、任意方向・未知物体・実宇宙機への一般化は示していない。次に進むなら、nearの頑健性改善を別の事前計画・新held-out集合で検討する判断が必要。今回は追加学習・追加形態・別条件・ハエ型機体やphotorealistic演出へ進まず終了する。
