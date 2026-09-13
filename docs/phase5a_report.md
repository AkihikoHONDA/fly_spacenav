# Phase 5A：保存済みclosed-loop control activity解析

**test_00はCase Bに最も近く、序盤集中というCase Aの一部も当てはまる。** 最初だけ操作しているわけではない。総Δvの76.13%が観測後の前半に集中する一方、55秒から終了まで制動が続く。中盤のΔvは全体の36.89%、終端25%にも6.98%存在する。ただし終端の指令中央値は最大ノルム基準の3.52%、joystick傾斜約1.31°で、小パネルでは目立ちにくい。動画間引きは影響するが、終端制動を大きく消している結果ではない。

新規推論・学習・simulationは**0**。Phase 3 testは既存の**approach 8/8、near 2/4**を維持。Phase 4A/4B/4CのGUI・IK・尺度・保存成果は不変。以下は保存ログの記述的解析であり、閉ループ再実行や新条件での成功評価ではない。

## 目的・入力・時間の定義

[指令](codex_phase5a.md)に従い、AGENTS、README、project、Phase 3/4A/4B/4C報告、保存処理、成功判定、viewerを確認した。

canonical sourceは **outputs/phase3/test_learner/test_00.npz〜test_11.npz**と各JSON、[evaluation.json](../outputs/phase3/evaluation.json)、[splits.json](../outputs/phase3/splits.json)、[固定設定](../configs/phase3.json)。12/12本・**5,244適用区間**が揃い、欠落ログ・必須フィールド欠落は0。教師testや別の再生用軌道は混ぜていない。

test_00はPhase 4C動画と同じrecord SHA
**3b3528eae0be59ed5b75dd790511970c90660ff548e3a4e82713702a65bd29a6**。
439 samples、状態は440点。動画manifestの全74 capture sample index・元時刻・viewer source hashも照合した。

- 主信号はraw **u_applied**。u_rawと保存済みteacher labelで代用しない。u_rawはCSVに参考として残す。
- states[k]は指令k適用**前**の位置・速度。acceleration_interval[k]は[k×0.5,(k+1)×0.5)物理秒。
- 保存interval両端とobservation_time差を確認し、全12試行ともdt=0.5秒。最後の区間終了もメタデータと照合。
- 0〜10秒はobservation、u=0。既存軌道はその間も移動する。post-observeは10秒から終了まで。
- test_00の最後の表示sampleは219.0秒、最後の状態と成功判定は**219.5秒**。積分は[219,219.5)も含み、状態の最小・最終値はN+1点を使用。
- wall_seconds・神経時間・15倍の動画時間を物理dtに使っていない。

[manifest](../outputs/phase5a/analysis_manifest.json)に入力path/SHA、コードSHA、dt、尺度、閾値、success source、対象trialを保存。workspaceに.gitがないためcommitはnull、コードSHAで版を識別する。README/projectも今回は追記せず保存したままとした。

## 指標と既存success条件

goalは**(-3.5355339059,+3.5355339059) m**、中心距離5 mの固定点。位置誤差||r-r_goal||と速度||v||は[viewer](../src/flyrendezvous/viewer_phase4c.py)と同じ定義。相対速度はLVLHの2成分ノルム。

[phase3_runtime.py の rollout](../src/flyrendezvous/phase3_runtime.py)と設定で確認した成功条件：

1. goal位置誤差 **<0.25 m**。
2. 相対速度 **<0.01 m/s**。
3. observation後、適用区間の**両端**で両条件を満たす区間を連続**10秒（20区間）**保持。
4. safety判定が成功判定に先行する。保存済み終了理由を維持し、successを再定義しない。

satは各軸±0.005 m/s²。axis fraction=|a_i|/0.005、norm fraction=||u||/(sqrt(2)×0.005)。最大ノルム基準は**0.007071067812 m/s²**であり、0.005ではない。test_00の最大0.00543746 m/s²は基準の76.90%、各軸範囲内。

ΔvはΣ||u_k||Δt_k、単位m/s。燃料消費や速度ノルムの正味増分ではない。window境界がsample途中なら区間との重なり時間で積分する。累積50/80/90%時刻はpiecewise-constant指令を区間内で積分するため、0.5秒格子とは限らない。

制動は**||v||>1e-4 m/sかつu·v<0**。速度は適用前の値で、区間内の符号を連続再構成していない。test_00の低速度除外は0 samples。軌道エネルギーの厳密分解でも、HCW自然項を含む速度変化の全原因でもない。

