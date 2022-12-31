import io
import os

import aiohttp
from discord import ChannelType, File, Interaction
from discord.app_commands import Command

from generate import generate_image

PENNY_THREAD_NAME = os.getenv("PENNY_THREAD_NAME", "pennythread")


async def chat_command_handler(interaction: Interaction):

    # Get the parent channel
    channel = (
        interaction.channel
        if interaction.channel.type != ChannelType.public_thread
        else interaction.channel.parent
    )

    # Decline if the bot is not allowed to create public threads in the current channel
    if not channel.permissions_for(interaction.guild.me).create_public_threads:
        await interaction.response.send_message(
            "Apologies, I do not have permission to create public threads in this channel.",
            ephemeral=True,
        )
        return

    # Create a thread
    thread = await channel.create_thread(
        name=PENNY_THREAD_NAME,
        type=ChannelType.public_thread,
        auto_archive_duration=1440,  # 1 day
    )
    await thread.send(
        f"{interaction.user.mention} Salutations! How may I be of assistance?"
    )
    await interaction.response.send_message(
        f"Thread created: {thread.mention}", ephemeral=True
    )


async def imagine_command_handler(interaction: Interaction, *, prompt: str):

    # Decline if the bot is not allowed to attach images in the current channel
    if not interaction.channel.permissions_for(interaction.guild.me).attach_files:
        await interaction.send(
            "Apologies, I do not have permission to attach images in this channel.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()

    # Generate the image
    image = await generate_image(prompt)
    filename = prompt.replace(" ", "_") + ".png"
    file = File(io.BytesIO(image), filename=filename)

    # Send the image
    await interaction.followup.send(content=f"I'm imagining {prompt}...", file=file)


chat_command = Command(
    name="chat", description="Start a chat with Penny", callback=chat_command_handler
)

image_command = Command(
    name="imagine",
    description="Generate an image from a prompt",
    callback=imagine_command_handler,
)

__all__ = ["chat_command", "image_command"]
