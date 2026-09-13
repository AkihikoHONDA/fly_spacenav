# Phase 1実行報告 — 2026-09-10

**公式学習済みFlyvisのCUDA推論・状態保持・数値記録・静的解剖形状と格子応答の同期表示を実行した。脳形状への根拠ある活動投影は未達。** Phase 2の実装は行っていない。

## 達成状況

| 項目 | 判定 | 証拠と限界 |
|---|---|---|
| A 実際の学習済みFlyvisの実行 | **達成** | 公式flow/0000/000をGPUで実行。公式ZIPハッシュ確認、全state_dictの厳密一致確認後に推論。公式最小刺激8フレーム→自作4刺激の順に検証。 |
| B 状態保持と応答記録 | **達成** | reset、1フレームstep、4フレームchunkを実装。全45,669細胞の応答・格子座標・時刻をNPZ保存。一括／分割一致、再現性、重み不変性を確認。 |
| C 脳の解剖形状の表示 | **達成（8領域の実描画）** | 公開FAFB14.1座標メッシュのME/LO/LOP左右とFB/EB。Rerunのheadlessレンダラーで描画し、スクリーンショット内容を確認。全脳の外形・全細胞形態ではない。 |
| D 根拠のある活動投影と同期再生 | **未達（活動投影）／同期表示は達成** | 入力・受容器入力・T4a格子応答を共通時刻で記録・描画。解剖への対応を確定できず、脳は全て中立色。既存Rerunでの自動再生とタイムライン表示は確認。人がGUIを操作する一時停止・時刻移動、Windows側GUIは**未検証**。 |

![Rerunの実レンダリング](evidence/screenshot.png)

この画像は実際にRerunへ保存ログを読み込ませて生成したもので、別の描画ライブラリで合成したモックではない。スクリーンショットでは静止刺激frame 22、入力0.220秒、更新後応答0.230秒が表示されている。推論GPUと描画デバイスは別で、描画はVulkan **llvmpipe CPUソフトウェアレンダラー**だった。対話ウィンドウを人手操作して確認したとは扱わない。

## 環境と依存

- Ubuntu **24.04.5 LTS**、WSL2 kernel 6.6.87.2、Python **3.12.3**。
- GPU **RTX 5070 Ti**、compute capability **12.0**、Windows NVIDIA driver **595.79**（nvidia-smi 595.54）。
- 初期空き容量は約955 GB。開始時の作業フォルダーは空で、Git管理や既存venvはなかった。
- 専用 `.venv`、PyTorch **2.7.1+cu128**、torchvision **0.22.1+cu128**、CUDAビルド **12.8**。
- Flyvis **1.2.0**、Rerun SDK **0.37.1**。全108依存を[requirements.lock](../requirements.lock)に固定。
- `pip check`：**No broken requirements found.**
- 全体の環境情報：[environment.json](evidence/environment.json)。sudo・システムPython変更・Linux NVIDIAドライバー追加・ソースからのPyTorchビルドは行っていない。
- Flyvisの古い `[pretrained]` extraの固定版は採用せず、Python 3.12と現行依存の組み合わせで実推論を検証した。公式配布ライブラリへのパッチはゼロ。
- CUDAの行列積実測：64×64のarange行列×転置、CUDA同期後に全要素finite、要素(0,0)=**85344.0**。GPUの列挙だけを検証扱いにしていない。

## 取得資産

[assets_manifest.json](assets_manifest.json)に全取得モデルファイル・設定・コネクトーム・ZIP・使用メッシュのSHA-256とbytesを保存した。

| 資産 | 内容 |
|---|---|
| 公式モデルZIP | results_pretrained_models.zip、**3,417,042 bytes**。公式配布は50個入りの小さな一括ZIPのためこれを取得し、000だけ展開・実行。UMAP解析ZIP・訓練動画は未取得。 |
| 使用モデル | flow/0000/000、bestチェックポイントが指すchkpts/chkpt_00000。best情報とvalidation lossも同じ公式ZIP由来。 |
| コネクトーム | Flyvis 1.2.0同梱fib25-fib19_v2.2.json、extent=15、n_syn_fill=1、公式モデル設定をそのまま使用。 |
| 解剖形状 | fafbsegのget_neuropil_volumesが読むJFRC2NP.surf.fw.zip、**1,081,524 bytes**。公式Gitコミットd0da95123ee606e204ae2c702e7bc78538646fbdに固定、Git blobも検証。8領域だけ展開。 |

主要ハッシュ：

