# Git操作の更新 - projects全体のプッシュ

## 変更概要
`!complete`コマンドのGit操作を、個別プロジェクトディレクトリではなく`./projects`全体をステージング・プッシュするよう変更しました。

## 変更内容

### command_manager.py
```python
# 変更前
git_commands = [
    ["git", "add", f"{thread_name}/*"],
    ["git", "commit", "-m", f"[{thread_name}] Complete {phase_name} phase"]
]

# 変更後
git_commands = [
    ["git", "add", "."],  # projects全体をステージング
    ["git", "commit", "-m", f"[{thread_name}] Complete {phase_name} phase"]
]
```

## メリット

1. **完全性の保証**
   - 全プロジェクトの変更が確実にリポジトリに保存される
   - ファイルの追加漏れがない

2. **履歴の一貫性**
   - 複数プロジェクトの並行作業でも全体の状態が保存される
   - リポジトリの状態が常に一貫している

3. **シンプルさ**
   - Git操作がシンプルになる
   - パス指定のエラーが減る

## 動作

### !completeコマンド実行時
1. `cd /home/seito_nakagane/project-wsl/projects`
2. `git add .` - 全ファイルをステージング
3. `git commit -m "[idea-name] Complete {phase} phase"`
4. `git push` - リモートにプッシュ

### 初回セットアップ時
- 既に`git add .`を使用しているため変更なし

## 影響範囲

- `src/command_manager.py`の`_execute_git_workflow()`メソッドのみ
- 他のGit操作には影響なし
- `!idea`コマンドはGit操作を行わないため影響なし

## テスト確認事項

- [ ] 新規プロジェクトの作成とコミット
- [ ] 既存プロジェクトの更新とコミット
- [ ] 複数プロジェクトが存在する場合の動作
- [ ] .gitignoreファイルの適用確認