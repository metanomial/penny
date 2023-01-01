import logging
import os
from typing import Optional

from hikari import (
    DMChannel,
    GatewayBot,
    Guild,
    GuildChannel,
    GuildThreadChannel,
    MessageCreateEvent,
    MessageType,
    OwnUser,
    ShardReadyEvent,
    TextableChannel,
)

from generate import generate_response, generate_thread_name
from prompt import (
    describe_chatroom,
    describe_personality,
    render_message,
    render_user,
    state_time,
)

PENNY_THREAD_NAME = os.getenv("PENNY_THREAD_NAME", "pennythread")


async def on_ready(event: ShardReadyEvent):
    name = render_user(event.my_user)
    logging.info(f"Salutations! Logged in as {name}")


async def on_message(event: MessageCreateEvent):

    # Ignore messages from bots
    if event.is_bot:
        return

    # Ignore non-text messages
    message = event.message
    if message.type != MessageType.DEFAULT:
        return

    # Fetch the channel
    channel = await message.fetch_channel()
    assert isinstance(channel, TextableChannel)

    # Get the bot user
    bot = event.app
    assert isinstance(bot, GatewayBot)
    bot_user = bot.get_me()
    assert isinstance(bot_user, OwnUser)

    # Determine the conversation mode
    if isinstance(channel, DMChannel):
        mode = "thread"
    elif isinstance(channel, GuildThreadChannel) and channel.owner_id == bot_user.id:
        mode = "thread"
    elif bot_user.id in message.user_mentions:
        mode = "reply"
    else:
        return  # Ignore messages not directed at the bot

    # Fetch up to 8 messages from the conversation history
    match mode:
        case "thread":
            messages = list(
                await channel.fetch_history()
                .limit(8)
                .filter(lambda m: m.type == MessageType.DEFAULT)
                .reversed()
            )
        case "reply":
            messages = [message]
            head = message
            for _ in range(7):
                if reference := head.message_reference:
                    head = await channel.fetch_message(reference.id)
                    messages.append(head)
                else:
                    break
            messages.reverse()

    # Fetch the guild and get the channel topic if they exist
    guild: Optional[Guild] = (
        await channel.fetch_guild() if isinstance(channel, GuildChannel) else None
    )

    # Build the prompt
    intro = " ".join(
        [
            describe_chatroom(channel),
            state_time(message.created_at),
            describe_personality(bot_user, guild),
        ]
    )
    conversation = [render_message(message, guild) for message in messages]
    conversation.append(f"<{render_user(bot_user, guild)}>\n")
    prompt = "\n\n".join([intro, *conversation]) + "\n"

    # Generate and send a response
    response = await generate_response(prompt, ["\n<"])
    if response:
        response_message = await channel.send(
            response, reply=message if mode == "reply" else None
        )
        messages.append(response_message)

    # Give threads unique names
    if isinstance(channel, GuildThreadChannel) and channel.name == PENNY_THREAD_NAME:
        thread_name = await generate_thread_name(prompt)
        await channel.edit(name=thread_name)


__all__ = ["on_ready", "on_message"]
