# FlyRendezvous Phase 2 実行・検証報告

実行日：2026-09-11 JST。**2A〜2Dを実装・実行し、固定testで学習器自身の閉ループは接近8/8・近傍4/4が成功した。** 初回成立の目安「未使用の接近条件で3例以上」を満たす。真の状態を読み出しへ渡す経路、教師による救済、成功条件の事後変更はない。

ただし、再生用の全細胞応答の再取得は、元評価と成功判定が一致する一方、厳密な数値一致は未達だった。最大位置成分差約2〜3.2 mm、1例の終了時刻差0.5秒を分けて報告する。

## A〜Dの判定

| 段階 | 判定 | 証拠 |
|---|---|---|
| A：HCW・教師・カメラ | 達成 | 学習前の教師30/30、モデル固定後のtest教師12/12が視野内で接近・減速・保持 |
| B：実Flyvisデータ | 達成 | train 24・validation 6試行の9,946画像を全45,669細胞で逐次計算、912特徴を保存 |
| C：線形読み出し | 達成 | 指定6候補を学習しvalidationで選択。モデル固定後にtest 12条件を評価、追加教師付け0回 |
| D：学習器自身の閉ループ | 達成（限定条件） | 接近8/8・近傍4/4。自身の飽和後加速度でHCWを更新。長期保持・任意条件・高信頼性は未検証 |
| 再生用再実行 | 部分達成 | 成功判定2/2一致、厳密な数値一致0/2。RRDとその再生元NPZの同期は全892サンプルで一致 |
| GUI | headless確認済み／対話GUI未検証 | native Rerunで実描画・再生・停止・時刻移動。Windows GUIのマウス操作は未検証 |

## 1. HCWと教師の採用条件

[設定](../configs/phase2.json)は初期数値案から変更なし。n=0.0011 rad/s、目標[10,0,0,0]、各軸加速度上限0.005 m/s²、物理刻み0.5秒、最大400秒、逸脱x<=5またはx>=40 m。接近初期条件はx=14〜22、y=±2 m、vx/vy各±0.02 m/s、近傍はx=9.5〜10.5、y=±0.5 m、vx/vy各±0.01 m/s。

LVLHのxは半径外向き、yは軌道進行方向。指令のA/Bをそのまま実装し、[SciPy cont2discrete](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.cont2discrete.html)のZOHを使用した。Aの逆行列は用いない。[solve_discrete_are](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_discrete_are.html)からP/Kを計算した。Q=diag(0.01,1/9,25,25)、R=diag(40000,40000)。

