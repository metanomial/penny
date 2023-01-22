import logging
import os
from typing import Optional

import aiohttp
import openai
import pytz
from dotenv import load_dotenv
from hikari import (
    UNDEFINED,
    Attachment,
    Bytes,
    ChannelType,
    CommandInteraction,
    CommandInteractionOption,
    CommandOption,
    DMMessageCreateEvent,
    ForbiddenError,
    GatewayBot,
    Guild,
    GuildChannel,
    GuildThreadChannel,
    Intents,
    InteractionCreateEvent,
    Message,
    MessageCreateEvent,
    MessageFlag,
    MessageType,
    OptionType,
    OwnUser,
    ResponseType,
    ShardReadyEvent,
    StartingEvent,
    TextableChannel,
    User,
)
from openai import Completion, Image

load_dotenv()

# Configure OpenAI
openai.organization = os.environ["OPENAI_ORGANIZATION"]
openai.api_key = os.environ["OPENAI_API_KEY"]

TEXT_ENGINE = "text-davinci-003"

# Settings
CHAT_THREAD_NAME = os.getenv("CHAT_THREAD_NAME", "chat")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Enable debug logging
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Debug mode enabled")

# Create the Discord bot and command tree
intents = Intents.ALL_UNPRIVILEGED | Intents.MESSAGE_CONTENT
discord_token = os.environ["DISCORD_TOKEN"]
bot = GatewayBot(token=discord_token, intents=intents)


@bot.listen()
async def handle_start(event: StartingEvent):

    application = await bot.rest.fetch_application()

    # Define slash commands
    commands = [
        bot.rest.slash_command_builder("chat", "Start a thread to chat with Penny"),
        bot.rest.slash_command_builder(
            "imagine", "Generate an image from a text prompt"
        ).add_option(
            CommandOption(
                type=OptionType.STRING,
                name="prompt",
                description="The text prompt",
                is_required=True,
            )
        ),
    ]

    # Register slash commands
    await bot.rest.set_application_commands(application, commands)


@bot.listen()
async def handle_ready(event: ShardReadyEvent):

    name = render_user(event.my_user)
    logging.info(f"Salutations! Logged in as {name}")


@bot.listen()
async def on_interaction(event: InteractionCreateEvent):

    interaction = event.interaction

    # Handle slash commands
    if isinstance(interaction, CommandInteraction):
        await handle_command(interaction)


async def handle_command(interaction: CommandInteraction):

    match interaction.command_name:
        case "chat":
            await handle_chat_command(interaction)
        case "imagine":
            await handle_imagine_command(interaction)


async def handle_chat_command(interaction: CommandInteraction):

    # Decline if the command is not invoked outside of a guild
    if interaction.guild_id is None:
        await interaction.create_initial_response(
            ResponseType.MESSAGE_CREATE,
            "Apologies, this command is only available in guilds.",
            flags=MessageFlag.EPHEMERAL,
        )
        return

    # Fetch the channel
    channel = await interaction.fetch_channel()

    # Decline if the channel is a thread
    if isinstance(channel, GuildThreadChannel):
        await interaction.create_initial_response(
            ResponseType.MESSAGE_CREATE,
            "Apologies, this command cannot be used in threads.",
            flags=MessageFlag.EPHEMERAL,
        )
        return

    # Create a thread
    try:
        thread = await bot.rest.create_thread(
            channel.id,
            ChannelType.GUILD_PUBLIC_THREAD,
            CHAT_THREAD_NAME,
        )
        await thread.send(
            f"{interaction.user.mention} Salutations! How may I be of assistance?"
        )
        await interaction.create_initial_response(
            ResponseType.MESSAGE_CREATE,
            f"Thread created: {thread.mention}",
            flags=MessageFlag.EPHEMERAL,
        )

    # Handle permission errors
    except ForbiddenError:
        await interaction.create_initial_response(
            ResponseType.MESSAGE_CREATE,
            "Apologies, I do not have permission to create public threads in this channel.",
            flags=MessageFlag.EPHEMERAL,
        )

    # Handle other errors
    except Exception:
        await interaction.create_initial_response(
            ResponseType.MESSAGE_CREATE,
            f"Apologies, I could not create a chat thread in this channel.",
            flags=MessageFlag.EPHEMERAL,
        )


async def handle_imagine_command(interaction: CommandInteraction):

    await interaction.create_initial_response(ResponseType.DEFERRED_MESSAGE_CREATE)

    # Fetch the prompt
    prompt_option = interaction.options[0]
    assert isinstance(prompt_option, CommandInteractionOption)
    prompt = prompt_option.value
    assert isinstance(prompt, str)

    # Query the OpenAI API
    response = Image.create(prompt=prompt, n=1, size="1024x1024")
    image_url = response["data"][0]["url"]

    # Download the image
    image: bytes
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            image = await response.read()

    # Create an attachment
    filename = prompt.replace(" ", "_") + ".png"
    attachment = Bytes(image, filename, mimetype="image/png")

    # Send the image
    await interaction.edit_initial_response(
        content=f"I'm imagining {prompt}...",
        attachment=attachment,
    )


