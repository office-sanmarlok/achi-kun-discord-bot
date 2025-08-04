# リファクタリング詳細計画書

## 1. 概要

このドキュメントでは、akdb-refactorプロジェクトのリファクタリング計画を詳細に説明します。
主な目的は、重複コードの削除、未使用コードの除去、そして構造の最適化による保守性の向上です。

## 2. 現状の課題と解決策

### 2.1 Git操作の重複

#### 現状の構造
```
command_manager.py
├── handle_idea_complete()      # Git操作コード（30行）
├── handle_requirements_complete() # Git操作コード（30行）重複
├── handle_design_complete()     # Git操作コード（30行）重複
└── handle_tasks_complete()      # Git操作コード（30行）重複
```

#### リファクタリング後の構造
```
command_manager.py
├── _execute_git_workflow()      # 共通Git操作（30行）
├── handle_idea_complete()       # _execute_git_workflow()を呼び出し（5行）
├── handle_requirements_complete() # _execute_git_workflow()を呼び出し（5行）
├── handle_design_complete()     # _execute_git_workflow()を呼び出し（5行）
└── handle_tasks_complete()      # _execute_git_workflow()を呼び出し（5行）
```

**削減効果**: 120行 → 50行（70行削減）

### 2.2 コマンド実行関数の統合

#### 現状の構造
```
プロジェクト全体
├── command_manager.py
│   └── _run_command()           # 非同期コマンド実行（20行）
├── project_manager.py
│   ├── execute_git_command()    # Git専用実行（25行）重複
│   └── _run_command()           # 汎用実行（20行）重複
└── lib/utils.py
    └── run_command()            # 同期実行（15行）
```

#### リファクタリング後の構造
```
プロジェクト全体
├── lib/command_executor.py      # 新規作成
│   ├── async_run()              # 非同期実行（25行）
│   └── sync_run()               # 同期実行（15行）
├── command_manager.py
│   └── （command_executor.async_run()を使用）
└── project_manager.py
    └── （command_executor.async_run()を使用）
```

**削減効果**: 80行 → 40行（40行削減）

### 2.3 プロンプト生成関数の汎用化

#### 現状の構造
```
claude_context_manager.py
├── generate_idea_prompt()       # 45行
├── generate_requirements_prompt() # 50行（ほぼ同じ構造）
├── generate_design_prompt()     # 65行（ほぼ同じ構造）
├── generate_tasks_prompt()      # 65行（ほぼ同じ構造）
└── generate_development_prompt() # 60行（ほぼ同じ構造）
```

#### リファクタリング後の構造
```
claude_context_manager.py
├── _generate_prompt_base()      # 共通ロジック（40行）
├── _get_stage_config()          # ステージ別設定（20行）
└── generate_prompt()            # 統一インターフェース（15行）
    
# 使用例：
# generate_prompt("idea", idea_name, **kwargs)
# generate_prompt("requirements", idea_name, **kwargs)
```

**削減効果**: 285行 → 75行（210行削減）

### 2.4 セッション管理の一元化

#### 現状の構造
```
セッション管理（分散）
├── session_manager.py
│   ├── SessionData              # データ管理
│   ├── create_session()
│   ├── delete_session()
│   └── get_session()
├── tmux_manager.py
│   ├── create_tmux_session()    # TMUX専用
│   ├── kill_tmux_session()
│   └── list_tmux_sessions()
└── thread_context_manager.py
    ├── manage_thread_context()   # スレッド専用
    └── get_thread_sessions()
```

#### リファクタリング後の構造
```
unified_session_manager.py        # 新規作成
├── SessionManager                # 統合クラス
│   ├── _tmux_backend            # TMUX操作
│   ├── _thread_backend          # スレッド操作
│   ├── _data_backend            # データ管理
│   ├── create()                 # 統一API
│   ├── delete()                 # 統一API
│   ├── get()                    # 統一API
│   └── list()                   # 統一API
└── SessionType                  # Enum (TMUX, THREAD, HYBRID)
```

**削減効果**: 重複ロジック約100行削減、API統一による保守性向上

### 2.5 設定値の外部化

