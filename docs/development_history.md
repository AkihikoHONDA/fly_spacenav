# 旧README・開発履歴

2026-09-14のREADME再編に伴い、従来の内容をここへ移しました。本文は当時の記録であり、Phaseごとの「最新」「今回」「次の判断」は現在の仕様を表すものではありません。リンクの相対位置だけを移動先に合わせて変更しています。コマンドはリポジトリのルートでの実行を前提とします。

現在の入口は[README](../README.md)、報告書一覧は[ドキュメント一覧](README.md)を参照してください。

---

# FlyRendezvous — Phase 3W 発表用Demo

主Demoは**T2/T4a/T5dを各12本、計36本の実測形態として表示するMode B**です。左右視葉と中央を含むneuropil contextの中で、保存済みモデル応答に応じて型ごとの明るさが変わります。

[実画面](../docs/evidence_phase3w/multi_hold.png) ／ [約14.6秒MP4](../outputs/phase3w/mp4/phase3w_test00.mp4) ／ [報告・3モード比較・再検証](../docs/phase3w_report.md)

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3w/multi.rrd --new --bind 127.0.0.1
~~~

20秒・85秒・219秒を比較してください。詳細はoutputs/phase3w/analysis.rrdの全体図と右視葉接写。各1本のMode Aはoutputs/phase3w/representative.rrd、T2全725本のMode Cは既存outputs/phase3p/t2_population.rrdを保持しています。

- 3D形態は、公式FlyWireでexact T2/T4a/T5d・rightと注釈された実測細胞です。既存代表1本＋固定seedの11本を型ごとに選び、元FAFB14.1座標で表示します。
- **同じtype内の12形態は、Flyvisの同型モデル群から得た同じaggregate RMS/qで同期着色します。** 各実測細胞自身のactivityでも、Flyvis細胞との一対一対応でもありません。
- qは型内の固定relative尺度で、型間の絶対activity比較には使えません。raw RMSはbar、細胞別の視野内応答はretinotopic mapに残します。枝内電位・伝播・spikeを描いていません。
- 背景は既存archiveの全78領域を使う**部分的なbrain / neuropil anatomy context**。灰色は活動ゼロを意味しません。完全な全脳細胞表示、ハエ頭部・外骨格・複眼モデルではありません。
- Flyvisの計算対象は全45,669モデル細胞です。今回は保存ログの再生だけで、新推論・学習・制御実験はありません。

制御・readout・HCW・完全固定sensor camera・Phase 3 test結果（approach8/8、near2/4）は不変。非GPUテスト121件、全777時点のRRD照合、旧2,431成果のSHA保持を確認しました。native撮影はMode B約0.52秒／枚（A約0.14秒、C約2.44秒）。Windows GUI実時間性能は未検証です。[全36形態・78meshの出典とSHA](../docs/anatomy_mapping_phase3w.json)。

---

以下はPhase 3P以前の説明・判断を当時の記録としてそのまま保持しています。

# FlyRendezvous — Phase 3P 表示比較

**T2の実測population全725本と、従来の代表1本表示を比較できます。** [比較報告・実画面・性能](../docs/phase3p_report.md) ／ [population動画](../outputs/phase3p/mp4/phase3p_test00.mp4)。

SpaceROS勉強会の主デモには軽く説明しやすい**representative mode**を推奨し、populationは解剖分布を示す補助表示として残します。

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3p/representative.rrd --new --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3p/t2_population.rrd --new --bind 127.0.0.1
~~~

T2 population viewは、固定版FlyWireでexact T2・rightと注釈された**全725実測形態**を、元FAFB14.1座標のまま表示します。Flyvisの**T2モデル群721細胞**とは別の集合です。一対一対応はなく、725形態すべてを同じtype-level aggregate RMS/qで着色します。個々の実測T2自身の活動や枝内伝播ではありません。型内固定relative尺度で、型間の絶対activity比較には使えません。raw RMSはbar、細胞別の視野内分布はretinotopic mapに残します。

T4a/T5dは既存代表1本ずつ。全枝保持のためpopulationは描画が重く、Windows GUI実時間性能は未検証です。制御・readout・HCW・完全固定sensor camera・Phase 3 test結果（approach 8/8、near 2/4）は不変。Flyvis計算対象は全45,669モデル細胞で、今回は保存ログ再生のみです。[全形態のID・出典・SHA・利用条件](../docs/anatomy_mapping_phase3p.json)。

