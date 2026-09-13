# FlyRendezvous Phase 2E 実施報告

実施日：2026-09-11（JST）。軌道を**下＝中心天体方向、左＝軌道進行方向**へ変更し、保存済みログから65型を比較した。制御結果・モデル・旧成果409ファイルは不変。最終表示の比較候補は8型、次の形態取得案は **T2・Tm3・T5d** の3型である。取得は実施していない。

表示・保存結果の数値監査・単体テストは通過した。一方、既存GPU統合テストは2回とも **1/2通過、1/2失敗**。同一画像prefixの再実行差が従来の許容値を超えた。全テスト成功とは扱わない。詳細は末尾の検証欄に記す。

## A. 表示座標と保存結果

LVLH物理座標は x＝radial outward、y＝along-track のまま。表示専用の純粋関数で **X=-y、Y=x（Y正方向は上）** とする。Rerun Spatial2Dの画面Y正方向は下のため、描画APIへは別の橋渡し関数で **[-y,-x]** を渡す。これは物理座標の変更ではない。

| LVLH | 論理表示 [X,Y] | 画面 |
|---|---|---|
| [+1,0] | [0,+1] | 上：Radial outward |
| [-1,0] | [0,-1] | 下：Central body |
| [0,+1] | [-1,0] | 左：Along-track |
| [0,-1] | [+1,0] | 右：Retrograde |

chaser、target、goal、軌跡、速度・加速度矢印、方向凡例に一貫適用した。goalは物理[10,0]→表示[0,10]、targetは[0,0]。速度矢印×20秒、加速度矢印×400秒²は従来どおり。評価図の軌道パネルは同じ変換と等距離尺度を使用する。加速度等のスカラーグラフ、固定-xカメラ、受容格子、神経格子・形態・色尺度は維持した。数値欄の加速度には「LVLH ax, ay」を明記した。

新ファイルは [display_coordinates.py](../src/flyrendezvous/display_coordinates.py)、[viewer_phase2e.py](../src/flyrendezvous/viewer_phase2e.py)。旧viewerはそのまま保存し、既存Rerun基盤を再利用したPhase 2E専用版を追加した。独自GUIは作っていない。

### 実際のRerunと評価図

![新しいRerun表示：制動区間](evidence_phase2e/braking.png)

実Rerun 0.37.1のheadless描画。test_00 replayのsample 191、物理95.5秒。画像は実測スクリーンショットであり、手作業で合成した画面ではない。方向ラベルと下向きの接近軌跡を目視確認した。[接近20秒](evidence_phase2e/approach.png)・[保持210.5秒](evidence_phase2e/hold.png)も保存。物理時間と神経時間、元レコードと画像SHAは [screenshots.json](evidence_phase2e/screenshots.json)。シーク・再生・一時停止はnative viewer-mcpで検証した。Windows GUIのマウス操作は今回未検証。

![元test結果を新座標で表示](../outputs/phase2e/evaluation_display_coordinates.png)

[評価図PDF](../outputs/phase2e/evaluation_display_coordinates.pdf)。軌道・誤差・速度は元の教師12試行と学習器12試行、加速度は元test_00。灰色破線は教師の独立した記録、青線は学習器自身の閉ループ記録。教師軌道を学習器の成果として再生していない。

Rerunは既存の**再生用test_00（422フレーム）とtest_05（470フレーム）**をそのまま使う。元testとの既知の微小差はPhase 2の過去の記録どおりで、今回新しく再計算した軌道ではない。スクリーニングの主集計・評価図にこのreplayを混ぜていない。

### Phase 2の不変性

作業開始時に旧出力・旧evidence・旧報告・設定・旧ソースとスクリプト・形態資産・checkpoint等409ファイルをSHA-256で固定し、終了時に全409件を照合した。[開始時ハッシュ](../outputs/phase2e/prior_hashes.json)と[最終検証](../outputs/phase2e/final_checks.json)を保存した。README/projectへの今回の追記とPhase 2E新規ファイルは、この旧成果集合とは別である。

| 保存物 | SHA-256（開始・終了一致） |
|---|---|
| 確定readout.npz | `7cc96bd86ba09fa3b688f7574249fde22abb6ff10a1149f7817832459e407151` |
| 公式checkpoint | `d0e42857e738d0315897c2d50fde9eb3fb1a3fb1f071d55dfc13d53d72bccc3f` |
| configs/phase2.json | `3fbe275795760df19bd0178d249188da4d27f62e74aff7e86fa67bb2d567ab9b` |


