"""Generate Phase 5B report from saved results, including gate stop."""
import json
from pathlib import Path
from flyrendezvous.recording import write_json
O=Path('outputs/phase5b')
def read(p):return json.loads((O/p).read_text())
def main():
    ev=read('evaluation.json');sel=read('readout_selection.json');diag=read('nominal_failure_diagnosis.json')
    phy=read('physics_validation.json');san=read('perturbation_sanity.json');reg=read('regression.json')
    video=read('mp4/H0_verification.json');lock=read('model_lock.json')
    rows=ev['trials'];main=next(r for r in rows if r['controller']=='learner' and r['trial_id']=='test_00')
    m=read('evaluation/H0/learner/test_00.json')
    table='\n'.join(f"| {c['candidate']} | {c['train_mse']:.6g} | {c['validation_mse']:.6g} | {c['success']}/{c['total']} | {c['mean_final_position_error']:.3f} |" for c in sel['candidates'])
    failures='\n'.join(f"| {r['trial_id']} | {r['result']} | {r['duration_s']:.1f} | {r['min_goal_error_m']:.4f} | {r['final_goal_error_m']:.4f} | {r['final_speed_mps']:.5f} |" for r in rows if r['controller']=='learner')
    references='\n'.join(f"| {r['condition']} | {r['absolute_position_error_m']:.3e} | {r['absolute_velocity_error_m_s']:.3e} | {r['relative_position_error_m']:.3e} | {r['relative_velocity_error_m_s']:.3e} |" for r in phy['integrator'])
    accel='\n'.join(f"| {name} | {san['accelerations'][key]['target_m_s2']:.6e} | {san['accelerations'][key]['chaser_m_s2']:.6e} | {san['accelerations'][key]['differential_m_s2']:.6e} |" for key,name in [('j2','J2'),('srp','SRP'),('drag','drag, rho=1e-12')])
    means={r['controller']:r for r in ev['condition_summary']}
    report=f"""# Phase 5B：nominal HCW学習とtruthモデル検証 — Gate 5停止

**教師56/56成功、データ生成48/48成功。選択readoutはvalidation 1/12、H0 held-out 0/8成功となり、Gate 5で停止した。** H0 LQR sanity referenceは8/8成功。T0/T1/E0/Elo/Ehi/R1/R3/R5/RM3の閉ループは**未実行**であり、0/8という結果ではない。truth耐性・外乱補正能力は結論できない。

[指令](codex_phase5b.md)の「H0が大きく壊れている場合はtruth評価へ進まない」に従った。実装前に成功6/8未満を停止基準として[training config](../configs/phase5b/training.json)と[contract](../outputs/phase5b/contract.json)へ固定した。実際は0/8であり、閾値の境界的な判断ではない。test後の再学習、条件緩和、教師への切替、test再実行は0。

## 研究課題・Phase 5Aからの動機

Phase 5Aでは旧test_00の総Δvの76.13%が観測後前半に集中し、55–219.5秒は長い制動、終端Pilot傾斜中央値は1.31°だった。今回の問いは、画像入力のみの固定Flyvis＋readoutが、nominal HCWと非線形力学・環境摂動の差を視覚フィードバックで補正できるか、である。距離の分布外一般化と力学差を分離するため、まず25–35 mで新規HCW学習を行った。

AGENTS、README、project、Phase 3/4C/5A報告、5A manifest・trial summary・geometry candidates、HCW・teacher・camera・rollout・特徴抽出・readout・成功/安全判定・4C viewer/Pilot/Brainを確認した。AGENTSの旧Phase範囲は履歴として維持し、今回の明示指令で許可されたPhase 5Bを分離実装した。

## 初期分布・固定条件

[split](../outputs/phase5b/splits.json)はtrain36、validation12、test8、全approach。seed5101/5102/5103。4次元の独立randomized Latin hypercubeで各split内のdepth/cross/vx/vyを層化、56初期状態の重複0、失敗sample再抽選0。

- e_goal=(-1,+1)/sqrt(2)、e_cross=(-1,-1)/sqrt(2)はPhase 3コードと一致。
- r0∈[25,35] m、c∈[-4,4] m、r_start=r0 e_goal+c e_cross。r0はdepth、中心距離はsqrt(r0²+c²)。
- LVLH vx/vyはPhase 3と同じ各[-0.02,+0.02] m/s。新velocity-error因子なし。
- goal=5 e_goal、球半径1 m、完全固定boresight=(+1,-1)/sqrt(2)、64×64、HFOV40°、supersampling8。
- dt物理0.5秒、dt神経0.01秒、warmup1神経秒、observation10物理秒、timeout600物理秒。
- input除外、pooling、LQR Q/Rとapproach座標へのcost回転、飽和各軸±0.005 m/s²を保持。

成功は位置誤差<0.25 m、回転系相対speed<0.01 m/s、観測後に**両端**が条件を満たす区間を連続10秒保持。安全判定が先行し、中心距離<=1.25 mでcollision、>=40 mでrange exit、球の全silhouetteが画像内に収まらなければFOV exit。Phase 3の円形silhouette envelope近似も変更していない。

## 教師ゲート・データ生成

Gate 3はtrain36/36、validation12/12、test候補8/8、合計**56/56**成功。終了247–272秒。[教師ゲート](../outputs/phase5b/teacher_gate.json)に全ログとSHAを保存。

Flyvisは45,669 model cellsを計算、R1–R8のinput-role 5,768細胞をreadoutから除外。39,901細胞・57型を既存4×4 retinotopic poolingで912特徴へ集約。神経データはtrain+validationの**48本・{diag['data_samples']:,} samples**、全て教師成功。選択候補のtrain control samplesは{diag['training_control_samples']:,}。testを学習・表示尺度設定に使用していない。[features](../outputs/phase5b/features.json)、[data](../outputs/phase5b/data.json)参照。

## 学習・validation・readout選択

current特徴（lag0）と既存lag5、lambda=1e-4/1e-2/1の6候補。trainのみで標準化、教師の飽和後指令/a_maxを回帰。教師軌道上のMSEと学習器自身によるvalidation閉ループを別記録。選択順はsuccess最大、平均最終誤差最小、teacher-forced MSE最小、lag/lambda。

| 候補 | train normalized MSE | validation normalized MSE | validation成功 | 平均最終誤差 m |
|---|---:|---:|---:|---:|
{table}

選択は**lag0、lambda=1e-4、912特徴**。教師軌道上のvalidation normalized RMSE={diag['teacher_forced_normalized_RMSE']:.6f}、加速度換算{diag['teacher_forced_acceleration_RMSE_m_s2']:.6e} m/s²だが、閉ループ成功は1/12。予測誤差と閉ループ成立は別の結果である。

**手順の制約：本runは6候補・1 round、augmentationなしを実行前に固定した。** Phase 3の実行には最大1 roundのtrain-only追加ラベル収集があったが、今回は行っていない。Phase 3の全学習過程を再現した、または既存familyで達成可能な最良性能を探索し尽くした、とは主張しない。これは本runの重要な制約。testを見てから追加roundを行っていない。

[readout](../models/phase5b/readout.npz) SHA-256：
{lock['readout_sha256']}

[model lock](../outputs/phase5b/model_lock.json)はreadout、pooling、Flyvisパラメータ、configs/split、実行コード、表示尺度をheld-out前に固定。128神経エピソード（data48＋validation72＋H0 test8）のパラメータSHAは全て次の値で不変：
{lock['parameter_sha256']}

## Earth/orbit・座標対応

[truth config](../configs/phase5b/truth_model.json)に値・単位・出典を固定。mu_E=3.986004418e14 m³/s²、R_E=6378137 m、J2=1.08262668e-3、omega_E=7.2921150e-5 rad/s、n=0.0011 rad/s。chief初期円軌道半径は**{san['chief_radius_m']:.9f} m**、高度**{san['chief_altitude_m']:.9f} m**。初期chief位置はECI +X、速度は+Y。

mu/R/omegaは[NGA WGS84](https://earth-info.nga.mil/?action=wgs84&dir=wgs84)、J2を含む指定定数は[ESA GTOC9 constants](https://kelvins.esa.int/gtoc9-kessler-run/constants/)と整合。

[physics_phase5b.py](../src/flyrendezvous/physics_phase5b.py)はequatorial ECIのtarget/chaser絶対位置・速度8成分を別々に積分。B=[e_r,e_t]、e_t=+z×e_r、omega=(r_t×v_t)_z/|r_t|²。

- rho_I=r_c-r_t、rho_L=Bᵀrho_I。
- v_rel,L=Bᵀ(v_c-v_t-omega×rho_I)。回転速度項を除去する。
- 逆変換：r_c=r_t+B rho_L、v_c=v_t+B v_rel,L+omega×(B rho_L)。
- goalは現在chiefのLVLHに固定し、ECI固定点にしない。
- 指令成分u_LVLHを0.5秒保持し、RK4の各stageでB(t)u_LVLHをchaserのみに加える。

truth rolloutはPhase 3の画像専用policy呼出し・成功/安全判定を分離コピーし、伝播だけをtruth環境へ接続。policy.stepにはimageだけを渡し、状態・label・外乱係数を渡さない。**このtruth rolloutのheld-out end-to-end実行はGate 5で停止したため未検証**。物理関数の数値検証とは区別する。

## two-body・J2・SRP・drag

two-bodyは各機に -mu r/|r|³。J2は一般3D摂動式を独立関数としz=0へ適用、J2=0ならtwo-bodyと一致。

SRPはsimple spherical-area model、P=4.57e-6 N/m²、加速度P C_R A/m。ECI Sun方向は初期chief radialから+45°、力はSunから遠ざかる向き。1 AU一定、cylindrical Earth shadowを実装。600秒の事前無制御checkではE0/Elo/Ehiのshadow samplesは0。held-out truth trialでの日照確認ではない。

出典：[NASA GEONS dynamics model](https://ntrs.nasa.gov/api/citations/20240004259/downloads/GEONSMS_R3_0_NASA-TP-20240004259.pdf)。PDF本体のWeb取得はエラーで、本文の式番号・ページを確認したとは主張しない。使用値・向きは指令指定どおり。

dragはv_atm=omega_E×r、v_rel=v-v_atm、a=-0.5 rho C_D A/m |v_rel|v_rel。rho=1e-12 kg/m³を代表値、3e-13/3e-12を感度値に固定。日時・緯度に対応する実密度ではない。[NASA CCMC NRLMSIS](https://ccmc.gsfc.nasa.gov/models/NRLMSIS~00/)が扱う変動する経験的大気密度モデルを今回は導入していない。

| 機体 | mass kg | SRP area m² | C_R | drag area m² | C_D | C_R A/m m²/kg | C_D A/m m²/kg |
|---|---:|---:|---:|---:|---:|---:|---:|
| target | 500 | 4 | 1.3 | 4 | 2.2 | 0.0104 | 0.0176 |
| chaser | 100 | 5 | 1.5 | 5 | 2.2 | 0.075 | 0.11 |

特定ミッションの仕様ではなく、差分を見るための代表property set。teacher試行前にdepth30 m・cross0・相対速度0で[perturbation_sanity.json](../outputs/phase5b/perturbation_sanity.json)を保存した。

| 項 | target m/s² | chaser m/s² | 差分ノルム m/s² |
|---|---:|---:|---:|
{accel}

J2の絶対値は大きいが近接2機の共通成分が相殺される。物理項を表示目的で増幅していない。

![Physical versus stress acceleration](evidence_phase5b/perturbation_magnitudes.png)

## residual stressの固定定義

物理SRP/dragとは別の**未モデル化差分加速度stress test**。初期chief along-trackであるECI +Y方向、chaserのみ。constant 1e-5/3e-5/5e-5 m/s²、RM3は3e-5を半開区間[120,180)秒でON。RK4境界を分割し、その区間側の力を全stageへ適用して端点での余分な重み付けを防ぐ。強さ・onsetは事前固定。

[10条件matrix](../configs/phase5b/evaluation_matrix.json)をH0/T0/T1/E0/Elo/Ehi/R1/R3/R5/RM3として固定。物理条件とresidualを同じ環境関数のflagで切り替える設計。力学をpolicy性能に合わせて変更していない。

## 物理・積分検証（Gate 1/2）

専用8テスト全pass。ランダム50状態の位置/速度round trip、同状態・同property・無制御で相対状態0、瞬時basisと+x/+y指令、J2一般式/zero、SRP圧力・方向・shadow・共通相殺、drag反対方向/zero、residual量/target除外/ON-OFF/総impulseを確認。

小分離[0.1,-0.1,0.0001,-0.0002]（m,m/s）、無制御60秒のtwo-body−HCW差は位置{phy['small_separation']['position_error_m']:.3e} m、速度{phy['small_separation']['velocity_error_m_s']:.3e} m/s。事前閾値1e-5 m、1e-7 m/sを通過。

RK4=4×0.125秒とDOP853（rtol2.3e-14、atol1e-10、max_step2秒）を600秒比較。選択状態[-22,21,-0.02,0.02]と固定LVLH指令を使い、学習器・held-out trialを使わない。事前閾値は絶対位置1e-4 m、絶対速度1e-7 m/s。

| 数値検証用force設定 | 最大絶対位置差 m | 最大絶対速度差 m/s | 最終相対位置差 m | 最終相対速度差 m/s |
|---|---:|---:|---:|---:|
{references}

誤差は600秒終端で比較し、絶対誤差は2機のうち大きい値。全時刻最大の検証ではない。\n\nこの表のT0/E0/RM3は**積分精度検証**の設定名であり、held-out closed-loop結果ではない。[physics_validation.json](../outputs/phase5b/physics_validation.json)に指令・閾値・数値を保存。

## H0 held-out・state-feedback sanity・未実行条件

H0は8条件を各1回、画像learnerとperfect-state LQRを別々に実行。LQRはnominal HCW state feedback、truth feedforwardなし。公平なsensory baselineとは扱わない。

| condition | image learner | state LQR sanity | 状態 |
|---|---:|---:|---|
| H0 nominal HCW | **0/8** | **8/8** | Gate 5失敗 |
| T0 nonlinear two-body | 未実行 | 未実行 | Gate 6停止 |
| T1 two-body + J2 | 未実行 | 未実行 | Gate 6停止 |
| E0 / Elo / Ehi | 未実行 | 未実行 | Gate 6停止 |
| R1 / R3 / R5 / RM3 | 未実行 | 未実行 | Gate 7停止 |

| trial | 失敗理由 | duration s | 最小goal誤差 m | 最終goal誤差 m | 最終speed m/s |
|---|---|---:|---:|---:|---:|
{failures}

range exit5例、FOV exit3例、衝突0。失敗をtimeout延長、goal/FOV変更、真の状態入力、教師切替で回避していない。

![H0 success](evidence_phase5b/condition_success.png)

## control activity・test_00の失敗診断

[Phase 5A解析コード](../src/flyrendezvous/analysis_phase5a.py)をそのまま再利用。u_appliedと適用前states[k]、0.5秒区間、N+1状態、観測後windows、speed>1e-4 m/sでu·v<0制動、速度直交成分、最大ノルムsqrt(2)×0.005基準の5% duty、連続active間の方向変化を使用。局所LQR指令は診断labelでありlearnerへ適用していない。

| H0平均（8本） | learner | state LQR |
|---|---:|---:|
| total Δv m/s | {means['learner']['mean_total_dv_m_s']:.6f} | {means['teacher']['mean_total_dv_m_s']:.6f} |
| perpendicular fraction | {means['learner']['mean_perpendicular_fraction']:.4f} | {means['teacher']['mean_perpendicular_fraction']:.4f} |
| ≥45° changes | {means['learner']['mean_direction_changes_45']:.3f} | {means['teacher']['mean_direction_changes_45']:.3f} |
| active duty 5% | {means['learner']['mean_active_duty_5pct']:.4f} | {means['teacher']['mean_active_duty_5pct']:.4f} |

![Control activity](evidence_phase5b/control_activity_comparison.png)

main demoは事前固定test_00のまま。depth29.665808 m、cross−3.928300 m、初期状態[-18.199167,23.754622,0.000958,-0.018031]。初期球直径約{2*diag['test00_initial_projection'][2]:.3f} px。成功例への差し替えなし。

- 最小goal誤差**{main['min_goal_error_m']:.6f} m（228.5秒）**。位置閾値0.25 mには一度も入らない。
- 教師が成功する258秒までの共通区間で位置差1 m未満。その後learnerは離脱し、**456.5秒でFOV exit**。
- 最終誤差{main['final_goal_error_m']:.6f} m、speed{main['final_speed_mps']:.6f} m/s。
- Δv={main['total_dv_mps']:.6f} m/s、post-first25% Δv={main['post_first25_dv_fraction']:.2%}、middle-half={main['middle_half_dv_fraction']:.2%}。
- 制動Δv={main['braking_dv_fraction']:.2%}、perpendicular={main['perpendicular_dv_fraction']:.2%}、active5%={main['active_duty_5pct']:.2%}。
- ≥45°変化{main['direction_changes_45deg']}回、≥90°変化{main['direction_changes_90deg']}回。観測後の各軸飽和を含む区間{m['saturation_fraction']:.2%}。
- learner状態でのLQR labelに対する制御RMSE={m['acceleration_rmse_m_s2']:.6f} m/s²。教師軌道上の小MSEとは異なる。

![Nominal diagnosis](evidence_phase5b/nominal_failure_diagnosis.png)

初期接近は教師に近い一方、終端収束とその後の安定性が成立していない。最大{diag['test00_max_fraction_of_features_outside_train_marginal_range']:.2%}の特徴がtrain教師データの各特徴のmin/maxを外れたが、記述的な分布逸脱であり原因の証明ではない。

**物理摂動への有効な中間修正が増えた結果とは解釈できない。** T0−H0、E0−T0、RM3−E0、120–180秒のpaired外乱前後比較は未実行。H0の90–180秒を外乱応答に読み替えていない。

## Demo GUI・実スクリーンショット・動画

Phase 4CのOrbit、36形態Brain、Sensor、T2/T4a/T5d maps、C2 Pilot、5型bars、compact statusのblueprint文字列とPilot/IK/カメラ/指令尺度が不変であることを照合。追加表示はTruth conditionとDisturbance OFF/ONのみ。Orbitの自動framingは記録軌道に従う既存動作で、sensor boresightを変更するgazeではない。

型relative scaleはPhase 5Bの48本train+validation control periodsから同じ方法で固定し、testでは変更していない。形態色は同型モデル集約応答であり、実測細胞への1対1対応や枝内伝播ではない。Pilotはbiological motor outputではなくpresentation layer、command scaleの誇張なし。

**H0失敗Demoだけ**を生成し、E0/RM3のRRD・動画はない。[test00_H0.mp4](../outputs/phase5b/mp4/test00_H0.mp4)は{video['duration_s']:.3f}秒、30fps、{video['frames']} frames、1600×1000、物理時間15倍。153枚のnative Rerun captureを次captureまで保持し、補間・架空活動なし。最後の表示sample456.0秒、最後の状態・失敗判定456.5秒。

native Rerunのseek/play/pauseと終端保持を確認。153 capture＋5選択frame＋終端frame＋連続再生frameを保存。MP4は全frame復号、PTS連続・time base1/30・元PNGとの最低PSNR{video['psnr_min_db']:.2f} dBを検証した。software headless rendererによる実RRD描画であり、Windows GUIマウス操作の検証ではない。

20秒の実frame（早期接近、最終結果はFOV exit）：

![Actual Rerun early](evidence_phase5b/H0/demo_early.png)

456秒の実frame（失敗直前の最後の表示sample、hold成功ではない）：

![Actual Rerun last sample](evidence_phase5b/H0/demo_terminal.png)

![H0 trajectory and command](evidence_phase5b/test00_condition_comparison.png)

上図はH0のみ。ファイル名にcomparisonを含むが、未実行E0/RM3を描いた図ではない。必須Figureのうちhcw_vs_twobody.pngとtest00_midcourse_correction.pngは必要なtruth closed-loopデータがないため作成していない。perturbation_magnitudesは事前代表状態のsanity値。

## テスト・回帰・未解決項目

| 検証 | 結果 |
|---|---|
| Phase 5B physics unit | 8 passed |
| 全既存＋追加non-integration | **169 passed、2 deselected** |
| 既存実GPU integration | **1 passed、1 failed、169 deselected** |
| 失敗prefix test単独再確認 | **1 failed** |
| 座標・HCW近似・DOP853精度gate | passed |
| 保存ログ監査 | 192本、神経samples {reg['neural_samples_checked']:,} passed |
| 旧成果SHA | 3,285ファイル不変、README/projectの2ファイルは追記のみ |
| Phase 4C GUI component回帰 | passed（出力先をPhase 5Bへ変更） |
| Phase 5B blueprint/Pilot/IK照合 | passed |
| H0 native playback / MP4復号 | passed |
| truth held-out end-to-end | **未実行** |

既存test_phase2_real_images_policy_prefix_and_weight_freezeは、同一画像prefixのraw出力がatol2e-7/rtol2e-5を超えて異なり、初回の違反最大差7.09e-7、単独再確認1.14e-6 m/s²。閾値・旧コードを変更せず[初回](../outputs/phase5b/integration_tests.log)と[再確認](../outputs/phase5b/integration_prefix_recheck.log)を保存。旧実GPU stateful testはpass。

**GPU数値再現性の原因は未確定で、回帰テスト全合格とは報告しない。** パラメータSHA一致はbitwise結果一致を保証しない。このfailだけでH0の大きな閉ループ破綻の原因は断定できない。[regression.json](../outputs/phase5b/regression.json)のpassは保存物/source監査であり、GPU prefix testのpassを意味しない。

Phase 3 approach8/8・near2/4、旧readout/HCW/camera/RRD/video、Phase 5A解析物・報告を変更していない。

## 保存物・再生／検証コマンド

保存先：configs/phase5b、models/phase5b、outputs/phase5b、docs/evidence_phase5b。[manifest](../outputs/phase5b/manifest.json)に入力・コード・出力SHA、gate状態、未実行条件を記録。

- [evaluation CSV](../outputs/phase5b/evaluation.csv)／[JSON](../outputs/phase5b/evaluation.json)：H0 learner8＋teacher8のみ。
- [test00 learner series](../outputs/phase5b/test00_timeseries_H0_learner.csv)／[状態N+1点](../outputs/phase5b/test00_states_H0_learner.csv)。teacherは別ファイル。
- [selection](../outputs/phase5b/readout_selection.json)、[diagnosis](../outputs/phase5b/nominal_failure_diagnosis.json)、[completion](../outputs/phase5b/completion.json)。
- [実capture metadata](evidence_phase5b/H0/screenshots_demo.json)、[動画verification](../outputs/phase5b/mp4/H0_verification.json)。

WSL workspaceで保存済み失敗記録を再生：

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase5b/demo/H0/demo.rrd --bind 127.0.0.1
~~~

保存ログ監査と単体テスト：

~~~bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/verify_phase5b.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest tests -m "not integration" -q
~~~

既存GPU検証（本runは1件fail）：

~~~bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest tests -m integration -q
~~~

実行順：init_phase5b → physics unit → validate_phase5b_physics → teacher_gate_phase5b → run_phase5b data → train → h0。h0はgate失敗で意図したexit code1。physical/residual stageは開始していない。これらを既存runの上書き・再学習・test再実行のコマンドとして使わない。

## 制約・次の判断・終了条件

今回完了したのは条件固定、物理実装・sanity・数値検証、教師ゲート、データ生成、readout選択、H0評価、失敗分析・H0再生資料・回帰監査まで。**Phase 5Bの主問いであるtruth耐性評価と3条件Demoは未達**。

次は新しい承認済みPhaseとsplitでnominal閉ループの成立を優先する。Phase 3で使ったboundedなtrain-only追加ラベル収集をどこまで再利用するかをtest前に決め、GPU prefix再現性も調べる。同じPhase 5B test8本を改良用に再利用しない。教師データへの低MSEだけを基準にせず、nominal validationの安定収束をgateにする。

Phase 5Cのrepresentation比較（raw pixel/hand-crafted/CNN等）は未実装。比較するなら、新規共通split・同じ画像/制御budget・nominal条件を事前登録し、nominal成立後に同一固定truth matrixでpaired評価する候補が妥当。特定方式の優位性はこの結果から判断できない。

**Gate 5停止としてPhase 5Bの結果報告を完了し、ここで停止する。**
"""
    Path('docs/phase5b_report.md').write_text(report,encoding='utf-8')
    write_json(O/'completion.json',dict(status='stopped_at_gate5',objective_fully_achieved=False,
        gates={'1':'passed','2':'passed','3':'passed 56/56','4':'selected; validation 1/12','5':'failed H0 learner 0/8; LQR 8/8','6':'not run','7':'not run'},
        withheld_conditions=['T0','T1','E0','Elo','Ehi','R1','R3','R5','RM3'],withheld_demo=['E0','RM3'],
        missing_required_figures=['hcw_vs_twobody.png','test00_midcourse_correction.png'],main_demo='test_00',
        test_retuning=False,post_test_training=False,old_results_unchanged=True,
        tests={'non_integration_passed':169,'integration_passed':1,'integration_failed':1,'prefix_recheck_failed':1},
        next_phase_started=False))
    print('Wrote gate-stop report')
if __name__=='__main__':main()
