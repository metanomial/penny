from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List

import discord
import openai

# Configure OpenAI
openai.organization = os.environ["OPENAI_ORGANIZATION"]
openai.api_key = os.environ["OPENAI_API_KEY"]

# Create the bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
discord_token = os.environ["DISCORD_TOKEN"]
tree = discord.app_commands.CommandTree(client)

# Regex patterns
angle_brackets = re.compile(r"[<>]")


@client.event
async def on_ready():
    await tree.sync()
    print(f"Salutations! Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):

    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Ignore messages sent in DMs
    if not message.guild:
        return

    # Determine if the message was sent in a "pennythread"
    is_pennythread = (
        message.channel.type == discord.ChannelType.public_thread
        and message.channel.owner == client.user
    )

    # Message was sent in a pennythread
    if is_pennythread:
        history = [message async for message in message.channel.history(limit=9)]
        history.reverse()

    # Trigger a response when the bot is mentioned anywhere
    elif client.user in message.mentions:
        history = await follow_message_chain(message, 9)

    else:
        return

    # Generate and send a response
    response = await generate_response(history)
    if not response == "":
        if is_pennythread:
            await message.channel.send(response)
        else:
            await message.reply(response)

    # If a pennythread doesn't have a unique name after 5 messages, rename it
    if is_pennythread and message.channel.name == "pennythread" and len(history) > 5:
        name = await generate_thread_name(history)
        await message.channel.edit(name=name.strip())


@tree.command(
    name="pennythread",
    description="Create a thread for speaking with Penny.",
)
async def pennythread_command(interaction: discord.Interaction):

    # If command is invoked in a thread, tell the user to use the parent channel
    if interaction.channel.type == discord.ChannelType.public_thread:
        await interaction.response.send_message(
            "Please use this command in the parent channel of the thread.",
            ephemeral=True,
        )
        return

    # If the bot is not allowed to create threads, tell the user
    if not interaction.channel.permissions_for(
        interaction.guild.me
    ).create_public_threads:
        await interaction.response.send_message(
            "Apologies, I do not have permission to create public threads in this channel.",
            ephemeral=True,
        )
        return

    # Create a thread
    greeting = f"<@{interaction.user.id}> Salutations! How may I be of assistance?"
    thread = await interaction.channel.create_thread(
        name="pennythread", type=discord.ChannelType.public_thread
    )
    await thread.send(greeting)
    await interaction.response.send_message(
        f"Thread created: {thread.mention}", ephemeral=True
    )


async def follow_message_chain(
    message: discord.Message, limit: int = 100
) -> List[discord.Message]:

    # Empty message chain
    if limit <= 0:
        return []

    # Follow the message chain
    chain = [message]
    for _ in range(limit - 1):
        if message.reference:
            message = await message.channel.fetch_message(message.reference.message_id)
            chain.append(message)
        else:
            break
    chain.reverse()

    return chain


def format_messages(messages: List[discord.Message]) -> str:

    formatted_messages = []

    for message in messages:
        author = (
            "Penny"
            if message.author == client.user
            else angle_brackets.sub("", message.author.display_name)
        )
        content = message.clean_content.strip()
        formatted_messages.append(f"<{author}>\n{content}")

    return "\n\n".join(formatted_messages)


async def generate_response(messages: List[discord.Message]) -> str:

    # Build the prompt
    intro = ""
    if len(messages) > 0:
        intro += f'The following is a conversation in a chatroom called "{messages[0].channel.name}". '
    intro += f"The date and time is {datetime.now():%Y-%m-%d %H:%M:%S}. "
    intro += "Penny is a cutesy, cheerful, and helpful assistant. "
    intro += 'Her favorite greeting is "Salutations!".'
    conversation = format_messages(messages)
    prompt = f"{intro}\n\n{conversation}\n\n<Penny>\n"

    # Query the OpenAI API
    completion = openai.Completion.create(
        engine="text-davinci-001",
        prompt=prompt,
        max_tokens=150,
        temperature=0.9,
        presence_penalty=0.6,
        stop=["\n<"],
    )

    return completion.choices[0].text.strip()


async def generate_thread_name(messages: List[discord.Message]) -> str:

    # Build the prompt
    intro = "The following is a conversation in a chatroom. "
    intro += f"The date and time is {datetime.now():%Y-%m-%d %H:%M:%S}. "
    intro += "Come up with a single short name for this thread."
    conversation = format_messages(messages)
    prompt = f"{intro}\n\n{conversation}\nThis thread should be called:"

    # Query the OpenAI API
    completion = openai.Completion.create(
        engine="text-davinci-001",
        prompt=prompt,
        max_tokens=15,
        temperature=0.9,
        presence_penalty=0.6,
        stop=["\n"],
    )

    return completion.choices[0].text.strip()


if __name__ == "__main__":
    client.run(discord_token)
