# FlyRendezvous Phase 3P 実装・実行・検証報告

**固定版FlyWire注釈のexact right-side T2全725本を取得・検証し、元のFAFB14.1座標でpopulation表示した。** T4a/T5dは既存の代表1本ずつ。全T2に同じモデル群の集約応答を適用し、個別対応・間引き・座標合わせは行っていない。

発表の主画面には**representative mode**を推奨する。T2 population modeは実測集団の解剖的な広がりを示す補助デモとして有用だが、細かな枝の説明と軽快な操作は代表表示が優れる。T4a/T5dのpopulation取得へは進まない。

[Mode A RRD](../outputs/phase3p/representative.rrd) ／ [Mode B RRD](../outputs/phase3p/t2_population.rrd) ／ [B動画MP4](../outputs/phase3p/mp4/phase3p_test00.mp4)

## 1. 対象集合と取得

[Phase 3Vと同じ公式注釈commit](https://github.com/flyconnectome/flywire_annotations/tree/8587524c1748ce5ef2080822a2fc890fc03bf597)のキャッシュをSHA確認し、cell_type == "T2" AND side == "right"の完全一致だけで列挙した。取得前に[全行・欠損・件数](../outputs/phase3p/enumeration_before_download.json)を保存した。

| 項目 | 結果 |
|---|---:|
| exact T2/right annotation | 725行 |
| unique root ID | 725、重複0 |
| 取得・構造検証 | **725/725成功、失敗0** |
| 新規取得／既存再利用 | 724本／Phase 3VのT2 1本 |
| cell_class | ME>LO:724、ME.LO:1 |
| 総頂点 | 864,608 |
| 総辺 | 863,883 |
| 元skeleton総bytes | 20,750,592（約20.8 MB） |
| assets/phase3p総bytes（info含む） | 20,750,762 |
| 取得・検証時間 | 約483秒 |
| Flyvis T2モデル細胞 | 721、実測725との個別対応なし |

ME.LOの1本はroot **720575940618970113**。exact T2/rightという指定条件を満たすので含めた。クラス名をME>LOへ修正していない。必須のroot_id/type/side/cell_classの欠損は0、soma座標欠損5、nucleus_id欠損60。任意注釈には多数の空欄があり、全フィールド別件数を取得前記録に残した。欠損を理由に恣意的に除外していない。725をモデル数721へ合わせていない。

取得は4並列、1ファイル2 MB・総量100 MBの異常検知、取得／構造異常なら停止する実装。約19.1 MBの事前概算に対して実取得20.8 MBで、停止条件には該当しなかった。全脳バルクや他typeのpopulationは取得していない。

[全725本の来歴manifest](anatomy_mapping_phase3p.json)には各root ID、注釈原行、side/class、dataset/materialization、URL、bytes、SHA-256、頂点／辺数、XYZ範囲、連結木検証を保存した。[取得コード](../scripts/fetch_phase3p_population.py)。

### 出典・座標・利用条件

- FlyWire female FAFB、materialization **783**。
- [個別precomputed skeleton配布](https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783/info)。配布infoはPhase 3Vのものと完全一致、identity transform。
- 注釈SHA-256: 9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be。
- 元座標FAFB14.1 nm。表示はfloat64で0.001倍してµmとし、Rerunのfloat32表現へ格納する通常の丸めだけを許す。
- 全体XYZ範囲[µm]: min=(651.876125,160.331563,85.528320)、max=(852.300688,396.891188,238.264656)。
- 独自の平行移動・回転・反転・形態の拡大縮小・座標fitなし。既存背景と同一座標。根拠は[公開skeleton API](https://fafbseg-py.readthedocs.io/en/latest/source/generated/fafbseg.flywire.get_skeletons.html)と[neuropil API](https://fafbseg-py.readthedocs.io/en/latest/source/generated/fafbseg.flywire.get_neuropil_volumes.html)、既存manifestの座標根拠を継承した。

利用条件・引用はPhase 3Vを継承。[FlyWire利用条件](https://flywire.ai/tos)は編集・注釈CC-BY-NC 4.0、関連[バルク形態配布](https://zenodo.org/records/10877326)はCC-BY 4.0。個別endpointのinfoには独立license欄がないため、バルクの広い再配布許諾を個別endpointに推定しない。ローカルで取得・表示し、外部公開はしていない。FlyWire Consortium、Dorkenwald et al. 2024、Schlegel et al. 2024、Matsliah et al. 2024、固定annotation READMEが指定するBerg et al. 2025へ帰属。背景は既存Jenett/JFRC2/fafbsegの出典を保持。[詳細引用・DOI](phase3v_report.md)。

## 2. 実装と表示の意味

Mode AはT2/T4a/T5d各1本のPhase 3Vと同じ代表表示。Mode BはT2だけ全725本に置換し、T4a **720575940605852192**、T5d **720575940623043327**を各1本のまま保持する。

725 root × 777時点 = 563,325回の重複した色更新を避け、**全T2の元geometryを1 entityの静的LineStrips3Dとして一度だけ記録し、時系列では1つのRGBAだけを更新**する。1,099頂点の1本を複製したものではなく、725本それぞれ異なる実測geometryである。

entityは/brain/populations/T2/arbors。[root別provenance](../outputs/phase3p/population_provenance.json)に、結合頂点・辺配列の半開区間offsetと元ファイルSHAを保存。描画strip番号は結合辺の行番号に一致する。全863,883辺を元ファイルまで追跡でき、削除・間引き・形態修復は0。

~~~text
RMS_T2(t) = sqrt(mean_i((activity_i(t) - baseline_i)^2))
q_T2(t) = clip((RMS_T2(t) - p05)/(p95 - p05), 0, 1)
RGB_T2(t) = round([255,166,65] * (0.35 + 0.65*q_T2(t)))
~~~

iはFlyvis内のT2モデル群721細胞。p05=0.20386891、p95=1.12842183はPhase 3 train+validation control periodsからtest前に固定済みで、再調整していない。全725実測T2へ同じqを同時適用する。個別の実測T2活動、発火率、枝内電位／伝播、モデル細胞との一対一／左右対応は示さない。Flyvisは全45,669モデル細胞を計算しており、今回は保存済み応答を表示するだけで新推論0。

qはそのtype自身の通常範囲内の相対応答で、type間の絶対活動比較には使えない。raw RMSを既存barに保持。モデルのretinotopic mapは細胞別signed Δvを表示し、実測populationへその空間分布を写してはいない。

## 3. Brain ViewとGUI

Demoの基本配置、sensor、軌道、3 maps、5 bars、compact statusはPhase 3Vのまま。右ME_R/LO_R/LOP_Rの中立contextを保持した。背景8領域の全59,238線分はRRDに残し、既定Brain queryには右3領域を表示する。

| 静的描画設定 | A | B |
|---|---|---|
| T2線幅、UI points | 2.8 | 0.20 |
| T2 alpha | 255 | 160 |
| T4a/T5d線幅・alpha | 2.8・255 | 同じ |
| 背景線幅・RGB | 0.22・[42,49,62] | 同じ |
| Brain eye position | [810,86,183] | [880,0,180] |
| Brain look target | [708,298,180] | [750,278,161] |

線幅は読みやすさのための画面上の値で、突起の物理的太さを示さない。alphaは全サンプルで固定し、activityに連動するのはRGBの明るさだけ。独立試行間の明示的RESETでは一時的にalpha=0で消すが、これはactivityによる透明度変化ではない。最終サンプルは保持する。

初回の3V観察視点ではpopulation右端が切れた。[初回画面](../outputs/phase3p/initial_framing/t2_population_hold.png)を残し、Brainの観察視点だけを引いて全体を収めた。**完全固定のsensor cameraは不変**。この画角差は性能比較の条件にも明記する。T4a/T5dの座標・太さ・色系統は変えず、常時前面表示も使わない。

透明な枝の重なりにより、画素の明るさは密度・遮蔽にも影響される。各形態へ渡すRGBAは同じでも、画面の局所明るさから個別細胞の応答やその数を推定できない。

## 4. 実再生と局面比較

元の成功approach **test_00**を使用。A/Bは同じtest_00/test_08/test_09計777サンプルを記録する。これは教師軌道や再推論ではなく、元の学習器閉ループ結果の再生である。

| test_00局面 | 時刻 | T2 raw RMS | q | 共通RGB |
|---|---:|---:|---:|---|
| early approach | 20 s | 0.236140 | 0.034904 | [95,62,24] |
| braking | 85 s | 0.411852 | 0.224955 | [127,82,32] |
| near/hold | 219 s | 0.917910 | 0.772310 | [217,141,55] |

A/Bともこの同じ実値で明るさが変わる。T4a/T5dもそれぞれ元の型応答に同期する。人工的な点滅、ニューロン別遅延、ランダム色、枝内アニメーションなし。

| 局面 | A：代表 | B：T2 population |
|---|---|---|
| early | [実画面](evidence_phase3p/representative_early.png) | [実画面](evidence_phase3p/t2_population_early.png) |
| braking | [実画面](evidence_phase3p/representative_braking.png) | [実画面](evidence_phase3p/t2_population_braking.png) |
| hold | [実画面](evidence_phase3p/representative_hold.png) | [実画面](evidence_phase3p/t2_population_hold.png) |

![A：代表](evidence_phase3p/representative_hold.png)

![B：T2 population](evidence_phase3p/t2_population_hold.png)

動画：B [WebP](../outputs/phase3p/t2_population_test00.webp) ／ [MP4](../outputs/phase3p/mp4/phase3p_test00.mp4)。native Rerunの実画面74枚（6サンプル間隔＋最後）、1600×1000、約14.633秒、15倍再生。MP4は30 fps・439フレーム。撮影間は同じ画面を保持し、活動・形態の補間をしていない。Aも同じ74枚の[比較WebP](../outputs/phase3p/representative_test00.webp)を保存。

[撮影A](evidence_phase3p/screenshots_representative.json) ／ [撮影B](evidence_phase3p/screenshots_t2_population.json) ／ [動画復号検証](../outputs/phase3p/video_review.json) ／ [MP4全フレーム検証](../outputs/phase3p/mp4/verification.json)。

## 5. 描画性能

| 指標 | A：代表 | B：T2 population |
|---|---:|---:|
| RRD size [MB] | 14.452 | 27.577 |
| unique entity数 | 84 | 84 |
| 形態線分数 | 2,556 | 865,341 |
| 記録された背景線分数 | 59,238 | 59,238 |
| 起動〜最初のseek完了 [s] | 2.325 | 2.932 |
| 動画74枚のscreenshot RPC平均 [s/枚] | 0.143 | 2.444 |
| screenshot RPC p95 [s/枚] | 0.151 | 2.468 |
| 動画74枚のscreenshot RPC合計 [s] | 10.573 | 180.848 |
| 動画PNG最初〜最後の取得span [s] | 24.204 | 216.844 |
| native viewer RSS [MiB] | 682.973 | 1096.684 |
| native viewer peak RSS [MiB] | 725.805 | 1120.496 |

撮影RPC平均はBがAの約17.1倍、PNG取得spanは約9.0倍。RRD容量は約1.91倍に抑えられたが、実描画負荷は大きい。[全測定値](../outputs/phase3p/performance.json)。

メモリは別の同条件6画面＋seek/play/pause後のnative binary直接起動で計測した。初回撮影ログの約11 MiBはPythonランチャーRSSだったためviewer値として採用しない。メモリprobeは動画全取得時のピークではなく、GPU専用メモリも含めていない。

同じnative Rerun 0.37.1 headless/software renderer、2240×1400、同じtest_00の74サンプルを使った各1回の実務的比較。Bだけ分布を収めるBrain画角へ調整しているため、同一画素負荷の厳密benchmarkではない。entity数は記録データ・メタデータのunique path数でblueprintを除く。上記線分は全形態と記録背景を区別して示す。

screenshot RPC時間は描画・readback・PNG・IPC込み。PNG取得spanは最初のファイル保存完了から最後までで、途中のseek/waitを含み最初の取得とエンコードを除く。これらをGUI FPSへ換算しない。**Windows GUIの実時間性能・プロジェクターでの視認性は未検証**。発表に使うなら既存MP4も用意し、対話再生の快適さを未確認のまま保証しない。

## 6. 検証と固定結果

- **111/111非GPU単体テスト通過、GPU2件deselect**。exact条件の否定例、全ID集合・重複、全形態のhash・finite・連結木・元接続・単位変換、全rootのoffset、同一ログ、全777時点の単一T2共通RGBを確認。
- A/B各777フレームを元NPZと照合。Bの全863,883枝座標、T4a/T5d、背景、bars、maps、sensor、軌道、速度／加速度、raw/q系列、時刻を確認。
- Brainと凡例以外の**180成分系列・42,066値**は旧Phase 3Vと完全一致。新RRDの作成時刻メタデータだけは比較対象外。
- **旧1,451ファイルすべてSHA一致**。README/projectは旧文をそのまま保持して今回分を追記。旧3V Demo/Analysisも元ログ照合済み。
- Phase 3は**approach 8/8、near 2/4**の既知結果のまま。near失敗（FOV外・timeout）は未調整。制御/readout/HCW/target/goal/split/success criterion/sensor camera変更0、新推論0、新制御実験0。
- GPU nondeterminismは本表示検証に混ぜず、既知の問題を解決したとは扱わない。
- WebP74/74、MP4全439/439フレーム・SHA・時間対応を検証。MP4は14.633333秒、最小PSNR 38.975 dB・平均40.867 dB。Rerun自身の形式検査も両RRDで通過。

[unit log](../outputs/phase3p/unit-tests.log)、[A RRD audit](../outputs/phase3p/rrd_audit_representative.json)、[B RRD audit](../outputs/phase3p/rrd_audit_t2_population.json)、[非Brain完全一致・旧成果保護](../outputs/phase3p/regression.json)、[保護SHA](../outputs/phase3p/prior_hashes.json)。

## 7. 採用判断

| 観点 | 判断 |
|---|---|
| scientific interpretability | Bは指定した実測T2集合の広がりを正確に示す。ただし空間的なモデル応答を実脳へ対応付けた表示ではない。全725本が同じ集約値という説明が必要で、一本代表より科学的対応が精密になったわけではない。 |
| visual appeal | Bは右視葉に広がる実測集団として迫力がある。Aは3型の形と色の違いが読み取りやすい。 |
| activity visibility | Bでもearly→braking→holdの全体的明暗変化は見える。反面、密度による画素混合があり、個々の枝の変化を追う表示には向かない。raw/q barの併用を維持する。 |
| anatomical context | Bは1本では分からないT2集団の範囲を示せる。背景は残るが、密なorangeが中立meshを覆う。 |
| clutter | Bは約86万枝が重なるため、個別枝の判読は困難。T4a/T5dは色で識別できるが、主役としての目立ち方はAに劣る。 |
| performance | 静的geometry＋共通色でRRD肥大とentity overheadを抑えたが、画面で全枝を描く負荷は残る。Aが明らかに軽い。 |

次の提案は**「一部typeは代表1本がよい」**。T2 populationは解剖分布を説明するときだけ使う補助モードとして残し、T4a/T5dは代表1本を維持する。今回の結果だけから両型のpopulation化の価値や総描画負荷は判断できず、追加取得を推奨済みの決定事項とはしない。

SpaceROS勉強会の主デモは**A**。画像→モデル応答→3型の色変化という説明が短く済み、他型がT2の密度に埋もれにくく、描画も軽い。実測集団の豊富さを紹介する短い場面にBの動画を併用するのが妥当。

## 8. 再生・再検証

WSLのプロジェクトルート：

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3p/representative.rrd --new --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3p/t2_population.rrd --new --bind 127.0.0.1
~~~

成功approachの20秒・85秒・219秒を比較する。

~~~bash
OPENBLAS_NUM_THREADS=4 .venv/bin/python -m pytest tests -m 'not integration'
.venv/bin/python scripts/verify_phase3p_rrd.py
.venv/bin/python scripts/verify_phase3p_regression.py
.venv/bin/python scripts/review_phase3p_video.py
~~~

既存ログから再生成（制御実験なし）：

~~~bash
.venv/bin/python scripts/fetch_phase3p_population.py
RERUN_ANALYTICS_ENABLED=false .venv/bin/python -m flyrendezvous.viewer_phase3p
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3p.py --mode representative --video
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3p.py --mode t2_population --video
.venv/bin/python scripts/verify_phase3p_rrd.py
.venv/bin/python scripts/verify_phase3p_regression.py
.venv/bin/python scripts/review_phase3p_video.py
.venv/bin/python scripts/export_phase3p_mp4.py
.venv/bin/python scripts/probe_phase3p_memory.py --mode representative
.venv/bin/python scripts/probe_phase3p_memory.py --mode t2_population
.venv/bin/python scripts/summarize_phase3p_performance.py
~~~

取得スクリプトはmanifestが存在すれば保存SHAを検証するだけで新規downloadしない。RRDを再生成したら撮影と動画も再生成する。既存venv・Rerun・ffmpegを再利用し、新しいvideo frameworkは導入していない。

8終了条件を満たしてここで停止する。T4a/T5d population、Tm3/L2形態、他type、再学習、near改善、追加方向、gaze control、ROS/MuJoCo、演出への展開は行わない。