## test_00 overviewとsuccess時刻

![Overview](evidence_phase5a/test00_overview.png)

| 項目 | 値 |
|---|---:|
| 初期goal error / 中心距離 | 11.00764 / 15.99991 m |
| 初期速度 | 0.0215348 m/s |
| 速度最大 | 54.5 sで0.1058904 m/s |
| 初めて速度条件を満たす | **203.0 s** |
| 初めて位置条件を満たす | **209.5 s** |
| 初めて両条件を満たす | **209.5 s** |
| 成功につながるhold開始 | **209.5 s** |
| success判定 | **219.5 s** |
| 最終goal error / 速度 | 0.175381 m / 0.00607873 m/s |

![Terminal detail](evidence_phase5a/test00_terminal_detail.png)

速度ピーク直後から長い制動があり、速度条件到達、位置条件到達、10秒保持へ続く。終端の大きな一回の逆噴射ではなく、**小さく長い減速**である。この対応は時間的な観測であり、制動を除いた場合の成功可否を検証した反実仮想実験ではない。

各trialのfirst speed conditionは単なる初回時刻で、その後ずっと条件内とは限らない。一部nearは初期速度がすでに条件内。test_08/10の最初のjoint conditionと成功hold開始も異なり、CSVで別に記録した。

## Δvの時間分布

**total Δv = 0.2210633043 m/s**。fractionの分母は全積分。observation中u=0なのでfull/postの総Δvは同じだが、時間windowの端が異なる。

| 時間window | Full基準 Δv比 | Post基準 Δv比 | Post Δv m/s |
|---|---|---|---|
| First 10% | 26.99% | 41.53% | 0.09181354 |
| First 25% | 55.41% | 56.13% | 0.12409219 |
| First 50% | 73.93% | 76.13% | 0.16828991 |
| Last 50% | 26.07% | 23.87% | 0.05277340 |
| Last 25% | 7.49% | 6.98% | 0.01542070 |
| Last 10% | 2.12% | 2.04% | 0.00451380 |

fullは0〜219.5秒、postは10〜219.5秒。post first25は10〜62.375秒、last25は167.125〜219.5秒。first10/25/50は相互に重複するwindowで、全行を足すものではない。

![Cumulative effort](evidence_phase5a/test00_cumulative_dv.png)

| 累積Δv | 到達物理時刻 | observation終了から |
|---|---:|---:|
| 50% | 39.404 s | 29.404 s |
| 80% | 124.048 s | 114.048 s |
| 90% | 153.738 s | 143.738 s |

半分は早期に使うが、80%到達は124秒。前半集中から「その後無操作」とは言えない。

## command分布とPilot尺度

![Command scale](evidence_phase5a/test00_command_scale.png)

test_00のsample/time割合を両方示す。一定dtなので同じ値。binは下端以上・上端未満が基本、50〜100%だけ100%を含む。

| ノルム基準 | Full sample比 | Full time比 | Post sample比 | Post time比 | Δv比 |
|---|---|---|---|---|---|
| 0–1% | 5.01% | 5.01% | 0.48% | 0.48% | 0.03% |
| 1–5% | 19.36% | 19.36% | 20.29% | 20.29% | 4.31% |
| 5–10% | 27.11% | 27.11% | 28.40% | 28.40% | 13.79% |
| 10–25% | 35.76% | 35.76% | 37.47% | 37.47% | 32.93% |
| 25–50% | 5.24% | 5.24% | 5.49% | 5.49% | 13.88% |
| 50–100% | 7.52% | 7.52% | 7.88% | 7.88% | 35.05% |
| >100% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

post-observe時間の49.16%はノルム基準10%未満。終端25%では**100%の時間が10%未満、63.01%が5%未満**。終端中央値2.4891×10^-4 m/s²、最大5.0093×10^-4 m/s²。

既存joystick平面変位は0.55×[-ay,ax]/0.005、shaft長1.2。この既存幾何から、ノルム基準5%はtilt約1.86°、10%は約3.72°。test_00のtilt中央値は早期quarter **10.80°**、中間half **4.20°**、終端quarter **1.31°**、hold **1.25°**。物体の傾斜角であり、画面ピクセル変位や人の識別率ではない。GUI scale・カメラ・IKは不変。

