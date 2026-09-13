# FlyRendezvous：目的・段階・確定事項

## 目的
宇宙ロボット技術チームの勉強会で、公開された生物由来の視覚回路モデルを実際に動かし、コネクトームに由来する構造と人工的に学習したパラメータの違いを説明する。従来制御への優位性や実用宇宙機への搭載を主張しない。

作業場所は既存のWSLディレクトリ `/home/jaxa/Workspace/fly_spacenav` を使用する。プロジェクト名はFlyRendezvous、Python配布名はfly-rendezvous。開始時は空ディレクトリで、Gitリポジトリ・既存AGENTS.md・既存venvはなかった。無関係なファイルを変更しない。

## 段階
- **Phase 1（今回のみ）**：公式の学習済みFlyvis 1モデルの推論、状態保持、刺激応答の数値保存、公開脳領域形状と実応答の同期表示、対応付けの成立性を検証する。
- **Phase 2以降（背景）**：軌道面内2D HCWの相対運動・教師生成・画像入力・読み出し学習・閉ループ評価を段階的に検討する。今回のコードには含めない。
- 将来の最終表示は3D。ハエ型機体、対象物、軌跡、速度、飽和後の実加速度、実センサー画像、神経応答を同期表示する。噴射表現を加える場合は実加速度の逆向き。観客向けカメラと制御入力画像を分離する。

## 未検証の制御仮説
画像時系列 → 学習済み・固定Flyvis → 学習する読み出し → 上限付き並進加速度 ax, ay → HCWを第一案とする。LQRを教師とし、最初の読み出しはリッジ回帰による線形層を想定する。閉ループでの成立性は未検証。Flyvis全体の再学習や強化学習へ自動変更しない。

真の位置・速度は教師生成と評価のみで使用し、学習制御器へ渡さない。将来のカメラはLVLHに対して固定し、既知サイズの対象が視野に収まる初期条件に限定する。対象追尾による画像中心固定はしない。非接触の目標位置へ接近して位置誤差と相対速度が小さくなることが成功条件。具体的座標、距離、速度、時間、許容値、モデル時間とHCW時間の倍率はPhase 2で確定する。

小天体風の対象は外観のみで、対象自身の重力、着陸、接触・結合、姿勢合わせ、羽ばたき空力を扱わない。初版は実計算した閉ループ結果の保存と同期再生が必須で、実時間推論は必須にしない。

## Phase 1で固定した実装境界
- `stimuli.py`：64×64のグレースケール円。静止・右移動・左移動・拡大。
- `adapter.py`：Flyvis公式APIでの読み込み、reset、step、chunk。CUDA不在時にCPUへ自動代替しない。
- `recording.py`：NumPyとJSON。GUIから独立し、原細胞別の空間情報を保存する。
- `anatomy.py`、`docs/anatomy_mapping.json`：公開メッシュと対応の根拠。認められた活動投影は今回ゼロ件。
- `viewer.py`：数値記録を読み直してRerunへ変換する。Flyvis/GPUをimportしない。全視野平均を制御特徴量として固定しない。

単一の公式モデル `flow/0000/000`、チェックポイント `chkpts/chkpt_00000`、Flyvis 1.2.0の対応する設定と `fib25-fib19_v2.2.json` を使用する。公式モデルは平均局所再構成から構成した格子上の視覚回路であり、全脳の実測細胞を一対一再現するものではない。公式学習済みパラメータの由来とハッシュはassets_manifest.json、実行時の不変性はvalidation.jsonを参照。

## 入力・状態・時間
設定は `configs/phase1.json`。100 Hz、dt=0.01秒、各24フレーム＝0.24モデル秒。背景0.5、対象1.0、半径6 px、移動60 px/s、拡大24 px/s。左右移動は同じ初期位置から対称方向。エピソードごとに1秒の一様灰色入力でウォームアップし、静的基準状態を作る。これは有限時間の緩和であり数学的な平衡収束を保証する名称ではない。公式最小例では別途random_walk_of_blocks＋fade_in_stateを実行する。

