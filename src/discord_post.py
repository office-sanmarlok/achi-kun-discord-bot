#!/usr/bin/env python3
"""
Discord Post実装
メッセージをDiscordに投稿する
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import SettingsManager

def get_session_info_from_api(session_num: int, flask_port: int = 5001):
    """
    Flask APIからセッション情報を取得
    
    Args:
        session_num: セッション番号
        flask_port: Flask APIのポート番号
    
    Returns:
        セッション情報の辞書、エラー時はNone
    """
    try:
        url = f"http://localhost:{flask_port}/session/{session_num}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            print(f"Error: Flask API returned status {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print("Error: Failed to connect to Flask API. Make sure 'vai' is running.")
        return None
    except Exception as e:
        print(f"Error connecting to Flask API: {e}")
        return None

def get_sessions_list_from_api(flask_port: int = 5001):
    """
    Flask APIからセッション一覧を取得
    
    Args:
        flask_port: Flask APIのポート番号
    
    Returns:
        セッション一覧、エラー時はNone
    """
    try:
        url = f"http://localhost:{flask_port}/sessions"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.json().get('sessions', [])
        else:
            return None
    except:
        return None

def post_to_discord(channel_id: str, message: str):
    """Post a message to Discord channel"""
    settings = SettingsManager()
    
    # Get bot token
    token = settings.get_token()
    if not token:
        print("Error: Discord bot token not configured")
        sys.exit(1)
    
    # Discord API endpoint
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    
    # Headers
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    
    # Payload
    payload = {
        "content": message
    }
    
    try:
        # Send request
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return True
        else:
            print(f"Error: Discord API returned status {response.status_code}")
            if response.status_code == 401:
                print("Invalid bot token")
            elif response.status_code == 403:
                print("Bot doesn't have permission to send messages in this channel")
            elif response.status_code == 404:
                print("Channel not found")
            else:
                print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Error: Failed to connect to Discord API")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Main function for command line usage"""
    settings = SettingsManager()
    
    # Check if stdin has data
    if not sys.stdin.isatty():
        message = sys.stdin.read().strip()
        
        # Session number is required
        if len(sys.argv) != 2:
            print("Error: Session number required")
            sys.exit(1)
            
        session_num = int(sys.argv[1])
        flask_port = settings.get_port('flask')
        
        # Look up session info from Flask API
        session_info = get_session_info_from_api(session_num, flask_port)
        
        if not session_info:
            print(f"Error: Session {session_num} not found")
            
            # Try to get available sessions
            sessions = get_sessions_list_from_api(flask_port)
            if sessions:
                print("Available sessions:")
                for session in sessions:
                    print(f"  Session {session['session_num']}")
            else:
                print("Could not retrieve session list from Flask API")
            sys.exit(1)
        
        channel_id = session_info['thread_id']
        
        # Post message
        if post_to_discord(channel_id, message):
            # Success - no output
            pass
        else:
            sys.exit(1)
    else:
        print("Usage: echo 'message' | discord_post.py <session_number>")
        sys.exit(1)

if __name__ == "__main__":
    main()