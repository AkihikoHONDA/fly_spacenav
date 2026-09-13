# Phase 4C報告：semi-stylized Fly Pilot

C1/C2/C3を生成し、**C2をdefaultとしてDemo / Analysisへ統合した**。制御・joystick・左右前脚IK・両カメラ・レイアウトはPhase 4Bと同じ。新たな推論・学習・制御試行は行っていない。成果をPhase 4Cのディレクトリへ分離した。

[Demo実画面](evidence_phase4c/demo_early.png) ／ [C1/C2/C3](evidence_phase4c/design_comparison.png) ／ [4A/4B/4C実画面比較](evidence_phase4c/phase4a_vs_4b_vs_4c.png) ／ [14.63秒MP4](../outputs/phase4c/mp4/phase4c_test00.mp4)

## 範囲と造形方針

AGENTS.md、README、project、Phase 4B報告・生成器・パラメータ・IK・viewer・検証・captureと既存証拠画像を確認した。今回のユーザー承認はPhase 4Cの造形改善に限定される。AGENTSの過去Phase停止指示と既存報告は履歴として残した。

Phase 4Bの残課題は、大きな球形head、貼り付けた丸いeye、弱い胸腹部の差、腹部taper不足、白い板状wing、太い棒状leg、マスコット寄りのsilhouetteだった。C2では胸部・腹部の輪郭を分け、目と翼と脚を改善した。身体や翅の動きは追加していない。

[参考画像](reference/rubik_fly_reference.png)から参考にしたのは、厚い胸部、細長い腹部、左右から前面へ回る赤い目、薄い細長い翅、細い脚という体型の方向性だけ。mesh reconstruction、image-to-3D、texture extraction、exact tracingはしていない。generatorは画像を読み込まない。体毛、複眼facet、口器、キューブ、背景をコピーしていない。[使用記録とSHA](../outputs/phase4c/reference_provenance.json)を保存した。参考画像の再配布ライセンスは推定していない。

## C1/C2/C3と寸法

![C1 C2 C3](evidence_phase4c/design_comparison.png)

| 案 | 造形差 | visual inspection |
|---|---|---|
| C1 | 縮小head、埋め込み楕円eye、先細り腹部、薄い翅、脚taper。触角・翅脈なし | 最小限の改善。細部が少なく読みやすい |
| **C2** | 胸腹部の差を強め、前寄りeye、長いwing、短い触角2本、各翅2本の薄い幾何学的翅脈 | 胸部と腹部が分かれ、4Bより飛翔昆虫らしい輪郭。指定どおりdefault |
| C3 | C2のhead / eyeを約6%拡大し、腹部を短縮 | friendly寄り。小パネルではC2との差は小さい |

以下はpresentation用の任意単位。生体寸法・HCW座標・FAFB14.1とは無関係。腹部寸法はtaper変形前、wing幅は生成パラメータであり最終投影幅ではない。

| 寸法 | Phase 4B B | C1 | C2 | C3 |
|---|---:|---:|---:|---:|
| head基準径（最大軸） | 1.0625 | 0.935 | 0.903125 | 0.9573125 |
| head XYZ | 1.0625 / 1.0625 / 1.0625 | 0.78 / 0.935 / 0.84 | 0.73 / 0.903125 / 0.81 | 0.774 / 0.9573125 / 0.859 |
| thorax L/W/H | 0.95 / 0.80 / 0.76 | 1.00 / 0.80 / 0.84 | 1.05 / 0.80 / 0.89 | 1.03 / 0.81 / 0.88 |
| abdomen L/W/H | 1.10 / 0.64 / 0.66 | 1.20 / 0.58 / 0.58 | 1.28 / 0.56 / 0.59 | 1.20 / 0.57 / 0.60 |
| wing L/W | 1.25 / 0.60 | 1.40 / 0.52 | 1.50 / 0.48 | 1.46 / 0.50 |
| leg radius proximal→distal | 0.060 uniform | 0.051→0.048 | 0.0492→0.0468 | 0.0504→0.0474 |

仕様内のhead「12〜18%縮小」と例示「0.88–0.93倍」は範囲が一致しないため、C2は前者を優先して基準径を15%縮小した。前後軸はさらに扁平化し、head中心を[0.015,0.25,1.62]へ寄せた。C3はC2比6%増を優先した。詳しい全値は[design_params.json](../assets/fly_pilot_phase4c/design_params.json)。