BoxEye(extent=15,kernel_size=13,ftype="mean")は公式の画像リサイズと13×13平均、六角格子サンプリングを用いる。画像(x,y)、格子(u,v)、モデルcell_indexを別フィールドに保持する。入力は[0,1]。時間方向の正規化や未来画像の使用はない。画像周期と積分dtは一致し、再サンプリングは行わない。

画像kは[k×dt,(k+1)×dt)に与え、保存応答はそのEuler更新後の状態。input_timeとresponse_timeを区別する。Rerunのinput_sample_sは4エピソードを連結した表示用時刻で、説明パネルに局所入力時刻と更新後時刻を明記する。実計算時間はCUDA同期を伴うperf_counter計測で別保存。ビューア再生速度は初期値0.25倍に設定し、HCW時間とは無関係。

## 科学的表示のルールと今回の未達
`nodes.activity` はPPNeuronIGRSynapsesのモデル電位で、較正されたmVやスパイク頻度ではない。T4aパネルでは各細胞のreset後基準からの変化を表示し、固定範囲[-1.5,+1.5]、青＝負、白＝ゼロ、赤＝正。初回試行で約[-1.18,+1.22]だったため1.5を採用して設定に固定した。再生中の自動正規化はしない。

メッシュはJFRC2由来の8領域をFAFB14.1座標で表示する。nm→µmの一様0.001倍のみ。カメラ視点は表示設定であり、解剖データを位置合わせ・変形しない。L/Rは元メッシュのラベル。Flyvis側の単眼応答を左右へ複製しない。

調査した公式資料と配布メタデータでは、モデルの左右・各格子細胞・解剖領域への根拠ある対応は確定できなかった。T4を単一領域へ排他的に割り当てる根拠もない。今回は全メッシュを中立色に保ち、別パネルで正確な格子応答を表示する。**脳形状への活動投影は未達。この代替は希望仕様の完成や変更承認を意味しない。** 全脳モデルへの変更も行わない。

## 環境の方針
専用venvのみを使用。sudo、システムPythonの変更、Linux用NVIDIAドライバー追加、全体アップグレード、PyTorchのソースビルド、カスタムCUDAを行わない。公式APIの小さな版適合以外の依存改変はしない。アカウント登録、有料サービス、データ公開、利用者の認証情報探索は行わない。

結果と再現手順は[phase1_report.md](phase1_report.md)、[README](../README.md)。取得元・版・SHA-256・利用条件は[assets_manifest.json](assets_manifest.json)。モデル・大容量データはGit除外。

格子表示は公式hex_to_pixelの平面式x=1.5v、y=-√3(u+v/2)を基準とし、Rerunの画面y正方向（下向き）に合わせてyだけ符号を反転する。これは格子パネルの表示座標で、メッシュの左右反転や位置合わせではない。BoxEyeの画像サンプリング座標そのものとも区別する。

## Phase 1Bで承認された仕様変更（2026-09-10）

上記のPhase 1の未達記録は当時の仕様として保持する。今回、**同じ細胞型のモデル群の実応答を、その型の代表的な実測形態に割り当てる表示**が明示的に承認された。この方式にはモデルと実測細胞の一対一ID・XYZ・半球対応を要求しない。必須なのは厳密な型注釈の対応、形態と背景の座標・単位の整合、集約値と表示上の限界の明示である。

T4aの721モデル細胞と、FlyWire 783の右側T4a `720575940605852192` の1形態を採用。形態全体に細胞別灰色基準からの変化RMSを一色で表示し、格子には各細胞の符号付き変化を残す。RMSは応答変化の大きさ・モデル単位であり、枝内電位、平均電位、発火頻度ではない。表示専用処理を将来の制御入力に混ぜない。固定色上限0.22は既存4試行から一度だけ算出した。

形態と既存背景はFAFB14.1のnmからµmへ変換する。実測の右側ラベルを保持し、モデルの左右は未割当。同じ形態の接写と全体文脈を同時に表示するが、形態の変形・位置合わせ・反転・多数複製はしない。対応は[Phase 1B専用表](anatomy_mapping_phase1b.json)へ保存し、一対一対応はfalse。旧accepted_mappingsは変更しない。

