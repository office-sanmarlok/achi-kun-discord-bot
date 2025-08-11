# コーディングスタイルと規約

## Python コーディング規約

### 全般的なスタイル
- **Python 3.8+** の機能を使用
- **PEP 8** に準拠（ただし、明示的なlinter設定はプロジェクトにない）
- インデント: スペース4つ
- 行の最大長: 明示的な制限なし（一般的には80-120文字程度）

### 命名規則
- **クラス名**: PascalCase（例: `ClaudeCLIBot`, `SessionManager`）
- **関数・メソッド名**: snake_case（例: `get_session_manager`, `handle_idea_command`）
- **定数**: UPPER_SNAKE_CASE（例: `CLEANUP_INTERVAL_HOURS`, `REQUEST_TIMEOUT_SECONDS`）
- **プライベートメソッド**: アンダースコア1つで開始（例: `_validate_message`, `_process_attachments`）

### ドキュメンテーション
- **Docstring**: 日本語で記述、関数・クラスの説明を含む
- 形式:
  ```python
  def function_name(param: Type) -> ReturnType:
      """
      関数の簡潔な説明
      
      Args:
          param: パラメータの説明
      
      Returns:
          戻り値の説明
      """
  ```

### 型ヒント
- 可能な限り型ヒントを使用
- 例: `def get_settings() -> SettingsManager:`
- Optional型、List型、Dict型などを適切に使用

### インポート
- 標準ライブラリ → サードパーティ → ローカルモジュールの順
- 各グループ内でアルファベット順
- 絶対インポートを優先

### エラーハンドリング
- try-except ブロックで適切にエラーをキャッチ
- ロギングを使用（`logger` インスタンスを各モジュールで定義）
- 例外は再発生させるか、適切にログに記録

### 非同期処理
- Discord.py の async/await パターンを使用
- 非同期メソッドには `async def` を使用
- `@commands.Cog.listener()` デコレータを使用

### ファイル構成
- 1ファイル1クラスまたは関連する機能のグループ
- `__init__.py` でモジュールを適切に公開

## プロジェクト固有の規約
- 日本語コメント・ドキュメントを許可
- tmux関連の処理は `TmuxManager` クラスに集約
- Discord関連の処理は専用のマネージャークラスに分離
- 設定は `SettingsManager` を通じて一元管理