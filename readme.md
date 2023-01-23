# Penny

Chat and image generation Discord bot.

## Overview

Mention the bot to start a conversation. Reply to the bot's messages to continue
the conversation. Responses are generated using
[OpenAI's GPT-3].

Alternatively, use the `/chat` command to start a dedicated conversation thread.
You don't need to reply to the bot's messages to continue the conversation.

Generate an image from a prompt with the `/imagine` command. Images are
generated using [OpenAI's DALL-E].

## Setup

Requires [Python 3.10+] and [Poetry].

1. Install dependencies with Poetry.

   ```
   poetry install
   ```

2. Create a `.env` file and set the following environment variables:

   ```bash
   # Discord API
   DISCORD_TOKEN = "your discord bot token"

   # OpenAI API
   OPENAI_ORGANIZATION = "your openai organization id"
   OPENAI_API_KEY = "your openai api key"

   # Optional settings
   CHAT_THREAD_NAME = "chat"
   ```

3. Run the bot with `poetry run python bot.py`.

## License

[MIT](license.txt)

[OpenAI's GPT-3]: https://openai.com/blog/openai-api
[OpenAI's DALL-E]: https://openai.com/blog/dall-e
[Python 3.10+]: https://www.python.org/downloads
[Poetry]: https://python-poetry.org