既存NPZを最初に検証して再利用し、その後1本の2.5秒の実刺激系列のみ追加した。元モデル・dt・前処理・状態保持・固定重みを維持し、Phase 1の出力とソースは保存。成果・実画面・検証範囲は[Phase 1B報告](phase1b_report.md)にまとめる。

現在の次の判断事項は、**この1種類の代表形態表示を次段階でも採用するか**。今回の成功を全脳活動表示の完成と扱わず、ユーザーの判断なしに型数の拡大・Phase 2・HCW・学習・閉ループへ進まない。

## Phase 2の現在の決定と結果（2026-09-11）

ユーザーはPhase 1Bの細胞型単位の代表表示を当面採用し、可視化方式未決定によるPhase 2保留を解除した。過去の個別細胞対応未達とaccepted_mappingsの記録は保持する。表示typeの最終決定は実応答を見て後から行い、今回はT4aのまま追加形態取得・型選別をしない。

FlyvisはT4aだけでなく、今回の構成では45,669個の視覚系モデル細胞を計算する。3D表示しているT4a形態は、別途取得した実測1細胞の形である。色はその実測細胞自身の活動ではなく、同型の721モデル細胞の電位変化を集約した値である。個別細胞の位置対応や枝内の電位伝播は計算していない。表示対象の細胞型は、計算対象や制御への読み出し対象とは別の選択である。

docs/codex_phase2.mdに従う2A〜2Dを実装・実行済み。固定カメラ画像→固定Flyvis→非入力57 typeの4×4符号付きプーリング→線形読み出し→各軸飽和→2D HCW。真の状態は教師・画像生成・評価のみで、学習器は画像しか受け取らない。

設定はconfigs/phase2.json。n=0.0011、目標[10,0,0,0]、a_max=0.005、物理dt=0.5秒、神経dt=0.01秒、比50。灰色reset後にu=0で物理10秒を観測する。成功条件は位置誤差<0.25 m・速度<0.01 m/sを20区間連続で満たすこと。最大400秒・初期範囲を学習前に固定。表示再生20倍とは別の時間対応である。

train 24／validation 6／test 12を試行単位で分離。指定6候補から現在値のみ・λ=1e-4をvalidationで選択し、追加教師付け0回。固定testは教師12/12、学習器接近8/8・近傍4/4が成功。限定条件の実測であり一般的な性能・従来法への優位性ではない。

成果はoutputs/phase2と[Phase 2報告](phase2_report.md)。再生用再実行は成功判定が一致したが最大約3.2 mmの位置成分差、0.5秒の終了時刻差があり厳密一致とは扱わない。RRDは各再実行自身の実軌道・活動・指令を同期する。詳細と再現コマンドは報告書を参照する。

## Phase 2Eの決定・表示と事後分析（2026-09-11）

今回のユーザー指令に基づき、Phase 2までのHCW・教師・学習済みFlyvis・確定readout・split・test結果を固定し、表示方向の変更と表示候補スクリーニングを実施した。物理座標はx=radial outward、y=along-track。表示のみX=-y、Y=x（上が正）へ変換する。Rerun Spatial2Dは画面Yが下向きのため描画座標を[-y,-x]とする。位置・goal・target・軌跡・速度・加速度矢印を同じ変換で描き、カメラ画像・受容格子・神経表示・物理スカラーは変換しない。

ユーザーは当面の細胞型単位の代表表示を採用する。T4a代表表示は「同型モデル群721細胞の灰色基準からの電位変化RMSを、別途実測された1細胞の形態へ表示したもの」である。その実測細胞自身の活動ではなく、モデル細胞との一対一ID・XYZ・左右対応はない。FlyvisはT4aだけでなく65型ラベル・45,669細胞の視覚回路を計算し、制御readoutは非入力57型・912空間特徴を用いる。T4a形態の全枝同一RMS色、格子の細胞別符号付き変化、固定色尺度を維持する。計算対象・学習対象・最終的な3D表示対象は別に定義する。

最終表示型はランデブー中の実応答と説明性を見て後からユーザーが決める。Phase 2Eでは元test12試行の65型のRMS、signed mean、状態・指令からの分析用局面、確定readoutの標準化後加算寄与を比較した。型ごとの寄与はpre-clippingの数値分解であり、因果的重要度ではない。局面・型候補選択を制御器入力や学習・test調整へ流用しない。T4/T5のsubtype suffixと今回の画面方向の対応は未確認で、推測ラベルを付けない。