全12本のpost-observeプール分布。試行等重みではなく実sample数・時間・Δvをプールし、長いtimeoutの寄与も残る。trial別のfull/post両分布は[all_trial_metrics.json](../outputs/phase5a/all_trial_metrics.json)。

| ノルム基準 | samples | sample比 | time比 | Δv比 |
|---|---|---|---|---|
| 0–1% | 11 | 0.22% | 0.22% | 0.01% |
| 1–5% | 849 | 16.97% | 16.97% | 3.58% |
| 5–10% | 1609 | 32.15% | 32.15% | 14.38% |
| 10–25% | 1638 | 32.73% | 32.73% | 27.57% |
| 25–50% | 518 | 10.35% | 10.35% | 22.38% |
| 50–100% | 379 | 7.57% | 7.57% | 32.08% |
| >100% | 0 | 0.00% | 0.00% | 0.00% |

## brakingと速度に対する分解

![Decomposition](evidence_phase5a/test00_control_decomposition.png)

| 制動指標 | test_00 |
|---|---:|
| braking samples | 335 / 439（76.31%） |
| post-observe分母 | 335 / 419（79.95%） |
| braking time | **167.5 s** |
| braking Δv（分類sampleの全ノルム積分） | **0.1147897623 m/s** |
| braking Δv / total | **51.93%** |
| 負のparallel成分だけの積分 | 0.1031784591 m/s |
| 最初のbraking | 10.0 s |
| 最大braking event | **85.0 s**（u·v最小） |
| 連続braking区間 | **[10,13)、[55,219.5) s** |

10〜13秒の制動は初期相対速度に逆らう成分で、終端制動ではない。最大eventは1sampleのu·v最小で、イベント塊の積分最大ではない。85秒のcommandノルム0.00091423 m/s²、速度0.0881442 m/s、u·v=-8.05166×10^-5 m²/s³。

u_parallel=(u·v_hat)v_hat、u_perp=u-u_parallelは**現在の相対速度**に対する分解。orbital radial/along-track成分ではない。perpendicular積分は**0.0731919191 m/s、total比33.11%**。2成分のノルム積分は足してtotal Δvにならない。低速度で未定義の成分はCSV空欄/JSON nullとし、除外時間・Δvを別記する。

| 区間 | 時刻 s | Δv m/s | Total比 | Parallel積分 | Perpendicular積分 |
|---|---|---|---|---|---|
| 早期quarter | 10.000–62.375 | 0.124092 | 56.13% | 0.095845 | 0.061647 |
| 中間half | 62.375–167.125 | 0.081550 | 36.89% | 0.080811 | 0.009141 |
| 終端quarter | 167.125–219.500 | 0.015421 | 6.98% | 0.015133 | 0.002404 |
| 成功hold（終端内） | 209.500–219.500 | 0.002384 | 1.08% | 0.002377 | 0.000167 |

early quarterのperpendicularは0.061647 m/sで、その大半も序盤にある。中盤は0.009141 m/s、全Δv比4.14%。**中盤に横向き成分は存在するが、主成分は減速**。中盤と終端の全sampleがbrakingで、中盤36.89%＋終端6.98%のeffortがその役割を担う。外乱への修正性能を実証した意味ではない。

## direction change補助指標

primary active閾値は最大ノルム基準5%。連続active区間内の隣接元sampleの角度変化**45°以上 / 90°以上**を数え、非active gapを跨がない。

| 閾値 | Post active duty | 連続active区間 | ≥45° | ≥90° |
|---|---|---|---|---|
| 2% | 98.09% | 2 | 0 | 0 |
| 5% | 79.24% | 3 | 0 | 0 |
| 10% | 50.84% | 3 | 0 | 0 |

5%のactive区間は[10,51)、[61.5,180)、[181,187.5)秒。全閾値で急な角度変更0件だが、**方向が変わらない意味ではない**。緩やかな変化や低振幅区間を介した加速→制動切替は数えない。active区間数も真の修正回数ではない。ガチャガチャした急な修正は、このログと定義では観測されない。

## 動画samplingの影響

[既存動画sampling解析](../outputs/phase5a/pilot_sampling_audit.json)は74枚のcapture indexから保持表示を数値的にたどっただけ。新動画生成・GUI更新はしていない。

