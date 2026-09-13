# ドキュメント

[プロジェクト概要](../README.md) / [セットアップ・実行](getting_started.md)

READMEは現在のリポジトリの入口です。Phase別報告書はその時点の条件・判断・結果を記録し、後の実装によって過去の失敗や未達を上書きしません。

## 設計・開発記録

- [プロジェクトの目的と段階ごとの決定](project.md)：時系列の設計記録。冒頭の「今回」は当時のPhaseを指します。
- [旧README・開発履歴](development_history.md)：README再編前の記載を保存。過去の「最新」「次の判断」「ここで停止」は当時の記述です。

## 実験・表示の報告

| Phase | 内容 |
|---|---|
| [1](phase1_report.md) | 学習済みFlyvisの状態保持、実刺激応答、数値記録 |
| [1B](phase1b_report.md) | T4aの実測代表形態と型単位の活動表示 |
| [2](phase2_report.md) | HCW教師、画像データ、readout学習、閉ループ評価 |
| [2E](phase2e_report.md) / [2F](phase2f_report.md) | 軌道表示、候補型の解析、bars・maps・相対尺度 |
| [3](phase3_report.md) | 球形ターゲットへの斜め方向のstandoff rendezvous |
| [3V](phase3v_report.md) | T2/T4a/T5dの代表形態とBrain View |
| [3P](phase3p_report.md) / [3W](phase3w_report.md) | T2 populationと各型12本の表示比較 |
| [4A](phase4a_report.md) / [4B](phase4b_report.md) / [4C](phase4c_report.md) | Fly Pilot、joystick同期、前脚IK、造形 |
| [5A](phase5a_report.md) | 保存済み閉ループログの制御量分析 |
| [5B](phase5b_report.md) | 25–35 m条件での学習、nominal失敗、物理摂動評価基盤 |
| [5B-R](phase5br_report.md) | 新splitとtrain-only追加ラベルによるnominal回復 |

## 出典・対応付け

- [モデル・脳領域資産manifest](assets_manifest.json)
- [初期の解剖対応調査](anatomy_mapping.json) / [T4a代表表示](anatomy_mapping_phase1b.json)
- [T2/T4a/T5d代表形態](anatomy_mapping_phase3v.json)
- [T2 population](anatomy_mapping_phase3p.json) / [各型12本の実測形態](anatomy_mapping_phase3w.json)

## Gitに含める文書と生成物

案内文書、Phase報告書、設計記録、出典・対応表をGit管理対象にしています。取得資産、数値ログ、RRD、動画、証拠画像、元の作業指令などは別管理です。報告書中のそれらへのリンクは、該当ファイルを持つ作業環境で参照してください。

今回のREADME再編では説明文書と文書用のGit除外設定だけを更新しています。制御器、readout、物理モデル、カメラ、既存test結果は変更していません。
