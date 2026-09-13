# Fly-SpaceNav

学習済みのハエ視覚回路モデル **Flyvis** と線形readoutを使い、画像入力による宇宙機の相対接近・停止を試すプロトタイプです。

```text
固定カメラ画像 → 学習済みFlyvis（重み固定）→ 学習した線形readout
       ↑                                      ↓
       └──── 相対運動シミュレーション ← 2D並進加速度

保存ログ → Rerun：軌道 / センサー画像 / 神経応答 / Fly Pilot
```

## 主な機能

- **画像による閉ループ制御**：球形ターゲットへ接近し、離れた目標位置で停止するstandoff rendezvous。軌道面内の相対運動にはHCWモデルを使います。
- **固定Flyvis＋読み出し学習**：45,669個の視覚系モデル細胞を計算し、空間的に集約した応答から並進指令を出します。真の位置・速度は教師・評価に使い、学習制御器には渡しません。
- **同期可視化**：軌道、センサー画像、脳解剖背景、T2/T4a/T5dの実測代表形態、activity bars、retinotopic mapsを表示します。
- **Fly Pilot**：保存された指令に合わせ、説明用の3Dハエ、joystick、前脚の簡易IKを動かします。
- **数値記録と検証**：試行・モデル・設定をPhaseごとに分離し、保存ログ、評価結果、出典・ハッシュを残します。

## セットアップ

動作確認環境は **WSL2 / Ubuntu 24.04、Python 3.12、NVIDIA CUDA GPU** です。推論にはCUDAが必要です。保存済みRRDの再生にはFlyvisの推論は不要ですが、Rerunを表示できるグラフィックス環境が必要です。

リポジトリのルートから、Linux / WSLのシェルで実行します。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip check
```

依存関係はFlyvis 1.2.0、PyTorch 2.7.1（CUDA 12.8版）、Rerun SDK 0.37.1を含みます。資産取得と最小実行の手順は[セットアップ・実行ガイド](docs/getting_started.md)を参照してください。

## Demoを見る

**モデル資産・保存ログ・RRD・動画はGitに含まれません。** 次のコマンドは、生成済み成果物がある環境で使います。cloneと依存インストールだけでは、このDemoファイルは作成されません。

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase5br/demo/H0/demo.rrd --bind 127.0.0.1
```

`outputs/phase5br/mp4/test00_H0.mp4`には短い再生動画があります。RRDと動画は保存済みclosed-loop試行の再生であり、GUI上で新たな制御計算を実行するものではありません。

最新の完了実験（Phase 5B-R）は、25–35 mのnominal HCW条件で、validation 11/12、未使用初期条件のtest 8/8成功でした。これは限定された条件での結果です。nonlinear two-bodyやJ2・SRP・dragを含むheld-out評価は未実施です。[実験報告](docs/phase5br_report.md)に条件・失敗・検証範囲を記録しています。

## 神経表示とPilotの意味

Brain ViewのT2/T4a/T5dは、FlyWireでその型と注釈された**実測由来の代表形態**です。標準のmulti-representative表示では各12本を、元のFAFB14.1座標系で表示します。

- 実測形態とFlyvisモデル細胞との一対一対応はありません。表示された実測細胞自身の活動を示すものでもありません。
- 同型モデル細胞群のbaseline-relative RMSで、形態全体の明るさを同期させます。固定された型内の相対尺度を使い、型間の絶対活動比較には使えません。raw RMSはbarsに残します。
- Retinotopic mapは、各型のモデル細胞が視野のどこに対応し、どう反応したかを示します。枝内の電位伝播やspikeは表示していません。
- 脳背景は部分的な解剖文脈です。灰色は活動未割当を表し、活動ゼロを意味しません。表示する3型以外も含め、Flyvisは全45,669モデル細胞を計算しますが、ハエの全脳モデルではありません。
- **Fly Pilotはpresentation layerです。** biological motor output、筋肉モデル、ハエの身体運動を再現するものではありません。

このプロジェクトは、理想化された固定カメラ・2D並進条件での実験です。実機への搭載性能や従来制御への優位性は検証していません。ROS / MuJoCoとの統合は含みません。

## リポジトリ構成

```text
src/flyrendezvous/  モデルアダプター、力学、readout、記録、viewer
configs/           Phase別の実験・表示設定
scripts/           資産取得、実験、解析、検証、動画出力
tests/             単体・統合テスト
models/            Phase別の確定readout（学習候補はGit除外）
docs/              導入手順、実験報告、出典、開発履歴
assets/            取得したモデル・解剖・表示資産（Git除外）
outputs/           数値ログ・評価・RRD・動画（Git除外）
```

## 開発・検証

テストの実行方法と必要な資産は[実行ガイド](docs/getting_started.md#テスト)、Phase別の仕様・結果は[ドキュメント一覧](docs/README.md)を参照してください。開発時の判断や従来のREADMEは[開発履歴](docs/development_history.md)へ分離しています。

## 出典・ライセンス

Flyvisの学習済みモデル、FlyWireの形態、脳領域メッシュは外部研究資産です。取得元・バージョン・SHA-256・利用条件は[資産manifest](docs/assets_manifest.json)と[形態対応表](docs/anatomy_mapping_phase3w.json)に記録しています。外部資産の利用条件はそれぞれの配布元に従います。

本リポジトリ独自コードのライセンスを指定する`LICENSE`ファイルは、現時点では配置されていません。