---

以下のPhase 3V以前の説明・結果は当時の記録としてそのまま保持しています。

# FlyRendezvous — Phase 3V Demo

SpaceROS勉強会向けの最新版は**Phase 3V**です。大きな軌道表示とBrain Viewで、T2・T4a・T5dの実測代表形態が保存済みモデル応答に応じて明るさを変える様子を確認できます。

[実Demo画面](../docs/evidence_phase3v/demo_hold.png) ／ [約14.6秒のMP4](../outputs/phase3v/mp4/phase3v_test00.mp4) ／ [Phase 3V報告・出典・検証](../docs/phase3v_report.md)

WSLのプロジェクトルートから：

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3v/phase3v_demo.rrd --new --bind 127.0.0.1
~~~

詳細な5型map・raw/q・制御グラフはoutputs/phase3v/phase3v_analysis.rrdを同じ方法で開きます。成功approachの20秒・85秒・219秒を比較してください。旧Phase 3では最後のRESETで形態が消える問題を再現しました。3Vでは試行間RESETを残し、最後の観測を保持します。旧版RRDは履歴として残しています。

**T2・T4a・T5dは、実際にそのexact cell typeとして公式注釈された、EM再構成由来の実測代表形態を各1個表示しています。** T2/T5dを各1本追加取得し、T4aは既存を再利用。FAFB14.1座標でnm→µmのみを適用しています。

表示の意味：

- Flyvisモデル細胞との一対一対応はありません。
- 表示した実測細胞自身のactivityではありません。
- 同型721モデル細胞のbaseline-relative RMS集約応答で形態全体を同じ色にしています。
- branch内電位や活動伝播を表示しているわけではありません。
- Flyvisは表示3型だけでなく**全45,669 model cells**を計算しています。

Brain Viewは「どのtypeのモデル群が反応しているか」を実測形態と解剖背景で示し、retinotopic mapは「その型内部で、視野のどの場所に対応するモデル細胞がどう反応したか」を示します。Tm3/L2はbarとAnalysisのmapに残します。

orange=T2、blue=T4a、magenta=T5dは識別用で、生物学的意味はありません。q=clip((RMS−p05)/(p95−p05),0,1)は**そのtype自身の通常範囲内の相対応答**。p05/p95はPhase 3 train+validation制御期間からtest前に固定した値です。型間の絶対活動比較には使いません。raw RMSをbarに併記し、q=0でも形が見える35%の表示明るさ下限を設けています。これは活動を足したものではありません。

制御器・readout・HCW・完全固定sensor camera・target/goal・test結果は不変。Phase 3は**接近8/8、near2/4成功**のままで、near失敗へ調整していません。単体106件、両RRD各777フレーム、実再生・動画、旧1,297成果の不変性を確認しました。新しい推論・制御実験は0です。

取得元・ライセンスと推奨引用は[形態来歴](../docs/anatomy_mapping_phase3v.json)と[報告書](../docs/phase3v_report.md)を参照してください。

---

以下は旧Phaseの結果・再現手順です。過去の未達記録を含め保持しています。

# FlyRendezvous — Phase 1 / Phase 1B / Phase 2

## Phase 2：画像からのHCW閉ループ

Phase 2A〜2Dを実装・実行しました。固定testでは教師LQRが12/12、**固定Flyvis＋線形読み出しが接近8/8・近傍4/4**で接近・減速・10秒保持に成功しました。既知サイズ円板・固定カメラ・限定初期条件でのデモであり、真の状態や教師による救済を学習器に使っていません。

[Phase 2報告・全試行結果](../docs/phase2_report.md) ／ [比較図](../docs/evidence_phase2/evaluation.png) ／ [実Rerun画面](../docs/evidence_phase2/braking.png)