@bot.listen()
async def on_message(event: MessageCreateEvent):

    # Ignore messages from bots
    if event.is_bot:
        return

    # Ignore non-text messages
    message = event.message
    if message.type != MessageType.DEFAULT:
        return

    # Get the bot user
    bot_user = bot.get_me()
    assert isinstance(bot_user, OwnUser)

    # Fetch the channel
    channel = await message.fetch_channel()
    assert isinstance(channel, TextableChannel)

    # Determine the conversation mode
    if isinstance(event, DMMessageCreateEvent):
        mode = "dm"
    elif isinstance(channel, GuildThreadChannel) and channel.owner_id == bot_user.id:
        mode = "thread"
    elif bot_user.id in message.user_mentions:
        mode = "mention"
    else:
        return  # Ignore messages that are not addressed to the bot

    # Fetch the conversation history
    messages: list[Message]
    if mode == "mention":

        # Start with the message that mentioned the bot
        messages = [message]
        head = message

        # Crawl up the message chain, up to 7 messages back
        for _ in range(7):
            if head.referenced_message is None:
                break
            head = await channel.fetch_message(head.referenced_message.id)
            if head.type != MessageType.DEFAULT:
                break
            messages.append(head)

        # Put the messages in chronological order
        messages.reverse()

    else:

        # Fetch the last 8 messages in the channel
        messages = list(
            await channel.fetch_history()
            .limit(8)
            .filter(lambda m: m.type == MessageType.DEFAULT)
            .reversed()
        )

    # Fetch the guild
    guild: Optional[Guild] = None
    if isinstance(channel, GuildChannel):
        guild = await channel.fetch_guild()
        assert isinstance(guild, Guild)

    # Build the date and time statement
    pacific_time = pytz.timezone("America/Los_Angeles")
    datetime_statement = f"The date and time is {message.created_at.astimezone(pacific_time).strftime('%B %d, %Y %I:%M:%S %p Pacific Time')}"

    # Build the prompt intro
    intro: str = f"The following is a conversation "
    if mode == "dm":
        intro += f"with {render_user(message.author)}."
    else:
        intro += f"in a channel called {channel.name}."
    if hasattr(channel, "topic"):
        intro += f" The topic is {channel.topic}."
    intro += f" {datetime_statement}. {render_user(bot_user, guild)} is a cutesy, cheerful, and helpful AI assistant. Her favorite greeting is 'Salutations!'"

    # Format the conversation history
    conversation = [render_message(message, guild) for message in messages]
    conversation.append(f"<{render_user(bot_user, guild)}>\n")

    # Build the prompt
    prompt = "\n\n".join([intro, *conversation])

    # Query the OpenAI API
    completion = Completion.create(
        engine=TEXT_ENGINE,
        prompt=prompt,
        max_tokens=180,
        temperature=0.9,
        presence_penalty=0.6,
        stop="\n<",
    )
    response: str = completion.choices[0].text.strip()
    logging.debug(prompt + response)

    # Send the response
    if response:
        reply = message if mode == "mention" else UNDEFINED
        response_message = await channel.send(response, reply=reply)
        messages.append(response_message)

    # Rename the thread
    if isinstance(channel, GuildThreadChannel) and len(messages) > 4:

        # Extend the prompt
        prompt = (
            f'{prompt}\n\n---\n\nCome up with a single short name for this thread: "'
        )

        # Query the OpenAI API
        completion = Completion.create(
            engine=TEXT_ENGINE,
            prompt=prompt,
            max_tokens=15,
            temperature=0.9,
            presence_penalty=0.6,
            stop=["\n", '"'],
        )
        thread_name = completion.choices[0].text.strip()
        logging.debug(prompt + thread_name)

        # Rename the thread
        if thread_name:
            await bot.rest.edit_channel(channel, name=thread_name)


def render_user(user: User, guild: Optional[Guild] = None) -> str:

    # If the guild is provided, try to get the member's display name
    if guild:
        member = guild.get_member(user.id)
        if member:
            return member.display_name

    # Otherwise, return the user's username with discriminator
    return f"{user.username}#{user.discriminator}"


def render_message(message: Message, guild: Optional[Guild] = None) -> str:
    return f"<{render_user(message.author, guild)}>\n{message.content.strip()}"


bot.run(asyncio_debug=DEBUG)
