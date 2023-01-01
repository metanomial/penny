import logging
import os

from hikari import GatewayBot, Intents, MessageCreateEvent, ShardReadyEvent

from handlers import on_message, on_ready

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Enable debug logging
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Debug mode enabled")

# Create the Discord bot and command tree
intents = Intents.ALL_UNPRIVILEGED | Intents.MESSAGE_CONTENT
discord_token = os.environ["DISCORD_TOKEN"]
bot = GatewayBot(token=discord_token, intents=intents)

# Subscribe to events
bot.subscribe(ShardReadyEvent, on_ready)
bot.subscribe(MessageCreateEvent, on_message)

bot.run(asyncio_debug=DEBUG)
