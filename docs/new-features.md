# Achi-kun Discord Bot - 新機能ドキュメント

## 概要

このドキュメントでは、Spec-Driven Development (SDD) ワークフローを自動化する新機能について説明します。

## 新しいコマンド

### 1. `!idea <idea-name>`

アイデアからプロジェクトを開始するコマンドです。

**使用方法:**
```
!idea my-awesome-app
```

**動作:**
1. アイデアを含むメッセージに返信する形で実行する必要があります
2. `idea-name`は小文字英字とハイフンのみ使用可能（例: `my-app`, `todo-list`）
3. `./projects/{idea-name}`ディレクトリが作成されます
4. 返信元メッセージの内容が`idea.md`として保存されます
5. スレッドが作成され、Claude Codeセッションが開始されます

### 2. `!complete`

現在のフェーズを完了して次のフェーズへ進むコマンドです。

**使用方法:**
```
!complete
```

**動作:**
- **#1-ideaで実行時:**
  - Git操作（add, commit, push）を実行
  - #2-requirementsに「要件定義: {idea-name}」を投稿
  - 新しいスレッドとClaude Codeセッションを開始

- **#2-requirementsで実行時:**
  - Git操作を実行
  - #3-designに「設計: {idea-name}」を投稿
  - design.md作成用のセッションを開始

- **#3-designで実行時:**
  - Git操作を実行
  - #4-tasksに「タスクリスト作成: {idea-name}」を投稿
  - tasks.md作成用のセッションを開始

- **#4-tasksで実行時:**
  - Git操作を実行
  - プロジェクトを開発ディレクトリにコピー
  - GitHubリポジトリを作成（要: `gh auth login`）
  - #5-developmentに「開発: {idea-name}」を投稿
  - 開発用セッションを開始

## 必要なチャンネル構成

以下の5つのチャンネルが必要です：

1. `#1-idea` - アイデア投稿用
2. `#2-requirements` - 要件定義用
3. `#3-design` - 設計用
4. `#4-tasks` - タスクリスト用
5. `#5-development` - 開発用

## セットアップ

### 1. GitHub CLI のインストールと認証

```bash
# macOSの場合
brew install gh

# Linux (Ubuntu/Debian)の場合
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh

# 認証
gh auth login
```

### 2. インストールスクリプトの実行

```bash
./install.sh
```

インストールスクリプトは以下をチェックします：
- Python 3.8以上
- tmux
- GitHub CLI（gh）
- GitHub認証状態

### 3. Bot起動

```bash
vai
```

## ワークフロー例

1. **アイデア投稿**
   ```
   ユーザー: 家計簿アプリを作りたい。収支を記録して月次レポートを生成する機能が欲しい。
   ユーザー: !idea household-budget-app
   ```

2. **要件定義作成**
   - Claude Codeが自動的に`requirements.md`を作成
   - 完了したら: `!complete`

3. **設計作成**
   - Claude Codeが自動的に`design.md`を作成
   - 完了したら: `!complete`

4. **タスクリスト作成**
   - Claude Codeが自動的に`tasks.md`を作成
   - 完了したら: `!complete`

5. **開発**
   - GitHubリポジトリが自動作成される
   - Claude Codeが`tasks.md`に従って開発を進める

## ディレクトリ構造

```
achi-kun/
├── projects/              # !ideaで作成されるプロジェクト
│   ├── project-a/
│   │   ├── idea.md
│   │   ├── requirements.md
│   │   ├── design.md
│   │   └── tasks.md
│   └── project-b/
│       └── ...
├── project-a/            # !complete（tasks→development）でコピーされる開発ディレクトリ
│   ├── .github/
│   │   └── workflows/
│   ├── src/
│   └── ...
└── achi-kun-discord-bot/ # Botのソースコード
    ├── src/
    ├── docs/
    └── ...
```

## エラーハンドリング

- **既存プロジェクト**: 同名のプロジェクトが存在する場合はエラー
- **Git操作失敗**: 詳細なエラーメッセージを表示
- **GitHub認証なし**: リポジトリ作成時に認証を促す
- **チャンネル不足**: Bot起動時に警告を表示

## トラブルシューティング

### GitHub認証エラー
```bash
gh auth status  # 認証状態を確認
gh auth login   # 再認証
```

### チャンネルが見つからない
- チャンネル名が正確か確認（`#1-idea`, `#2-requirements`など）
- Botがチャンネルへのアクセス権限を持っているか確認

### Git pushエラー
- リモートリポジトリが設定されていない可能性
- 手動で設定: `git remote add origin <url>`