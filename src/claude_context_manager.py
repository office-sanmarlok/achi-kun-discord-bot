#!/usr/bin/env python3
"""
Claude Context Manager - Claude Codeへのコンテキストとプロンプト生成

このモジュールは以下の責務を持つ：
1. Claude Codeセッションの初期コンテキスト生成
2. SDD.mdに基づくステージ別プロンプト生成
3. Discord統合情報の整形
"""

import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ClaudeContextManager:
    """Claude Codeへのコンテキストとプロンプトを管理するクラス"""
    
    def __init__(self, sdd_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            sdd_path: SDD.mdファイルのパス（デフォルト: ./docs/SDD.md）
        """
        if sdd_path is None:
            # デフォルトパスを設定
            self.sdd_path = Path(__file__).parent.parent / "docs" / "SDD.md"
        else:
            self.sdd_path = sdd_path
        
        logger.info(f"ClaudeContextManager initialized with SDD path: {self.sdd_path}")
    
    def generate_initial_context(self, 
                               session_num: int,
                               thread_info: Dict[str, str],
                               parent_message: Optional[Dict[str, str]] = None) -> str:
        """
        初期コンテキストメッセージを生成
        
        Args:
            session_num: セッション番号
            thread_info: スレッド情報 {"channel_name", "thread_name", "thread_id"}
            parent_message: 親メッセージ情報 {"author", "timestamp", "content"}
            
        Returns:
            フォーマットされた初期コンテキストメッセージ
        """
        context_lines = [
            "=== Discord スレッド情報 ===",
            f"チャンネル名: {thread_info.get('channel_name', 'Unknown')}",
            f"スレッド名: {thread_info.get('thread_name', 'Unknown')}",
            f"スレッドID: {thread_info.get('thread_id', 'Unknown')}",
            f"セッション番号: {session_num}",
            "",
            "【重要】このセッションはDiscordのスレッド専用です。",
            f"メッセージ送信は: dp {session_num} \"メッセージ\"",
            ""
        ]
        
        # 親メッセージがある場合は追加
        if parent_message:
            context_lines.extend([
                "=== 親メッセージ ===",
                f"作成者: {parent_message.get('author', 'Unknown')}",
                f"時刻: {parent_message.get('timestamp', 'Unknown')}",
                f"内容:",
                parent_message.get('content', ''),
                "==================="
            ])
        
        return "\n".join(context_lines)
    
    def generate_idea_prompt(self, idea_name: str, parent_content: str) -> str:
        """
        idea.md生成用プロンプトを生成
        
        Args:
            idea_name: アイデア名
            parent_content: 親メッセージの内容
            
        Returns:
            idea.md生成用プロンプト
        """
        prompt = f"""親メッセージの内容をもとに、./projects/{idea_name}/idea.mdに企画提案書を記載してください。

親メッセージ:
{parent_content}

以下の要素を含めて、マークダウン形式で記載してください：
- プロジェクトの概要
- 解決したい課題
- 提案する解決策
- 期待される効果
- 実装の概要（技術的な観点）"""
        
        return prompt
    
    def generate_requirements_prompt(self, idea_name: str) -> str:
        """
        requirements.md生成用プロンプトを生成（SDD.md参照）
        
        Args:
            idea_name: アイデア名
            
        Returns:
            requirements.md生成用プロンプト
        """
        prompt = f"""./projects/{idea_name}/idea.mdを読んで、{self.sdd_path}のRequirement Gatheringセクションに従って./projects/{idea_name}/requirements.mdに要件定義を記載してください。

具体的には以下の形式で記載してください：

1. Introduction セクション
   - 機能の概要を明確に記述

2. Requirements セクション
   - 各要件を階層的な番号付きリストで記載
   - 各要件には以下を含める：
     - User Story: "As a [role], I want [feature], so that [benefit]" 形式
     - Acceptance Criteria: EARS形式（Easy Approach to Requirements Syntax）で記載
       - WHEN [event] THEN [system] SHALL [response]
       - IF [precondition] THEN [system] SHALL [response]

エッジケース、ユーザー体験、技術的制約、成功基準を考慮して、包括的な要件を定義してください。"""
        
        return prompt
    
    def generate_design_prompt(self, idea_name: str) -> str:
        """
        design.md生成用プロンプトを生成（SDD.md参照）
        
        Args:
            idea_name: アイデア名
            
        Returns:
            design.md生成用プロンプト
        """
        prompt = f"""./projects/{idea_name}/requirements.mdを読んで、{self.sdd_path}のCreate Feature Design Documentセクションに従って./projects/{idea_name}/design.mdに設計書を記載してください。

設計書には以下のセクションを含めてください：

1. Overview
   - システムアーキテクチャの概要

2. Architecture
   - システム全体の構成
   - 主要コンポーネント間の関係
   - データフローの説明

3. Components and Interfaces
   - 各コンポーネントの詳細設計
   - インターフェース定義
   - API仕様

4. Data Models
   - データ構造の定義
   - データベーススキーマ（該当する場合）

5. Error Handling
   - エラー処理戦略
   - 例外処理の方針

6. Testing Strategy
   - テスト方針
   - テストケースの概要

必要に応じてMermaid形式の図を含めてください。
全ての要件がどのように実現されるかを明確に示してください。"""
        
        return prompt
    
    def generate_tasks_prompt(self, idea_name: str) -> str:
        """
        tasks.md生成用プロンプトを生成（SDD.md参照）
        
        Args:
            idea_name: アイデア名
            
        Returns:
            tasks.md生成用プロンプト
        """
        prompt = f"""./projects/{idea_name}/design.mdを読んで、{self.sdd_path}のCreate Task Listセクションに従って./projects/{idea_name}/tasks.mdに実装タスクリストを記載してください。

以下の指示に従ってタスクリストを作成してください：

1. 設計を一連のコーディングタスクに変換
2. テスト駆動開発を優先
3. 段階的な進行を確保（複雑さの大きな飛躍を避ける）
4. 各タスクが前のタスクに基づいて構築されるようにする
5. 最後は統合作業で終わる
6. 孤立したコードがないようにする

フォーマット：
- 番号付きチェックボックスリスト（最大2階層）
- 各タスクには明確な目標を記載
- サブ情報は箇条書きで追加
- 要件ドキュメントの具体的な要件番号を参照（_Requirements: X.X_ 形式）

コーディングタスクのみを含め、以下は除外：
- ユーザーテスト
- デプロイメント
- パフォーマンス測定
- ドキュメント作成（コード内コメントは除く）

例：
- [ ] 1. プロジェクト構造とコアインターフェースの設定
  - ディレクトリ構造の作成
  - インターフェース定義
  - _Requirements: 1.1_"""
        
        return prompt
    
    def generate_development_prompt(self, idea_name: str) -> str:
        """
        開発開始用プロンプトを生成
        
        Args:
            idea_name: アイデア名
            
        Returns:
            開発開始用プロンプト
        """
        prompt = f"""./projects/{idea_name}/tasks.mdのタスクリストに従って、v0の開発を開始してください。

タスクリストの順番に従って実装を進め、各タスクが完了したら該当するチェックボックスを埋めてください。

開発にあたって：
1. テスト駆動開発を心がける
2. コミットは適切な粒度で行う
3. エラーハンドリングを適切に実装する
4. コードの可読性を重視する

最初のタスクから開始してください。"""
        
        return prompt
    
    def format_complete_message(self, stage: str, idea_name: str) -> str:
        """
        !complete実行時の次チャンネルへの投稿メッセージを生成
        
        Args:
            stage: 現在のステージ（idea, requirements, design, tasks）
            idea_name: アイデア名
            
        Returns:
            次チャンネルへの投稿メッセージ
        """
        stage_messages = {
            "idea": f"要件定義: {idea_name}",
            "requirements": f"設計: {idea_name}",
            "design": f"タスクリスト作成: {idea_name}",
            "tasks": f"開発: {idea_name}"
        }
        
        return stage_messages.get(stage, f"次フェーズ: {idea_name}")
    
    def get_stage_from_channel(self, channel_name: str) -> Optional[str]:
        """
        チャンネル名からステージを判定
        
        Args:
            channel_name: Discordチャンネル名
            
        Returns:
            ステージ名（idea, requirements, design, tasks, development）
        """
        channel_stage_map = {
            "1-idea": "idea",
            "2-requirements": "requirements",
            "3-design": "design",
            "4-tasks": "tasks",
            "5-development": "development"
        }
        
        # チャンネル名から番号とステージ名を抽出
        for key, stage in channel_stage_map.items():
            if key in channel_name:
                return stage
        
        return None