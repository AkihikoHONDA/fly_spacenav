# Phase 5B-R：train-only dataset aggregationによるnominal回復実験

**nominal recovery達成。別途承認された次Phaseでtruth評価再開を検討できる。今回truthへは進んでいない。**

fresh教師gateは56/56成功。最終実行Round 1のselected validationは**11/12成功**、catastrophic exits 0/12。詳細を以下に記す。旧Phase 5Bの結果・モデル・記録・報告は不変。

## 動機・確認範囲

[指令](codex_phase5br.md)に従い、AGENTS、README、project、Phase 3/5A/5B報告、5B config/teacher gate/selection/diagnosis/model lock、Phase 3 bounded追加ラベル収集、features/ridge/rolloutとGPU failure logを確認した。

旧5Bは教師56/56、validation1/12、H0 learner0/8、state LQR8/8でGate 5停止。教師軌道だけへの回帰がlearner自身の訪問状態で成立するかが問題だった。今回はlearner-visited statesの画像→固定Flyvis→特徴量に、同じHCW教師のlabelを追加するDAgger-like手順だけを導入した。learnerの入力はimage onlyであり、真の状態はteacher labelingとoffline sampling/診断にのみ使用する。

## fresh split・固定条件・重複除外

[training config](../configs/phase5br/training.json)、[split](../outputs/phase5br/splits.json)、[contract](../outputs/phase5br/contract.json)を全試行前に固定。train36/validation12/test8、seed5201/5202/5203、4次元randomized Latin hypercube。

depth25–35 m、cross±4 m、LVLH vx/vy各±0.02 m/s。e_goal=(-1,+1)/sqrt(2)、e_cross=(-1,-1)/sqrt(2)、goal=5 e_goal。旧5B全56初期状態およびfresh内の重複を、全4成分の絶対差<=1e-12をduplicateとして検査し、**重複0**。再抽選なし。[duplicate audit](../outputs/phase5br/duplicate_audit.json)。

sphere R1 m、64×64、HFOV40°、完全固定boresight、Flyvis checkpoint/weights、input-role除外、retinotopic pooling、HCW、teacher、goal、成功/安全、飽和±0.005 m/s²、dt0.5物理秒/0.01神経秒、observation10秒、timeout600秒を保持。成功は位置<0.25 m・回転系speed<0.01 m/sを両端で満たす連続10秒、安全優先。学習済みFlyvisは45,669細胞、readoutはinput-roleを除外した912特徴。lag5はcurrent＋5神経step前の特徴で1824入力、2.5物理秒の履歴である。

## teacher gate・Round 0

fresh教師はtrain36/36、validation12/12、test候補8/8、計56/56成功。[teacher gate](../outputs/phase5br/teacher_gate.json)。その後fresh teacher train/validation48本だけから神経データ生成。旧5B教師データは再利用していない。

Round0はteacher train control periodsのみ、lag0/lag5×lambda1e-4/1e-2/1の6候補。trainでのみscalerをfit。validation teacher-forced MSEと、候補learnerが自身の指令で進むfresh validation12本を分離保存した。

## 固定selection ruleとvalidation gate

候補選択はsuccess最大→catastrophic exit最小→最終goal誤差中央値最小→最終speed中央値最小→total Δv中央値最小→teacher-forced validation MSE最小→lag0優先→lambda小。catastrophicはrange/FOV/collision、timeoutは含めない。

testを開けるgateは**success>=10/12、catastrophic<=1/12、median error<=0.50 m、median speed<=0.015 m/s**の全条件。途中変更なし。

| Round | selected | success | catastrophic | median error m | median speed m/s | median Δv m/s | teacher-forced val MSE | gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 0 | lag0_lambda0.0001 | 0/12 | 0/12 | 12.75544 | 0.019962 | 1.34125 | 0.00127888 | False |
| 1 | lag0_lambda0.0001 | 11/12 | 0/12 | 0.17273 | 0.006743 | 0.45774 | 0.00508478 | True |

![Validation](evidence_phase5br/validation_by_round.png)

全候補の保存結果：

