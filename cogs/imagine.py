import io
import logging

import aiohttp
import discord
import openai

logger = logging.getLogger("penny.imagine")


class ImagineCommand(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.slash_command(
        name="imagine", description="Generate an image from a text prompt."
    )
    async def imagine_command(
        self,
        ctx: discord.ApplicationContext,
        prompt: discord.Option(str, "The text prompt", required=True),
    ):
        await ctx.defer()

        # Query the OpenAI API
        response = openai.Image.create(prompt=prompt, n=1, size="1024x1024")
        image_url = response["data"][0]["url"]

        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                image = await response.read()

        await ctx.edit(
            content=f"I'm imagining {prompt}...",
            file=discord.File(
                io.BytesIO(image),
                filename=prompt.replace(" ", "_") + ".png",
                description=prompt,
            ),
        )
