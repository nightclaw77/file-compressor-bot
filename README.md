# 📦 File Compressor Bot

Telegram bot to compress files to ZIP/RAR and merge multiple files.

## Features

- 📇 Compress to ZIP
- 📦 Compress to RAR  
- 🔀 Merge multiple files into one archive

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/help` | Show help |
| `/zip` | Set mode to ZIP |
| `/rar` | Set mode to RAR |
| `/merge` | Merge multiple files |
| `/done` | Finish merge and create archive |
| `/compress` | Reply to a file to compress it |

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set bot token
export BOT_TOKEN="your_bot_token_here"

# Run
python bot.py
```

## Docker

```bash
docker build -t compressor-bot .
docker run -d -e BOT_TOKEN="your_token" compressor-bot
```

## Usage

1. Send a file → Auto-compress to ZIP
2. Send `/zip` then files → Compress to ZIP
3. Send `/rar` then files → Compress to RAR
4. Send multiple files then `/merge` → Merge into one ZIP