## 目・翼・脚

C2の目はXYZ **0.43 / 0.24 / 0.54**の縦長楕円体。中心は[0.25, 0.25±0.325, 1.64]、左右で逆向きの約26°回転を加え、頭部に一部を埋め込んだ。くすんだ赤色と小さなhighlightのみで、facetはない。頭部との重なりを持つが、小パネルではなお赤い丸いパーツとして見える角度がある。

Wingは閉じた厚い楕円体から、丸い輪郭の薄い単一曲面へ変更。thorax上部から後方へ伸びる。左右pitch差は0.12 rad（約6.9°）。C2 alpha **0.28**、gray-blue、roughness 0.7、emissionなし。各2本の細いvein geometryを加えた。実Rerunでは4Bの白い板感が減り、重なった輪郭が透けて見える。透明度の見え方はrenderer依存。

LegはC2で**18〜22%細く**し、proximalからdistalへ円錐状にtaperした。関節球とcontact tipも縮小した。中・後脚の基部を胸部側、先端を横方向へ広げ、4本の支持脚の底面を従来の床面Z=-0.045へ合わせた。床接触は静的な見た目であり、接触物理の計算ではない。

## IK・カメラ・Rerun統合

**肩位置は変更していない。** 左[0.12,0.63,1.16]、右[0.12,-0.13,1.16]。前脚length **0.62 / 0.62**、grip transverse offset **±0.11**、pole rule、clamp、IKの分岐、rotation hierarchyは従来どおり。新IKは実装せず、[ik_phase4b.py](../src/flyrendezvous/ik_phase4b.py)を直接importしている。

変更したのはbodyと6個のlimbの静的GLB。joint originとlocal +Zは維持し、777サンプルの全joint transformをPhase 4B RRDと完全一致で照合した。画面のcommand値・guide・joystick・resetも同じ。a_disp=[-ay,ax]、a_ref=0.005 m/s²は不変。

Pilot camera position [1.35,-1.95,3.85]、look [-0.15,0.25,1.05]、up Zの3/4視点をそのまま使用。sensor cameraも固定。Demo / Analysisのlayoutは変更せず、viewerソースの差分はPhase名・出力先・pilot importだけであることをテストした。

![Demo actual Rerun frame at 20 s](evidence_phase4c/demo_early.png)

## 実画面と動画

既存のtest_00を用いた。静止画は**実際のRerun 0.37.1 native renderer**の出力。Blender design renderと区別している。時刻・元ログSHA・u_applied・RRD SHAは[screenshots_demo.json](evidence_phase4c/screenshots_demo.json)にある。

| 物理時刻 | 用途 | 実画面 |
|---|---|---|
| 0 s | observe / neutral（u=0） | [neutral](evidence_phase4c/demo_neutral.png) |
| 20 s | early approach | [early](evidence_phase4c/demo_early.png) |
| 85 s | braking | [braking](evidence_phase4c/demo_braking.png) |
| 219 s | near / hold | [hold](evidence_phase4c/demo_hold.png) |

接近時に前へ傾くjoystickを両脚が追い、制動・holdでは中立付近へ戻る。元ログの小さな指令は小さな動きのまま。身体・翅は静止し、架空の運動や見た目用の平滑化はない。遠側脚が重なる角度は残る。

[MP4](../outputs/phase4c/mp4/phase4c_test00.mp4)は**14.633秒、1600×1000、30fps、H.264、1,106,762 bytes**。0〜219 sを15倍速。実Rerun capture 74枚（6保存sampleごと＋最後）を次captureまで保持して439動画フレームへ変換し、神経活動・commandの補間はしていない。30fpsで新しい姿勢を計算しているわけではない。

MP4の全439 decode frameの時刻を照合し、対応する元画像との最小PSNR 40.327 dBを確認。[MP4検証](../outputs/phase4c/mp4/verification.json)。実viewerで連続playを開始し、時刻進行を9枚記録、219 s到達、pause保持、seek一致も確認した。[連続再生とcapture manifest](../outputs/phase4c/video_manifest_demo.json)。WebP全74 decode frameの相違とdurationも確認済み。[動画確認](../outputs/phase4c/video_review.json)。これはnative headlessでの再生検証であり、Windows上のマウス操作や発表PCの実時間FPSの測定ではない。

