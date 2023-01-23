import logging
import os
from typing import Optional

import discord
import openai
import pytz
from dotenv import load_dotenv

from cogs import ChatCommand, ImagineCommand

load_dotenv()

chat_thread_name = os.getenv("CHAT_THREAD_NAME", "chat")

token = os.environ["DISCORD_TOKEN"]
debug = os.getenv("DEBUG", "false").lower() == "true"

openai.organization = os.environ["OPENAI_ORGANIZATION"]
openai.api_key = os.environ["OPENAI_API_KEY"]

text_model = "text-davinci-003"

logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
logger = logging.getLogger("penny")


class Penny(discord.Bot):
    async def on_ready(self):
        logger.info(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        if message.is_system():
            return

        # Handle chat thread
        if (
            message.channel.type == discord.ChannelType.public_thread
            and message.channel.owner == self.user
        ):
            await self.chat(message, mode="thread")
            return

        # Handle mention
        if self.user in message.mentions:
            await self.chat(message, mode="mention")
            return

        # Handle DM
        if message.channel.type == discord.ChannelType.private:
            await self.chat(message, mode="dm")
            return

    async def chat(self, message: discord.Message, mode: str):
        if mode == "mention":
            history = await crawl_replies(message)
        else:
            history = list(
                await message.channel.history(limit=8, oldest_first=True).flatten()
            )

        prompt, conversation = create_prompt(history, mode)
        response = await generate_response(prompt)
        conversation += response

        if response:
            if mode == "mention":
                await message.reply(response)
            else:
                await message.channel.send(response)

        if mode == "thread" and message.channel.name == chat_thread_name:
            await rename_thread(message, conversation)


def create_prompt(history: list[discord.Message], mode: str) -> tuple[str, str]:
    message = history[-1]

    # Build the date and time statement
    pacific_time = pytz.timezone("America/Los_Angeles")
    datetime_statement = f"The date and time is {message.created_at.astimezone(pacific_time).strftime('%B %d, %Y %I:%M:%S %p Pacific Time')}"

    # Build the prompt intro
    intro = "The following is a conversation "
    if mode == "dm":
        intro += f"with {message.author.display_name}."
    else:
        intro += f"in a channel called {message.channel.name}."
    if hasattr(message.channel, "topic") and message.channel.topic:
        intro += f" The topic is {message.channel.topic}."
    intro += f" {datetime_statement}. {bot.user.display_name} is a cutesy, cheerful, and helpful AI assistant."

    # Build the final prompt
    conversation = ""
    for msg in history:
        conversation += (
            f"{msg.author.display_name} {msg.author.mention}:\n{msg.clean_content}\n\n"
        )
    conversation += f"{bot.user.display_name} {bot.user.mention}:\n"
    prompt = f"{intro}\n\n{conversation}"

    return prompt, conversation


async def generate_response(prompt: str) -> str:
    completion = openai.Completion.create(
        engine=text_model,
        prompt=prompt,
        max_tokens=180,
        temperature=0.9,
        frequency_penalty=0.5,
        presence_penalty=0.8,
        stop="\n\n",
    )
    response: str = completion.choices[0].text.strip()
    logger.debug(prompt + response)
    return response


async def rename_thread(message: discord.Message, conversation: str):
    prompt = f'The following is a conversation in a thread:\n\n{conversation}\n\n---\n\nChose a short name for this thread: "'
    completion = openai.Completion.create(
        engine=text_model,
        prompt=prompt,
        max_tokens=15,
        temperature=0.9,
        presence_penalty=0.6,
        stop=["\n", '"'],
    )
    thread_name: Optional[str] = completion.choices[0].text.strip()
    logger.debug(f'{prompt}{thread_name}"')
    if thread_name:
        await message.channel.edit(name=thread_name)


async def crawl_replies(message: discord.Message) -> list[discord.Message]:
    replies = [message]
    head = message
    for _ in range(7):
        if head.reference is None:
            break
        head = await message.channel.fetch_message(head.reference.message_id)
        replies.append(head)
    replies.reverse()
    return replies


def format_message(message: discord.Message) -> str:
    """Format a message for the prompt."""
    pacific_time = pytz.timezone("America/Los_Angeles")
    return f"[{message.created_at.astimezone(pacific_time).strftime('%H:%M:%S %d/%m/%Y')}] {message.author.display_name} {message.author.mention}:\n{message.clean_content}"


intents = discord.Intents.default()
intents.message_content = True
bot = Penny(intents=intents)
bot.add_cog(ChatCommand(bot, chat_thread_name))
bot.add_cog(ImagineCommand(bot))
bot.run(token)
