# セットアップ・実行ガイド

[READMEへ戻る](../README.md)

以下はLinux / WSLのシェルで、リポジトリのルートから実行する手順です。保存済み成果物の再生、最小の神経応答実験、閉ループ実験を分けて説明します。

## 環境

確認済み環境はWSL Ubuntu 24.04、Python 3.12.3、NVIDIA RTX 5070 Tiです。依存バージョンは[requirements.lock](../requirements.lock)、Pythonの対応範囲は[pyproject.toml](../pyproject.toml)で固定しています。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
```

既存の専用`.venv`がある場合はそれを再利用できます。`venv`作成時に`ensurepip`がない環境では、Python 3.12のvenv機能が利用できる環境を用意してください。過去の環境固有のbootstrap手順は[旧README](development_history.md)に残しています。

推論経路はCUDA必須で、CPUへ自動代替しません。RerunのRRD再生・保存ログからのviewer生成はFlyvis推論と独立しています。GUIにはWSLgなどの表示環境が必要です。

## 最小の神経応答実験

初回の取得にはネットワーク接続が必要です。次のスクリプトは公式Flyvisモデルbundleと脳領域メッシュarchiveを取得し、モデル`flow/0000/000`を展開します。取得済みcacheはハッシュを確認して再利用します。

```bash
.venv/bin/python scripts/fetch_assets.py
```

取得先は`assets/`、出典・SHA-256の記録先は`docs/assets_manifest.json`です。このコマンドだけで後期DemoのFlyWire形態やPilot資産がすべて揃うわけではありません。

まず静止・左右移動・拡大の4刺激に対する実モデル応答を計算します。下記は新しい保存先`outputs/quickstart`を使い、既存Phaseの成果物と分離します。同名の保存先を再使用すると、その中の記録を更新します。

```bash
.venv/bin/python -m flyrendezvous.run --config configs/phase1.json --output outputs/quickstart
.venv/bin/python -m flyrendezvous.viewer --input outputs/quickstart --output outputs/quickstart/demo.rrd
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/quickstart/demo.rrd --bind 127.0.0.1
```

この最小例はPhase 1の神経応答確認用です。ランデブー制御や3型の代表形態、Fly Pilotは含みません。NPZに画像・細胞別活動・基準値・時刻を保存し、`validation.json`で実行完了と数値検証結果を確認できます。viewerは検証済み記録からRRDを生成します。

## 保存済みランデブーDemo

現在の主DemoはPhase 5B-Rの`test_00`（H0 / nominal HCW）です。対応するRRDがある環境で実行してください。

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase5br/demo/H0/demo.rrd --bind 127.0.0.1
```

- RRD：`outputs/phase5br/demo/H0/demo.rrd`
- 動画：`outputs/phase5br/mp4/test00_H0.mp4`
- 結果と再現手順：[Phase 5B-R報告](phase5br_report.md)

再生は保存された画像・応答・指令・軌道を表示します。Flyvis推論、readout学習、制御シミュレーションを再実行しません。Rerunのタイムラインで停止・移動でき、表示速度はシミュレーションの物理時間や神経モデルの時間とは別です。

## 閉ループ実験の再現

閉ループ実験はPhase別に設定、split、モデル選択、成功条件、実行gateを固定しています。一般的な単一の`train`コマンドではなく、各報告書の手順で再現します。

| 内容 | 手順・結果 |
|---|---|
| 画像入力からのHCW制御の基礎 | [Phase 2](phase2_report.md) |
| 球形ターゲットと斜め方向のstandoff | [Phase 3](phase3_report.md) |
| 25–35 m条件と物理摂動評価基盤 | [Phase 5B](phase5b_report.md) |
| train-only追加ラベルによるnominal回復 | [Phase 5B-R](phase5br_report.md) |

実験用スクリプトには既存ファイルの存在やハッシュを前提にするものがあります。単なるDemo再生のために実験初期化・学習スクリプトを実行する必要はありません。旧test結果を新しい学習や選択へ流用せず、新規実験は保存先とsplitを分離します。

## テスト

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest tests -m "not integration"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest tests -m integration
```

`not integration`はCUDA統合テストを除く指定です。一部のテストは既存の取得資産・Phase別保存ログを参照するため、コードだけのcloneでは全件を実行できません。`integration`には公式checkpointとCUDAが必要です。skipは実モデル検証の成功を意味しません。

数値照合・RRD照合などのPhase専用検証は[各報告書](README.md)を参照してください。Phase 5B-R時点では非GPUテスト180件が通過し、GPU prefix比較には既知の微小差による失敗が記録されています。詳細な条件と許容値は報告書に残しています。

過去の成果保護スクリプトには当時のREADMEのハッシュや追記形式を検査するものがあります。今回のREADME再編は文書の意図的な更新です。過去の検証結果や基準ハッシュを書き換えて、再検証済みと扱うことはしていません。

## 動画出力用のローカルツール

動画exportスクリプトは`.tools/video/python`に導入した`imageio-ffmpeg`を使います。FFmpeg実行ファイルとwheelはGitに含めず、必要な環境で再取得します。

```bash
.venv/bin/python -m pip install --no-deps --target .tools/video/python imageio-ffmpeg==0.6.0
```

取得にはネットワーク接続が必要です。既に導入済みなら再インストールは不要です。動画生成には、対応するPhaseの保存ログやcaptureなどの成果物も必要です。
