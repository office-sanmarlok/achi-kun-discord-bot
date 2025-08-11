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
from typing import Dict, Optional, Any
from datetime import datetime
from string import Template

logger = logging.getLogger(__name__)


class PromptTemplateLoader:
    """プロンプトテンプレートをファイルから読み込むクラス"""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            prompts_dir: プロンプトディレクトリのパス（デフォルト: ./prompts）
        """
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).parent.parent / "prompts"
        else:
            self.prompts_dir = prompts_dir
            
        logger.info(f"PromptTemplateLoader initialized with prompts directory: {self.prompts_dir}")
    
    def load_template(self, template_name: str) -> Optional[str]:
        """
        テンプレートファイルを読み込む
        
        Args:
            template_name: テンプレート名（例: "cc.md", "complete/requirements.md"）
            
        Returns:
            テンプレート内容、ファイルが存在しない場合はNone
        """
        template_path = self.prompts_dir / template_name
        
        if not template_path.exists():
            logger.warning(f"Template file not found: {template_path}")
            return None
            
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"Loaded template: {template_path}")
                return content
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {e}")
            return None
    
    def load_and_combine_templates(self, command_template: str, 
                                   base_template: str = "context_base.md") -> Optional[str]:
        """
        ベーステンプレートとコマンドテンプレートを結合して読み込む
        
        Args:
            command_template: コマンド特有のテンプレート名
            base_template: ベーステンプレート名（デフォルト: context_base.md）
            
        Returns:
            結合されたテンプレート内容、失敗時はNone
        """
        # ベーステンプレートを読み込み
        base_content = self.load_template(base_template)
        if not base_content:
            logger.warning(f"Base template not found: {base_template}. Using command template only.")
            base_content = ""
        
        # コマンドテンプレートを読み込み
        command_content = self.load_template(command_template)
        if not command_content:
            logger.warning(f"Command template not found: {command_template}")
            # コマンドテンプレートがない場合は、ベーステンプレートのみ返す
            return base_content if base_content else None
        
        # 両方を結合（ベース + 改行 + コマンド）
        if base_content:
            combined = base_content + "\n\n" + command_content
            logger.info(f"Combined templates: {base_template} + {command_template}")
        else:
            combined = command_content
            
        return combined
    
    def render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """
        テンプレート内の変数を置換
        
        Args:
            template_content: テンプレート内容
            variables: 置換する変数の辞書
            
        Returns:
            変数置換後のテンプレート内容
        """
        try:
            template = Template(template_content)
            # Noneの値を空文字列に変換
            safe_variables = {k: (v if v is not None else '') for k, v in variables.items()}
            return template.safe_substitute(safe_variables)
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return template_content


class ClaudeContextManager:
    """Claude Codeへのコンテキストとプロンプトを管理するクラス"""
    
    def __init__(self, sdd_path: Optional[Path] = None, prompts_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            sdd_path: SDD.mdファイルのパス（デフォルト: ./docs/SDD.md）
            prompts_dir: プロンプトディレクトリのパス（デフォルト: ./prompts）
        """
        if sdd_path is None:
            # デフォルトパスを設定
            self.sdd_path = Path(__file__).parent.parent / "docs" / "SDD.md"
        else:
            self.sdd_path = sdd_path
            
        # テンプレートローダーを初期化
        self.template_loader = PromptTemplateLoader(prompts_dir)
        
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
    
    def generate_idea_prompt(self, idea_name: str, parent_content: str, 
                            thread_info: Dict[str, str] = None,
                            session_num: int = None) -> str:
        """
        idea.md生成用プロンプトを生成
        
        Args:
            idea_name: アイデア名
            parent_content: 親メッセージの内容
            
        Returns:
            idea.md生成用プロンプト
        """
        # 統一メソッドを使用
        return self.generate_prompt(
            stage='idea',
            idea_name=idea_name,
            parent_content=parent_content,
            thread_info=thread_info,
            session_num=session_num
        )
    
    def generate_requirements_prompt(self, idea_name: str,
                                    thread_info: Dict[str, str] = None,
                                    session_num: int = None) -> str:
        """
        requirements.md生成用プロンプトを生成（SDD.md参照）
        
        Args:
            idea_name: アイデア名
            
        Returns:
            requirements.md生成用プロンプト
        """
        # 統一メソッドを使用
        return self.generate_prompt(
            stage='requirements',
            idea_name=idea_name,
            thread_info=thread_info,
            session_num=session_num
        )
    
    def generate_design_prompt(self, idea_name: str,
                              thread_info: Dict[str, str] = None,
                              session_num: int = None) -> str:
        """
        design.md生成用プロンプトを生成（SDD.md参照）
        
        Args:
            idea_name: アイデア名
            
        Returns:
            design.md生成用プロンプト
        """
        # 統一メソッドを使用
        return self.generate_prompt(
            stage='design',
            idea_name=idea_name,
            thread_info=thread_info,
            session_num=session_num
        )
    
    def generate_tasks_prompt(self, idea_name: str,
                            thread_info: Dict[str, str] = None,
                            session_num: int = None) -> str:
        """
        tasks.md生成用プロンプトを生成（SDD.md参照）
        
        Args:
            idea_name: アイデア名
            
        Returns:
            tasks.md生成用プロンプト
        """
        # 統一メソッドを使用
        return self.generate_prompt(
            stage='tasks',
            idea_name=idea_name,
            thread_info=thread_info,
            session_num=session_num
        )
    
    def generate_development_prompt(self, idea_name: str,
                                   thread_info: Dict[str, str] = None,
                                   session_num: int = None) -> str:
        """
        開発開始用プロンプトを生成
        
        Args:
            idea_name: アイデア名
            
        Returns:
            開発開始用プロンプト
        """
        # 統一メソッドを使用
        return self.generate_prompt(
            stage='development',
            idea_name=idea_name,
            thread_info=thread_info,
            session_num=session_num
        )
    
    def _generate_prompt_base(self, 
                             template_path: str,
                             idea_name: str,
                             stage: str,
                             thread_info: Dict[str, str] = None,
                             session_num: int = None,
                             parent_content: str = None,
                             default_prompt: str = None) -> str:
        """
        プロンプト生成の共通ロジック
        
        Args:
            template_path: テンプレートファイルのパス
            idea_name: アイデア名
            stage: ステージ名（idea, requirements, design, tasks, development）
            thread_info: スレッド情報
            session_num: セッション番号
            parent_content: 親メッセージの内容（ideaステージ用）
            default_prompt: テンプレートが存在しない場合のデフォルトプロンプト
            
        Returns:
            生成されたプロンプト
        """
        # テンプレートをロード
        template_content = self.template_loader.load_and_combine_templates(template_path)
        
        if template_content:
            # テンプレートが存在する場合は変数を置換
            variables = {
                'idea_name': idea_name,
                'sdd_path': str(self.sdd_path),
                'channel_name': thread_info.get('channel_name', '') if thread_info else '',
                'thread_name': thread_info.get('thread_name', '') if thread_info else '',
                'thread_id': thread_info.get('thread_id', '') if thread_info else '',
                'session_num': session_num if session_num else '',
                'author': thread_info.get('author', '') if thread_info else '',
                'created_at': thread_info.get('created_at', '') if thread_info else '',
                'parent_content': parent_content if parent_content else thread_info.get('parent_content', '') if thread_info else ''
            }
            return self.template_loader.render_template(template_content, variables)
        else:
            # テンプレートが存在しない場合はデフォルトを使用
            return default_prompt if default_prompt else f"No template found for {stage} stage"
    
    def generate_prompt(self, stage: str, idea_name: str, **kwargs) -> str:
        """
        統一インターフェースでプロンプトを生成
        
        Args:
            stage: ステージ名（idea, requirements, design, tasks, development）
            idea_name: アイデア名
            **kwargs: その他のオプション引数（thread_info, session_num, parent_content等）
            
        Returns:
            生成されたプロンプト
        """
        # ステージ別の設定を取得
        stage_configs = {
            'idea': {
                'template_path': 'idea.md',
                'requires_parent_content': True,
                'default_prompt': f"""親メッセージの内容をもとに、./projects/{idea_name}/idea.mdに企画提案書を記載してください。

親メッセージ:
{kwargs.get('parent_content', '')}

以下の要素を含めて、マークダウン形式で記載してください：
- プロジェクトの概要
- 解決したい課題
- 提案する解決策
- 期待される効果
- 実装の概要（技術的な観点）"""
            },
            'requirements': {
                'template_path': 'complete/requirements.md',
                'default_prompt': f"""./projects/{idea_name}/idea.mdを読んで、{self.sdd_path}のRequirement Gatheringセクションに従って./projects/{idea_name}/requirements.mdに要件定義を記載してください.

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
            },
            'design': {
                'template_path': 'complete/design.md',
                'default_prompt': f"""./projects/{idea_name}/requirements.mdを読んで、{self.sdd_path}のDesignセクションに従って./projects/{idea_name}/design.mdに設計書を記載してください。

具体的には以下のセクションを含めてください：
- Overview: 設計の概要
- Architecture: システムアーキテクチャ
- Components and Interfaces: コンポーネントとインターフェース
- Data Models: データモデル
- Error Handling: エラーハンドリング
- Testing Strategy: テスト戦略

必要に応じてMermaidダイアグラムを使用してください。"""
            },
            'tasks': {
                'template_path': 'complete/tasks.md',
                'default_prompt': f"""./projects/{idea_name}/design.mdを読んで、{self.sdd_path}のTask Listセクションに従って./projects/{idea_name}/tasks.mdに実装タスクリストを記載してください。

具体的には以下の形式で記載してください：
- タスクをチェックボックスリスト形式で作成
- 各タスクは具体的で実行可能なコーディングタスク
- タスクは段階的に実装できるよう順序立てる
- 各タスクに要件への参照を含める"""
            },
            'development': {
                'template_path': 'complete/development.md',
                'default_prompt': f"""./projects/{idea_name}/tasks.mdのタスクリストに従って開発を進めてください。

作業ディレクトリ: ./development/{idea_name}/

タスクを順番に実装し、テスト駆動開発のアプローチを採用してください。"""
            }
        }
        
        config = stage_configs.get(stage, {})
        
        # ステージ別の処理
        if stage == 'idea' and config.get('requires_parent_content') and 'parent_content' not in kwargs:
            raise ValueError("parent_content is required for idea stage")
        
        return self._generate_prompt_base(
            template_path=config.get('template_path', f'{stage}.md'),
            idea_name=idea_name,
            stage=stage,
            thread_info=kwargs.get('thread_info'),
            session_num=kwargs.get('session_num'),
            parent_content=kwargs.get('parent_content'),
            default_prompt=config.get('default_prompt')
        )
    
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