#!/usr/bin/env python3
"""
Flask HTTP Bridge - Discord ↔ Claude Code 連携の中核

このモジュールは以下の責任を持つ：
1. Discord BotからのHTTP APIリクエスト受信
2. メッセージのClaude Codeセッションへの転送
3. システム状態の監視・報告
4. セッション管理の支援
5. ヘルスチェック機能の提供

拡張性のポイント：
- 新しいAPIエンドポイントの追加
- メッセージ転送方式の多様化
- 認証・権限管理の実装
- ログ・監視機能の強化
- 負荷分散・スケーリング対応
"""

import os
import sys
import json
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# パッケージルートの追加（相対インポート対応）
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from flask import Flask, request, jsonify, Response
except ImportError:
    print("Error: Flask is not installed. Run: pip install flask")
    sys.exit(1)

from config.settings import SettingsManager

# ログ設定（本番環境では外部設定ファイルから読み込み可能）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TmuxMessageForwarder:
    """
    tmuxセッションへのメッセージ転送処理
    
    将来の拡張：
    - tmux以外の転送方式（WebSocket、gRPC等）
    - メッセージキューイング
    - 失敗時のリトライ機構
    - 負荷分散対応
    """
    
    # 設定可能な定数（将来は設定ファイル化）
    TMUX_DELAY_SECONDS = 0.2
    SESSION_NAME_PREFIX = "claude-session"
    
    @classmethod
    def forward_message(cls, message: str, session_num: int) -> Tuple[bool, Optional[str]]:
        """
        指定されたセッションにメッセージを転送
        
        拡張ポイント：
        - 転送方式の選択機能
        - メッセージ暗号化
        - 転送状況の詳細記録
        - バッチ処理対応
        
        Args:
            message: 転送するメッセージ
            session_num: 転送先セッション番号
        
        Returns:
            Tuple[bool, Optional[str]]: (成功フラグ, エラーメッセージ)
        """
        try:
            session_name = f"{cls.SESSION_NAME_PREFIX}-{session_num}"
            
            # ステップ1: メッセージ送信
            cls._send_tmux_keys(session_name, message)
            
            # ステップ2: Enter送信（コマンド実行）
            time.sleep(cls.TMUX_DELAY_SECONDS)
            cls._send_tmux_keys(session_name, 'C-m')
            
            logger.info(f"Message forwarded to session {session_num}")
            return True, None
            
        except subprocess.CalledProcessError as e:
            error_msg = f"tmux command failed: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    @classmethod
    def _send_tmux_keys(cls, session_name: str, keys: str):
        """
        tmuxセッションにキー入力を送信
        
        拡張ポイント：
        - 送信前検証
        - セッション存在確認
        - 代替転送方式
        """
        subprocess.run(
            ['tmux', 'send-keys', '-t', session_name, keys],
            check=True,
            capture_output=True
        )