表示比較候補はT2・Tm3・T5d・T4a・L2・Mi4・T4c・Tm1の8型。次の追加形態案はT2・Tm3・T5dの3型であり、取得は未実施。ローカルannotationのexact type存在だけを確認した。既存T4a形態は現状維持。球形ターゲット、別方向接近、goal変更、再学習、新規形態取得は今回実施していない。

成果はoutputs/phase2eと[Phase 2E報告](phase2e_report.md)。旧成果409ファイルのSHA一致、保存93試行・34,856フレームの再監査、単体68件、実RRD892フレームの照合と実描画を確認した。既存CUDA統合テストは2回とも1/2通過・1/2失敗（同一画像prefixの再実行出力が従来許容差を超過）。旧コード・重み・許容値は変更しておらず原因特定は未完了。保存済みPhase 2のtest成績は接近8/8・近傍4/4のままである。過去の個別解剖対応未達・Phase 2時点の検証記録は書き換えない。

## Phase 2Fの表示比較と判断材料（2026-09-11）

Phase 2/2Eの制御・学習・保存結果を固定し、既存ログだけでT2/Tm3/T4a/T5d/L2を同時比較した。RerunはPhase 2Eの軌道方向、実sensor image、5本のbar、5枚のsigned retinotopic map、T4a同一形態のabsolute/relative比較、raw/q時系列を表示する。追加の形態取得・代表本数の増加・枝内伝播演出・再学習・新しいランデブー条件は実施していない。

型RMSの校正は元held-out test12試行の制御期間のみ。試行iの各フレーム重みを1/(12 N_i)とし、混合経験分布の逆CDFから固定p05_j/p95_jを求める。q_j=clip((RMS_j-p05_j)/(p95_j-p05_j),0,1)をbarとrelative色に使い、raw RMSを併記する。毎フレームの正規化はしない。qは型自身の固定test範囲に対するレベルで、発火率・percentile rank・型間絶対比較ではない。q=0はp05以下であり活動ゼロを意味しない。range<=1e-8はneutral q=0.5とrelative_valid=falseで区別する。今回5型のscaleは全て有効。

細胞別全応答のある既存replay test_00/test_05の2試行について、各試行総重みを1/2として制御中|delta_v|のp99からsigned mapの固定対称limit_jを求めた。元test全12本のmapを評価したという意味ではない。型ごとに異なるlimitをタイトルと凡例に明記し、色強度を型間の絶対活動として比較しない。mapはモデルcell_index/u/vと細胞別符号付き応答を保持し、型aggregateで失われる正負・位置・広がりを示す。これは実脳内XYZとの一対一対応ではない。

T4aは既存実測1細胞ID 720575940605852192をそのまま使う。全枝同一色は721モデル細胞のRMS集約値であり、実測細胞自身の活動・枝内電位ではない。従来0..0.22と今回固定relativeの2ビューは同じ形態の尺度比較であり、新しい代表形態を追加したものではない。

成果はoutputs/phase2f、docs/evidence_phase2f、[Phase 2F報告](phase2f_report.md)。892フレームの実RRDを元活動・時刻・stateと照合し、native Rerunの再生/停止/seek、3局面の実画面、142フレーム・14.066秒のanimated WebPを確認した。MP4は既存エンコーダー不在のため作らず、既存Pillow/libwebpを使用。Windows GUIやブラウザ内での再生性能は未検証。単体84件は通過、既存GPU統合は1/2通過・1/2失敗（既知prefix再現差、閾値変更なし）。旧成果460ファイルはSHA一致で保持した。

今回の推奨はT4aの固定relative尺度とbar/mapの継続。5型のbarは似た経過を示すため、全型の3D形態追加を急がず、取得するならまずT2、T5dは説明目的に応じた候補、Tm3/L2はbar/mapを優先する。最終3D表示型・relative尺度・最終画面のmap採否はPhase 2F結果を見てユーザーが決定する。斜め接近などの新しい制御問題は別の判断事項で、今回の表示検証から制御成功を外挿しない。