元のstate、指令、成功判定、split、学習結果を含むファイル全体のハッシュが一致する。さらに既存の数値監査を、結果保存先だけPhase 2Eにして再実行した。**93試行・34,856フレーム**のHCW遷移、教師ラベル、readout指令、現時刻stateからのカメラ画像、成功区間、train限定標準化を再検証した。これは保存データの再計算検証で、制御実験や学習の再実行ではない。

HCW遷移の最大残差は **3.55×10⁻¹⁵**、保存pre-clipping指令との最大差は **3.33×10⁻¹⁶ m/s²**。成功判定も保存結果と一致した。[数値監査JSON](../outputs/phase2e/phase2_numerical_audit.json)。

| 固定された元test結果 | 成功数／総数 | 失敗理由 |
|---|---:|---|
| 学習器・接近 | 8/8 | なし |
| 学習器・近傍 | 4/4 | なし |
| 教師 | 12/12 | なし |
| zero対照 | 0/1 | 400秒timeout |

この限定された元testの結果を維持した。再学習、readout探索、test追加、成功閾値・goal変更、教師への切替は0回。

## B. 細胞型スクリーニング

### 対象・指標・局面

主対象は元の学習器test_00〜test_11、**4,077フレーム（制御期間3,837、初期観測240）**。保存済み全型signed mean/RMS、phi、pooling metadata、state、指令、時刻と確定readoutを使った。解析・表示生成のFlyvis再推論は0回。後述の既存GPU回帰テストのみ短い推論を行った。

モデルの実ラベル**65型・45,669細胞**を評価した。入力8型R1〜R8の5,768細胞はreadoutに使わず、非入力57型・39,901細胞の各16 bin、計912特徴を使う。論文の「64 cell types」と実装のラベル数を同一視しない。モデルではCT1(M10)・CT1(Lo1)も別の集計ラベルとして扱う。roleはモデルメタデータ上の分類であり、例えばoutputを「宇宙機の運動出力ニューロン」という意味にはしない。

各細胞の灰色reset後基準との差をΔvとし、型signed mean＝mean(Δv)、型RMS＝sqrt(mean(Δv²))。単位はモデル活動単位で、mVや発火頻度ではない。signed meanでは正負が相殺されるため、RMSと別々に保存・表示した。

- robust dynamic range：各試行の制御期間でp95−p05を計算し、12試行の中央値を取る。
- 時間変化：mean(|ΔRMS|)/0.5秒、およびsigned meanの同指標。物理秒であって神経秒ではない。
- 最小・最大：12試行の制御期間全標本での極値。初期観測の立ち上がりをランキング指標から除外した。時間系列図には観測期間も含める。
- readout寄与RMS・dynamic range：各軸・各試行で計算し、試行間中央値。長い試行を過剰に重み付けしない。
- 冗長性：試行内の型RMS間Pearson相関を12試行で中央値集計。resetをまたぐ連結相関は使わない。

局面は保存state・applied commandから以下の優先順で分類した。制御入力へは渡していない。

| 局面 | 条件 |
|---|---|
| observation | control_maskがfalse（最優先） |
| near_hold | 制御中、位置誤差<0.25 m かつ速度<0.01 m/s |
| braking | 上記以外でx>10、vx<0、applied ax>0 |
| approach | 上記以外でx>10.25、vx<0 |
| other | 残り |

brakingは「接近速度に逆らうradial**指令**」の分類であり、HCWの自然項まで含む瞬間的な正味dvx/dt>0を主張しない。approachの遠方はgoal許容範囲外の高x側と定義した。スクリーンショット時刻を分類条件に使っていない。

各局面5標本以上ある同一の9試行（test_00〜07とtest_10）にそろえ、各試行内の局面RMS中央値→9試行間中央値を求め、その3局面のmax−minをphase contrastとした。test_08/09/11は接近・制動標本がないため局面比較から除外するが、12試行の通常指標からは除外しない。test_10はnear初期条件でもルール上3局面を含む。全局面の標本数と欠測はNPZ/JSONに残した。