| Round | candidate | success | catastrophic | median error m |
|---|---|---:|---:|---:|
| 0 | lag0_lambda0.0001 | 0/12 | 0/12 | 12.75544 |
| 0 | lag0_lambda0.01 | 0/12 | 12/12 | 0.88721 |
| 0 | lag0_lambda1 | 0/12 | 10/12 | 1.01424 |
| 0 | lag5_lambda0.0001 | 0/12 | 2/12 | 13.82630 |
| 0 | lag5_lambda0.01 | 0/12 | 12/12 | 1.14639 |
| 0 | lag5_lambda1 | 0/12 | 10/12 | 1.41544 |
| 1 | lag0_lambda0.0001 | 11/12 | 0/12 | 0.17273 |
| 1 | lag0_lambda0.01 | 2/12 | 5/12 | 2.44743 |
| 1 | lag0_lambda1 | 1/12 | 10/12 | 1.06762 |
| 1 | lag5_lambda0.0001 | 11/12 | 1/12 | 0.17600 |
| 1 | lag5_lambda0.01 | 2/12 | 4/12 | 1.27352 |
| 1 | lag5_lambda1 | 1/12 | 10/12 | 1.39042 |

## Round 1/2：train-only収集・sampling・cap

本runはRound1でgateを通過したため、Round2は未実行。最大学習予算を使い切るための追加学習は行っていない。

Round1はRound0 selected learnerをfresh train36からrollout。Round2はRound1 gate未達の場合だけRound1 selected learnerを同じfresh train36からrollout。teacher labelは各learner訪問状態で同じHCW state feedbackへ問い合わせた飽和後command。適用learner commandを正解labelに置換していない。

- Round1 primary：観測後2秒毎（4sample stride）、最大300/rollout。goal error<2 m、speed<0.03 m/s、またはsafety failure前10秒は0.5秒sampleを追加。primaryを保持し、critical extras込み最大450。
- Round2：error>=5 mは2秒毎、2<=error<5 mは1秒毎、error<2 m/低速/安全失敗前10秒は0.5秒毎。最大600/rollout。
- safety failure前10秒という未来情報は、完了したtrain軌道のoffline samplingだけに使い、learnerへ渡さない。
- 超過はgoal strata [0,.5), [.5,2), [2,5), [5,10], (10,∞)へ均等quotaを割り当て、不足層の余剰を再配分。各層内で時系列順の等間隔midpoint indicesを決定的に採用する。
- 各aggregation round<=N_teacher_train、合計<=2*N_teacher_train。D1=teacher+agg1、D2=teacher+agg1+agg2、weightは全て1.0、loss weightingなし。
- lagged featureは元の連続0.5秒列から構成**後**にsampleを選ぶ。間引いた列を新しい時間間隔として扱わない。

| aggregation round | per-trial cap後/global cap前 | 最終採用samples | N_teacher cap | per-trial cap |
|---|---:|---:|---:|---:|
| 1 | 16014 | 16014 | 17899 | 450 |

[aggregation manifest](../outputs/phase5br/aggregation_manifest.json)にsource trial/path/SHA/sample/time、true state、teacher label、error/speed、sampling reason、roundを全sample保存。採用データはfresh trainだけ。validation/test由来0、old5B由来0。最終selected modelのtrain36は診断専用に収集し、追加dataset・Round3にはしていない。

## feature-distribution audit

各selected roundのvalidation control periodsについて、D_teacher per-feature min/max外、current train min/max外、実readout scalerでの|z|>3/5を記録。以下はtrial等重み平均。z-scoreはconstant featureを除外。lagによって912/1824と分母が変わるため、[JSON](../outputs/phase5br/feature_coverage.json)にfeature数を明記した。

| Round | teacher-bound exceedance | current-train exceedance | z>3 | z>5 |
|---|---:|---:|---:|---:|
| 0 | 6.564% | 6.564% | 2.441% | 0.846% |
| 1 | 1.382% | 0.001% | 0.049% | 0.007% |

![Coverage](evidence_phase5br/feature_coverage.png)

分布指標と性能の因果は断定しない。追加データは訪問状態を覆うが、安定したfeedback lawの存在・観測可能性・線形表現能力を証明するものではない。

## learner-state teacher error

各selected learner自身のfresh train rollout（次round収集または最終診断）で、観測後applied commandと局所teacher飽和commandを比較。角度は両ノルム>1e-8 m/s²のsampleのみ。saturation disagreementは各軸の飽和有無が異なるfraction。教師軌道上MSEとは別の指標である。