### Phase 2FのMP4追加対応

初回報告後、ユーザーから動画ツール追加の許可を受け、imageio-ffmpeg 0.6.0同梱ffmpeg 7.0.2をプロジェクト内.tools/video/pythonへ分離導入した。既存venvの依存は変更していない。保存済みRerun描画142枚から30 fps・422フレーム・14.066667秒のH.264 MP4を生成し、全フレーム復号・元画像比較・時刻照合を実施した。新規推論・学習・制御実験・形態取得は0件。初回の未生成記録は当時の記録として残し、現行MP4と検証はoutputs/phase2f/mp4、詳細はphase2f_report.md末尾。


## Phase 3の現在の決定と結果（2026-09-11）

ユーザー指令[保存版](codex_phase3.md)に基づき、半径1 m球、中心距離5 m、goal=(-3.5355339,+3.5355339) m、固定boresight=(+1,-1)/√2の斜め下側standoffを実装した。旧成果を保持し、configs/phase3.json・outputs/phase3・docs/evidence_phase3・docs/phase3_report.mdへ分離した。

初期QをLVLHへそのまま使う教師は接近0/20（FOV外）、near10/10。Q/Rが初期案である指令に基づき、Qの同じ重みを接近radial/tangential軸へ回転した教師で30/30成功。球・goal・FOV・HCW・上限・成功条件を維持し初回失敗も保存した。カメラの円形silhouetteは真の球のpinhole接線境界から導いた保守的円近似で、軸外の厳密な楕円との差を明記した。

新seed3101/3102/3103のtrain24/validation6/test12、旧来の912特徴と指定6候補のみを使用。現時刻のみ・λ=0.0001がvalidation6/6で選択され、追加教師付け0round。固定後testは**接近8/8、near2/4**、FOV外1、timeout1、衝突0。教師test12/12、旧readout zero-shot0/4。test後の再調整・教師救済・再評価なし。

DemoとAnalysisは同じ元test記録を使用し、再生用再推論を廃した。T4a1形態と脳背景、5型bar、DemoのT2/T4a/T5d mapを同時表示。relative/map尺度は非test教師30本から固定した。45,669細胞計算、57非input型readout、5型表示、T4a721モデル細胞→1実測形態の区別と限界を維持する。

単体96/96、保存155試行・51,875ステップ、両RRD各777フレーム、旧681ファイル不変を確認。既存GPU統合は1/2失敗（既知prefix比較、閾値不変）。詳細は[Phase 3報告](phase3_report.md)。指定範囲を終了し、near改善、追加形態、別条件、演出への追加実験は自動で行わない。


## Phase 3V：代表形態とDemo GUI（2026-09-11）

ユーザー指令に基づき表示のみを仕上げた。旧Phase 3 RRDにT4a777時点と背景7 entity、2つのBrain 3D viewは存在したが、最終試行後のRESETで形態が消えることを再現した。3Vでは試行間RESETを残し、最終観測を保持する。脳の小さな分割パネルを大きな右視葉Brain Viewへ再配置した。

公式annotation固定commitからexact T2（720575940608937923）・T5d（720575940623043327）の右側代表を各1本だけ取得。既存T4a（720575940605852192）を再利用し、FAFB14.1 nm→µm以外の変形なし。型ごとの実モデル群RMSと、Phase 3の非test30試行で固定済みp05/p95からqを使う。固定色系統orange/blue/magentaのRGBを0.35+0.65q倍し、全枝同色。低qでも見える表示下限は実活動を追加したものではない。

Demoは大きなorbitとBrain、sensor、T2/T4a/T5d maps、小さな5型bars/status。Analysisに全5型mapと詳細系列。形態は実測細胞自身の活動・一対一対応・枝内伝播を意味せず、計算対象45,669細胞のうち同型群を集約した代表表示である。

制御・readout・HCW・完全固定sensor camera・target/goal・testは不変（接近8/8、near2/4）。新推論・制御実験0、旧1,297ファイルのSHA一致、単体106件、各777フレームのRRD照合、実画面・14.633秒動画を検証。既知GPU prefix問題は未解決のまま、今回GPU統合テストは再実行していない。