## 回帰・テスト

| 検証 | 結果 |
|---|---|
| non-GPU tests | **150 passed / 0 failed / 2 integration deselected** |
| C1/C2/C3・default・6 limb・manifest再生成 | Blender 4.0.2、SHA-256が完全一致 |
| original saved samples | **777 / 777** |
| 実Rerun描画・時刻照合・画面取得 | **777 / 777**、2240×1400 |
| 両前脚の独立FK検証 | **1,554 / 1,554** target到達 |
| 最大FK接触誤差（RRD float32） | 7.8972×10^-8 presentation units |
| 前脚length | 0.62 / 0.62、全sample一致 |
| new clamp | **0** |
| IK flip | **0**、隣接bend最小内積0.477944 |
| 非Asset Pilot component | Phase 4Bと全値・時刻が一致 |
| Orbit / Brain / sensor / maps / bars / status等 | **441 streams / 53,977値**、全値・時刻が一致 |
| 保護した旧成果ファイル | **3,068 / 3,068** SHA不変 |
| Phase 3 test | approach **8/8**、near **2/4**の既存結果を維持 |
| 新推論・学習・制御実験 | **0** |

[独立FK / Pilot検証](../outputs/phase4c/pilot_verification.json)、[既存成果回帰](../outputs/phase4c/regression.json)、[pytest XML](../outputs/phase4c/pytest.xml)、[テスト履歴](../outputs/phase4c/test_history.json)。

最初のテストは新規layout比較がapplication名の大文字差を未考慮で1件失敗し、4B/4CのBlender再生成が60秒timeoutで2件失敗した。新規比較だけを修正し、OMP_NUM_THREADS=1 / OPENBLAS_NUM_THREADS=1で再実行したところ全150件が11.50秒で通過した。旧テスト・timeout・数値許容差を変更していない。並列数による実行条件差はあるが、timeout原因の低レベル解析までは行っていない。

既存Phase 3 GPU統合の既知prefix再現性問題は過去記録のまま。今回は推論を禁止しているためintegrationを再実行せず、結果を改善したとは扱わない。near失敗2件の調整もない。


全777保存sampleを実viewerで個別seekし、2描画stepを待ち、時刻一致を確認してフル画面PNGを取得した。Pilot領域の非blankも検査した。所要588.38秒。[全描画記録](../outputs/phase4c/all_frames_render.json)に777枚分の時刻・trial・sample・PNG SHAを保存し、作業用PNGは上書きして最後の1枚だけ保持した。非blank検査は美観評価ではなく、表示成立の機械的確認である。

## 4A / 4B / 4Cのvisual inspection

![same-sized actual Pilot crops](evidence_phase4c/phase4a_vs_4b_vs_4c.png)

全てtest_00の20 s、2240×1400画面から同じ505×425領域を切り出し、**resizeなし**で比較した。4Aの既存overhead cameraと4B/4Cの3/4 cameraは異なる。4Aを新たに描き直して印象を合わせてはいない。[比較元画像・SHA・crop](evidence_phase4c/comparison.json)。design比較はBlenderの同一camera/light・neutral pose、実画面比較とは光源が異なる。

以下は**visual inspection（画像に基づく定性的所見）**であり、美観・怖さ・認識率を測定した数値スコアではない。

| 観点 | 4A | 4B B | 4C C2 |
|---|---|---|---|
| fly認識・silhouette | 細部は昆虫的だが暗いbody | friendlyだが球形キャラクター寄り | 頭部縮小、胸腹部の分離、後方taperで4Bよりfly-like |
| friendliness | 細かい写実要素が目立つ | 最もtoy寄り | 丸みとwarm paletteを維持し、写実的な毛・口器を加えていない |
| eye | 小パネルで暗く潰れやすい | 球を貼った印象 | 赤い縦長楕円体、頭部へ重ねたが丸い部品感は一部残る |
| wing | 翅脈・白さが目立つ | 白い板状 | 細長い透明gray-blue、白潰れが減少 |
| leg | 固定姿勢 | 太い棒と大きいjoint | 細いtaper、支持脚が横へ広がる |
| 小パネル | joystickと固定bodyの関係は弱い | body・gripは読みやすい | body輪郭・wing・gripは読める。触角・veinは控えめ |
| joystick / forelegs | joystickのみ同期 | 両前脚IK、XY guide併記 | 同じ同期・IK・guide。遠側脚の遮蔽は残る |