| source selected Round | train trials | 平均RMSE m/s² | 平均角度誤差 deg | 軸saturation不一致 |
|---|---:|---:|---:|---:|
| 0 | 36 | 0.003345 | 46.384 | 28.965% |
| 1 | 36 | 0.000458 | 16.657 | 4.025% |

![Learner-state error](evidence_phase5br/learner_state_error.png)

[learner_state_error.json](../outputs/phase5br/learner_state_error.json)にtrial別値・有効角度sample数を保存。RMSE/角度はtrial等重みの平均で、pooled RMSEではない。

## terminal stabilization・failure modes

全selected validation trialに、最小error、最初の2 m/.5 m/位置条件/速度条件/joint条件、連続hold、final speed、初回2 m後のΔv・制動率・FOV/range exitを保存。[terminal diagnostics](../outputs/phase5br/terminal_stabilization.json)。

failure診断は「2 mへ未到達」「到達したが2 m内でspeed<0.01に未到達」「2 m内で減速したが安定せず」「減速後再び2 m外」等を分離する。これは元のsuccess/safety判定を変更する分類ではない。

| Round | success | timeout | FOV exit | range exit | collision |
|---|---:|---:|---:|---:|---:|
| 0 | 0 | 12 | 0 | 0 | 0 |
| 1 | 11 | 1 | 0 | 0 | 0 |

![Failures](evidence_phase5br/failure_modes_by_round.png)

validation_00（同じfresh validation初期条件をRound比較）：

| Round | min error m | first <2m s | first <.5m s | first joint s | longest hold s | final speed m/s | 診断 |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 0.3478 | 191.0 | 238.5 | None | 0.0 | 0.04980 | slowed_then_redeparted |
| 1 | 0.2214 | 177.0 | 223.0 | 247.5 | 10.0 | 0.00306 | success |

![Terminal val00](evidence_phase5br/terminal_stabilization_val00.png)

## final model・fresh test・main demo

fresh testはmodel lock後に一度だけ実行。**8/8成功**、catastrophic exits=0/8、最終goal誤差中央値=0.167295 m、speed中央値=0.007032 m/s。recovery gateは6/8以上。test後の再学習なし。

- test_00: success, 263.0 s, final error 0.17561 m
- test_01: success, 241.5 s, final error 0.16404 m
- test_02: success, 284.0 s, final error 0.17791 m
- test_03: success, 282.0 s, final error 0.17055 m
- test_04: success, 272.5 s, final error 0.17145 m
- test_05: success, 252.0 s, final error 0.14823 m
- test_06: success, 244.0 s, final error 0.15053 m
- test_07: success, 327.5 s, final error 0.13016 m

main demoは事前固定のfresh test_00。成功例への差し替えなし。[Demo RRD](../outputs/phase5br/demo/H0/demo.rrd)、[MP4](../outputs/phase5br/mp4/test00_H0.mp4)。再生条件は15倍速・既存camera/layout/Pilot尺度。表示は保存済みlearnerの実応答で、教師軌道再生と区別する。

固定[readout](../models/phase5br/readout.npz)のSHA-256は 903ea832565b8f544ad583914b50e3b3c27a832b2d06029b5a35c80198151117。[model lock](../outputs/phase5br/model_lock.json)に選択・data manifest・scaler/pooling・コード・尺度を固定した。D0の教師trainは17,899 samples、D1は33,913 samples（教師＋16,014追加）、全sample weight=1。

fresh test_00は263.0物理秒で10秒holdを完了。最後の表示sampleは262.5秒、最後の状態/成功判定は263.0秒。実native Rerun headlessでseek/play/pause/終端保持を確認した。Windows GUIマウス操作や実時間FPSの保証ではない。

MP4は17.533秒、30fps、526 frames、1600×1000、物理時間15倍。89枚の実captureを次captureまで保持し、補間や架空活動を加えていない。全frameを復号し、PTS連続・time base1/30・最低PSNR 39.49 dBを検証。

[RRD照合](../outputs/phase5br/viewer_verification.json)では526 sample×8 streamsの指令、Orbit、Pilot shaft、T2/T4a/T5d色、sensor uint8画像を元ログと一致確認した。Blueprintは旧5Bと同一。旧Orbit枠では遠方開始位置がpanel端へ寄るが、今回framingやPilot尺度を見栄え目的で変えていない。

