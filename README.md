# Claude-Discord Bridge

A portable bridge tool that seamlessly connects Claude Code with Discord, supporting multi-session environments, slash commands, and multi-image attachments.

**[日本語版 (Japanese) / 日本語ドキュメント](./README_ja.md)**

## Key Features
- **Scalable Multi-Session**: Simply create one Discord bot, and Claude Code sessions are automatically spawned each time you add a channel.
- **Image Attachment Support**: Complete support for image analysis workflows
- **Slash Command Support**: Commands can also be executed via Discord
- **Fully Automated Setup**: One-command environment detection and one-click deployment
- **Portable Design**: No dependency on absolute paths or system-specific settings

## Operation Overview
1. Create a Discord Bot. Grant permissions and issue a Bot token
2. Launch install.sh to start installation.
3. During installation, you can configure Bot token and up to 3 Channel IDs.
   (Additional channels can be added later with vai add-session {channel id})
4. Add Discord response rules to CLAUDE.md.
5. Start with "vai".
6. Use "vai view" to directly operate and monitor multiple sessions in real-time with tmux
7. Chat from Discord → Responses come from Claude Code.

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

## Command List
### Basic Commands
- `vai` - Start all functions (Discord bot + routing + Claude Code session group)
- `vai status` - Check operational status
- `vai doctor` - Run environment diagnostics
- `vai view` - Display all sessions in real-time
  (Currently only supports up to 6 screen display)
- `vexit` - Stop all functions
- `vai add-session <channel_id>` - Add channel ID
- `vai list-session` - List channel IDs
- `dp [session] "message"` - Send message to Discord

## License
MIT License - See LICENSE file for details