import os
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


# Chance to respond
RESPONSE_RATE = int(config["response_rate"])

# Define possible personalities

SLAP_SHOT = """You’re Slapshot: a garbage-talker with a surprising knowledge of game mechanics. 
            You short‑hand everything, toss in memes and mild profanity, and low‑key hype players when they pull 
            something clutch. You roast hard but always land the vibe."""

BONGO = """You are Boingo the Gaming Clown: a wild, prank-happy Discord bot who never stops clowning. 
You speak like a goofy circus performer crossed with a trash-talkin’ gamer. Drop clown emojis, hype each play, 
roast with love, and randomly honk or say “pie in their face!” when it’s spicy. Always bring hype and silliness.
"""

PERCY = """You are Prim & Proper Percy: a polite, old-school gaming purist who abhors profanity and disrespect 
on Discord. You gently correct anyone who uses bad language, enforce chat rules with formal reminders, and uphold 
a “PG-13” atmosphere. Use gaming analogies in an overly serious tone.
"""

PERSONALITIES = [SLAP_SHOT, BONGO, PERCY]

class GeminiCog(commands.Cog):
    """Cog that forwards messages to Gemini and replies."""

    def __init__(self, bot):
        self.bot = bot
        self.client = genai.Client()
        self.model_name = "gemini-2.5-flash"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.conent.startswith(self.bot.command_prefix):
            return

        will_speak = r.randint(1,100) <= RESPONSE_RATE

        if will_speak:
            self.bot.logger.info(f"Processing message with Gemini: {message}")
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
                for chunk in (text[i:i+2000] for i in range(0, len(text), 2000)):
                    await message.reply(chunk)
            except Exception as e:
                await message.reply("My brain stopped!")
                self.bot.logger.error(f"Could not contact Gemini: {e}")

        else:
            self.bot.logger.info(f"will_speak: {will_speak}. Choosing not to respond")

async def setup(bot):
    await bot.add_cog(GeminiCog(bot))