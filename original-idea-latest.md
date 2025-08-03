# Achi-kun-discord：AIアシスタント駆動の半自動アプリ開発システム

## 概要
Achi-kun-discordは、アイデアから実装までのシームレスなアプリ開発ワークフローを実現するシステムです。DiscordにClaude Code（CLIのLLM）のラッパーとしてbotが常駐し、スペック駆動開発（SDD）の手法に基づいて、半自動かつ並列で開発を進めます。

## システム構成

### 使用ツール
- **Discord**: コミュニケーションハブ
- **Claude Code**: AIアシスタント（Maxプラン）
- **[Achi-kun-discord](https://github.com/office-sanmarlok/achi-kun-discord)**: Slackボット本体
- **GitHub**: コード管理
- **GitHub CLI (`gh`)**: リポジトリ操作
- **[claude-code-action](https://github.com/anthropics/claude-code-action)**: CI/CD連携
- **WSL環境**: achi-kun-discordディレクトリをストレージとして使用

### 前提条件
- GitHub Appは"All repositories"設定でインストール済み
- Achi-kun-discord botはワークスペースレベルで認証済み
- Claude Code（Maxプラン）がローカル環境で利用
可能
- GitHub CLIがインストール済みかつ全スコープ有効化済み

## スペック駆動開発（SDD）フロー

SDDの詳細は`./SDD.md`で定義され、Claude Codeが各フェーズで参照します。以下は概要。

### 開発フェーズ

#### 1. アイデア投稿（idea.md）
- ユーザーの頭の中にあるプロダクトアイデアをラフに文書化
- UI参考画像や抽象的な機能説明を含む

#### 2. 要求定義（requirements.md）
- **ユーザーストーリー**: 利用者視点の具体的な要求
- **受入基準**: EARS形式でエッジケースまで明確に定義

#### 3. 設計（design.md）
- **アーキテクチャ**: システム全体の構成
- **コンポーネントとインターフェース**: モジュール間の連携
- **データモデル**: データ構造の定義

#### 4. タスクリスト化（tasks.md）
- 実装タスクの細分化
- 依存関係を考慮した順序付け
- チェックボックス形式の実行可能リスト

## システム構造
### ディレクトリ構造
- achi-kun(CLAUDE_WORKING_DIR)
    * achi-kun-discord-bot（現在のディレクトリ）
    * projects
        - ${idea-name}
        - ${idea-name}
        ...
    * ${idea-name}
    * ${idea-name}
    ...

achi-kunディレクトリ直下のディレクトリはすべてgitレポジトリです。achi-kun-discord-bot, projects, ${idea-name}（複数）

## Discordについて
### チャンネル構造
```
Achi-kunカテゴリー/
├── #1-idea          # 各スレッド = 各./projects/${idea-name}/idea.md
├── #2-requirements  # 各スレッド = 各./projects/${idea-name}/requirements.md
├── #3-design        # 各スレッド = 各./projects/${idea-name}/design.md
├── #4-tasks         # 各スレッド = 各./projects/${idea-name}/tasks.md
└── #5-development   # 各スレッド = 各./${idea-name}ディレクトリ
```

### Discordコマンド
- !idea idea-name （メッセージに対する返信として使用）
    * 引数のidea-nameをスレッドタイトルとしてスレッド化
    * そのスレッドに紐づく形でCCセッションを開始
    * ./projects/${idea-name}/idea.mdを作成
    * 親メッセージの内容をもとに企画提案書をidea.mdに記載
    * mdの中身とそこへのパスを新スレッドに送信
- !complete （スレッド内で使用）
    * #1-ideaで実行時
        - スレッドタイトルからidea-nameを取得
        - ./projects/${idea-name}をgit push
        - #2-requirementsチャンネルに"要件定義: idea-name"と送信
        - "要件定義: idea-name"をidea-nameをスレッド名としてスレッド化
        - ./projects/${idea-name}/requirements.mdを生成
        - ./projects/${idea-name}/idea.mdをもとに要件定義書をrequirements.mdに記載
        - mdの中身とそこへのパスを新スレッドに送信
    * #2-requirementsで実行時
        - スレッドタイトルからidea-nameを取得
        - ./projects/${idea-name}をgit push
        - #3-designチャンネルに"設計: idea-name"と送信
        - "設計: idea-name"をidea-nameをスレッド名としてスレッド化
        - ./projects/${idea-name}/design.mdを生成
        - ./projects/${idea-name}/requirements.mdをもとに設計書をdesign.mdに記載
        - mdの中身とそこへのパスを新スレッドに送信
    * #3-designで実行時
        - スレッドタイトルからidea-nameを取得
        - ./projects/${idea-name}をgit push
        - #4-tasksチャンネルに"タスクリスト作成: idea-name"と送信
        - "タスクリスト作成: idea-name"をidea-nameをスレッド名としてスレッド化
        - ./projects/${idea-name}/tasks.mdを生成
        - ./projects/${idea-name}/design.mdをもとに設計書をtasks.mdに記載
        - mdの中身とそこへのパスを新スレッドに送信
    * #4-tasksで実行時
        - スレッドタイトルからidea-nameを取得
        - ./projects/${idea-name}をgit push
        - ./projects/${idea-name}を./${idea-name}へコピーし
        - ./achi-kun-discord-bot/.github/workflowsを./${idea-name}/.github/workflowsへコピー
        - ${idea-name}レポジトリをパブリックで作成してgit push
        - #5-developmentチャンネルに"開発: idea-name"と送信
        - "開発: idea-name"をidea-nameをスレッド名としてスレッド化
        - ./${idea-name}でv0の開発を開始
