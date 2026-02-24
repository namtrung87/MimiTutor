---
name: telegram-integration
description: Allows the Orchestra Assistant to communicate via Telegram for notifications and commands.
metadata:
  version: "1.0"
  type: "bridge"
---
# Skill: Telegram Integration

This skill allows the Orchestra Assistant to communicate with the user via a Telegram Bot. It supports proactive notifications and direct command processing.

## Capabilities
*   **Proactive Notifications:** The Supervisor can send "Task Complete" alerts directly to your phone.
*   **Command Execution:** Send any text message to the bot, and it will be routed through the `Supervisor` graph.
*   **Secure Access:** The bot only responds to the configured `TELEGRAM_USER_ID`.

## Configuration
Requires the following variables in `.env`:
*   `TELEGRAM_BOT_TOKEN`: The API token from @BotFather.
*   `TELEGRAM_USER_ID`: Your unique Telegram ID (Get it from @userinfobot).

## Usage
1.  Run the bridge: `python bridges/telegram_bridge.py`.
2.  Send a message to your bot on Telegram.
3.  The bot will process the request using the full agent orchestra and reply with the result.