### 線形readout寄与の意味

凍結したcurrent-only readoutのtrain由来mean/stdとkeep maskを使い、型jの16 binについて **c_j(t)=a_max W_j z_j(t)** を計算した。interceptは型へ配分せず **a_max b=[−7.345725×10⁻⁵, −6.779087×10⁻⁵] m/s²** として別保存した。

全型寄与の和＋interceptは元testのpre-clipping指令に最大 **2.78×10⁻¹⁶ m/s²** で一致。初期観測中は方策を仮に適用した分解値で、実指令はu=0のため、ランキングにはcontrol_mask=trueのみ使った。全細胞活動が保存されているreplay 2本でも65型のmean/RMSを再集計し、保存値との差はともに0だった。replayはこの照合用途に分離した。

これは**標準化した空間特徴を線形readoutが数値的にどう加算したか**であり、生物学的・因果的な重要度ではない。重みの大きさだけのランキングでもない。相関した型・binは互いに打ち消せる。型RMSが小さくても標準化後の寄与は大きくなり得る。型RMSの色を制御寄与の色と読み替えない。

### 上位比較候補8型

順序は最終デモへの定性的な表示優先度で、総合スコアではない。T4aは取得済みの基準として残す。全型の全指標は [CSV](../outputs/phase2e/cell_type_screening.csv) と [JSON](../outputs/phase2e/cell_type_screening.json)。候補判断は [candidate_selection.json](../outputs/phase2e/candidate_selection.json)。

以下のDRとphaseはモデル活動単位。c_ax/c_ayは各型のpre-clipping加算成分RMS、単位 **10⁻³ m/s²**。rはT4aとのRMS相関。8候補はいずれも721モデル細胞、readout使用あり・16 bin。

| 型 | model role | RMS DR | phase contrast | c_ax | c_ay | r(T4a) | 推奨 |
|---|---|---:|---:|---:|---:|---:|---|
| T2 | output | 0.176602 | 0.184873 | 0.109 | 0.121 | 0.915 | strongly recommended |
| Tm3 | output | 0.033982 | 0.035272 | 0.273 | 0.162 | 0.931 | strongly recommended |
| T5d | output | 0.015932 | 0.016496 | 0.567 | 0.245 | 0.933 | useful |
| T4a | output | 0.017784 | 0.015521 | 0.353 | 0.469 | 1.000 | useful |
| L2 | intermediate | 0.077278 | 0.080434 | 0.140 | 0.135 | 0.885 | useful |
| Mi4 | intermediate | 0.062476 | 0.064860 | 0.073 | 0.058 | 0.944 | optional |
| T4c | output | 0.018183 | 0.015640 | 0.676 | 0.168 | 0.921 | optional |
| Tm1 | output | 0.000453 | 0.000414 | 0.468 | 0.765 | 0.926 | not recommended for display |


| 候補 | actual response visibility / phase contrast | readout上の評価 | 生物学的説明性と推奨理由 |
|---|---|---|---|
| T2 | DR・phaseとも全65型で最大。接近→制動→近傍でRMS増大が見やすい | ax/ayとも比較的小さい | 小物体・ON/OFFコントラスト応答というT4aと異なる説明を添えられる。表示向けstrong |
| Tm3 | T4aよりDR・phaseが大きい | axは中程度 | T4への入力段階を示せる。Mi1とほぼ同じRMS経過でDRは大きく、まず片方ならTm3 |
| T5d | 色変化は控えめ。T4aと近いDR | axは全型2位 | T4aにOFF-motion系を補う。方向ラベルは付けず、寄与とRMSの違いも説明できる |
| T4a | DR・phaseは控えめ。平均の正負相殺も大きい | ax/ayとも無視できない加算成分 | 既存の形態と説明を維持する基準。最大応答・最大重要度という扱いはしない |
| L2 | 大きいDR・phase | ax/ayは小さめ | より早い視覚処理段階を示す候補。ただしT2/L1との重複が強い |
| Mi4 | DR・phaseは大きい | ax/ayとも小さい | T4入力の比較用。Tm3とのRMS相関が極めて高く、同時追加は優先しない |
| T4c | T4aに近いDR・phase | axは全型1位 | 同じT4系を増やすより処理段階の違う型を先に選ぶ。寄与比較を重視するならoptional |
| Tm1 | RMS DRは0.000453で共通尺度ではほぼ平坦 | ayは全型1位 | T5入力としての説明性はあるが、単色arborの変化を見せる次回表示には非推奨 |