[Phase 3V報告](phase3v_report.md)、[形態来歴](anatomy_mapping_phase3v.json)。成果はoutputs/phase3v。README先頭から最新版を開く。追加形態・新条件・再学習・ROS/MuJoCo・演出へ進まず終了する。


## Phase 3P：T2 measured population比較（2026-09-11 JST）

ユーザー指令に基づき、3Vと同じ固定FlyWire注釈のexact T2/right全725本を取得・検証した（724本新規、既存T2 1本再利用、失敗0）。864,608頂点・863,883辺を省略せずFAFB14.1 nm→µmだけで表示する。T4a/T5dは代表各1本のまま。各rootの原注釈・SHA・辺/頂点offsetを保持する。

FlyWire measured population725本とFlyvis model population721細胞を区別する。一対一対応なし、全実測T2に同じモデル群のtype-level aggregate RMS/qを適用。個別実測細胞のactivity、枝内伝播ではない。Phase 3でtest前に固定したrelative尺度・brightness方式を維持し、population線幅/alphaだけを静的表示設定にした。元の形態座標、fixed sensor camera、制御、readout、HCW、test条件・結果（approach8/8、near2/4）は不変。

outputs/phase3pに代表modeとpopulation modeの両RRD、実画面・動画・描画負荷比較を分離。非GPU単体111件と全777時点の照合、旧1,451成果のSHA一致を確認。主発表には代表mode、解剖分布説明にはT2 populationの補助利用を推奨。Windows GUIの実時間性能は未検証。詳細は[Phase 3P報告](phase3p_report.md)と[全形態来歴](anatomy_mapping_phase3p.json)。T4a/T5d populationや他typeの取得、新制御実験へは進まず終了する。


## Phase 3W：36実測代表形態とbilateral context（2026-09-11 JST）

ユーザー指令[保存版](codex_phase3w.md)に基づき、T2/T4a/T5d各12本を選択・表示した。固定annotation commit、exact type/right、整数root安定ソート、既存代表1本固定＋PCG64で11本一様抽出。型別seedは310401/310402/310403。T2の12本と既存T4a/T5d各1本を再利用し、T4a/T5d不足22本のみ新規取得・検証した。36本は30,321頂点・30,285辺、座標はFAFB14.1 nm→µmのみ。

ローカルJFRC2由来archiveの全78 neuropil meshを列挙し、未展開70を追加抽出した。左右ME/LO/LOP・FB/EB・中央側を含む部分的なbrain anatomy contextで、完全な全脳神経再構成や頭部外形ではない。中立wireframeにactivityは割り当てず、灰色を活動ゼロと解釈しない。

同型12形態は同じtype-level RMS/q・固定relative brightnessで同期する。個別Flyvisモデル細胞との対応や枝内伝播はない。retinotopic mapとraw RMS barは従来のまま。Demoは全体context、Analysisは全体＋右視葉接写。主発表には36本Mode B、細部説明に1本Mode A、T2分布の補足に旧full population Mode Cを推奨する。

Phase 3の制御・readout・HCW・完全固定sensor camera・test結果（approach8/8、near2/4）は不変。非GPU121件、各777時点照合、旧2,431成果SHA一致、動画74枚・MP4全439枚を検証。Windows GUI実時間性能は未検証。成果はoutputs/phase3wと[報告](phase3w_report.md)、[形態・背景来歴](anatomy_mapping_phase3w.json)。ここで停止し、全population化や新制御実験には進まない。


## Phase 4A scope

ユーザー指令 `docs/codex_phase4a.md` により、Phase 3WのDemoへFly Pilot Viewを追加する。保存済み `u_applied` だけを操縦桿へ同期し、外部ハエは説明用固定姿勢とする。これはpresentation layerでありbiological motor outputではない。制御・readout・HCW・fixed sensor camera・Phase 3 test結果は固定。実装・出力・証拠はphase4aとして分離し、結果を `docs/phase4a_report.md` に保存した時点で停止する。


## Phase 4B結果（2026-09-12 JST）