参考画像の「厚い胸部＋先細り腹部＋薄い翅」というsemi-realistic silhouetteへ近づいた一方、参考画像の細かな顔・体毛・翅脈は再現していない。C2はこの範囲で止め、見た目を理由に構造や機能を増やしていない。

## 描画コスト

同じ2240×1400 native headless software renderer。起動には2秒の待機を含み、screenshot時間はIPC / readback / PNG書出し込み。FPSと読み替えない。

| 指標 | 4A | 4B | 4C |
|---|---:|---:|---:|
| Demo RRD bytes | 8,711,413 | 8,623,356 | 8,679,754 |
| first seekまで | 2.405 s | 2.401 s | 2.450 s |
| screenshot RPC中央値 | 0.516 s | 0.522 s | 0.519 s |
| viewer RSS | 880,556 kB | 894,528 kB | 880,212 kB |
| peak RSS | 887,468 kB | 907,200 kB | 892,996 kB |
| 74枚capture所要 | 56.64 s | 57.24 s | 57.20 s |

C2 bodyは35 objects / 4,224 vertices / 8,248 triangles。body＋6 limbで307,732 bytes（4Bは292,056 bytes、約5.4%増）。Demo RRDは約0.65%増。この測定では大幅な描画負荷増は観測されないが、RSS差を性能改善の証拠とは扱わない。[performance.json](../outputs/phase4c/performance.json)、[asset manifest](../assets/fly_pilot_phase4c/manifest.json)。

## 再生成・再生コマンド

WSLのプロジェクトルートから実行する。Blender / ffmpegは既存環境を再利用した。

~~~bash
blender --background --disable-autoexec --python-exit-code 1 --python assets/fly_pilot_phase4c/generate_fly_phase4c.py
.venv/bin/python -m flyrendezvous.viewer_phase4c
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4c/demo.rrd --bind 127.0.0.1
RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase4c/analysis.rrd --bind 127.0.0.1

env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -m pytest tests -m "not integration" -q
.venv/bin/python scripts/verify_phase4c_pilot.py
.venv/bin/python scripts/verify_phase4c_regression.py
.venv/bin/python scripts/capture_phase4c.py --mode demo --video
.venv/bin/python scripts/capture_phase4c.py --mode analysis
.venv/bin/python scripts/render_all_phase4c.py
.venv/bin/python scripts/compare_phase4c.py
.venv/bin/python scripts/review_phase4c_video.py
.venv/bin/python scripts/export_phase4c_mp4.py
~~~

capture / render_allは同一localhostポート9890を使用するため順番に実行する。generatorの再現性はGLB単位、RRD自体にはrecording metadata等があるため再生成後はcapture/videoのSHA対応も更新する。既存4A/4Bを上書きしない。

## 残る制約と採用判断

**SpaceROS内部勉強会ではC2を補助Pilot表示として採用することを推奨する。** 4Bの同期と読みやすさを保ちながら、wingと腹部の輪郭が改善した。C1/C3はレビュー用に保存し、指定どおりC2 defaultで止める。

これはsemi-stylizedな**presentation model**でありactual fly anatomyではない。実測T2/T4a/T5d神経形態とは別の説明用bodyで、Flyvisは生物学的な脚関節出力を生成していない。前脚はillustrative IK、motor neuron・muscle・physical contact・全身運動・操作力のモデルではない。

小さいパネルでeyeの回り込み、触角、細いveinは弱く、遠側脚の重なり、3D投影単独の方向理解、自己接触回避なしという制約は残る。中・後脚は固定、羽ばたきなし。小さなhold指令を誇張していないためholdの動きは僅か。Windows手動GUI操作と発表PC実時間FPSは未検証。新しい制御条件・神経モデル・全身力学・Phase 5へ進まない。