早期接近20秒の実frame：

![Fresh actual early](evidence_phase5br/H0/demo_early.png)

制動中の実frame（実時刻はcapture metadata参照）：

![Fresh actual braking](evidence_phase5br/H0/demo_braking.png)

終端262.5秒の実frame：

![Fresh actual hold](evidence_phase5br/H0/demo_terminal.png)

[実capture metadata](evidence_phase5br/H0/screenshots_demo.json)と[MP4検証](../outputs/phase5br/mp4/H0_verification.json)に時刻・元ログSHAを保存。

![Fresh test status](evidence_phase5br/fresh_test_summary.png)

GUI経路は既存Phase 4C/5Bを分離再利用する設計で、sphere/camera/Orbit/Brain/maps/Pilot/layoutとPilot尺度を変えない。形態はモデル型集約応答、Pilotはpresentation layerでありbiological motor outputではない。test未実行の場合、今回の新RRDによるGUI検証は行っていない。

## historical Phase 5Bとの比較上の注意

旧test0/8はhistorical failure referenceのみ。今回のfresh testとはsampleが異なりpairedではない。同じtestが0/8から改善したという主張をしない。比較可能なのは分布範囲、readout family、training procedureであり、samplingとselection ruleは今回指令の規則で新たに固定した。

## GPU prefix再現性

既存GPU integration testsを**1回だけ**実行。pytest exit=1、prefix最大絶対差**1.586506441e-06 m/s²**、parameter mutation=False、nonfinite=False。閾値・旧コードは変更していない。既知prefix failをpassへ読み替えない。

差は~1e-6級で1e-4 m/s²停止基準未満、既知以外のテスト失敗なしのため、指令21に従い継続。大きなorder-dependent driftを否定する包括的検証ではない。[gpu_reproducibility.json](../outputs/phase5br/gpu_reproducibility.json)に実prefix配列・max diff・前後parameter SHAを保存。テスト観測wrapperは元assertをそのまま呼び、assertionを弱めていない。

## tests・regression

最終non-integrationは、既存分・Phase 5B physics・sampling/cap/duplicate/scaler/model lock/history/endpoint診断を含め**180 passed / 2 deselected**。途中の専用テストも11/11 pass。[最終テストログ](../outputs/phase5br/unit_tests_final.log)を保存した。GPU integrationは1 pass/既知prefix1 failで、再実行していない。

[regression](../outputs/phase5br/regression.json)：旧3956ファイルを保護、aggregation label 16,014件を元状態のTeacher.commandと照合、round cap、source split、決定的sample選択、train-only scaler、selection rule、fresh test guardを監査。Phase 4C GUI成分回帰は結果保存先だけphase5brへ変更。旧Phase 3 approach8/8・near2/4、旧5B0/8、旧モデル・RRD/video・5A解析を保持した。

## 保存物・再生・監査

新成果はconfigs/phase5br、models/phase5br、outputs/phase5br、docs/evidence_phase5brへ分離。[manifest](../outputs/phase5br/manifest.json)にSHAを記録。

~~~bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/verify_phase5br.py
~~~

fresh test実行時のみ、保存済みRRDを再生：

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase5br/demo/H0/demo.rrd --bind 127.0.0.1
~~~

model lock CLIの関数名不一致をtest前に修正した。修正前のtest起動要求はmodel-lock guardで推論前に拒否され、started markerは作られなかった（[guardログ](../outputs/phase5br/fresh_test_run.log)）。実trialは修正・lock後の一度だけ（[実行ログ](../outputs/phase5br/fresh_test_execution.log)）。

学習stageの再実行・fresh testの再実行を防ぐstarted markerを保存している。既存結果へ上書きしない。sampling/config/gateを結果後に変更する再開手順は設けていない。

## 制約・推奨・停止

nominal recovery達成。別途承認された次Phaseでtruth評価再開を検討できる。今回truthへは進んでいない。

最大Round2まで、追加hyperparameter/非線形head/新Flyvis学習/重み付け/goal・FOV・timeout緩和なし。truth、J2/SRP/drag、residualのclosed-loopは一切実行していない。今回の表示・データ診断から、生物学的motor outputや実測細胞との一対一対応を主張しない。

**Phase 5B-Rの結果報告時点で停止する。**