WSLのプロジェクトルートから保存済み結果を開く：

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase2/phase2.rrd --bind 127.0.0.1
```

初期停止、再生20倍。20秒の接近加速、95.5秒の減速、210.5秒の保持直前を比較してください。実際の機体位置・速度・飽和後加速度、センサー画像、神経活動を同期表示します。軌道mと解剖µmは別ビュー。矢印の表示長は速度×20秒、加速度×400秒²です。

**FlyvisはT4aだけでなく、今回の構成では45,669個の視覚系モデル細胞を計算する。3D表示しているT4a形態は、別途取得した実測1細胞の形である。色はその実測細胞自身の活動ではなく、同型の721モデル細胞の電位変化を集約した値である。個別細胞の位置対応や枝内の電位伝播は計算していない。表示対象の細胞型は、計算対象や制御への読み出し対象とは別の選択である。**

代表表示を当面採用し、Phase 2保留は解除済みです。最終表示typeは後から判断し、今回は追加形態取得をしていません。過去の個別対応未達の記録は保持しています。

物理dt=0.5秒、神経dt=0.01秒、尺度比50は神経モデルへの画像時系列の再尺度化で、再生倍率20とは別です。灰色1秒reset後、物理10秒をu=0のHCW運動で観測してから制御します。撮像後の計算・通信遅延はゼロという理想化です。

元testと再生用再実行は成功判定が一致しましたが、最大約3.2 mmの位置成分差、0.5秒の終了時刻差があり、厳密再現は未達です。RRDは再実行自身の画像・活動・指令を使い、元test結果は別に保持します。native headlessの実描画・再生・停止・時刻移動は検証済み、Windows GUIのマウス操作は未検証です。

```bash
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python -m pytest tests -m 'not integration'
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 .venv/bin/python -m pytest tests -m integration
OPENBLAS_NUM_THREADS=4 .venv/bin/python scripts/verify_phase2.py
.venv/bin/python -m flyrendezvous.viewer_phase2
.venv/bin/python scripts/capture_phase2.py
.venv/bin/python scripts/verify_phase2_rrd.py
```

単体53件・実GPU統合2件が通過しました。実験全体の再現は[報告書](../docs/phase2_report.md)のコマンドで新しい出力先を指定します。既存venvの再構築や依存の追加は不要です。

---

**以下はPhase 1／1Bの記録と再現手順です。**


## Phase 1B：T4aの1代表形態と実応答

T4aの721モデル細胞の応答RMSで、公式注釈付きの実測形態1細胞（FlyWire 783、ID `720575940605852192`）の枝全体の色を変える試作を追加しました。形態と背景はFAFB14.1で整合しています。**同型の代表表示で、モデル細胞との個別位置対応や枝内電位分布はありません。** 既存Phase 1の成果は保存しています。

[Phase 1B報告](../docs/phase1b_report.md) ／ [対応表・出典](../docs/anatomy_mapping_phase1b.json) ／ 実Rerun画面：[RMS 0.07828](../docs/evidence_phase1b/low.png)・[RMS 0.16625](../docs/evidence_phase1b/high.png)

既存環境のWSLプロジェクトルートで、保存済み結果を開く：

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase1b/phase1b.rrd --bind 127.0.0.1
```

初期は停止、再生倍率0.5倍。下部の再生／停止とタイムラインを使い、表示2.36秒・3.66秒で、中央の枝全体の色とRMSグラフのカーソル、左の入力・光受容器・符号付き格子、右の数値を確認してください。右欄には局所input_timeとresponse_timeを別々に表示します。独立試行間はRESETの空白が入ります。

ネイティブheadlessの実描画、viewer-mcpによる再生・停止・時刻移動を検証済みです。Windows GUIのマウス操作は未検証です。別ビューアや新規インストールは不要です。

保存済み応答から再生成する手順：

```bash
.venv/bin/python scripts/fetch_morphology.py
.venv/bin/python -m flyrendezvous.phase1b --include-extended
.venv/bin/python -m flyrendezvous.viewer_phase1b
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun rrd verify outputs/phase1b/phase1b.rrd
.venv/bin/python scripts/verify_phase1b.py
.venv/bin/python scripts/capture_phase1b.py
.venv/bin/python -m pytest tests -m 'not integration'
.venv/bin/python -m pytest tests -m integration
```

追加した2.5秒系列を実推論し直す場合のみ、集約前に `.venv/bin/python -m flyrendezvous.sequence_phase1b` を実行します。これはPhase 1Bの系列記録を更新するため、その後のRRDと画面証拠も再生成してください。通常の再生には推論は不要です。数値・設定・検証は `outputs/phase1b`、実画像は `docs/evidence_phase1b` にあります。単体45件・実モデル統合1件が通過し、実RRDの全346サンプルを元NPZと照合しました。

---

**以下はPhase 1の記録と再現手順です。**


