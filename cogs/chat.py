import logging

import discord

logger = logging.getLogger("penny.chat")


class ChatCommand(discord.Cog):
    def __init__(self, bot: discord.Bot, chat_thread_name: str):
        self.bot = bot
        self.chat_thread_name = chat_thread_name

    @discord.slash_command(
        name="chat",
        description="Start a thread to chat with Penny.",
    )
    async def chat_command(self, ctx: discord.ApplicationContext):
        # Decline if the command is invoked outside of a guild
        if ctx.guild_id is None:
            await ctx.respond(
                "Apologies, this command is only available in guilds.",
                ephemeral=True,
            )
            return

        channel = ctx.channel or await self.bot.fetch_channel(ctx.channel_id)

        # Decline if the channel is not a text channel
        if channel.type != discord.ChannelType.text:
            await ctx.respond(
                "Apologies, this command is only available in text channels.",
                ephemeral=True,
            )
            return

        # Create a thread
        try:
            thread = await channel.create_thread(
                name=self.chat_thread_name,
                type=discord.ChannelType.public_thread,
            )
            await thread.send(
                f"{ctx.author.mention} Salutations! How may I be of assistance?"
            )
            await ctx.respond(f"Thread created: {thread.mention}", ephemeral=True)
            logger.info(
                f"Created thread {thread.id} in channel {channel.id} '{channel.name}'"
            )

        except discord.Forbidden:
            await ctx.respond(
                "Apologies, I do not have permission to create public threads in this channel.",
                ephemeral=True,
            )
            logger.info(
                f"Forbidden to create thread in channel {channel.id} '{channel.name}'"
            )

        except Exception as exc:
            await ctx.respond(
                "Apologies, I could not create a chat thread in this channel.",
                ephemeral=True,
            )
            logger.exception("Failed to create thread", exc_info=exc)