- モデルZIP：`71c78d4070556a536b13b23ee3139cd2788aa2a9d07d430a223b4edead281db1`
- チェックポイント：`d0e42857e738d0315897c2d50fde9eb3fb1a3fb1f071d55dfc13d53d72bccc3f`
- コネクトーム：`bfbb0766251ff09e22723d0ebbf7b14793e70b3ae8ad0eea64eac9d28223351a`

FlyvisのコードはPyPIのMIT分類を確認。重み専用の追加ライセンスは配布物内で見つからなかったため、重みの再配布許諾を追加で主張しない。JFRC2元テンプレートは[Zenodo 10567](https://zenodo.org/records/10567)のCC0表記を取得して確認し、fafbsegの変換済み配布物はGPL-3.0-or-laterリポジトリ由来として出典を残した。元データ指定の引用はJenett et al., “A GAL4-Driver Line Resource for Drosophila Neurobiology”と同DOI。取得原文はassets/sourcesにローカル保存している。

メッシュはJFRC2由来をFlyWire **FAFB14.1**へ変換したもので、元単位はnm。表示で一様0.001倍してµmに変換し、左右反転・非剛体位置合わせ・細胞同定は行わない。L/Rは配布名を保持し、モデルの左右を推測しない。ユーザー情報・認証情報の探索や外部公開は行っていない。

## 実モデル・刺激・意味

実ロードしたモデルは45,669細胞、**65個のモデルtypeラベル**を持つ（CT1の区分などを含むラベル数であり、生物学的細胞型数を新たに主張しない）。原始的なconnectome構築情報と、課題で学習されたバイアス・時定数・シナプス関連パラメータを使用する。独自モデルへの置換や再学習はない。

まず[公式Custom Stimuli例](https://turagalab.github.io/flyvis/examples/07_flyvision_providing_custom_stimuli/)にあるrandom_walk_of_blocksをseed=42、1系列×8フレームで生成し、BoxEye→fade_in_state→simulateを実行。finiteな実応答をofficial_smoke.npzへ保存した。その後、自作の静止・右移動・左移動・拡大へ差し替えた。

64×64、各24フレーム、背景0.5・対象1.0、半径6px、移動60px/s、半径増加24px/s。BoxEye(extent=15,kernel_size=13)の公式平均フィルターとリサイズで721受容点へ変換する。BoxEyeの処理結果をそのまま保存し、将来画像を用いた正規化はしない。

モデル刻みと入力刻みは0.01秒で一致。再サンプリングなし。各エピソードのresetは一様灰色1秒の有限ウォームアップ。活動の表示基準はその終了状態。途中のstep/chunkでstateを初期化せず、公式simulateのas_states=Trueが返す最後の状態を次へ渡す。

`PPNeuronIGRSynapses.nodes.activity` は公式dynamics実装上のモデル電位。**発火頻度ではなく、較正されたmVでもない**。画像の画素座標・受容格子u/v・元cell_indexを別々に保存。各NPZはactivity=(24,45669)を保持し、T4aだけへデータを削減していない。T4a表示の721細胞も平均せず個別表示する。

## 数値検証とGPU実測

[validation.json](evidence/validation.json)に完全な値を保存。許容誤差はatol=rtol=2e-5。GPUのscatter演算等に伴う微小差を許容するが、完全なbit一致とは説明しない。

| 刺激 | 分割との最大絶対差 | reset再実行の最大差 | 24フレームの実計算時間 | 実計算秒／モデル秒 |
|---|---:|---:|---:|---:|
| 静止 | 1.43e-6 | 1.43e-6 | 16.33 ms | 0.0681 |
| 右移動 | 9.54e-7 | 1.43e-6 | 16.76 ms | 0.0698 |
| 左移動 | 9.54e-7 | 1.91e-6 | 13.52 ms | 0.0563 |
| 拡大 | 1.43e-6 | 1.43e-6 | 13.04 ms | 0.0543 |

計測範囲は、初期化・ロード・resetウォームアップを除いた4フレームchunk×6回。BoxEye処理・推論・CPUへの応答転送を含み、前後およびチャンク完了時にCUDA同期してperf_counterで計測した。記録パスの最大CUDA allocated memoryは各 **193,075,712 bytes＝約184.1 MiB**。この値はこの区間でのPyTorch割当ピークであり、ドライバー予約量や検証用一括実行を含むプロセス全体のピークではない。単回の小さな実測で、一般的な実時間性能や将来閉ループ性能を保証しない。

全刺激のNaN/Infなし。全6ペアのRMS差は約0.077〜0.110、右／左のRMS差は約0.106。これだけで方向選択性の生物学的再現を証明したとはしない。少なくとも同一応答しか出ていない状態ではない。

推論前後のパラメータ全体SHA-256は双方：
`f7f8252191ac4bfc38e18cc03a55061f603e68cc03a402eaf363d2141d53baa9`。
eval・requires_grad=Falseも検証。Flyvis forward内のclampを含め、パラメータは変化しなかった。

## 解剖対応と色

[対応調査記録](anatomy_mapping.json)のaccepted_mappingsは空。公式connectome資料と配布nodesにはtype・格子座標はあるが、FlyWire実測ID、解剖XYZ、左右の対応がない。T4a〜d、Mi1などの少数候補に絞って検討し、根拠ある左右付き投影を確定できなかった。T4の複数領域への投射を無視して単一領域へ割り当てたり、単眼の結果を両側へ複製したりしない。

全解剖メッシュは静的な中立色で「活動未割当」。格子パネルは各T4a細胞の実電位−当該細胞の灰色基準状態。固定[-1.5,+1.5]、青／白／赤を使用し、凡例と説明を画面に表示。毎フレームの自動正規化なし。**この代替で脳形状への活動投影を完成したとは扱わない。**

## テスト・記録と再現

- 単体：**12 passed、0 skipped**、統合1件は選択対象外。刺激の左右対称・拡大・prefix因果性・入力検証、数値再読込、非有限値・誤ったindex拒否、固定色尺度を検証。[証拠](evidence/unit-tests.txt)
- 統合：**1 passed、0 skipped**、単体12件は選択対象外。実公式モデルで1フレームstepと一括の一致、reset再現性、finite、重み固定を確認。[証拠](evidence/integration-tests.txt)
- runコマンド：公式最小例と4刺激について上記の実GPU検証を完了。
- Rerun：**1 file verified without error**。footerを含む読み込み検証。[証拠](evidence/rrd-verify.txt)
- Rerunの実描画スクリーンショットを確認。ブラウザー制御は環境エラーにより利用できず、Rerun自身のheadless機能を使用した。別Webアプリは開発していない。
- 資産取得スクリプトをネットワーク呼び出し禁止状態で再実行し、ローカルキャッシュだけで検証・展開できることを確認。[証拠](evidence/cache-check.txt)
- 新規環境へのlockからの再インストールは未実行。現在の環境で全依存整合性と実動作を確認した。

主要コマンド（全てWSL内のプロジェクトルート）：

```bash
python3 -m venv .venv
# ensurepipなしで失敗。作成された専用venvのPythonでpipを導入。
.venv/bin/python assets/sources/get-pip.py
.venv/bin/python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -m pip install -e . torch==2.7.1+cu128 torchvision==0.22.1+cu128
.venv/bin/python scripts/fetch_assets.py
.venv/bin/python -m pytest tests -m 'not integration' -q
.venv/bin/python -m flyrendezvous.run
.venv/bin/python -m pytest tests -m integration -q
.venv/bin/python -m flyrendezvous.viewer
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun rrd verify outputs/phase1/phase1.rrd
RERUN_ANALYTICS_ENABLED=false RUST_LOG=error .venv/bin/rerun outputs/phase1/phase1.rrd --bind 127.0.0.1 --headless --screenshot-to outputs/phase1/screenshot.png --window-size 1600x1000
.venv/bin/python -m pip check
```

数値記録はoutputs/phase1/{static,right,left,expand}.npz、cells.csv、config.json、validation.json。同期ログはoutputs/phase1/phase1.rrd。報告証拠はdocs/evidenceに複製。大型資産・venv・outputsは.gitignoreで除外。初回の取得・依存導入ログはoutputs/install-*.logに保存。再取得・ローカル再実行・Windows側再生の具体的手順は[README](../README.md)に記載。

途中で生じた失敗：標準venvのensurepip不足、Codexサンドボックス初期化エラー、ブラウザー制御のsandboxPolicyメタデータ不足、調査初期の旧GitHubパス404、Rerun 0.37.1には存在しないトップレベルflush呼び出し。前者は専用venv内へのpip導入と許可されたWSL実行、GitHubは公式リンクの正しいリポジトリ、flushは実版のRecordingStream.flushへ修正して解消。ブラウザー操作自体は未解消だが、Rerunの描画経路は独立して検証できた。

## 次段階への判断

A/Bの基盤はPhase 2の実験へ再利用できる。一方、重要成果である「脳の形の中で根拠を持つ領域が反応する」表示は未達なので、**Phase 1全体を完成扱いにして自動でPhase 2へ進めない**。

先に、片側の細胞群と領域への対応を追加資料で確定できるか、または静的形状＋別格子パネルという表示方針を受け入れるかの判断が必要。これは現状の根拠不足であり、全脳モデルへの変更が必要と証明されたわけではない。全脳モデルへの変更、独自位置合わせ、追加形態の大規模取得は実施していない。