公式の学習済みFlyvis **1モデル**へ4種類の画像刺激を与え、細胞別応答と公開脳形状をRerunで同期再生する試作です。今回の脳形状は静的表示です。**解剖形状への活動投影は未達**で、制御・学習・HCWは実装していません。

結果：[Phase 1報告](../docs/phase1_report.md) ／ [仕様と将来仮説](../docs/project.md) ／ [実描画](../docs/evidence/screenshot.png)。

## 環境構築（WSL Ubuntu、プロジェクトルート）
検証環境はPython 3.12.3、RTX 5070 Ti、Windows NVIDIA driver 595.79、PyTorch 2.7.1+cu128です。WSLへLinux用NVIDIAドライバーを追加しません。

既存の `.venv` があれば以下の作成・インストールを繰り返す必要はありません。標準ensurepipがない環境でもシステム変更をせず作れる手順です。

```bash
cd /home/jaxa/Workspace/fly_spacenav
python3 -m venv --without-pip .venv
mkdir -p assets/sources
test -f assets/sources/get-pip.py || curl -fL https://bootstrap.pypa.io/get-pip.py -o assets/sources/get-pip.py
.venv/bin/python assets/sources/get-pip.py pip==26.2.1
.venv/bin/python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
```

CUDA wheelと付属ライブラリは数GBです。モデル自体は小さいです。`requirements.lock` に動作確認済みの全依存を固定し、CUDA取得indexも保存しています。

## 公式モデル・解剖資産の取得
```bash
.venv/bin/python scripts/fetch_assets.py
```

公式モデルZIP（3,417,042 bytes）を公式SHA-256で検証し、`flow/0000/000` のみ展開します。50モデルを実行しません。約1.1MBのメッシュZIPからME/LO/LOPの左右とFB/EBの8領域だけ展開します。訓練動画や全ニューロン形態は取得しません。再実行ではローカルZIPを再利用し、不要な再ダウンロードをしません。

資産の取得元、版、ハッシュ、利用条件は `docs/assets_manifest.json`。取得スクリプトは公式Flyvisダウンローダーに同梱された公開配布設定を使用し、利用者の鍵を探しません。

## 最小実行・検証
```bash
.venv/bin/python -m pytest tests -m 'not integration' -q
.venv/bin/python -m flyrendezvous.run --config configs/phase1.json --output outputs/phase1
.venv/bin/python -m pytest tests -m integration -q
.venv/bin/python -m flyrendezvous.viewer --input outputs/phase1 --output outputs/phase1/phase1.rrd
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun rrd verify outputs/phase1/phase1.rrd
```

設定：64×64、24フレーム×4刺激、dt=0.01秒、reset時に灰色入力1秒、4フレームずつ状態を引き継ぎます。初めに公式random_walk_of_blocksの8フレームで動作を確認します。推論はGUI不要です。CUDAが利用できなければ明示的に失敗し、CPU結果をGPU成功と扱いません。統合テストのskipは成功ではありません。

## 保存記録の再生
WSLgからネイティブRerunで開く：
```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase1/phase1.rrd --bind 127.0.0.1
```

下部の再生／停止ボタンとタイムラインで再生・移動します。初期再生速度は0.25倍。左に画像・光受容器入力・T4a格子応答、右に静的な解剖形状と説明・凡例を表示します。脳の灰色は「活動未割当」であり「活動ゼロ」ではありません。8領域の形状で、全脳ニューロン再構成ではありません。

WSLではVulkanのllvmpipe描画を確認しました。Windows側で同じログを開く代替手順（**Windows GUIは未検証**）：
```powershell
py -m venv .venv-rerun-viewer
.\.venv-rerun-viewer\Scripts\python -m pip install rerun-sdk==0.37.1
.\.venv-rerun-viewer\Scripts\rerun.exe "\\wsl.localhost\Fly-SpaceNav\home\jaxa\Workspace\fly_spacenav\outputs\phase1\phase1.rrd" --bind 127.0.0.1
```

Rerun自身で実描画スクリーンショットを作成（実行・画像確認済み）：
```bash
RERUN_ANALYTICS_ENABLED=false RUST_LOG=error .venv/bin/rerun outputs/phase1/phase1.rrd \
  --bind 127.0.0.1 --headless --screenshot-to outputs/phase1/screenshot.png --window-size 1600x1000
```

