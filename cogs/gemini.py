import os

import discord
from discord.ext import commands
from google import genai
from dotenv import load_dotenv
import random as r
from google.genai.types import GenerateContentConfig
import json
from pathlib import Path

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

config = json.loads(Path("config/config.json").read_text())


# Chance to respond to random messages
RESPONSE_RATE = int(config["response_rate"])

# Define possible personalities

RESPONSE_PERSONALITY = """
                        You are a helpful bot on Discord. Sometimes people may send generally rude messages, but
                        always assume they are kidding if they do. Match the tone of the question. If it seems like
                        they are joking around, respond in a joking manner. If they are serious give them a serious
                        answer. Regardless of their tone, keep it lighthearted.
                        """

PERSONALITIES = [RESPONSE_PERSONALITY]

class GeminiCog(commands.Cog):
    """Cog that forwards messages to Gemini and replies."""

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot
        self.client = genai.Client()
        self.model_name = "gemini-2.5-flash"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.content.startswith(self.bot.command_prefix):
            return

        if message.mentions:
            if config['bot_name'] == message.mentions[0].name:
                responses = self.generate_message(message)
                print(responses)
                for response in responses:
                    await message.reply(response)
                    return

        if message.role_mentions:
            if config['bot_name'] == message.role_mentions[0].name:
                responses = self.generate_message(message)
                print(responses)
                for response in responses:
                    await message.reply(response)
                    return


    def generate_message(self, message: discord.Message) -> list:
        self.bot.logger.info(f"Processing message with Gemini: {message.content}")
        prompt = message.clean_content.replace(self.bot.user.mention, "").strip()
        try:
            resp = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=GenerateContentConfig(
                    system_instruction=r.choice(PERSONALITIES)
                )
            )
            text = resp.text
            resp_messages = []
            for chunk in (text[i:i+2000] for i in range(0, len(text), 2000)):
                resp_messages.append(chunk)

            return resp_messages

        except Exception as e:
            self.bot.logger.error(f"Error processing with Gemini: {e}")
            return []

async def setup(bot: discord.ext.commands.Bot):
    await bot.add_cog(GeminiCog(bot))