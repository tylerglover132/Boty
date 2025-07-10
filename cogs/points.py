import json

import discord
from discord.ext import commands, tasks
from pathlib import Path

class PointsCog(commands.Cog):
    """Cog that manages user points"""

    def __init__(self, bot: discord.ext.commands.Bot)-> None:
        self.bot = bot
        self.add_points_for_all.start()

    @commands.command(name="trackpoints")
    async def trackpoints(self, ctx) -> None:
        points_list = json.loads(Path("data/points.json").read_text())
        if str(ctx.author.id) in points_list:
            await ctx.reply("You're already signed up to track points")
        else:
            points_list[ctx.author.id] = 0
            try:
                with open("data/points.json", "w", encoding="utf-8") as f:
                    json.dump(points_list, f, ensure_ascii=True, indent=4)
                await ctx.reply("You points are now being tracked.")
            except Exception as e:
                await ctx.reply("Sorry, there was an error. Please try to sign up for points tracking later.")
                self.bot.logger.error(f"Error occurred while adding point tracking: {e}")

    @tasks.loop(minutes=120.0)
    async def add_points_for_all(self) -> None:
        points_list = json.loads(Path("data/points.json").read_text())
        for key in points_list.keys():
            points_list[key] += 1
        try:
            with open("data/points.json", "w", encoding="utf-8") as f:
                json.dump(points_list, f, ensure_ascii=True, indent=4)
            self.bot.logger.info("All users given 1 point.")
        except Exception as e:
            self.bot.logger.error(f"Error occurred while updating all user points: {e}")

    @add_points_for_all.before_loop
    async def before_add_points_for_all(self) -> None:
        """
        Before adding points, we make sure that the bot is running
        """
        await self.bot.wait_until_ready()

async def setup(bot: discord.ext.commands.Bot) -> None:
    await bot.add_cog(PointsCog(bot))