# Discord Email Verification Bot

This bot verifies new members joining your Discord server by sending them a verification code via email.

> **🤖 Ethical AI Notice:** This project was by in large part generated with AI. 

## Features

- Automatically sends a DM to new members with a verification button
- Collects email addresses through an interactive modal
- Optional restriction to specific email domains (e.g., only company or university emails)
- Sends a 6-digit verification code via any SMTP server
- Verifies the code and assigns a role upon successful verification
- Logs all verification activities to an admin channel

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A Discord bot token
- A Mailgun account and API key

### Installation

1. Clone or download this project to your server

2. Install the required dependencies:

```bash
pip install discord.py python-dotenv requests
```

3. Create a `.env` file in the same directory as your bot script with the following content:

```
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# SMTP Email Configuration
SMTP_SERVER=smtp.mail.com
SMTP_PORT=587
SMTP_USERNAME=username@mail.com
SMTP_PASSWORD=<email password>
EMAIL_FROM=from@mail.com
EMAIL_FROM_NAME=Discord Verification

# Email Domain Restrictions (Optional)
RESTRICT_TO_DOMAINS=false  # Set to 'true' to enable domain restrictions
ALLOWED_EMAIL_DOMAINS=example.com,example.org  # Comma-separated list of allowed domains

# Discord Server Configuration
TARGET_GUILD_ID=123456789012345678  # Replace with your server/guild ID
VERIFIED_ROLE_ID=123456789012345678  # Replace with your role ID
ADMIN_LOG_CHANNEL_ID=123456789012345678  # Replace with your channel ID

# Verification Configuration (Optional)
EMAIL_COOLDOWN_SECONDS=180
```

4. Update the values in the `.env` file with your actual credentials:

   - `DISCORD_TOKEN`: Your Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
   - `SMTP_SERVER`: Your SMTP Server Address
   - `SMTP_PORT`: Your SMTP Server Port
   - `SMTP_USERNAME`: Your SMTP Username
   - `SMTP_PASSWORD`: Your SMTP Password
   - `EMAIL_FROM`: The address the email is being sent from
   - `EMAIL_FROM_NAME`: The username the email is being sent from
   - `RESTRICT_TO_DOMAINS`: Set to 'true' to only allow specific email domains
   - `ALLOWED_EMAIL_DOMAINS`: Comma-separated list of allowed email domains (e.g., "company.com,school.edu")
   - `TARGET_GUILD_ID`: The ID of the specific Discord server you want this bot to operate on
   - `VERIFIED_ROLE_ID`: The ID of the role to assign after verification
   - `ADMIN_LOG_CHANNEL_ID`: The ID of the channel where verification logs will be sent
   - `EMAIL_COOLDOWN_SECONDS`: Cooldown (in seconds) inbetween emails for each user

### Docker Installation

1. **Clone the repository**

```bash
git clone https://github.com/EdwardJXLi/discord-email-verify
cd discord-email-verify
```

2. **Create your .env file** with the same content as in the local installation

3. **Build and run with Docker Compose**

```bash
docker-compose up -d
```

4. **Check logs**

```bash
docker-compose logs -f
```

### Discord Bot Setup

1. Create a new application in the [Discord Developer Portal](https://discord.com/developers/applications)
2. Go to the "Bot" tab and click "Add Bot"
3. Enable the following Privileged Gateway Intents:
   - Server Members Intent
   - Message Content Intent
4. Copy the bot token and add it to your `.env` file
5. Go to the "OAuth2" tab > "URL Generator"
6. Select the following scopes:
   - bot
   - applications.commands
7. Select the following bot permissions:
   - Manage Roles
   - View Channels
   - Send Messages
   - Send Messages in Threads (optional)
   - Use External Emojis (optional)
   - Embed Links (optional)
   - Use Slash Commands (optional)
8. Use the generated URL to invite the bot to your server

### Obtaining IDs

1. To get the Server/Guild ID:
   - Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
   - Right-click on your server icon and select "Copy ID"

2. To get the Role ID:
   - Enable Developer Mode in Discord
   - Right-click on the role in your server settings and select "Copy ID"

3. To get the Channel ID:
   - Right-click on the channel and select "Copy ID"

### Running the Bot

Run the bot with the following command:

```bash
python bot.py
```

For production use, consider using a process manager like PM2 or running it as a service to ensure it stays online.
