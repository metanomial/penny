import os

from discord import ChannelType, Message, MessageType, Thread, User

from generate import generate_response, generate_thread_name

PENNY_THREAD_NAME = os.getenv("PENNY_THREAD_NAME", "pennythread")


async def handle_channel(user: User, channel: Thread):

    # Get up to the last 8 text messages in the channel
    history = [message async for message in channel.history(limit=8)]
    history = [message for message in history if message.type == MessageType.default]
    history.reverse()

    # Generate and send a response
    response = await generate_response(user, history)
    if not response == "":
        newest_message = await channel.send(response)
        history.append(newest_message)

    # Give the thread a unique name
    if (
        channel.type == ChannelType.public_thread
        and channel.name == PENNY_THREAD_NAME
        and len(history) > 5
    ):
        name = await generate_thread_name(user, history)
        if not name == "":
            await channel.edit(name=name.strip())


async def handle_chain(user: User, message: Message):

    # Follow the message chain
    original_message = message
    history = [message]
    for _ in range(9):
        if message.reference:
            message = await message.channel.fetch_message(message.reference.message_id)
            history.append(message)
        else:
            break
    history.reverse()

    # Generate and send a response
    response = await generate_response(user, history)
    if not response == "":
        await original_message.reply(response)


__all__ = ["handle_channel", "handle_chain"]