class MessageValidator:
    """
    受信メッセージの検証処理
    
    将来の拡張：
    - スパム検出
    - 不正コンテンツフィルタリング
    - レート制限
    - 権限チェック
    """
    
    @staticmethod
    def validate_discord_message(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Discord メッセージデータの検証
        
        拡張ポイント：
        - 詳細バリデーションルール
        - カスタム検証ロジック
        - ユーザー権限チェック
        
        Args:
            data: 受信したメッセージデータ
        
        Returns:
            Tuple[bool, Optional[str]]: (有効フラグ, エラーメッセージ)
        """
        if not data:
            return False, "No data provided"
        
        # 必須フィールドの確認
        required_fields = ['message', 'session', 'channel_id']
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # メッセージ長制限チェック
        message = data.get('message', '')
        if len(message) > 4000:  # Discord制限に合わせた上限
            return False, "Message too long"
        
        return True, None

class FlaskBridgeApp:
    """
    Flask HTTP Bridgeアプリケーション
    
    アーキテクチャ特徴：
    - RESTful API設計
    - 堅牢なエラーハンドリング
    - 構造化ログ出力
    - 拡張可能なルーティング
    
    拡張可能要素：
    - 認証・認可システム
    - API版数管理
    - レート制限機能
    - メトリクス収集
    - WebSocket対応
    """
    
    def __init__(self, settings_manager: SettingsManager):
        """
        Flaskアプリケーションの初期化
        
        Args:
            settings_manager: 設定管理インスタンス
        """
        self.settings = settings_manager
        self.app = Flask(__name__)
        self.message_forwarder = TmuxMessageForwarder()
        self.message_validator = MessageValidator()
        self.active_processes = {}  # 拡張：アクティブプロセス管理
        
        # ルーティング設定
        self._configure_routes()
        
        # アプリケーション設定
        self._configure_app()
    
    def _configure_app(self):
        """
        Flaskアプリケーションの設定
        
        拡張ポイント：
        - CORS設定
        - セキュリティヘッダー
        - ミドルウェア追加
        """
        # 本番環境設定
        self.app.config['DEBUG'] = False
        self.app.config['TESTING'] = False
        
    def _configure_routes(self):
        """
        APIルーティングの設定
        
        拡張ポイント：
        - 新しいエンドポイント追加
        - API版数管理
        - 権限ベースルーティング
        """
        # ヘルスチェックエンドポイント
        self.app.route('/health', methods=['GET'])(self.health_check)
        
        # メッセージ処理エンドポイント
        self.app.route('/discord-message', methods=['POST'])(self.handle_discord_message)
        
        # セッション管理エンドポイント
        self.app.route('/sessions', methods=['GET'])(self.get_sessions)
        
        # ステータス確認エンドポイント
        self.app.route('/status', methods=['GET'])(self.get_status)
    
    def health_check(self) -> Response:
        """
        ヘルスチェックエンドポイント
        
        拡張ポイント：
        - 依存サービス状態確認
        - 詳細ヘルス情報
        - アラート機能
        """
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',  # 拡張：バージョン管理
            'active_sessions': len(self.active_processes),
            'configured_sessions': len(self.settings.list_sessions())
        }
        
        return jsonify(health_data)
    
    def handle_discord_message(self) -> Response:
        """
        Discord メッセージ処理のメインエンドポイント
        
        処理フロー：
        1. リクエストデータの検証
        2. メッセージ詳細の抽出
        3. Claude Codeセッションへの転送
        4. 処理結果の返却
        
        拡張ポイント：
        - 非同期処理対応
        - メッセージキューイング
        - 優先度制御
        - 統計情報収集
        """
        try:
            # ステップ1: データ検証
            data = request.json
            is_valid, error_msg = self.message_validator.validate_discord_message(data)
            if not is_valid:
                logger.warning(f"Invalid message data: {error_msg}")
                return jsonify({'error': error_msg}), 400
            
            # ステップ2: メッセージ詳細抽出
            message_info = self._extract_message_info(data)
            
            # ステップ3: ログ記録
            self._log_message_info(message_info)
            
            # ステップ4: Claude Codeへの転送
            success, error_msg = self._forward_to_claude(message_info)
            if not success:
                return jsonify({'error': error_msg}), 500
            
            # ステップ5: 成功レスポンス
            return jsonify({
                'status': 'received',
                'session': message_info['session_num'],
                'message_length': len(message_info['message']),
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Unexpected error in message handling: {e}", exc_info=True)
            return jsonify({'error': 'Internal server error'}), 500
    
    def _extract_message_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        リクエストデータからメッセージ情報を抽出
        
        拡張ポイント：
        - 追加メタデータの抽出
        - データ正規化処理
        - カスタムフィールド対応
        """
        return {
            'message': data.get('message', ''),
            'channel_id': data.get('channel_id', ''),
            'session_num': data.get('session', 1),
            'user_id': data.get('user_id', ''),
            'username': data.get('username', 'Unknown'),
            'timestamp': datetime.now().isoformat()
        }
    
    def _log_message_info(self, message_info: Dict[str, Any]):
        """
        メッセージ情報のログ記録
        
        拡張ポイント：
        - 構造化ログ出力
        - 外部ログシステム連携
        - メトリクス収集
        """
        session_num = message_info['session_num']
        username = message_info['username']
        message_preview = message_info['message'][:100] + "..." if len(message_info['message']) > 100 else message_info['message']
        
        print(f"[Session {session_num}] {username}: {message_preview}")
        logger.info(f"Message processed: session={session_num}, user={username}, length={len(message_info['message'])}")
    
    def _forward_to_claude(self, message_info: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Claude Codeセッションへのメッセージ転送
        
        拡張ポイント：
        - 転送方式の選択
        - 失敗時のリトライ
        - 負荷分散
        """
        session_num = message_info['session_num']
        message = message_info['message']
        
        success, error_msg = self.message_forwarder.forward_message(message, session_num)
        
        if success:
            print(f"✅ Forwarded to Claude session {session_num}")
        else:
            print(f"❌ Failed to forward to Claude session {session_num}: {error_msg}")
        
        return success, error_msg
    
    def get_sessions(self) -> Response:
        """
        設定済みセッション一覧の取得
        
        拡張ポイント：
        - セッション詳細情報
        - セッション状態確認
        - フィルタリング機能
        """
        sessions = self.settings.list_sessions()
        response_data = {
            'sessions': [
                {
                    'number': num,
                    'channel_id': ch_id,
                    'status': 'active'  # 拡張：セッション状態確認
                }
                for num, ch_id in sessions
            ],
            'default': self.settings.get_default_session(),
            'total_count': len(sessions)
        }
        
        return jsonify(response_data)
    
    def get_status(self) -> Response:
        """
        アプリケーション状態の取得
        
        拡張ポイント：
        - 詳細システム情報
        - パフォーマンス指標
        - 依存サービス状態
        """
        status_data = {
            'status': 'running',
            'configured': self.settings.is_configured(),
            'sessions_count': len(self.settings.list_sessions()),
            'active_processes': len(self.active_processes),
            'uptime': datetime.now().isoformat(),  # 拡張：稼働時間計算
            'version': '1.0.0'
        }
        
        return jsonify(status_data)
    
    def run(self, host: str = '127.0.0.1', port: Optional[int] = None):
        """
        Flaskアプリケーションの実行
        
        拡張ポイント：
        - WSGI サーバー対応
        - SSL/TLS設定
        - 負荷分散設定
        """
        if port is None:
            port = self.settings.get_port('flask')
        
        print(f"🌐 Starting Flask HTTP Bridge on {host}:{port}")
        logger.info(f"Flask app starting on {host}:{port}")
        
        try:
            # 本番モードで実行
            self.app.run(
                host=host,
                port=port,
                debug=False,
                threaded=True,  # マルチスレッド対応
                use_reloader=False
            )
        except Exception as e:
            error_msg = f"Failed to start Flask app: {e}"
            print(f"❌ {error_msg}")
            logger.error(error_msg, exc_info=True)
            sys.exit(1)

def run_flask_app(port: Optional[int] = None):
    """
    Flask アプリケーションの起動関数
    
    拡張ポイント：
    - 設定ファイルからの起動パラメータ読み込み
    - 環境別設定の切り替え
    - 複数インスタンス管理
    """
    settings = SettingsManager()
    
    # 設定確認
    if not settings.is_configured():
        print("❌ Claude-Discord Bridge is not configured.")
        print("Run './install.sh' first.")
        sys.exit(1)
    
    # アプリケーション作成・実行
    app = FlaskBridgeApp(settings)
    app.run(port=port)

if __name__ == "__main__":
    run_flask_app()