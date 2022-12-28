import os
import re
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

# Regex patterns
angle_brackets = re.compile(r"[<>]")
whitespace = re.compile(r"[\n\t\s]+")


@client.event
async def on_ready():
    print(f"Salutations! Logged in as {client.user}")


@client.event
async def on_message(message: discord.Message):

    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Trigger a response when the bot is mentioned
    if client.user in message.mentions:
        await generate_response(message)


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


def normalize_username(user: discord.Member) -> str:

    # Return "Penny" for the bot itself
    if user == client.user:
        return "Penny"

    # Remove angle brackets from the user's display name
    return angle_brackets.sub("", user.display_name)


async def generate_response(message: discord.Message) -> str:

    # Build the prompt
    intro = f"""
        The following is a conversation in a chatroom called "{message.channel.name}".
        The date is {message.created_at:%Y-%m-%d}. Penny is a cutesy, cheerful, helpful
        assistant who often uses the word "salutations" when greeting people.
    """
    intro = whitespace.sub(" ", intro).strip()
    messages = await follow_message_chain(message, 9)
    messages = [
        f"<{normalize_username(m.author)}>\n{m.clean_content.strip()}" for m in messages
    ]
    conversation = "\n\n".join(messages)
    prompt = f"{intro}\n\n{conversation}\n\n<Penny>\n"

    # Query the OpenAI API
    completion = openai.Completion.create(
        engine="text-curie-001",
        prompt=prompt,
        max_tokens=150,
        temperature=0.9,
        presence_penalty=0.6,
        stop=["\n<"],
    )

    # Respond to the user
    response = completion.choices[0].text.strip()
    await message.channel.send(response, reference=message)


discord_token = os.environ["DISCORD_TOKEN"]
client.run(discord_token)
