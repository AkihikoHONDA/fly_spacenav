# Phase 1B 実行・検証報告

実行日：2026-09-10。**T4aの1代表形態による試作は、今回の4終了条件を達成した。** 見せ方の最終採用は未決定であり、型数の拡大やPhase 2には進んでいない。

| 終了条件 | 結果と証拠 |
|---|---|
| 型注釈付きの代表形態を取得 | 達成。公式注釈のT4a、FlyWire root ID `720575940605852192`、1細胞・829頂点・828接続 |
| 整合する脳の文脈で表示 | 達成。形態と既存背景はFAFB14.1。両方にnm→µmのみを適用 |
| 実応答に応じた色変化と同期 | 達成。全346入力サンプルで、実RRD内の形態・色・入力・格子・受容器・グラフを元NPZと照合 |
| 意味と限界を説明 | 達成。画面と対応表に同型代表表示、個別位置対応なし、枝内電位分布ではないことを明示 |

## 1. 採用した形態と根拠

モデル側は保存メタデータの `cell_type == "T4a"` に一致する**721モデル細胞**。元の45,669細胞のインデックスと格子座標を保持する。形態側は[FlyWire公式注釈表](https://github.com/flyconnectome/flywire_annotations/blob/8587524c1748ce5ef2080822a2fc890fc03bf597/supplemental_files/Supplemental_file1_neuron_annotations.tsv)の、同じ文字列 `T4a`、`side=right`、`cell_class=ME>LOP` が付いた単一細胞を採用した。T4から亜型を推定していない。

| 項目 | 値 |
|---|---|
| データセット | FlyWire female FAFB、materialization 783 |
| 注釈の固定commit | `8587524c1748ce5ef2080822a2fc890fc03bf597` |
| 形態ID | `720575940605852192` |
| 公開形態 | Neuroglancer precomputed skeleton、19,896 bytes |
| 構造 | 829頂点・828接続、連結した木。EM再構成から抽出された公開スケルトン |
| 元ファイルSHA-256 | `636df53b81276202a6209a128f5e7636141e14cd44eb094c3f9fff9402877858` |
| SWC | 元の接続と座標を保持しµmで書き出し。rootは任意のグラフ頂点で、細胞体や枝種別を推定しない |

取得経路は**1系統**で成功した。公式注釈表で候補のT4aとMi1を確認し、最初に見つかった厳密なT4a行を採用した。[fafbsegの公開実装](https://fafbseg-py.readthedocs.io/en/latest/_modules/fafbseg/flywire/skeletonize.html)が用いる[個別形態URL](https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783/720575940605852192)へ到達し、HTTP 200で実ファイルを取得した。Mi1の形態は取得していない。第2系統は不要だった。注釈表約31.7 MBと1細胞の形態のみを取得し、数GBの全形態配布は取得していない。

利用条件は[対応表](anatomy_mapping_phase1b.json)に分離して記録した。[FlyWireの利用条件](https://flywire.ai/tos)には編集・注釈についてCC-BY-NC 4.0、関連する[Schlegelのバルク形態配布](https://zenodo.org/records/10877326)にはCC-BY 4.0の記載がある。今回の個別エンドポイント自体には独立したライセンス欄がないため、両者を記録し、広い再配布許諾を推定しない。出典表示を保持したローカルの非商用試作として扱う。FlyWire Consortium、Dorkenwald et al.、Schlegel et al.、Matsliah et al.へ帰属を表示する。背景の出典と条件は既存の[資産manifest](assets_manifest.json)を維持した。

## 2. 座標・左右・背景

[公開スケルトンAPI](https://fafbseg-py.readthedocs.io/en/latest/source/generated/fafbseg.flywire.get_skeletons.html)と配布infoに従い、形態はFAFB14.1のnm座標として読む。既存のJFRC2由来FAFB14.1背景と同じく0.001倍してµmに変換する。形態の表示範囲はXYZそれぞれ約694.118–754.375、242.783–263.073、132.668–228.935 µm。位置調整・反転・非剛体変換は行っていない。

出典の右側ラベルは**表示資産の属性**として保持する。Flyvisの左右は未割当で、実測root IDをモデルのcell_indexへ割り当てていない。`one_to_one_model_cell_mapping: false` と `model_hemisphere_assigned: false` を明示した。

全体ビューでは右ME・LOPを既存メッシュの三角形辺の輪郭として表示し、左ME・LO・LOPとFB・EBを中立色で残す。右LOは隠して遮蔽を減らした。これらの背景には活動を割り当てていない。接写は同一の `/brain/representative` を別カメラで表示し、形態の座標や寸法を拡大していない。全脳ニューロン群の表示ではない。

## 3. 表示値と固定尺度

細胞別基準は各記録の灰色ウォームアップ終了状態 `baseline_i`。表示専用の計算は次のとおり。

```text
delta_v_i(t) = activity_i(t) - baseline_i
s(t) = sqrt(mean_i(delta_v_i(t)^2)), i in cell_type == T4a
```

名称は**応答変化の大きさ（RMS、モデル単位）**。平均電位、興奮の強さ、発火頻度、mVとは呼ばない。正負の変化を相殺せずまとめるが、符号や位置情報は失う。そのため格子には721細胞それぞれの符号付き変化と元のu/vを残す。

形態の828接続すべてに、同じ時刻の1つのRGBを適用する。枝内の局所電位や伝播は計算していない。表示処理は制御器・特徴量生成に接続していない。

RMS尺度は既存4条件の最大値 `0.21757323818638996` から `ceil(max × 100) / 100 = 0.22` と決定し、追加系列の推論前に固定した。RGBはゼロの `[70,110,160]` から上限の `[255,205,65]` へ線形補間し、整数に丸める。上限超えはクリップする。格子はPhase 1と同じ固定±1.5の青・白・赤。ゼロ・上限・クリップを画面凡例に表示する。今回、形態・格子ともクリップは0件だった。

| 試行 | フレーム | T4a RMS最小 | 最大 |
|---|---:|---:|---:|
| static | 24 | 0.00011622 | 0.19343011 |
| right | 24 | 0.00011624 | 0.18449705 |
| left | 24 | 0.00011623 | 0.21757324 |
| expand | 24 | 0.00011622 | 0.21384313 |
| sequence | 250 | 0.00011622 | 0.19343012 |

## 4. 追加刺激と時刻

まず既存4条件のNPZをハッシュ・validation付きで読み、集約と実描画を確認した。初期の[RRD](../outputs/phase1b/phase1b_existing.rrd)と[画面](../outputs/phase1b/existing.png)を残した。その後、0.24秒より動作を追いやすい**1本の2.5秒系列**を追加した。

静止0.5秒 → 右移動0.5秒 → 停止0.5秒 → 左移動0.5秒 → 停止0.5秒。既存の円刺激生成器を使用し、速度24 px/s、半径6 px、中心xは31.5→43.5→31.5 px。画像を整数12 px移動する区間も含むが、対象は常に画像内にあり、端からの折返しはない。

既存のモデル、dt=0.01秒、BoxEye前処理、1秒灰色reset、4フレームずつの状態保持を再利用した。系列内の段階間にはresetを入れない。RTX 5070 Tiで250フレームを実計算し、全45,669細胞を `sequence.npz` に保存した。推論・前処理・CPU転送のCUDA同期済み所要時間は約0.331秒（モデル読込とwarmupを除く）、CUDA最大割当約185.9 MB。学習・重み更新は0で、前後のパラメータSHA-256が一致した。[実行記録](../outputs/phase1b/sequence_validation.json)

input_timeは画像を保持する区間の開始、response_timeはその入力に対応するEuler更新終了で、差は0.01秒。表示時刻はepisode offset + input_timeであり、実際の局所入力時刻と応答時刻を読み出し欄に併記する。独立エピソード間には0.2秒の表示用RESET空白を設け、入力・格子・形態を消す。これはウォームアップ1秒そのものの再生ではない。グラフは試行ごとに別系列とし、resetをまたいで線を結ばない。再生倍率は0.5倍で、モデル時刻と数値を変更しない。

## 5. 実Rerunのスクリーンショット

以下は完成予想図ではなく、最終 `phase1b.rrd` を**Rerun 0.37.1のネイティブheadless renderer**で描画した1800×1050 PNG。導入済みのviewer-mcpで時刻を指定し、描画後の実タイムライン値を照合して保存した。追加系列の入力0.5秒以降の実測最小・最大を選び、刺激提示直後の立上がりを除いた2例である。

| 画像 | 試行／段階 | サンプル | input_time | response_time | 表示時刻 | RMS | RGB |
|---|---|---:|---:|---:|---:|---:|---|
| [low.png](evidence_phase1b/low.png) | sequence／right | 60 | 0.60 s | 0.61 s | 2.36 s | 0.0782812813 | 136,144,126 |
| [high.png](evidence_phase1b/high.png) | sequence／left | 190 | 1.90 s | 1.91 s | 3.66 s | 0.1662492585 | 210,182,88 |

![入力0.60秒、RMS 0.07828の実描画](evidence_phase1b/low.png)

![入力1.90秒、RMS 0.16625の実描画](evidence_phase1b/high.png)

両方で入力・受容器・符号付き格子、接写、脳内の位置、グラフのカーソル、数値欄を確認した。枝全体の色が変わり、背景色は中立のまま。2時刻の円は同じ位置だが、移動方向と刺激履歴が異なる。この2点だけで方向選択性の評価結果とはしない。

viewer-mcpで時刻移動、再生による時刻進行、停止後の時刻保持を確認した。検証はnative headless・software rasterizerの範囲。**Windows GUIのマウス操作は未検証**であり、対話GUIを直接操作した成功とは扱わない。[画像ハッシュ・実時刻・操作証拠](evidence_phase1b/screenshots.json)

## 6. 検証結果と既存成果の保持

- 単体テスト：**45 passed**（既存12＋追加33）。型選択、ゼロ・正負混在RMS、NaN/Inf拒否、固定色とクリップ、時刻・長さ・インデックス不整合、改変検知、枝接続、SWCの欠損親・重複・不正座標、刺激の視野内保持を確認。[ログ](../outputs/phase1b/unit-tests.log)
- 既存実モデル統合テスト：**1 passed、skipなし**。chunkと逐次stepの一致、reset再現性、有限値、固定重みを再確認。[ログ](../outputs/phase1b/integration-tests.log)
- 集約NPZ：元NPZから独立に `sqrt(mean(delta**2))` を再計算し、全試行で最大誤差 `2.78e-17`。保存RGBも一致。[数値検証](../outputs/phase1b/display_validation.json)
- 実RRD：導入済み `rerun.experimental.RrdReader` で全346サンプルを読み直し、形態の接続座標・全枝共通色、格子の色と位置、受容器色、画像の全画素、グラフ値、共通時刻を元NPZと照合。[検証JSON](../outputs/phase1b/rrd_data_validation.json)
- `rerun rrd verify` は成功。元のPhase 1ビューアも別の `phase1_regression.rrd` に再生成し、読み込み検査に成功。
- 作業前に記録したPhase 1の出力・設定・報告・対応表・元ソースの**20ファイルはすべてSHA-256不変**。[作業前ハッシュ](../outputs/phase1b/phase1_before.json) と上記RRD検証JSONに結果を保存。`docs/anatomy_mapping.json` のaccepted_mappingsは空のまま。
- 既存venvを使用し、依存の追加・更新なし。`pip check` は成功。新規アカウント、認証情報、有料サービス、全脳形態一括取得は利用していない。

## 7. 再生と再現

WSLのプロジェクトルートから、保存済み結果を開く1本のコマンド：

```bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase1b/phase1b.rrd --bind 127.0.0.1
```

初期は停止状態。下部の再生ボタンを押し、表示時刻2.36秒と3.66秒で枝色・RMS・グラフカーソルを比較する。左の格子は符号付き、中央の形態は型RMSであること、右欄の入力・応答時刻の0.01秒差を確認する。

保存済み数値からの再生成と検証（推論は不要）：

```bash
.venv/bin/python scripts/fetch_morphology.py
.venv/bin/python -m flyrendezvous.phase1b --include-extended
.venv/bin/python -m flyrendezvous.viewer_phase1b
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun rrd verify outputs/phase1b/phase1b.rrd
.venv/bin/python scripts/verify_phase1b.py
.venv/bin/python scripts/capture_phase1b.py
```

取得済み資産はキャッシュをハッシュ検証して再利用する。新規の形態ダウンロードは1細胞だけ。追加刺激自体の再実行が必要な場合のみ、集約の前に `.venv/bin/python -m flyrendezvous.sequence_phase1b` を実行する。このコマンドはPhase 1Bの系列とvalidationを更新するため、以降の集約・RRD・証拠も再生成する。Phase 1の記録は変更しない。

## 8. 残る制約と次の判断

同じ型を代表する**説明用の割当**であり、同一個体・同一位置のモデル再現ではない。1つのスケルトンが型内の形態差を代表し切る保証はなく、枝の種類・伝導・局所活動を表さない。形態の細かな枝分かれは全体ビューでは小さく、接写を併用する構成が必要だった。固定尺度で見える色差は今回の範囲に留まり、強い光や活動伝播の演出は加えていない。

次はユーザーが、この1種類の画面で「生物由来の形態と実モデル応答」を説明しやすいか、格子と形態の役割が読み取れるかを判断する。全脳活動の完成や最終的な訴求力の完成とは扱わない。HCW、LQR、読み出し学習、閉ループ、追加の細胞型は未実装。