#### 現状の構造
```
各ファイルにハードコード
├── channel_validator.py
│   ├── REQUIRED_CHANNELS = ["idea", "requirements", ...]  # ハードコード
│   └── REQUIRED_PERMISSIONS = [...]                       # ハードコード
├── command_manager.py
│   └── STAGE_CHANNELS = {"idea": "requirements", ...}     # ハードコード
└── その他多数のファイル
```

#### リファクタリング後の構造
```
config/
├── settings.py                  # 既存
│   └── （既存の設定）
├── channels.yaml                # 新規作成
│   ├── required_channels
│   ├── stage_transitions
│   └── permissions
└── prompts.yaml                 # 新規作成
    └── stage_templates

# 使用例：
from config import load_config
config = load_config()
channels = config.channels.required_channels
```

### 2.6 未使用コードの削除

#### 削除対象
```
lib/utils.py
├── is_service_running_legacy()  # 削除（新バージョンあり）
└── format_session_list()        # 削除（未使用）

その他
└── 未使用のインポート文        # 全ファイルから削除
```

## 3. 実装手順

### フェーズ1: 基盤整備（1日目）
1. **lib/command_executor.py**の作成
   - 全てのコマンド実行を統一
   - テストコード作成

2. **config/channels.yaml**と**config/prompts.yaml**の作成
   - ハードコードされた値を移行
   - 設定ローダーの実装

### フェーズ2: 重複削除（2-3日目）
3. **command_manager.py**のリファクタリング
   - Git操作の共通化（_execute_git_workflow）
   - ステージ遷移の共通化（_transition_to_next_stage）
   - command_executorへの移行

4. **claude_context_manager.py**のリファクタリング
   - プロンプト生成の汎用化
   - 設定ファイルからのテンプレート読み込み

### フェーズ3: 統合（4日目）
5. **unified_session_manager.py**の作成
   - 既存3つのマネージャーを統合
   - 後方互換性の維持

### フェーズ4: クリーンアップ（5日目）
6. **未使用コードの削除**
   - デッドコードの除去
   - 未使用インポートの削除
   - リントツールの実行

7. **テストとドキュメント更新**
   - 全テストの実行と修正
   - ドキュメントの更新

## 4. 期待される成果

### 定量的効果
- **コード行数**: 3,500行 → 2,950行（約550行削減、15%減）
- **重複コード**: 4箇所 → 0箇所
- **ファイル数**: 20個 → 18個（統合により減少）

### 定性的効果
- **保守性**: 変更箇所が1/4に減少
- **可読性**: 責務が明確化され理解が容易に
- **拡張性**: 新機能追加時の影響範囲が限定的
- **テスト**: テスト対象が減少し、カバレッジ向上
- **バグリスク**: 重複実装によるバグを根本的に排除

## 5. リスクと対策

### リスク
1. **後方互換性の破壊**
   - 対策: 段階的な移行、deprecation warning使用

2. **統合による複雑性増加**
   - 対策: 明確なインターフェース設計、十分なドキュメント

3. **テスト不足による不具合**
   - 対策: 各フェーズでのテスト実施、CI/CDの活用

## 6. 成功基準

- [ ] 全ての重複コードが削除される
- [ ] コード行数が15%以上削減される
- [ ] 全テストがパスする
- [ ] 新規バグが発生しない
- [ ] パフォーマンスが劣化しない

## 7. タイムライン

| フェーズ | 期間 | 主な作業 | 成果物 |
|---------|------|----------|--------|
| フェーズ1 | 1日 | 基盤整備 | command_executor.py, 設定ファイル |
| フェーズ2 | 2日 | 重複削除 | リファクタリング済みマネージャー |
| フェーズ3 | 1日 | 統合 | unified_session_manager.py |
| フェーズ4 | 1日 | クリーンアップ | クリーンなコードベース |

合計: **5営業日**

## 8. 次のステップ

1. このドキュメントのレビューと承認
2. フェーズ1の実装開始
3. 各フェーズ完了時の進捗報告
4. 最終レビューとマージ

---

*このドキュメントは随時更新される可能性があります。*
*最終更新: 2025-08-04*