生物学的根拠は数値観測とは分ける。Flyvis論文では、T4はON-motion、T5はOFF-motion選択性を持つ群として扱い、Mi1・Tm3・Mi4をT4への主要入力（ON flashで一過性脱分極）、Tm1をT5への主要入力（ON flashで一過性過分極）として比較している。Tm3の広い空間受容野、L2のlamina monopolar cellとしてのコントラスト応答も説明の背景とした。[Lappalainen et al., Nature 2024](https://doi.org/10.1038/s41586-024-07939-3)

T2については一次研究で小物体への応答とON/OFF輝度ステップの双方への応答が報告されている。[Keleş et al., Cell Reports 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7210872/) 今回の円板接近ログでこのcheckpointの小物体選択性を検証したわけではない。大きなRMS変化をもって物体検出機能が再現されたとは結論しない。

論文のensemble／選択clusterの結果と、今回固定した単一checkpointの実応答を同一視しない。[Flyvis公式の機構解析例](https://turagalab.github.io/flyvis/examples/figure_04_mechanisms/)もclusterごとの解析を明示している。ON/OFFの説明は今回のRMSの符号から推定したものではない。RMSには符号がなく、コントラスト選択性は別の刺激比較を要する。[Flyvis公式flash応答](https://turagalab.github.io/flyvis/examples/03_flyvision_flash_responses/)

**a/b/c/dと今回の画面上下左右・軌道方向の対応は付けていない。** その対応を確認する追加刺激推論も行っていない。T4/T5という群の説明までに留める。OFF系が明るい対象のログ中で活動したことだけから、OFF選択性の破綻や制動検出を主張しない。

### T4aとの違い・冗長性

同じ対象の接近・見かけサイズ変化を受けるため、多くの型RMSは強く相関する。r(T2,L2)=0.9966、r(L1,L2)=0.9999、r(Mi1,Tm3)=0.9977、r(Mi4,Tm3)=0.9985、r(Am,T2)=0.9965。共通の時間経過を独立した「接近センサー」「制動センサー」と命名しない。phase contrastにも制御局面以外に画像のサイズ等の変化が交絡する。

T2はT4aより変化が大きく、小物体応答の説明を付けられる。Tm3はT4の入力段階、T5dはOFF-motion群を比較できる。一方、この違いは今回の型RMS時系列の独立性を意味しない。65×65相関行列と型別寄与時系列を保存してあり、空間binや寄与の同一性をRMS相関だけで決めない。

AmはDRで2位、L1は4位だったが、T2/L2とのRMS重複が大きく、次回の少数形態追加を優先しなかった。Mi1はモデルに実在し有力なON入力候補だが、今回のTm3とRMS経過がほぼ同じでDRが小さい。TmY群の一部に大きな活動・寄与があることも全型表に残し、限定された表示枠では説明しやすい入力・T4/T5群を優先した。除外を「制御に不要」とは扱わない。

指定された10ラベルは**すべて存在**した。以下も実ログで確認済み。全て721細胞・16 bin、Mi1はmodel role=intermediate、残りはoutput。列単位は上表と同じ。

| 指定型 | RMS DR | phase contrast | c_ax | c_ay | r(T4a) |
|---|---:|---:|---:|---:|---:|
| Mi1 | 0.022056 | 0.022139 | 0.375 | 0.143 | 0.942 |
| Tm3 | 0.033982 | 0.035272 | 0.273 | 0.162 | 0.931 |
| T4a | 0.017784 | 0.015521 | 0.353 | 0.469 | 1.000 |
| T4b | 0.020333 | 0.005868 | 0.194 | 0.355 | 0.741 |
| T4c | 0.018183 | 0.015640 | 0.676 | 0.168 | 0.921 |
| T4d | 0.011374 | 0.011829 | 0.441 | 0.213 | 0.943 |
| T5a | 0.021148 | 0.021790 | 0.218 | 0.179 | 0.963 |
| T5b | 0.011117 | 0.008949 | 0.411 | 0.180 | 0.958 |
| T5c | 0.011733 | 0.011741 | 0.361 | 0.215 | 0.927 |
| T5d | 0.015932 | 0.016496 | 0.567 | 0.245 | 0.933 |


### 次段階の形態取得見込み

既存のFlyWire公式annotation table（ローカル `assets/phase1b/sources/annotations.tsv`）のみをexact type名で照合した。以下8型はすべて **available in cached annotations**。件数はこのキャッシュ版の行数で、今回のモデル細胞数や新しい形態取得成功数ではない。

| 型 | exact annotation件数 | 状態 |
|---|---:|---|
| T2 | 1466 | available in cached annotations |
| Tm3 | 1756 | available in cached annotations |
| T5d | 1467 | available in cached annotations |
| T4a | 1462 | available in cached annotations |
| L2 | 1699 | available in cached annotations |
| Mi4 | 1532 | available in cached annotations |
| T4c | 1706 | available in cached annotations |
| Tm1 | 1555 | available in cached annotations |


キャッシュのcommitは `8587524c1748ce5ef2080822a2fc890fc03bf597`、materialization 783。表のSHA-256は `9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be`。例示root ID/sideもJSONに保存したが、T4a以外の最終代表IDを選定したわけではなく、個別形態の完全性や取得APIでの現時点の成功までは未確認。新規skeleton downloadは0件。既存T4a `720575940605852192` の形態・右側ラベル・色・828枝を維持した。

### 比較図（2枚）

![元test_00の候補RMSとsigned mean](evidence_phase2e/candidate_traces.png)

図1：元学習器test_00、同じ物理時間軸・同じ活動尺度。RMS実線／signed mean破線、局面背景色はstate/commandによる分類。初期観測を含む。型ごとの自動正規化はなく、Tm1の変化が小さいこともそのまま見える。[PDF](evidence_phase2e/candidate_traces.pdf)

![応答変化・局面差・readout寄与の分離比較](evidence_phase2e/candidate_metrics.png)

図2：制御期間のみ、試行を等重み。DRとphase contrastは同じモデル活動尺度、ax/ay寄与は同じ加速度尺度。T4aだけを拡大・強調していない。[PDF](evidence_phase2e/candidate_metrics.pdf)

## C. 次の判断

次に新しく代表形態を取得するなら **T2・Tm3・T5dの3型**を提案する。T4aは既存形態を維持する。

1. **T2**：最も大きな実応答変化。T4aと異なる小物体・ON/OFF応答の生物学的背景を説明できる。
2. **Tm3**：T4への入力段階を比較でき、T4aよりRMS変化が見やすい。Mi1/Mi4と重複して並べるより、まず1型にする。
3. **T5d**：OFF-motion群を補い、実readoutのax加算成分も大きい。色変化は控えめであることを了解して選ぶ。

より早い視覚処理段階を説明することが主目的なら、T2の代わりにL2を選ぶ余地がある。T2とL2はRMS相関が0.997なので初回から両方取得する優先度は低い。T4cは軸別寄与の比較重視、Tm1は寄与解析の教材として候補に残すが、次の単色形態追加には優先しない。

現行T4aの固定RMS尺度は0..0.22のまま。T2等に将来そのまま転用すると飽和し得るため、型を実際に追加する段階で比較目的と固定尺度を決める必要がある。今回の比較図では全候補を共通尺度で示しただけで、代表表示の色設定は変更していない。

**最終選択はユーザー判断**。今回の取得・複数形態表示は0件。球形ターゲット、別方向接近、goal変更、長期保持・ノイズ試験、再学習は実施していない。

## D. 実行した検証と限界

| 検証 | 結果・証拠 |
|---|---|
| 既存＋追加単体テスト | **68/68通過**。既存53＋追加15。[log](../outputs/phase2e/unit-tests.log) |
| 追加契約 | 4方向、位置・ベクトルの線形変換と非改変、不正値拒否、非連続type grouping、signed mean/RMS、保存bin対応、train尺度・keep mask・bias付き寄与分解、局面の優先順と時刻非依存、元ログ再構成・409ファイル不変性 |
| 既存数値監査 | **93/93試行、34,856フレーム通過**。[log](../outputs/phase2e/phase2-numerical-audit.log) |
| 全細胞replay集約 | **2/2試行、892フレーム×65型**。signed mean/RMS差0、各replayのreadout再構成も通過 |
| 実RRD照合 | **12種類の時系列×892フレーム**。画像、受容格子色、神経格子色、形態色と828枝、位置、軌跡、速度・加速度矢印（原点含む）、ax/ay、誤差、速度を各replayの元数値と照合。静的goal/targetも確認。[audit](../outputs/phase2e/rrd_audit.json) |
| RRD形式検証・描画 | `rerun rrd verify` exit 0。実画面3枚、シーク・再生・停止通過。[capture](evidence_phase2e/screenshots.json) |
| 旧成果 | **409/409ハッシュ一致**。Phase 1/1B/2の報告・未達記録も保持 |
| 既存CUDA統合テスト | **各回1/2通過、1/2失敗、skip 0**。初回＋同条件で1回再確認。[初回](../outputs/phase2e/integration-tests.log)／[再確認](../outputs/phase2e/integration-tests-retry.log) |

GPUで失敗したのは `test_phase2_real_images_policy_prefix_and_weight_freeze` の同じ先頭10画像に対する再実行出力比較。従来閾値はatol=2×10⁻⁷、rtol=2×10⁻⁵。初回は20成分中3成分が超過し、超過成分の最大絶対差7.2776×10⁻⁷ m/s²、再確認も3成分、1.08065×10⁻⁶ m/s²だった。

既存adapterのcheckpoint/statefulテストは両回通過した。失敗したtestはprefix比較で中断しており、その後のassertion通過を主張しない。GPU再実行の微小な数値再現差と整合するが、原因は今回特定していない。Phase 2E表示関数はこのテスト経路に入らず、旧コード・重み・環境設定は変更していない。許容値を緩めず、都合のよい成功実行だけを選ぶ再試行もせず、2回の失敗を残した。

この問題は**元の保存済みtest結果が変わったという意味ではない**。保存データのSHAと独立した成功判定再計算は通過している。ただし、将来の再推論を数値一致まで求める場合の未解決課題である。今回の報告を「GPUを含む全回帰テスト合格」として扱わない。

## E. 保存物と再現コマンド

主要数値は [cell_type_metrics.npz](../outputs/phase2e/cell_type_metrics.npz)。全65型のフレーム時系列、型・bin対応、型別2軸寄与と別bias、局面、試行別DR/寄与、局面標本数と中央値、65×65相関を含む。存在しない局面の試行別中央値はNaNで区別し、ゼロ応答には置き換えない。JSONには元レコードのSHA・集計方法・全型統計・annotation状態を保存した。

新RRDは [outputs/phase2e/phase2e.rrd](../outputs/phase2e/phase2e.rrd)、[viewer manifest](../outputs/phase2e/viewer_manifest.json)、[最終検証](../outputs/phase2e/final_checks.json)。解析コードは [screening.py](../src/flyrendezvous/screening.py) と [screen_phase2e.py](../scripts/screen_phase2e.py)。今回使った候補順と定性的理由はcandidate_selection.jsonに独立保存した。

WSLのプロジェクトルートで既存venvを使う。**再生だけ**なら：

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase2e/phase2e.rrd --bind 127.0.0.1
```

保存ログから分析・表示を再生成する手順（学習・制御の再実行なし）：

```bash
.venv/bin/python scripts/screen_phase2e.py
.venv/bin/python scripts/plot_phase2e_screening.py
.venv/bin/python scripts/plot_phase2e_orbit.py
.venv/bin/python -m flyrendezvous.viewer_phase2e
.venv/bin/python scripts/verify_phase2e_records.py
.venv/bin/python scripts/verify_phase2e_rrd.py
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun rrd verify outputs/phase2e/phase2e.rrd
.venv/bin/python scripts/capture_phase2e.py
.venv/bin/python scripts/verify_phase2e.py
```

テストの再実行（GPUテストには上述の未解決の再現差がある）：

```bash
.venv/bin/python -m pytest tests -m 'not integration'
.venv/bin/python -m pytest tests -m integration
```

Phase 2Eの5項目（表示方向、旧結果不変、候補比較、実応答・寄与・生物学的根拠の分離、次の選択材料）は整えた。残る検証上の制約は既存GPU prefix比較の失敗。ここで作業を終了し、追加形態取得や新規制御実験には進まない。
