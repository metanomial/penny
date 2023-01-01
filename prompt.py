from datetime import datetime
from typing import Optional

import pytz
from hikari import DMChannel, Guild, Message, TextableChannel, User


def state_time(time: datetime) -> str:
    pacific_time = pytz.timezone("America/Los_Angeles")
    return f"The date and time is {time.astimezone(pacific_time).strftime('%B %d, %Y %I:%M:%S %p Pacific Time')}."


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


def describe_chatroom(channel: TextableChannel) -> str:

    description = "The following is a conversation in a "

    # The chatroom is a DM
    if isinstance(channel, DMChannel):
        description += f"DM with {render_user(channel.recipient)}."

    # The chatroom is a guild channel
    else:
        description += f"channel called {channel.name}."

        # The chatroom has a topic
        if hasattr(channel, "topic") and channel.topic:
            description += f" The topic is {channel.topic}."

    return description.strip()


def describe_personality(user: User, guild: Optional[Guild] = None):
    return f"{render_user(user, guild)} is a cutesy, cheerful, and helpful AI assistant. Her favorite greeting is 'Salutations!'"


__all__ = [
    "state_time",
    "render_user",
    "render_message",
    "describe_chatroom",
    "describe_personality",
]
