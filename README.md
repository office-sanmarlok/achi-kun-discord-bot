# Claude-Discord Bridge

A portable bridge tool that seamlessly connects Claude Code with Discord, supporting multi-session environments, slash commands, and multi-image attachments.

**[日本語版 (Japanese) / 日本語ドキュメント](./README_ja.md)**

## Key Features

- **Scalable Multi-Session**: Create one Discord bot and automatically spawn Claude Code sessions as you add channels
- **Image Attachment Support**: Full support for image analysis workflows
- **Slash Command Support**: Execute commands directly through Discord
- **Zero Configuration Setup**: One-command automated environment detection and installation
- **Portable Design**: No dependency on absolute paths or system-specific settings

## How It Works

1. Create a Discord Bot and obtain a bot token
2. Run install.sh to start installation
3. During installation, configure bot token and up to 3 channel IDs 
   (Additional channels can be added later with `vai add-session {channel_id}`)
4. Add Discord integration rules to your CLAUDE.md file
5. Start with `vai`
6. Monitor and interact with multiple sessions in real-time using `vai view`
7. Chat from Discord → Receive responses from Claude Code

## System Requirements

- macOS or Linux
- Python 3.8+
- tmux
- Discord Bot Token (create at [Discord Developer Portal](https://discord.com/developers/applications))

## Installation / Uninstallation

```bash
git clone https://github.com/yamkz/claude-discord-bridge.git
cd claude-discord-bridge
./install.sh
```

```bash
cd claude-discord-bridge
./uninstall.sh
```

## Quick Start

**1. Add to CLAUDE.md**
Add the following configuration to your workspace CLAUDE.md file:
[CLAUDE.md Configuration Example](./CLAUDE.md)

**2. Start Bridge and Check Session Status**
```bash
vai
vai view
```

**3. Test on Discord**

**4. Stop**
```bash
vexit
```

## Command Reference

### Basic Commands
- `vai` - Start all components (Discord bot + routing + Claude Code sessions)
- `vai status` - Check operational status
- `vai doctor` - Run environment diagnostics
- `vai view` - Display all sessions in real-time
  (Currently supports up to 6 session display)
- `vexit` - Stop all components
- `vai add-session <channel_id>` - Add new channel ID
- `vai list-session` - List all channel IDs
- `dp [session] "message"` - Send message to Discord

## Why Use Claude-Discord Bridge?

**One Discord Bot, Infinite Scaling**
- Create bot once in Discord Developer Portal
- Each new Discord channel automatically spawns a corresponding Claude Code session
- Separate channels for different use cases: teams, projects, personal workflows

**Example Use Cases**:
- #development-help → Claude Code Session 1 (development environment)
- #data-analysis → Claude Code Session 2 (analysis environment)  
- #design-review → Claude Code Session 3 (UI/UX workspace)
- Each session runs completely independently with different projects and workflows

## Architecture

```
Discord Channel ↔ Discord Bot ↔ Flask App ↔ Claude Code Session
     (1:1)           (API)        (Bridge)      (Independent)
```

## Configuration

Settings are stored in `~/.claude-discord-bridge/`:
- `.env` - Discord bot token and system settings
- `sessions.json` - Channel to session mappings

Add new sessions:
```bash
vai add-session <channel-id>
```

## Troubleshooting

**Port conflicts**: Run `vai doctor` to check and resolve port issues

**Bot not responding**: Verify bot token and permissions in Discord server

**Bridge won't start**: Run `vai doctor` for complete diagnostics

## Development

1. Fork the repository
2. Create a feature branch
3. Implement changes
4. Test with `vai doctor`
5. Submit a Pull Request

## License

MIT License - see LICENSE file for details

## Core Technologies

- Discord.py (bot framework)
- Flask (HTTP bridge)
- tmux (session management)