## NumPyからの再読込
```python
import numpy as np
with np.load("outputs/phase1/right.npz", allow_pickle=False) as log:
    print(log["activity"].shape)  # (24, 45669)
    mask = log["cell_type"] == "T4a"
    voltage = log["activity"][:, mask]
    delta_voltage = voltage - log["baseline"][mask]
    print(log["cell_index"][mask], log["u"][mask], log["v"][mask])
```

各NPZにimages、receptor_input、input_time、response_time、activity、baseline、cell_index、cell_type、u/v、receptor_u/v、wall_secondsを保存します。入力画像kと更新後の応答kはdtだけ時刻が異なります。wall_secondsは同期済みチャンク完了時刻で、同一チャンクの各フレームに同じ値を記録します。FlyWire root IDは付与しません。

`cells.csv` にモデル由来のroleも保存します。`validation.json` は実行結果・資産ハッシュ・数値記録ハッシュ・GPU実測を含みます。ビューアは検証未完了・改変済み数値記録を拒否します。詳細は報告書を参照してください。

## Phase 2E：表示方向と細胞型候補（2026-09-11）

軌道表示は **下＝中心天体方向、左＝軌道進行方向**。表示だけを `X=-y, Y=x` へ変換し、Phase 2のモデル・readout・保存結果（接近8/8、近傍4/4成功）を保持しました。

当面、細胞型単位の代表形態表示を採用します。Flyvisは45,669個の視覚回路モデル細胞を計算し、T4aの721細胞の集約応答を実測1細胞の形に表示します。これはその実測細胞自身の活動ではなく、モデル細胞との一対一対応もありません。最終表示型は実ランデブー応答と説明性から後で決め、表示型の選択と制御器の計算・学習対象を区別します。

65型を比較し、次の形態取得案はT2・Tm3・T5d。T4aは維持し、追加取得は行っていません。[Phase 2E報告・候補比較図](../docs/phase2e_report.md)に判断材料をまとめました。単体68件と保存結果監査は通過しましたが、既存GPU統合テストのprefix再現比較1件は2回とも許容差超過で未解決です。

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase2e/phase2e.rrd --bind 127.0.0.1
```

## Phase 2F：5型の神経活動を動画で比較（2026-09-11）

既存ログのT2/Tm3/T4a/T5d/L2を、型全体のrelative activity barと細胞別retinotopic mapで同時比較できます。T4aの同じ1形態を、従来のabsolute尺度と固定p05–p95 relative尺度で比較しました。[報告・判断材料](../docs/phase2f_report.md)／[14.066秒の実描画アニメーション](../outputs/phase2f/phase2f_test00.webp)。

3D形態色は同型モデル群の集約値で、実測細胞との一対一対応やその細胞自身の活動ではありません。relative尺度は表示専用で型間の絶対活動比較には使えず、q=0でもraw活動は非ゼロになり得ます。mapはモデル内の細胞別活動・正負・空間配置を保持するため、型aggregateより情報量があります。

T4aへの固定relative尺度とbar/mapの継続を推奨します。追加3D形態を選ぶならまずT2、Tm3/L2はbar/map優先、T5dは説明目的次第です。最終3D表示型と尺度はこの結果を見てユーザーが決定します。追加取得・再学習・新条件試験は行っていません。単体84件と表示照合は通過、既知GPU prefix比較1件は従来閾値のまま失敗しています。

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase2f/phase2f.rrd --bind 127.0.0.1
```

Phase 2F追加対応：ユーザー承認後にffmpegをプロジェクト内へ導入し、[約14秒のMP4](../outputs/phase2f/mp4/phase2f_test00.mp4)も作成・全フレーム検証しました。再生成は `.venv/bin/python scripts/export_phase2f_mp4.py`。元の学習環境・RRD・活動データは保持しています。


## Phase 3：球への斜め接近とstandoff（2026-09-11）

固定カメラ画像→固定Flyvis→線形readoutで、半径1 m球の中心から5 mの斜め下側goalへ接近した。held-outは**接近8/8・near2/4、合計10/12成功**。nearの失敗はFOV外1・timeout1、衝突0。教師12/12、旧readout zero-shot0/4。test後の調整・教師救済はない。

[Phase 3報告](../docs/phase3_report.md) ／ [Demo実画面](../docs/evidence_phase3/demo_hold.png) ／ [実描画動画](../outputs/phase3/phase3_test00.webp)

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3/phase3_demo.rrd --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3/phase3_analysis.rrd --bind 127.0.0.1
~~~

