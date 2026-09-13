# FlyRendezvous Phase 3W 実装・実行・検証報告

2026-09-11 JST。**T2/T4a/T5d各12本、計36本の実測形態を、左右視葉と中央を含む78領域のneuropil context内に表示した。** 各型の既存代表1本を固定し、残り11本を固定seedで抽出。T2はcacheを再利用し、T4a/T5dの不足22本だけを取得・検証した。

SpaceROS勉強会の主Demoには**Mode B：36本multi-representative**を推奨する。Mode Aは枝の細部説明、Mode CはT2集団分布の補足として保持する。制御・readout・HCW・fixed sensor camera・Phase 3 test成績は不変。新推論・新制御実験0。

[指令保存版](codex_phase3w.md) ／ [Mode B実画面](evidence_phase3w/multi_hold.png) ／ [14.633秒MP4](../outputs/phase3w/mp4/phase3w_test00.mp4) ／ [Demo RRD](../outputs/phase3w/multi.rrd) ／ [Analysis RRD](../outputs/phase3w/analysis.rrd)

## 1. 固定した範囲と選定

AGENTS、project、README、Phase 3/3V/3P報告・来歴・viewer・取得処理・保存RRDを確認し、旧2,431成果を取得前のSHAで保護した。新成果はphase3w名へ分離。旧README/project本文はそのまま保持して今回の説明を追記する。