ユーザー指令[codex_phase4b.md](codex_phase4b.md)に基づき、Blender primitiveによるA/B/Cと、既定B＋左右2-link IKを実装・実行・検証した。外部asset追加なし。Phase 4Aのu_appliedとjoystick geometryをそのまま使用し、body固定、左右footはgrip±0.11へ追従。各link0.62、下向きpole固定、clampあり。3/4 Pilot cameraと正確な平面guideを併用する。これは説明用presentation layerであり、実測解剖・生物学的motor outputではない。

非GPU144 passed、GPU integration 2 deselected。A/B/C・全segmentの再生成SHA一致、各RRD777 sampleのFK照合、旧2,913ファイル不変を確認。Phase 3 testはapproach8/8・near2/4、再推論・再学習・新制御実験0。実画面、A/B/C比較、4A比較、14.633秒MP4を保存した。[Phase 4B報告](phase4b_report.md)。Bを内部勉強会の補助Pilotへ推奨するが、遮蔽・自己接触回避なし・斜め投影の限界を記録した。ここで停止し、次Phaseへ自動着手しない。


## Phase 4C実施記録

ユーザー指令 docs/codex_phase4c.md に基づき、Fly Pilotの造形だけを変更。C1/C2/C3をprocedural生成しC2 defaultで統合した。前脚のPhase 4B IK・肩・0.62/0.62リンク、joystick信号と同期、両カメラ、Rerunレイアウト、全制御結果は不変。新推論・学習・制御実験は0。参考画像は体型の参考だけであり、外部asset・image-to-3D・texture抽出を用いない。

成果は assets/fly_pilot_phase4c、outputs/phase4c、docs/evidence_phase4c、docs/phase4c_report.md。non-GPU 150件通過。全777サンプルの両脚先・関節変換・非形状Pilot成分をPhase 4Bと照合し、他ビュー441 streams / 53,977値も一致。Phase 3 approach 8/8、near 2/4を保持。SpaceROS勉強会用のpresentation layerであり、生体解剖・motor neuron・muscle modelではない。Phase 4C報告時点で停止し、新機能・制御実験へ自動移行しない。

## Phase 5B実施記録：Gate 5で停止

[Phase 5B指令](codex_phase5b.md)に基づき、新しい25–35 m / cross ±4 m、36/12/8の固定splitでnominal HCW教師・神経データ・readout学習を実行した。Flyvis、画像専用入力、HCW設定、fixed camera、成功条件、既存成果は保持。6候補1 round・augmentationなしを事前固定した。

教師56/56、データ48/48。選択lag0/lambda1e-4のvalidation成功1/12、H0 learner成功0/8（range exit5/FOV exit3）、state LQR8/8。事前停止基準6/8未満によりtruth評価へ進んでいない。readoutやtest条件は再調整していない。

two-body/J2/SRP/drag/residualの物理関数・座標・RK4精度gateは通過。physical perturbationとresidual stressは別条件。T0/T1/E0/Elo/Ehi/R1/R3/R5/RM3のheld-out結果は未実行。test_00を事前固定したmain caseとして保持し、H0失敗のRRD/動画だけを保存した。

non-integration169 pass、GPU integrationは1 pass/1 fail（prefix精度、単独再確認もfail）。旧成果SHA・Phase 4C GUI回帰・保存ログ監査はpass。詳細・制約・再生方法は[phase5b_report.md](phase5b_report.md)。Phase 3のapproach8/8・near2/4は不変。次の改良には別Phaseと新splitが必要で、このtestを調整用に再利用しない。Phase 5Cやtruth追加試行は開始せず停止。

## Phase 5B-R：train-only dataset aggregation

fresh split（36/12/8、seed5201/5202/5203）で教師56/56成功後、同じ6候補の線形readoutを最大2roundのtrain-only追加ラベルで学習した。Flyvis・HCW・fixed camera・goal・飽和・成功条件は固定。最終Round 1のvalidationは11/12成功、fresh test 8/8成功。旧5B test8本を学習・選択・回復判定へ再利用していない。truth評価は未実行。

[Phase 5B-R報告](phase5br_report.md)に各round、sample出典/cap、特徴分布、終端安定化、GPU既知prefix問題、旧成果保護を記録。nominal recoveryを達成したが、truth評価へ自動移行せず停止した。
