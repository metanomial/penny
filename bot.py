import logging
import os

from discord import ChannelType, Client, Intents, Message
from discord.app_commands import CommandTree

from commands import chat_command, image_command
from handlers import handle_chain, handle_channel

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Enable debug logging
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Debug mode enabled")

# Create the Discord bot and command tree
intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)
command_tree = CommandTree(client)

# Ready event
@client.event
async def on_ready():
    await command_tree.sync()
    logging.info(f"Salutations! Logged in as {client.user}")


# Message event
@client.event
async def on_message(message: Message):

    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Handle conversations in DMs
    if message.channel.type == ChannelType.private:
        await handle_channel(client.user, message)
        return

    # Handle conversations in designated threads
    if (
        message.channel.type == ChannelType.public_thread
        and message.channel.owner == client.user
    ):
        await handle_channel(client.user, message.channel)
        return

    # Handle conversations triggered by a mention
    if client.user in message.mentions:
        await handle_chain(client.user, message)
        return


# Register commands
command_tree.add_command(chat_command)
command_tree.add_command(image_command)

discord_token = os.environ["DISCORD_TOKEN"]
client.run(discord_token)
