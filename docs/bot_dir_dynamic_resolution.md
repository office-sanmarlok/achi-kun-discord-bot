# bot_dir動的解決の実装

## 概要
`project_manager.py`の`self.bot_dir`のハードコードを解消し、git worktreeで複数のブランチ/バージョンをテストできるよう動的解決を実装しました。

## 実装内容

### 優先順位による解決方式
`_determine_bot_dir()`メソッドで以下の優先順位で動的に決定：

1. **BOT_DIR環境変数**（最優先）
   - 明示的に設定されている場合は最優先で使用
   - 存在確認も実施

2. **__file__からの推定**（最も信頼性が高い）
   - 実行中のPythonファイルの場所から推定
   - `src/project_manager.py` → `akdb-*`ディレクトリ
   - `bin/vai`の存在で正しいボットディレクトリか確認

3. **sys.argv[0]からの推定**
   - `vai`コマンドまたは`discord_bot`から起動された場合
   - コマンドの場所からボットディレクトリを推定

4. **現在の作業ディレクトリからの推定**
   - cwdまたはその親ディレクトリがボットディレクトリか確認
   - `bin/vai`と`src`ディレクトリの存在で判定

5. **PYTHONPATHからの推定**
   - 環境変数PYTHONPATHに設定されたパスから推定
   - vaiコマンドの存在で確認

6. **フォールバック**
   - どの方法でも決定できない場合は`akdb-refactor`を使用
   - 警告ログを出力

## メリット

### git worktreeでの利便性向上
```bash
# 各ブランチでworktreeを作成
git worktree add ../akdb-develop develop
git worktree add ../akdb-feature feature-branch

# それぞれのディレクトリで独立して動作
cd ../akdb-develop && ./bin/vai start  # akdb-developディレクトリを使用
cd ../akdb-feature && ./bin/vai start   # akdb-featureディレクトリを使用
```

### 環境変数での明示的な指定も可能
```bash
# 特定のディレクトリを強制的に使用したい場合
export BOT_DIR=/home/seito_nakagane/project-wsl/akdb-prod
./bin/vai start  # akdb-prodディレクトリを使用
```

## 実装の詳細

### コード変更箇所
- `src/project_manager.py`の`__init__`メソッド
- 新規メソッド`_determine_bot_dir()`の追加

### 判定ロジック
各方法で以下のチェックを実施：
- project-wsl配下のディレクトリであること
- ボットディレクトリとして必要なファイル/ディレクトリが存在すること
  - `bin/vai`（ボットの起動スクリプト）
  - `src`ディレクトリ（ソースコード）

## テスト結果

### 基本動作確認
```python
# akdb-refactorディレクトリで実行
pm = ProjectManager()
print(pm.bot_dir)  # /home/seito_nakagane/project-wsl/akdb-refactor
```

### ログ出力例
```
INFO: Determined bot_dir from __file__: /home/seito_nakagane/project-wsl/akdb-refactor
INFO: ProjectManager initialized - bot_dir: /home/seito_nakagane/project-wsl/akdb-refactor, projects: /home/seito_nakagane/project-wsl/projects, achi-kun: /home/seito_nakagane/project-wsl
```

## 今後の改善案

1. **設定ファイルでの指定**
   - `.env`ファイルにBOT_DIRを記載できるようにする
   - worktree毎に異なる`.env`を持てるようにする

2. **自動検出の改善**
   - `pyproject.toml`や`package.json`など、プロジェクト固有のファイルも判定に使用
   - より正確なプロジェクトルート検出

3. **エラーハンドリングの強化**
   - 不正なディレクトリが指定された場合の詳細なエラーメッセージ
   - 推奨される解決方法の提示