元command更新は0.5物理秒。動画は6sample＝3物理秒ごとのcaptureを保持し、15倍速で約0.2動画秒ごとに更新。MP4の30fpsは30種類の指令/秒ではない。

- captureのcommandピークは元ピークの**98.96%**。
- post-observeの見かけのノルム積分0.2165661に対し真値0.2210633 m/s、**約2.03%小さい**。別の物理Δvではなく表示差の診断量。
- 10秒の制御開始は9秒captureのu=0を12秒まで保持するため、2物理秒遅れて表示される。全期間の最大瞬間差が大きい主因。
- 終端quarterの見かけの積分0.01556993、真値0.01542070で**約0.97%大きい**。terminal command vectorのRMS差2.3741×10^-5 m/s²。
- 間引きは速い変化を粗くするが、終端制動を消す主因としては、**small commandとfull-scale mappingの方が整合的**。Case Cは主結論にしない。

画面サイズ・3/4投影・遠側脚の遮蔽は既存4C報告の制約。今回、人の視認閾値は測定していない。

## 全12試行とsuccess/failure比較

[trial_summary.csv](../outputs/phase5a/trial_summary.csv) ／ [JSON](../outputs/phase5a/trial_summary.json)。全指標はCSVに保存。fraction・active dutyはpost-observe基準。

| trial | group | result | 終了 s | Δv m/s | 制動比 | active 5% | ≥45° | 最終speed |
|---|---|---|---|---|---|---|---|---|
| test_00 | approach | success | 219.5 | 0.22106 | 51.9% | 79.2% | 0 | 0.00608 |
| test_01 | approach | success | 222.0 | 0.25220 | 52.0% | 84.2% | 0 | 0.00599 |
| test_02 | approach | success | 266.0 | 0.28079 | 53.2% | 84.6% | 0 | 0.00632 |
| test_03 | approach | success | 247.5 | 0.23956 | 49.9% | 76.4% | 0 | 0.00612 |
| test_04 | approach | success | 252.5 | 0.18088 | 52.0% | 80.0% | 0 | 0.00593 |
| test_05 | approach | success | 239.5 | 0.19988 | 48.5% | 75.2% | 0 | 0.00601 |
| test_06 | approach | success | 258.5 | 0.25249 | 51.0% | 80.7% | 0 | 0.00605 |
| test_07 | approach | success | 250.0 | 0.22773 | 52.2% | 83.8% | 0 | 0.00623 |
| test_08 | near | success | 84.0 | 0.15662 | 56.5% | 100.0% | 0 | 0.00671 |
| test_09 | near | field_of_view_exit | 85.0 | 0.22861 | 43.1% | 100.0% | 1 | 0.02818 |
| test_10 | near | success | 97.5 | 0.15428 | 54.6% | 97.7% | 0 | 0.00296 |
| test_11 | near | timeout | 400.0 | 0.55001 | 48.3% | 83.8% | 1 | 0.01773 |

test_09は最小error 0.09566 mまで近づくが、最長hold6秒で10秒に届かず85秒でFOV exit。test_11は最小error 0.34345 mで位置条件を満たさず、400秒timeout。nullを0で埋めていない。failure調整・再実行なし。

![Trial comparison](evidence_phase5a/trial_comparison.png)

| trial中央値 | approach成功 n=8 | near成功 n=2 | near失敗 n=2 |
|---|---|---|---|
| Total Δv m/s | 0.233649 | 0.155451 | 0.389309 |
| Max command m/s² | 0.00577735 | 0.00390188 | 0.00707107 |
| Braking fraction | 0.519589 | 0.555628 | 0.456833 |
| Perpendicular fraction | 0.306887 | 0.80384 | 0.648522 |
| Active duty 5% | 0.803421 | 0.988571 | 0.919231 |
| Direction changes ≥45° | 0 | 0 | 1 |
| Min error m | 0.176239 | 0.162891 | 0.219555 |
| Final speed m/s | 0.00606427 | 0.00483252 | 0.022954 |

上表は**trial中央値**で、プール時間割合とは異なる。approach前半Δv比は75.55〜77.68%、制動比48.52〜53.16%と似た経過。near成功もactive dutyが高く、直交成分が大きい。near失敗は両軸同時satの最大ノルムに達し最終速度も高い。timeoutのΔv増には400秒という期間も寄与する。

near成功2本・失敗2本なので、有意差・因果・一般的失敗原因は断定しない。braking/perpendicular fractionが大きいほど成功するという単調な指標ではない。