公式annotationのcommit **8587524c1748ce5ef2080822a2fc890fc03bf597**、SHA **9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be**を再利用。[公式固定版](https://github.com/flyconnectome/flywire_annotations/tree/8587524c1748ce5ef2080822a2fc890fc03bf597)。

| type | exact type/right母集団 | 固定seed | 既存代表ID | 選択 | 新規取得 |
|---|---:|---:|---|---:|---:|
| T2 | 725 | 310401 | 720575940608937923 | 12 | 0 |
| T4a | 737 | 310402 | 720575940605852192 | 12 | 11 |
| T5d | 727 | 310403 | 720575940623043327 | 12 | 11 |

各型でroot IDを**整数値で安定ソート**し、既存代表を固定。残りからNumPy PCG64で11本を重複なし一様抽出し、出力を再度root順に並べる。「12本すべてを無条件一様抽出」ではなく、既存1本を含む条件付き抽出である。候補の見た目・枝長・モデル応答は選定に使っていない。入力行順を逆にしても同じ集合になることをテストした。重複0、不足0、別side/近似typeによる補完0。

[seed/config](../configs/phase3w.json)、[取得前の選定原行](../outputs/phase3w/selection_before_download.json)、[選択36本のCSV](../outputs/phase3w/selected_morphologies.csv)、[全来歴・個別SHA](anatomy_mapping_phase3w.json)。T2の12本と既存T4a/T5d各1本の計14本はcache再利用。新規22本は22/22成功、36本すべてのhash・有限座標・辺端点・連結木を確認した。

| type | vertices | edges | 元skeleton bytes |
|---|---:|---:|---:|
| T2 ×12 | 13,440 | 13,428 | 322,560 |
| T4a ×12 | 9,657 | 9,645 | 231,768 |
| T5d ×12 | 7,224 | 7,212 | 173,376 |
| 合計 | **30,321** | **30,285** | **727,704** |

assets/phase3wの新規保存量はinfo・22形態・追加70 meshを含め1,733,962 bytes。既存参照ファイルの再複製はしていない。

## 2. 出典と解剖座標

FlyWire female FAFB、materialization **783**、[Phase 3Vと同じ個別precomputed配布](https://flyem.mrc-lmb.cam.ac.uk/flyconnectome/flywire_skeletons_783/info)。配布infoは既存と一致する。各形態のexact annotation原行、root ID、side、cell_class、dataset、materialization、URL、bytes、SHA、vertices/edges、XYZ範囲と検証結果をmanifestへ記録した。

sourceは**FAFB14.1 nm**、表示は0.001倍したµm。元接続と座標を保持し、移動・回転・反転・形態拡大・位置合わせ・間引きなし。表示用観察カメラの設定と、形態自体の座標変換を区別する。Rerunへのfloat32格納による通常の丸めを元座標から照合した。

[全36本の頂点・辺offset来歴](../outputs/phase3w/provenance.json)で、各typeの結合配列をroot別に追跡できる。/brain/multi/T2/arbors、T4a/arbors、T5d/arborsの3 entityに全geometryを一度だけ静的記録し、時系列で型ごと1色を更新する。12本の複製ではなく、12個の別々の実測細胞である。

利用条件はPhase 3V/3Pと同じ。[FlyWire編集・注釈のCC-BY-NC 4.0](https://flywire.ai/tos)、関連[バルク配布のCC-BY 4.0](https://zenodo.org/records/10877326)を区別し、個別endpointに独立license欄がないことも記録。個別endpointへ広い再配布許諾を推定せず、今回外部公開はしていない。FlyWire Consortium、Dorkenwald/Schlegel/Matsliah et al. 2024、固定annotation READMEのBerg et al. 2025の帰属を継承。[引用・DOI一覧](phase3v_report.md)。

## 3. Bilateral / central anatomy context

既存assets/JFRC2NP.surf.fw.zipの**78個のtop-level PLY**を全件調べた。macOSの付随メタデータ78件はmeshとして数えない。展開済み8領域に加え、同じarchiveから70領域をphase3wへ抽出した。ネットワークで新しい解剖データを取得していない。

表示mesh全一覧：

AL_L, AL_R, AME_L, AME_R, AMMC_L, AMMC_R, AOTU_L, AOTU_R, ATL_L, ATL_R, AVLP_L, AVLP_R, BU_L, BU_R, CAN_L, CAN_R, CRE_L, CRE_R, EB, EPA_L, EPA_R, FB, FLA_L, FLA_R, GA_L, GA_R, GNG, GOR_L, GOR_R, IB_L, IB_R, ICL_L, ICL_R, IPS_L, IPS_R, LAL_L, LAL_R, LA_L, LA_R, LH_L, LH_R, LOP_L, LOP_R, LO_L, LO_R, MB_CA_L, MB_CA_R, MB_ML_L, MB_ML_R, MB_PED_L, MB_PED_R, MB_VL_L, MB_VL_R, ME_L, ME_R, NO, OCG, PB, PLP_L, PLP_R, PRW, PVLP_L, PVLP_R, SAD, SCL_L, SCL_R, SIP_L, SIP_R, SLP_L, SLP_R, SMP_L, SMP_R, SPS_L, SPS_R, VES_L, VES_R, WED_L, WED_R

[archive内全一覧・座標範囲](../outputs/phase3w/mesh_inventory.json)。全78領域・100,892三角形・151,297個の重複除去した三角形辺をwireframe表示する。ME/LO/LOPの左右、FB/EBを含め、表示subsetへの変更はしていない。

archiveはfafbsegの固定commit **d0da95123ee606e204ae2c702e7bc78538646fbd**のJFRC2由来FAFB14.1配布。既存の[資産manifest](assets_manifest.json)と同じSHA・由来・座標を確認した。元[Zenodo 10567](https://doi.org/10.5281/zenodo.10567)のCC0、配布repositoryのGPL-3.0-or-laterと既存帰属を保持する。

全contextのXYZ範囲[µm]はmin=(85.877047,63.046820,-3.396809)、max=(893.490688,445.224156,270.892406)。全meshでarchive原座標×0.001と原三角形の一致を検証した。

**これは「既存atlas archiveの全78領域」を表示した、脳全体の位置関係を見るための部分的なneuropil anatomy contextである。全脳の全細胞・全突起・全解剖構造を網羅したものではない。頭部外形、外骨格、複眼、触角のモデルでもない。** 灰色背景に活動は割り当てない。左側が灰色なのは左脳の活動ゼロを意味せず、今回の実測形態がright-sideから選ばれているだけである。

## 4. ActivityとGUI

各typeのFlyvisモデル群721細胞について、灰色warmup後baselineとの差のRMSを使う。モデル計算対象は全45,669細胞で、今回新たに計算したものではなく保存済みログを再生する。

~~~text
RMS_type(t) = sqrt(mean_i((activity_i(t)-baseline_i)^2))
q_type(t) = clip((RMS_type(t)-p05_type)/(p95_type-p05_type),0,1)
RGB_type(t) = round(base_RGB_type * (0.35+0.65*q_type(t)))
~~~

Phase 3 train+validation control periodsからtest前に固定したp05/p95を再利用し、testを見て再調整していない。T2 orange=[255,166,65]、T4a blue=[80,175,255]、T5d magenta=[245,100,225]は識別用で、生物学的な色の意味はない。

**同じtypeの12形態は全て同じq、同じRGBで同時に変化する。** 個々のFlyvis model cellと実測rootの一対一・位置・左右対応はない。表示した実測細胞自身のactivityではなく、branch内電位・propagation・spikeでもない。qは型自身の通常範囲に対するレベルで、型間の絶対activity比較に使わない。

raw RMSは従来barに残し、T2/T4a/T5dのretinotopic mapは細胞別signed応答を保持。mapの視野内空間分布を実測形態群へ転写してはいない。

### 最終表示設定

- 形態：全36本、線幅1.2 UI points、alpha255。全枝保持、常時前面化なし。
- 全78背景：RGB=[90,95,105]、alpha170、線幅0.18 UI points。
- 右ME/LO/LOP：RGB=[95,100,110]、alpha185、線幅0.20 UI points。
- 固定Brain eye：position=[490,-400,160]、look_target=[490,254,134]、eye_up=[0,0,1]。
- ラベルは型ごと1個。T2は最大X、T4aは最小Z、T5dは最大Zの実頂点に置き、ラベル同士の重なりを減らした。

線幅・alpha・背景・視点は活動と無関係の静的表示設定で、突起の実太さを意味しない。activityに連動するのはRGBの明るさだけ。試行間の明示的RESET時は透明化し、最終サンプルを保持する。

初回の背景が薄すぎたため、[初回画面](../outputs/phase3w/initial_context/multi_hold.png)を残し、背景の静的設定と型ラベルだけを調整した。[最終override](../outputs/phase3w/display_override.json)。選定・活動尺度・形態座標は変更していない。

Demoは大きなorbitとbilateral Brain、中段相当のsensor・3 maps、小さな5 bars/statusという従来の基本配置を維持する。Analysisには全体Brainと右視葉接写、5 maps、raw/q・加速度・誤差・速度の詳細系列を残した。接写も同じ36本を同じ座標で表示する。[Analysis実画面](evidence_phase3w/analysis_braking.png)。

## 5. 実画面と動画

元の学習器closed-loop成功試行**test_00**を再生した。教師軌道への切替・再推論は0。RRDは従来と同じtest_00/test_08/test_09、計777フレームを保持する。test_00は0〜219秒、15倍再生。最後のtest_09は既知失敗で、成功へ見せ替えていない。

| 局面 | 時刻 | Mode A：各1本 | Mode B：各12本 |
|---|---:|---|---|
| early approach | 20 s | [実画面](evidence_phase3w/representative_early.png) | [実画面](evidence_phase3w/multi_early.png) |
| braking | 85 s | [実画面](evidence_phase3w/representative_braking.png) | [実画面](evidence_phase3w/multi_braking.png) |
| near/hold | 219 s | [実画面](evidence_phase3w/representative_hold.png) | [実画面](evidence_phase3w/multi_hold.png) |

![Mode B：36本と左右・中央neuropil context](evidence_phase3w/multi_hold.png)

同時刻のCは[保持済みPhase 3P画面](evidence_phase3p/t2_population_hold.png)。CのRRD・動画・性能測定は再生成せずSHA確認して参照した。

| type | early q / raw RMS | braking q / raw RMS | hold q / raw RMS |
|---|---|---|---|
| T2 | 0.034904 / 0.236140 | 0.224955 / 0.411852 | 0.772310 / 0.917910 |
| T4a | 0 / 0.093359 | 0.328451 / 0.123272 | 0.501905 / 0.138608 |
| T5d | 0.049380 / 0.067712 | 0.215902 / 0.078776 | 0.735606 / 0.113305 |

earlyでは特にT4aが暗く、braking〜holdで各型群が明るくなる。低応答時の全体viewでは細い枝の判読が難しいことも確認した。brightness floorやp05/p95を変えて強調せず、barの数値とAnalysis接写を併用する。

[Mode B WebP](../outputs/phase3w/multi_test00.webp)はnative Rerun実画面74枚、6サンプル間隔＋最終サンプル、14,633 ms。[MP4](../outputs/phase3w/mp4/phase3w_test00.mp4)は1600×1000、30 fps、439フレーム、14.633333秒。撮影間は画面保持で、活動の補間・架空の点滅を加えていない。Aも[同じ74枚の動画](../outputs/phase3w/representative_test00.webp)を保存。

native viewerのseek/play/pauseと連続再生を確認。Bの連続再生9画面で時刻進行を記録し、WebP全74枚とMP4全439枚を復号検証した。MP4の最小PSNR39.942 dB、平均41.676 dB、PTSは0〜438、time base 1/30。既存ffmpegを再利用し、新しいvideo frameworkは導入していない。

[撮影A](evidence_phase3w/screenshots_representative.json) ／ [撮影B](evidence_phase3w/screenshots_multi.json) ／ [動画照合](../outputs/phase3w/video_review.json) ／ [MP4検証](../outputs/phase3w/mp4/verification.json)。

## 6. A/B/Cの性能比較

| 指標 | A：各1本 | B：各12本 | C：T2 full＋2本 |
|---|---:|---:|---:|
| 形態本数 | 3 | 36 | 727 |
| 頂点 | 2559 | 30321 | 866068 |
| 辺 | 2556 | 30285 | 865341 |
| RRD [MB] | 14.445 | 8.226 | 27.577 |
| unique entity（blueprint除外） | 84 | 154 | 84 |
| 起動〜最初のseek [s] | 2.326 | 2.401 | 2.932 |
| screenshot RPC平均 [s/枚] | 0.141 | 0.516 | 2.444 |
| screenshot RPC p95 [s/枚] | 0.145 | 0.525 | 2.468 |
| 動画74枚のRPC合計 [s] | 10.460 | 38.166 | 180.848 |
| 動画PNG最初〜最後span [s] | 24.116 | 55.676 | 216.844 |
| native RSS [MiB] | 869.4 | 851.6 | 1096.7 |


[測定JSON](../outputs/phase3w/performance.json)。同じtest_00、同じ74サンプル、2240×1400、native Rerun 0.37.1 software renderer。A/Bは今回測定、Cは保持したPhase 3P測定。Aは右視葉接写、Bは78領域の左右context、Cは全T2用の右視葉視点なので、同一画素負荷の厳密benchmarkではない。

撮影RPCは描画/readback/PNG/IPC込み。PNG spanは最初の保存完了〜最後で、途中seek/wait込み、初回取得と動画encodeを除く。A/Bの取得ループ全体は別途24.476秒／56.462秒。ロード値には撮影スクリプトの固定2秒待機も含む。

BはAの撮影RPC約3.65倍、Cより約4.74倍速い。BのRRDがAより小さいのは、全形態を静的geometry＋型ごとの色更新にしたためで、実描画負荷が小さいという意味ではない。A/Bのnative RSSは同程度だった。CのRSSは別の6画面probe後の旧値で、動画全取得後のA/Bと測定時点が異なるため厳密比較しない。専用GPUメモリは未計測。

**Windows GUIの手動操作・実時間FPS・プロジェクターでの視認性は未検証。** headless結果からGUIが何fpsで動くとは主張しない。保存動画は発表用の再生物として利用できる。

## 7. 検証と制御結果の保持

| 検証 | 結果 |
|---|---|
| 非GPU単体 | **121/121通過**（既存111＋追加10、GPU2件deselect） |
| 選定 | seed再現性、逆順入力、exact/right否定例、重複検知、各12本、既存代表包含 |
| 形態 | 全36本のSHA・finite・連結木、元頂点×0.001、元辺、root offset |
| 背景 | archive内78個を全列挙、hash、原座標×0.001、全原三角形 |
| Activity | 各型12本へ1色、全777時点でその型自身のRMS/qと一致、他型のq取り違えなし |
| RRD vs source | A/B/Analysis各777フレーム、全geometry・背景・maps/bars・画像・軌道・系列・時刻。Rerun形式検査も3本通過 |
| 非Brain表示 | A/B各180成分系列・42,066値がPhase 3Vと一致。RRD生成時刻メタデータは対象外 |
| 旧成果 | **2,431/2,431 SHA一致**。README/project旧本文保持 |
| 動画 | WebP74枚、MP4全439枚、source PNG/RRD/NPZ SHA・時間対応・復号品質を確認 |
| 新推論／新制御実験 | **0 / 0** |

[unit log](../outputs/phase3w/unit-tests.log)、[A audit](../outputs/phase3w/rrd_audit_representative.json)、[B audit](../outputs/phase3w/rrd_audit_multi.json)、[Analysis audit](../outputs/phase3w/rrd_audit_analysis.json)、[旧成果・非Brain比較](../outputs/phase3w/regression.json)、[取得前SHA](../outputs/phase3w/prior_hashes.json)。

Phase 3は**approach 8/8、near 2/4成功**のまま。nearのFOV外・timeoutは既知の失敗として固定し、readout調整もtest再評価も行っていない。HCW、target/goal、sensor camera、checkpoint、readout、split、成功条件はファイルSHAと元ログで保持を確認。既知GPU nondeterminismを今回の可視化試験へ混ぜず、解決したとも扱わない。

## 8. 終了時の判断

### A. Multi-representativeの価値

1本より複数の実測神経群として見え、同型の解剖的なばらつき・広がりを伝えやすい。T2/T4a/T5dを各12本にしたことで、full T2だけが視覚的に支配する状態を避けられた。

36本でも右視葉内の枝は重なり、全枝・全rootを一画面で識別できるわけではない。細胞間のsynapseや接続は表示しておらず、「神経網らしい見た目」を回路接続の再現と解釈しない。実応答による型全体の明暗変化は確認できるが、低応答時の細部はAまたはAnalysis接写の方が分かりやすい。

### B. Whole-brain context

左右と中央が同じ座標で見えるため、色付き形態が脳全体の文脈のどこにあるかはA/Cより説明しやすくなった。表示は**ローカルatlasの全78表面、脳解剖としては部分的なneuropil context**。完全な全脳細胞表示や頭部形状とは呼ばない。背景にactivityがないこと、モデルの左右対応を確定していないことを維持する。

### C. Performance

Aが最も軽く、Bは背景を78領域へ広げてもCのfull populationより十分軽かった。Bは発表用動画を作成・再生できる負荷に収まり、保存RRDも約8.23 MB。対話GUIの実時間性能までは保証しない。

### D. 発表推奨

**主DemoはB。** 「脳のどの部分に、実測されたどんな形態群を使い、型レベル応答をどう表示しているか」を1画面で説明できる。Aを枝形態の詳細説明、CをT2全実測集合の広がりを示す補助表示に使う。

36本はFlyvis36細胞のactivityではない。同型12本を同期着色する表示が十分説明できることを前提に採用する。T4a/T5d full populationへ展開する判断は今回行わず、追加取得もしない。

## 9. 再生・再検証

WSLのプロジェクトルートから：

~~~bash
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3w/multi.rrd --new --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3w/analysis.rrd --new --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3w/representative.rrd --new --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase3p/t2_population.rrd --new --bind 127.0.0.1
~~~

20秒・85秒・219秒を比較する。再検証：

~~~bash
OPENBLAS_NUM_THREADS=4 .venv/bin/python -m pytest tests -m 'not integration'
.venv/bin/python scripts/verify_phase3w_rrd.py
.venv/bin/python scripts/verify_phase3w_regression.py
.venv/bin/python scripts/review_phase3w_video.py
~~~

既存ログから再生成する場合：

~~~bash
.venv/bin/python scripts/fetch_phase3w_morphologies.py
RERUN_ANALYTICS_ENABLED=false .venv/bin/python -m flyrendezvous.viewer_phase3w
RERUN_ANALYTICS_ENABLED=false .venv/bin/python -m flyrendezvous.viewer_phase3w --mode analysis
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3w.py --mode representative --video
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3w.py --mode multi --video
RERUN_ANALYTICS_ENABLED=false .venv/bin/python scripts/capture_phase3w.py --mode analysis
.venv/bin/python scripts/verify_phase3w_rrd.py
.venv/bin/python scripts/verify_phase3w_regression.py
.venv/bin/python scripts/review_phase3w_video.py
.venv/bin/python scripts/export_phase3w_mp4.py
.venv/bin/python scripts/summarize_phase3w_performance.py
~~~

取得manifestがあれば既存選定とSHA検証だけを行い、追加downloadしない。RRD再生成後は撮影・動画も再生成する。旧Phase 3/3V/3Pは参照のみ。

8終了条件を満たしてここで停止する。全population同時表示、Tm3/L2形態、モデル↔実測一対一対応、branch propagation、fake spikes、gaze、再学習、near改善、新条件、頭部／機体／小惑星演出、ROS/MuJoCoには進んでいない。
