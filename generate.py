import logging
import os
import re
from datetime import datetime
from typing import Optional

import aiohttp
import openai
import pytz
from discord import Message, User
from openai import Completion, Image

ANGLE_BRACKETS = re.compile(r"[<>]")
PENNY_THREAD_NAME = os.getenv("PENNY_THREAD_NAME", "pennythread")

# Configure OpenAI
openai.organization = os.environ["OPENAI_ORGANIZATION"]
openai.api_key = os.environ["OPENAI_API_KEY"]


async def generate_response(user: User, messages: list[Message]) -> str:

    # Build the prompt
    intro = [*prompt_intro(), "Penny is thinking what to say."]
    conversation = format_messages(user, messages)
    prompt = f"{' '.join(intro)}\n\n{conversation}\n\n<Penny>\n"

    # Query the OpenAI API
    completion = Completion.create(
        engine="text-davinci-001",
        prompt=prompt,
        max_tokens=180,
        temperature=0.9,
        presence_penalty=0.6,
        stop=["\n<"],
    )

    response = completion.choices[0].text.strip()
    logging.debug(prompt + response)

    return response


async def generate_thread_name(user: User, messages: list[Message]) -> str:

    # Build the prompt
    intro = [
        *prompt_intro(channel_name=messages[0].channel.name, personality=True),
        "Come up with a single short name for this thread.",
    ]
    conversation = format_messages(user, messages)
    prompt = f"{' '.join(intro)}\n\n{conversation}\n\nThis thread should be called:"

    # Query the OpenAI API
    completion = Completion.create(
        engine="text-davinci-001",
        prompt=prompt,
        max_tokens=15,
        temperature=0.9,
        presence_penalty=0.6,
        stop=["\n"],
    )

    thread_name = completion.choices[0].text.strip()
    logging.debug(prompt + thread_name)

    return thread_name


async def generate_image(prompt: str) -> bytes:

    # Query the OpenAI API
    response = Image.create(prompt=prompt, n=1, size="1024x1024")
    image_url = response["data"][0]["url"]

    # Fetch final image
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            return await response.read()


def prompt_intro(*, channel_name: Optional[str] = None, personality=False) -> list[str]:

    # Discard channel name if it's the default
    channel_name = None if channel_name == PENNY_THREAD_NAME else channel_name

    # Get the current date and time in Pacific Time
    now = datetime.now()
    pacific_time = pytz.timezone("America/Los_Angeles")
    formatted_datetime = now.astimezone(pacific_time).strftime(
        "%B %d, %Y %I:%M:%S %p Pacific Time"
    )

    # Base statements
    statements = [
        f'The following is a conversation in a chatroom called "{channel_name}".'
        if channel_name
        else "The following is a conversation in a chatroom.",
        f"The date and time is {formatted_datetime}.",
    ]

    # Append extra statements about Penny's personality
    if personality:
        statements.extend(
            [
                "Penny is a cutesy, cheerful, and helpful assistant.",
                "Her favorite greeting is 'Salutations!'",
            ]
        )

    return statements


def format_messages(user: User, messages: list[Message]) -> str:

    formatted_messages = []

    for message in messages:
        author = (
            "Penny"
            if message.author == user
            else ANGLE_BRACKETS.sub("", message.author.display_name)
        )
        content = message.clean_content.strip()
        formatted_messages.append(f"<{author}>\n{content}")

    return "\n\n".join(formatted_messages)


__all__ = ["generate_response", "generate_thread_name"]