## 開始距離との関係

![Start distance](evidence_phase5a/start_distance_relationship.png)

保存approachの初期goal errorは**11.008〜16.156 m**、中心距離は**16.000〜21.151 m**。nearのgoal errorは**0.343〜0.626 m**。cross offset・速度・終了理由・観測時間も異なる。

接近8本から25〜35 mのΔv・duration・修正回数へ外挿できるかは**判断不能**。接近の方向変化指標は8本とも0で、この距離差から頻回修正増加も示せない。回帰線や有意差を作らなかった。

## Phase 5Bの条件候補（提案のみ）

以下は実ログと固定カメラ幾何に基づく**未検証の案**。実装・新split生成・推論・軌道生成はしていない。旧testを見た後の設計なので、将来は新しいsplitと条件を事前固定し、旧testへ合わせた調整を避ける。

### 開始距離と画像サイズ

まず**中心からのradial depth r0=25 / 30 / 35 m**を候補にする。現行r=r0 e_r+c e_tと同じ定義で、goal errorではない。旧nominal r0=14〜22 mから拡張する。cross=0のgoal errorは20 / 25 / 30 m。

64×64、FOV40°、R=1 m、f=31.5/tan20°の既存geometryによる計算：

| r0中心depth m | 軸上goal error m | 球直径 px | 球角半径 deg |
|---|---|---|---|
| 25 | 20 | 6.929 | 2.292 |
| 30 | 25 | 5.773 | 1.910 |
| 35 | 30 | 4.947 | 1.637 |

[全幾何候補](../outputs/phase5a/phase5b_geometry_candidates.json)に|cross|=0/2/4/6 mの12組を保存。左右は対称。|cross|=4 mで画素端marginは25 mで14.62 px、30 mで17.54 px、35 mで19.61 px。全候補は**初期**FOVと40 m未満のrange条件内。接近中もFOV内とは限らない。

直径約5〜7画素なので幾何学的には消失しないが、未学習距離でFlyvis/readoutが十分応答する保証はない。既存の保守的な円形球投影式を用い、画像生成・推論はしていない。**goal error 25〜35 m**を意図するなら軸上中心距離30〜40 mとなり、40 mは現行range exit（>=40）に当たる。この距離定義の区別が次の判断に必要。

### cross offsetと初期速度誤差

- 旧±2 mを対照として残し、まず**±4 m**、追加強条件として±6 mを候補にする。保存approachの実crossは約−1.674〜+1.810 m、test_00は+0.738 m。
- 速度差はapproach basisの**tangential成分に±0.005 / ±0.01 m/s**を候補にする。radialも同オーダーを別要因として検討し、初めから混ぜない。
- 旧nominal速度はLVLH各軸±0.02 m/sで、座標系が異なるため単純な上乗せが旧範囲内とは限らない。新評価の初期速度は真値として固定しても、画像policyへは渡さない。
- これらは提案であり、今回条件をsampleしたり適用したりしていない。

### truth-model mismatch

候補は**nominal HCWに整合した基準軌道からchief/deputyを別々に非線形two-bodyで伝播し、相対状態へ戻すtruth**。座標・初期値整合を先に確認する設計が妥当。現設定はn=0.0011 s^-1だが、中心天体μ・chief半径・完全な軌道要素はないため、今回決めない。

35 mへ延ばして非線形化するだけで十分な中間修正が生じるとは言えない。HCWとtruthの自然な差と、追加のdifferential disturbanceは分けて扱う案とする。同時に変えると原因が混ざる。nonlinear truth・J2/SRP/dragは未実装。

### differential disturbanceのオーダー

**1×10^-5 / 3×10^-5 / 5×10^-5 m/s²**を候補とする。まず一方向の一定bias、必要なら事前固定した中盤開始の有限区間biasという案。主に視線直交方向なら現test_00の小さいmidcourse perpendicularとの差を観察しやすい可能性がある。相対運動に残るdifferential量として定義し、どちらも未実装。

根拠はtest_00 terminal中央値**2.489×10^-4**、hold平均**2.384×10^-4 m/s²**。候補範囲はterminalの約**4〜20%**、holdの約**4〜21%**、一軸にかかる場合のaxis authority比**0.2〜1%**。終端制御に無視できない可能性がある一方、単純振幅比では全authorityを使い切らないオーダー。画像policyが打ち消せる保証ではない。

