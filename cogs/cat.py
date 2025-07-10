import os

import discord
from discord.ext import commands
import aiohttp
from dotenv import load_dotenv

load_dotenv()
os.environ["CAT_API_KEY"] = os.getenv("CAT_API_KEY")

class CatCog(commands.Cog):
    """Cag that allows accessing random cat images"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    @commands.command(name="cat")
    async def cat(self, ctx):
        headers = {"x-api-key": os.environ["CAT_API_KEY"]}
        params = {"limit":1, "size": "small", "mime_types": "jpg"}
        async with self.session.get(
            "https://api.thecatapi.com/v1/images/search",
            headers=headers,
            params=params
        ) as response:
            if response.status == 200:
                data = await response.json()
                await ctx.send(data[0]["url"])
            else:
                await ctx.send("Error: Could not get cat")
                self.bot.logger.info(f"Error {response.status}")

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

async def setup(bot):
    await bot.add_cog(CatCog(bot))