u_eq=[-0.0000363,0] m/s²で目標平衡が成立する。連続／離散の平衡をテストし、非飽和Ad-BdKのスペクトル半径は0.9899466632<1。教師はu_eq-K(s-s_goal)を各軸クリップする。飽和込みの軌道成功を別に実測した。入力制約付きの厳密最適解とは説明しない。[LQRの背景](https://underactuated.mit.edu/lqr.html)

[A/B/Ad/Bd、Q/R、P/K、u_eq、固有値](../outputs/phase2/lqr.json)と[教師ゲート](../outputs/phase2/phase2a.json)を保存した。学習前に接近20/20・近傍10/10が成功。初期実装のカメラ設定受け渡し不備を修正したが、データ生成前のコード修正で、数値条件の変更ではない。

成功は位置誤差ノルム<0.25 m、速度ノルム<0.01 m/sを制御中に10秒維持すること。実装は隣接する両端状態が条件内である0.5秒区間を20区間連続で数える。連続時間の区間内全極値を証明する判定ではない。達成後は記録を終了するだけで状態を強制停止しない。10秒を超える長期保持は未検証。

## 2. カメラ・初期観測・時刻

カメラは64×64、水平画角40度、光軸LVLH -x固定、原点のyz平面の半径1 m円板を投影する。f=31.5/tan(20度)、u=31.5-f*y/x、v=31.5、r=f/x。y>0で左へずれ、距離半減で半径が2倍になることを検証した。追尾・オートズーム・切り出しはない。

8×8固定スーパーサンプリングで境界の被覆率を計算し、中心と半径を整数へ丸めない。微小移動への応答をテストした。ただし有限サンプリングなので数学的に完全な連続関数ではない。既存BoxEye(extent=15,kernel_size=13,mean)を使用する。スモーク半径は5.72〜5.82 px／8.71〜8.80 px、中心受容点は1.0、画像階調は44／65種類だった。[診断](../outputs/phase2/camera_diagnostic.json)

真の状態と中心・半径はレンダリングと診断のみで、読み出しには渡さない。既知の対象サイズと固定較正を前提とし、未知サイズ対象の距離推定を実証したものではない。

| 時間 | 意味 |
|---|---|
| dt_phys=0.5秒 | HCW・制御区間。力学は常に物理秒 |
| dt_neural=0.01秒 | 既存Flyvisの刻み |
| 時間尺度比50 | 画像時系列の神経時間への再尺度化 |
| 灰色reset 1神経秒 | 試行開始時のみ。ここでは物理状態を進めない |
| 初期観測10物理秒 | 20画像、u=0で実HCW運動を観測。履歴を保持し学習ラベルから除外 |
| 再生倍率20 | 物理時間のビューア再生倍率。尺度比50とは別 |

順序はs[k]→I[k]→実Flyvis更新→phi[k]→読み出し→飽和u[k]→HCW→s[k+1]。撮像後の計算・通信遅延はゼロという理想化であり、実遅延の検証ではない。sample_id、observation_time、neural_input_time、neural_response_time、acceleration_intervalを保存する。学習器のAPIは `ImagePolicy.step(image)` のみで、真の状態・教師・時刻・シミュレータを渡さない。

## 3. データと固定特徴

[初期条件・split](../outputs/phase2/splits.json)を先に保存した。seedはtrain=2101、validation=2102、test=2103、全42初期状態は重複しない。フレームを混ぜて分割しない。[設定固定contract](../outputs/phase2/contract.json)

| split | 接近 | 近傍 | 全画像数 | 回帰対象 |
|---|---:|---:|---:|---:|
| train | 16 | 8 | 7,924 | 7,444 |
| validation | 4 | 2 | 2,022 | 1,902 |
| test | 8 | 4 | モデル固定後に自身の軌道で生成 | 学習・選択対象外 |

2本×60画像の実GPUスモーク後にtrain/validationを生成した。到達・保持後の画像やほぼゼロの指令を水増ししない。全45,669細胞をeval・勾配なし・固定重みで計算し、試行開始時だけresetする。

実メタデータの `role=input` はR1〜R8の5,768細胞。これを読み出し特徴から除外するが、回路計算から取り除かない。残り39,901細胞・57 typeを、既存の網膜対応格子x=1.5v、画面y=√3(u+v/2)の共通4×4境界でプーリングする。灰色基準からの符号付き電位変化を平均し、57×16=912次元。内部区間は左閉右開、最大端は最後へ含め、空領域はゼロと定義したが今回は空領域0。

[pooling.npz](../outputs/phase2/pooling.npz)に使用／除外cell_index、境界、全割当を保存した。[特徴説明](../outputs/phase2/features.json)。これは人工的な固定線形処理で、生物学的に同定した出力経路ではない。表示用T4a RMSを制御特徴へ流用しない。

全typeの符号付き平均とRMSも軽量保存する。一般試行はphi・状態・画像・教師ラベル・実指令・時刻・基準を保存し、全細胞応答はスモーク、履歴診断、再生用2試行に限定した。

## 4. 学習とvalidation

教師の飽和後総加速度／a_maxをラベルに、Wとbのみ学習した。u_eqを後付けせず総加速度を予測する。

```text
minimize (1/N) sum_k ||W z[k] + b - target[k]||² + lambda ||W||_F²
u_raw = a_max * (W z + b)
u_applied = clip(u_raw, -a_max, +a_max)
```

切片は正則化しない。Gram行列と右辺をNで割り、λをサンプル数と整合させる。以下のMSEは報告用にサンプルと2軸で平均した値。平均・標準偏差・定数特徴除外はtrainの制御フレームだけから決定し、validation/testでは固定した。

現在値のみ／5フレーム前との連結（物理2.5秒前、神経0.05秒前）×3λの6候補だけを実行した。保持特徴は912／1,824次元で、全特徴が閾値1e-8を上回った。

| 特徴lag | λ | train MSE | validation MSE | validation閉ループ |
|---:|---:|---:|---:|---:|
| 0 | 0.0001 | 0.0000293 | 0.0105349 | 6/6 |
| 0 | 0.01 | 0.0001964 | 0.0045072 | 6/6 |
| 0 | 1 | 0.0013586 | 0.0033043 | 4/6 |
| 5 | 0.0001 | 0.0000173 | 0.0088352 | 6/6 |
| 5 | 0.01 | 0.0001538 | 0.0047951 | 6/6 |
| 5 | 1 | 0.0010294 | 0.0033934 | 4/6 |


選択規則は事前に「validation閉ループ成功数→平均終了位置誤差→教師軌道上MSE→lag・λ」の優先順で固定。**現在値のみ・λ=1e-4**が選ばれた。validation 6/6成功なので、追加教師付けの発動条件（正規化RMSE<0.25かつ閉ループ失敗あり）に該当せず、追加0回。[全候補とvalidation軌道](../outputs/phase2/round0/candidates.json)

教師軌道上MSEの最小候補λ=1は、両構成ともvalidation_00／02が400秒でtimeout。終了位置誤差は現在値で3.718／1.297 m、履歴連結で3.425／0.922 m。回帰誤差だけでは制御成功を選べない実例である。

[読み出し・標準化係数](../outputs/phase2/readout.npz)、[モデル固定](../outputs/phase2/model_lock.json)を保存した。testを見て調整していない。モデルSHA-256は `7cc96bd86ba09fa3b688f7574249fde22abb6ff10a1149f7817832459e407151`。PCA探索、NN、RL、状態推定器、Flyvis再学習へ拡大していない。

## 5. 未使用testの全結果

教師は接近8/8・近傍4/4、学習器も接近8/8・近傍4/4。以下は元のtest評価で、再生用再実行を分母に混ぜない。

| 試行 | 群 | 教師終了秒 | 学習器終了秒 | 位置誤差m | 速度m/s | 終了理由 |
|---|---|---:|---:|---:|---:|---|
| test_00 | approach | 226.0 | 210.5 | 0.182168 | 0.005848 | success |
| test_01 | approach | 209.0 | 212.5 | 0.186793 | 0.005410 | success |
| test_02 | approach | 231.5 | 241.0 | 0.185451 | 0.005526 | success |
| test_03 | approach | 220.5 | 246.5 | 0.187921 | 0.005276 | success |
| test_04 | approach | 201.5 | 168.5 | 0.200637 | 0.004046 | success |
| test_05 | approach | 217.5 | 235.0 | 0.187479 | 0.005084 | success |
| test_06 | approach | 226.0 | 217.0 | 0.180668 | 0.005909 | success |
| test_07 | approach | 232.0 | 248.5 | 0.185249 | 0.005429 | success |
| test_08 | near | 51.5 | 39.5 | 0.192381 | 0.005605 | success |
| test_09 | near | 33.5 | 34.5 | 0.184129 | 0.006059 | success |
| test_10 | near | 78.0 | 77.5 | 0.211340 | 0.003588 | success |
| test_11 | near | 93.0 | 107.5 | 0.190140 | 0.005909 | success |


全例successで、範囲逸脱・視野離脱・非有限値・時間切れは各0/12。終了時刻は初期観測10秒と保持10秒を含む。保持開始は終了の10秒前。誤差と速度は終了状態s[N]。最小対象距離、飽和率、加速度誤差、∫||u||dtを[results.csv](../outputs/phase2/results.csv)と[全評価JSON](../outputs/phase2/evaluation.json)に保存した。加速度積分を燃料消費量とは呼ばない。

無入力はtest_00を別実行し、**0/1、400秒でtimeout**。終了位置誤差10.8374 m、速度0.01459 m/sだった。

学習器test_04は飽和率14.83%、教師との加速度RMSE約0.001876 m/s²と大きく、異なる強い加速・減速で成功した。教師軌道の再現や燃料最適性、従来制御への優位性とは解釈しない。

![元test評価の軌道・誤差・速度・実加速度](evidence_phase2/evaluation.png)

[同図PDF](evidence_phase2/evaluation.pdf)。青は学習器、灰破線は別実行の教師。右下はtest_00の実加速度。再生用再実行は含まない。

## 6. 神経履歴と因果性

x=18→16と14→16 mの60画像で最終画像を同一にした実GPU診断を行った。これは規定HCW軌道とは別の指定画像履歴で、学習データには加えていない。

最終画像は完全一致、最終特徴L2差0.0621383、全細胞応答差RMS 0.00499109、飽和前加速度差約[0.00192680,-0.00019819] m/s²。[診断記録](../outputs/phase2/history_diagnostic.json)

別のGPU統合試験では共通prefixの後だけ画像を変更し、過去の指令の一致と変更後の指令差を確認した。特徴変更でも指令が変わり、単なる時刻表再生ではない。応答差だけで線形制御成功とは判定せず、実閉ループ性能を別評価した。

## 7. Rerun・代表表示・再実行差

軌道mと解剖µmは別ビュー。機体は点、対象は原点のマーカー、目標はx=10 m。速度矢印は20秒倍、飽和後の実加速度矢印は400秒²倍の表示長で、物理更新には影響しない。

**FlyvisはT4aだけでなく、今回の構成では45,669個の視覚系モデル細胞を計算する。3D表示しているT4a形態は、別途取得した実測1細胞の形である。色はその実測細胞自身の活動ではなく、同型の721モデル細胞の電位変化を集約した値である。個別細胞の位置対応や枝内の電位伝播は計算していない。表示対象の細胞型は、計算対象や制御への読み出し対象とは別の選択である。**

この説明をREADME・projectと短い画面凡例に反映した。既存のT4a 1形態、右由来・モデル左右未割当を保持し、追加形態取得・型選別は0件。形態RMS尺度はPhase 1Bの固定0〜0.22、格子は±1.5。再生2試行のクリップは両方0件。[表示manifest](../outputs/phase2/viewer_manifest.json)

再生用は最初の成功例test_00と、終了誤差が中央値側の典型例test_05。testに失敗例はないため失敗動画は作っていない。892画像の全細胞応答を再取得した。

| 試行 | 成功結果 | 最大位置成分差m | 最大速度成分差m/s | 最大加速度差m/s² | 終了時刻差 |
|---|---|---:|---:|---:|---:|
| test_00 | 一致 | 0.0019833 | 0.00005647 | 0.00001316 | +0.5秒 |
| test_05 | 一致 | 0.0032073 | 0.00008347 | 0.00001580 | 0秒 |

最初の厳密チェックは終了サンプル不一致で停止した。元testを上書きせず、一致／不一致を記録する経路へ修正して2例を保存した。atol=rtol=2e-5での厳密な数値一致は両例とも未達。灰色基準の最大差7.15e-7、画像が初めて異なったサンプル26／58。微小なGPU数値差と有限サブピクセル境界の閉ループでの累積が一因と考えられるが、原因を完全に分離した試験ではない。[比較記録](../outputs/phase2/replay_comparison.json)

**RRDには再実行自身の画像・応答・軌道・指令を記録し、別軌道の活動を貼り付けていない。** 保存済みRRDの再生は新規推論を行わない。収録test_00は211.0秒で成功し、最後の表示入力は210.5秒。

| 画像 | 試行／sample | 物理秒 | 神経前→後 | RMS | 実ax,ay m/s² |
|---|---|---:|---|---:|---|
| [approach.png](evidence_phase2/approach.png) | test_00／40 | 20.0 | 0.40→0.41 | 0.089766 | -0.0034447, -0.0006472 |
| [braking.png](evidence_phase2/braking.png) | test_00／191 | 95.5 | 1.91→1.92 | 0.098865 | +0.0010474, -0.0000788 |
| [hold.png](evidence_phase2/hold.png) | test_00／421 | 210.5 | 4.21→4.22 | 0.109025 | +0.0000874, -0.0000091 |


![減速中の実Rerun画面](evidence_phase2/braking.png)

上記はnative Rerun 0.37.1の実headless描画。別ライブラリの合成予想図ではない。[画像ハッシュ・viewer時刻・操作記録](evidence_phase2/screenshots.json)。software rasterizerの実描画とviewer-mcpによる時刻移動・再生進行・停止保持を確認。Windows GUIマウス操作は未検証。

## 8. テスト・監査・計算量

- **単体53 passed**：既存45＋追加8。HCWのn=0解、高精度DOP853との比較、平衡・飽和、カメラ符号・サイズ・微小移動・視野、入力除外、履歴prefix、試行分離、train-only標準化、リッジ勾配・切片・再読込、時刻対応。[ログ](../outputs/phase2/unit-tests.log)
- **実GPU統合2 passed、skipなし**：既存状態保持/reset/固定重みと、実画像から選択読み出しまでの逐次処理・prefix因果性。[ログ](../outputs/phase2/integration-tests.log)
- **独立監査93記録・34,856フレーム**：全候補・データ・test・再生を照合。HCW最大差3.56e-15、保存指令と読み出し再計算最大差3.34e-16。画像がs[k]由来、成功判定、train-only標準化も再計算。[audit.json](../outputs/phase2/audit.json)
- **実RRD 892サンプル**：画像・受容器・格子・全枝の色と座標・機体・速度／加速度矢印・実加速度／誤差／速度グラフを元NPZと照合。[rrd_audit.json](../outputs/phase2/rrd_audit.json)
- `rerun rrd verify` と `pip check` が成功。依存追加・更新なし。
- Phase 1／1Bの報告・出力・証拠等64ファイルのSHA-256不変。[作業前ハッシュ](../outputs/phase2/prior_hashes.json)。過去のaccepted_mappingsと個別対応未達の記録は保持。

RTX 5070 Ti、Flyvis 1.2.0、既存flow/0000/000を使用。train/validationの画像生成・逐次推論・転送・特徴処理は計約27.16秒、候補6件の学習・保存・validation閉ループは約51.49秒、test学習器12件の同処理は約11.49秒。試行wall_secondsは読込・reset・圧縮保存を除く。CPU処理を含む壁時計時間で、GPUカーネル単独時間ではない。CPU転送による同期を含む経路で計測した。

PyTorch CUDA最大割当166,593,024 bytes（約158.9 MiB）、outputs追加約369 MB（約0.344 GiB）で5 GiB目安以内。VRAM値はドライバー予約を含む全プロセスではない。全パラメータ前後ハッシュは `f7f8252191ac4bfc38e18cc03a55061f603e68cc03a402eaf363d2141d53baa9` で一致し、Flyvis更新は0回。

## 9. 再生・再現コマンド

WSLのプロジェクトルートから：

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase2/phase2.rrd --bind 127.0.0.1
```

初期停止、再生20倍。表示20秒で接近加速、95.5秒で減速、210.5秒で保持直前。次試行は表示221秒からで、独立試行間に10秒のRESET空白がある。

保存済み結果から表示・監査を再生成：

```bash
.venv/bin/python -m flyrendezvous.viewer_phase2
.venv/bin/python scripts/capture_phase2.py
.venv/bin/python scripts/verify_phase2_rrd.py
OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/verify_phase2.py
.venv/bin/python scripts/plot_phase2.py
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun rrd verify outputs/phase2/phase2.rrd
```

実験全体は新しい出力先で再現し、確定結果を保持する：

```bash
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python scripts/run_phase2.py a --output outputs/phase2_reproduction
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python scripts/run_phase2.py b --output outputs/phase2_reproduction
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python scripts/run_phase2.py c --output outputs/phase2_reproduction
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python scripts/run_phase2.py d --output outputs/phase2_reproduction
.venv/bin/python -m flyrendezvous.viewer_phase2 --input outputs/phase2_reproduction
```

完了済みのa/b/c/dは同じ出力先への再実行を拒否する。GPU数値差により新しい実験の軌道・候補順位までbit一致を保証しない。今回のreadout.npzとRRDは今回の結果を固定する成果物である。

## 10. 次の判断と限界

既知サイズ円板、固定較正、限定初期条件、ゼロ計算遅延、50倍の神経時間再尺度化という条件で成立した。未知サイズ・遮蔽・ノイズ・カメラ運動・実遅延・長期保持・範囲外初期条件は未検証。12例の成功を一般的な信頼性や生物回路全般の優位性へ一般化しない。

912特徴で今回の閉ループは成立したが、T4aが制御の中心という因果的同定はしていない。最終表示typeは保存した全typeの実応答を見て後から判断する。今回、追加形態調査へ戻っていない。

次は限定条件と再実行差の説明方法、より長い保持や誤差要因を別段階で評価するかの判断が必要。今回の範囲を超える学習方式・制御再調整・MuJoCo／ROS・姿勢／接触／スラスタ・映像制作・外部公開には進んでいない。