Demoは大きな軌道・sensor・target/standoff circle/goal・T4aと脳背景・5型bar・T2/T4a/T5d map・statusを同時表示。Analysisは全5型map、raw/q、制御指標、absolute/relative比較。元testを再推論せず同じ記録から再生する。

T4aは同じ実測1形態を721モデル細胞の型全体RMSで着色する代表表示で、個別対応や枝内伝播ではない。relative尺度はPhase 3のtrain/validationだけでtest前に固定した。raw値を残し、型間の絶対活動比較に使わない。計算対象45,669細胞と表示選択は別。球の円形近似と教師Qの座標系変更は報告に明記した。

単体96/96、保存155試行と両RRD各777フレームの監査が通過。旧成果681ファイルは不変。既存GPU統合は1/2失敗（既知prefix再現性、閾値不変）。新成果はoutputs/phase3に分離した。


## Phase 4A: Fly Pilot View

Phase 4A adds an explanatory 3D fly and joystick beside the saved Phase 3 learner playback. Launch from the WSL project directory:

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4a/demo.rrd --bind 127.0.0.1
# Detailed neural graphs and a larger Pilot panel:
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4a/analysis.rrd --bind 127.0.0.1
~~~

This is a **presentation layer, not biological motor output**. The external house-fly model is an illustration, not a measured FlyWire morphology or a validated Drosophila motor model. Its pose is fixed. Only the procedural joystick follows the recorded learned **applied** 2D translational acceleration; there is no foreleg tracking, wing animation, flight mechanics, joint control, or muscle simulation.

Pilot and Orbit use the same source `u_applied`. In Cartesian display axes, `a_disp = [-a_y, a_x]`; left means positive along-track, down means toward the central body. The joystick uses per-axis `clip(a_disp / 0.005, -1, 1)`, with a fixed shaft length. This normalization only sets display travel and does not alter commands. Numeric values are in m/s². The Pilot camera is fixed overhead to preserve screen direction. The sensor camera, HCW, trained readout, original records, and Phase 3 results (approach 8/8, near 2/4) remain fixed.

The 36 measured T2/T4a/T5d neural morphologies and their within-type activity coloring retain the meanings and limits described above. They are separate from the illustrative fly body.

