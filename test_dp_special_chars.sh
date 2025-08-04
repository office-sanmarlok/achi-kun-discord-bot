#!/usr/bin/env bash
#
# dpコマンドの特殊文字処理テスト
#

echo "========================================="
echo "dpコマンド特殊文字テスト"
echo "========================================="

# テストケース定義
declare -a test_cases=(
    "[Twitter/X] → スクレイピング"
    "図解: A -> B -> C"
    "配列の例: arr[0] = 100"
    "パイプ処理: cmd1 | cmd2 | cmd3"
    "括弧の使用: (グループ1) と {グループ2}"
    "引用符: \"hello\" と 'world'"
    "バックスラッシュ: C:\\Users\\test"
    "アスタリスク: *.txt, *.md"
    "疑問符と感嘆符: 本当に？ すごい！"
    "ドル記号: \$100, \${variable}"
    "バッククォート: \`command\`"
    "改行を含む\nメッセージ\nテスト"
    "タブを含む\tメッセージ"
    "複合的な例: [配列] -> {オブジェクト} | パイプ & アンド"
)

# モックPythonスクリプトを作成（実際のDiscord APIは使わない）
cat > /tmp/mock_discord_post.py << 'EOF'
#!/usr/bin/env python3
import sys

# Read from stdin
if not sys.stdin.isatty():
    message = sys.stdin.read().strip()
    session = sys.argv[1] if len(sys.argv) > 1 else "1"
    
    print(f"[Session {session}] Received message:")
    print(f"  {repr(message)}")
    print(f"  Length: {len(message)} characters")
    print()
EOF

chmod +x /tmp/mock_discord_post.py

# dpコマンドのテスト用バージョンを作成
cat > /tmp/test_dp << 'EOF'
#!/usr/bin/env bash
SESSION="$1"
MESSAGE="$2"

# 元のdpコマンドと同じ方法でメッセージを送信
printf '%s\n' "$MESSAGE" | python3 /tmp/mock_discord_post.py "$SESSION"
EOF

chmod +x /tmp/test_dp

# テスト実行
echo "テスト開始..."
echo

for i in "${!test_cases[@]}"; do
    test_message="${test_cases[$i]}"
    echo "テストケース $((i+1)): $test_message"
    echo "-----------------------------------------"
    
    # テスト実行
    /tmp/test_dp 1 "$test_message" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ 成功"
    else
        echo "✗ 失敗"
    fi
    echo
done

# クリーンアップ
rm -f /tmp/mock_discord_post.py /tmp/test_dp

echo "========================================="
echo "テスト完了"
echo "========================================="