# FlyRendezvous
宇宙ロボット技術チームの勉強会用に、生物由来の視覚回路の実応答を説明する。
今回の範囲はPhase 1のみ。HCW、LQR、読み出し学習、閉ループ制御を先回りして実装しない。
学習済みFlyvis以外をデモ経路に代入しない。全脳・実測細胞との一対一対応や発火頻度を称さない。
解剖への投影は根拠・粒度・集約・固定色尺度を示し、未モデル化領域を活動ゼロと区別する。
仕様はdocs/project.md、実測と未達事項はdocs/phase1_report.mdに保存する。
検証: `.venv/bin/python -m pytest tests -m "not integration"`。
実モデル検証: `.venv/bin/python -m pytest tests -m integration`（skipは達成ではない）。

## Phase 1Bの承認済み範囲

現在の追加作業はPhase 1B。上記Phase 1の境界・報告は履歴として維持する。
同型モデル群の応答を、型注釈が確認された1代表形態へ表示してよい。一対一ID/XYZ/左右対応の不足だけでは、この方式を却下しない。
必須条件は型対応の根拠、背景との座標整合、表示専用RMSと限界の明示。形態IDをモデルcell_indexへ割り当てない。
T4a 1型・FlyWire 783 root ID 720575940605852192の1形態まで。右側由来、モデル左右未割当、一対一対応false。
形態は全枝同一RMS色、格子は細胞別符号付き変化。枝内電位・伝播・発火頻度を称さない。
Phase 1の元ソース・設定・出力・報告・accepted_mappingsは保持し、追加はphase1b名の資産・設定・出力・報告へ分離する。
詳細はdocs/phase1b_report.mdとdocs/anatomy_mapping_phase1b.json。数値から実RRDまでの照合は `.venv/bin/python scripts/verify_phase1b.py`。
次はこの可視化方式の採否をユーザーが判断する。多数型・全脳表示・HCW・学習・閉ループを先回りしない。

## Phase 2実施記録（2026-09-11）

ユーザー指令 docs/codex_phase2.md に基づく2A〜2Dの実装・実行・検証が完了した。結果と現在の決定は docs/phase2_report.md、設定は configs/phase2.json、保存結果は outputs/phase2。
ユーザーはPhase 1Bの代表表示を当面採用した。計算対象45,669細胞、読み出し対象57 type、表示T4a 721細胞のRMSを区別する。追加形態取得は実施していない。
固定testの学習器は接近8/8・近傍4/4が成功。再生用再実行には微小な数値差があるため、厳密一致とは扱わない。過去の個別対応未達の報告と証拠は保持した。
再生コマンド: `RERUN_ANALYTICS_ENABLED=false .venv/bin/rerun outputs/phase2/phase2.rrd --bind 127.0.0.1`。
追加検証: `.venv/bin/python scripts/verify_phase2.py`、`.venv/bin/python scripts/verify_phase2_rrd.py`。既存の単体・実GPU統合テストも実行済み。
今回の作業は終了。次の新規実験や対象拡大は新たなユーザー指令による。