Fly asset: **Low Poly House Fly (Diptera)** by **Glowbox 3D**, [original Sketchfab model](https://sketchfab.com/3d-models/low-poly-house-fly-diptera-2baa84955f704a4091a274ef4acec24a), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source also carries a NoAI notice; it is used here solely for deterministic 3D presentation, not generative-AI training or asset generation. Original binaries, redistribution provenance, conversion changes, and SHA-256 values are recorded in [assets/fly_pilot](../assets/fly_pilot/). CadNav was attempted first; the specified Sketchfab fallback is used.

[Phase 4A report](../docs/phase4a_report.md) contains the actual screenshots, playback tests and limitations. [Demo MP4](../outputs/phase4a/mp4/phase4a_test00.mp4) is a short export of real Rerun frames, with frames held between captures; no command or neural activity is interpolated.


## Phase 4B：stylized Fly Pilotと前脚IK

[報告・実画面](../docs/phase4b_report.md) ／ [A/B/C比較](../docs/evidence_phase4b/design_comparison.png) ／ [Phase 4Aとの比較](../docs/evidence_phase4b/phase4a_vs_phase4b.png) ／ [14.63秒のDemo MP4](../outputs/phase4b/mp4/phase4b_test00.mp4)

Blender Pythonのprimitiveから生成した説明用stylized modelを表示します。既定はVariant B。実測のハエ解剖模型ではありません。左右前脚は操縦桿のtargetを追う**illustrative IK**で、Flyvis由来の脚関節出力、motor neuron、muscle、身体・接触力学の再現ではありません。

操縦桿の信号はPhase 4Aと同じ保存済みlearned 2D translational commandの **u_applied**。元の指令と時刻を維持し、見た目用の平滑化や架空の動きを加えていません。3/4視点で脚を見せ、小さなCommand XY guideで「左=軌道進行、下=中心天体」の正確な平面方向を併記します。bodyと翼は静止します。

制御・readout・HCW・固定sensor camera・Phase 3 test結果（approach 8/8、near 2/4）は不変です。Phase 4Aの外部モデルと成果は残しています。脳内の実測代表神経形態と、説明用pilot characterを区別してください。

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4b/demo.rrd --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4b/analysis.rrd --bind 127.0.0.1
~~~

生成手順・寸法・SHAは[Phase 4B資産](../assets/fly_pilot_phase4b/README.md)。非GPUテスト144件と実RRD・動画照合が通過しました。前脚の接続と追従は検証済みですが、生物学的運動・衝突回避・発表PC上の実時間FPSを保証するものではありません。


## Phase 4C：semi-stylized Fly Pilot（C2 default）

[結果報告](../docs/phase4c_report.md) ／ [C1/C2/C3比較](../docs/evidence_phase4c/design_comparison.png) ／ [4A/4B/4C実画面比較](../docs/evidence_phase4c/phase4a_vs_4b_vs_4c.png) ／ [Demo MP4・14.63秒](../outputs/phase4c/mp4/phase4c_test00.mp4)

Phase 4Cは造形を改善した **semi-stylized presentation model** です。頭部の縮小・扁平化、横から前へ重なる赤い楕円形の目、胸部と先細り腹部、薄い翅、細い脚をprocedural生成しました。参考画像は体型の方向性にのみ使用し、モデル再構成・トレース・テクスチャ抽出はしていません。

**actual fly anatomyではありません。** 前脚はPhase 4Bと同じ **illustrative IK** で、motor-neuron / muscle model、物理的な接触や生物学的運動の再現ではありません。command sourceは保存済みの同じlearned **u_applied**。joystick同期、0.62/0.62リンク、肩位置、固定sensor camera、Pilot camera、Rerunレイアウト、制御・readout・HCW・Phase 3 test結果（approach 8/8、near 2/4）は維持しています。脳内の実測神経形態とpilotの説明用ボディを区別してください。

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4c/demo.rrd --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4c/analysis.rrd --bind 127.0.0.1
~~~

[資産・再生成手順](../assets/fly_pilot_phase4c/README.md)。non-GPUテスト150件が通過し、全777サンプルの実Rerun描画・IKと1,554脚先を照合しました。4A/4Bは比較用として保持しています。MP4は15倍速・実Rerunの74枚を次のcaptureまで保持する短縮動画です。細かな眼の回り込みや遠側脚には小パネルでの見えづらさが残ります。

## Phase 5B：25–35 m HCW学習とtruth評価基盤（Gate 5停止）

Phase 5Bは新しい25–35 m nominal HCWデータで、Flyvisを固定しreadoutのみ学習した。policy inputはimage only。教師56/56、データ48/48成功に対し、選択readoutはvalidation 1/12、H0 held-out 0/8成功となり、事前固定gateで停止した。H0 state-feedback LQRは8/8成功で、perfect-stateを使うsanity referenceである。

nonlinear two-body・J2・SRP・簡易dragを独立実装し、座標・積分精度・力のsanityを検証した。J2/SRP/dragはphysics terms、residual accelerationは別のstress test。ただしH0失敗のためtruth held-out評価とE0/RM3 Demoは未実行。旧Phase 3〜5Aの結果・制御・GUIは保持した。

[Phase 5B報告書](../docs/phase5b_report.md)に失敗理由、未達範囲、GPU prefixテスト1件の失敗、固定条件と次の判断を記載。[H0 test_00動画](../outputs/phase5b/mp4/test00_H0.mp4)は456.5秒でFOV exitした失敗の再生であり、成功Demoではない。Pilotは既存と同じpresentation layerで、biological motor outputではない。

保存済みH0をWSLで再生：
~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase5b/demo/H0/demo.rrd --bind 127.0.0.1
~~~

## Phase 5B-R：train-only dataset aggregation

fresh split（36/12/8、seed5201/5202/5203）で教師56/56成功後、同じ6候補の線形readoutを最大2roundのtrain-only追加ラベルで学習した。Flyvis・HCW・fixed camera・goal・飽和・成功条件は固定。最終Round 1のvalidationは11/12成功、fresh test 8/8成功。旧5B test8本を学習・選択・回復判定へ再利用していない。truth評価は未実行。

[Phase 5B-R報告](../docs/phase5br_report.md)に各round、sample出典/cap、特徴分布、終端安定化、GPU既知prefix問題、旧成果保護を記録。nominal recoveryを達成したが、truth評価へ自動移行せず停止した。
