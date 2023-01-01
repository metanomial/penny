import logging
import os

import aiohttp
import openai
from openai import Completion, Image

# Configure OpenAI
openai.organization = os.environ["OPENAI_ORGANIZATION"]
openai.api_key = os.environ["OPENAI_API_KEY"]

TEXT_ENGINE = "text-davinci-003"


async def generate_response(prompt: str, stop: list[str]) -> str:
    completion = Completion.create(
        engine=TEXT_ENGINE,
        prompt=prompt,
        max_tokens=180,
        temperature=0.9,
        presence_penalty=0.6,
        stop=stop,
    )
    response: str = completion.choices[0].text.strip()
    logging.debug(prompt + response)

    return response


async def generate_thread_name(prompt: str) -> str:

    prompt = f"{prompt}\n\n---\n\nCome up with a single short name for this thread:"

    # Query the OpenAI API
    completion = Completion.create(
        engine=TEXT_ENGINE,
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


__all__ = ["generate_response", "generate_thread_name", "generate_image"]