距離だけ、cross/速度差、truth差、差分biasを要因別に比較する条件設計を推奨する。距離拡張で400秒timeoutが十分かも判断不能。後から条件を緩めるのでなく、次Phase開始前に定義する必要がある。

## 実装・検証・保存物

[解析モジュール](../src/flyrendezvous/analysis_phase5a.py)、[実行](../scripts/analyze_phase5a.py)、[独立監査](../scripts/verify_phase5a.py)。解析からpolicy・rollout・teacher.command/advanceを呼んでいない。

- [test00_metrics.json](../outputs/phase5a/test00_metrics.json) ／ [timeseries CSV](../outputs/phase5a/test00_timeseries.csv)：raw指令・状態・u·v・成分・尺度・区間開始/終了累積Δv。
- [trial_summary.csv](../outputs/phase5a/trial_summary.csv) ／ [JSON](../outputs/phase5a/trial_summary.json)：全12本、算出不能はnull/空欄。
- [全trial指標](../outputs/phase5a/all_trial_metrics.json)、[プール分布](../outputs/phase5a/pooled_command_distribution.json)、[sampling audit](../outputs/phase5a/pilot_sampling_audit.json)、[幾何候補](../outputs/phase5a/phase5b_geometry_candidates.json)。
- 必須6図＋terminal補助図をPNG/PDFで保存。
- [manifest](../outputs/phase5a/analysis_manifest.json)、[verification](../outputs/phase5a/verification.json)、[pytest XML](../outputs/phase5a/pytest.xml)、[test scope](../outputs/phase5a/test_scope.json)。

**155 passed、8 deselected**。既存non-GPUの実行可能144件＋解析専用11件。除外は既存non-GPU 6件とGPU integration 2件。

既存non-GPUテストには新しいODE積分、teacher/dummy-policy rollout、readout fit/predictを行うものがある。「推論・学習・simulationを一切行わない」という直接指定を優先し、以下6件は**未実行**。既存テスト・閾値は変更していない。

1. test_hcw_zero_n_and_independent_integration
2. test_ridge_train_only_scaling_intercept_reload
3. test_rollout_time_initial_observation_and_no_state_reset
4. test_image_only_causal_interface
5. test_contributions_use_training_scaling_keep_mask_and_separate_bias
6. test_frozen_original_test_reconstruction_and_screening

[テスト実行器](../scripts/test_phase5a.py)は理由を保存し、runtime profile hookでもrollout/readout fit/predict/adapter推論/solve_ivpを拒否する。「全既存non-GPUを再実行して通過」とは報告しない。GPUの既知prefix再現性問題も再評価していない。

解析11件は可変dt、部分区間積分、累積到達時刻、braking、低速除外、parallel/perpendicular、gapを跨がない方向差、2/5/10% sensitivity、bin境界、strict success閾値・hold中断・observation除外、不正timestampを手計算配列で検証。synthetic control simulationは含めない。

独立監査は全5,244区間のΔv/brakingをscalar loop、perpendicularを2D外積、方向差をatan2で別計算しCSV/JSON照合。window積分・累積到達・保存成功時刻も確認した。既存4C回帰とPilot FKの検証関数を再使用し、**結果の書き出し先だけ5Aへ向けた**。旧RRDの441 streams / 53,977値、777 samples / 1,554脚先の一致を再確認。旧regression.jsonは上書きしていない。

**既存3,234ファイルのSHA不変**。既存source・設定・モデル資産・ログ・画像・動画・報告・README/projectを保護。実行cacheは対象外。checkpoint/readout、split、HCW、teacher、target/goal、両カメラ、sat、success、全saved u_applied、near結果は固定。

## 再実行方法と限界

WSL project rootから解析だけを再実行する：

~~~bash
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/analyze_phase5a.py
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/test_phase5a.py
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/verify_phase5a.py
.venv/bin/python scripts/report_phase5a.py
~~~

真の位置・速度を**解析**に使ったがpolicyへ渡していない。u·v分類・直交成分は因果の証明ではない。制動なし試行・外乱応答・遠距離の視覚頑健性・人の視認性能は未測定。小標本と条件・観測期間差から一般化しない。

test_00には序盤以降も実モデル出力による小さく長い制動があり、中盤は主に減速、終端は小振幅の制動・保持が続く。Phase 5B候補を提案した時点で**停止**する。
