import asyncio
import json
import discord
from discord.ext import commands, tasks
from pathlib import Path
import random as r
import aiohttp
import html
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.db import DB
from db.db import User

URL = 'https://botly-api-rcyr.shuttle.app'
TRIVIA_URL = "https://opentdb.com/api.php?amount=1&difficulty=hard&type=multiple"

config = json.loads(Path('config/config.json').read_text())

class PointsCog(commands.Cog):
    """Cog that manages user points"""

    def __init__(self, bot: discord.ext.commands.Bot)-> None:
        self.bot = bot
        self.gamble_cooldown = False
        self.database = DB()
        self.session = aiohttp.ClientSession()

        # Start loops
        self.add_points_roulette.start()
        self.refresh_gamble_cooldown.start()
        self.db_update.start()


    @commands.command(name="trackpoints")
    async def trackpoints(self, ctx: discord.ext.commands.Context) -> None:
        new_user = User(ctx.author.id, ctx.author.name, 0)
        if self.database.add_user(new_user):
            await ctx.reply('You are now tracking points!')
        else:
            await ctx.reply('There was an issue! You may already be tracking. If not, please try again.')

    @commands.command(name="gamble")
    async def gamble(self, ctx: discord.ext.commands.Context) -> None:
        if not self.gamble_cooldown:
            curr_user: User = self.database.get_user(ctx.author.id)
            if r.choice((True, False)):
                curr_user.points *= 2
                message = f"Congrats, you've doubled your points! New value: {curr_user.points}"
                if self.database.update_user(curr_user):
                    await ctx.reply(message)
                else:
                    await ctx.reply("Something went wrong! You might not be tracking your points!")
            else:
                curr_user.points /= 2
                message = f"You lose! You're points have been cut in half. New value: {int(curr_user.points)}"
                if self.database.update_user(curr_user):
                    await ctx.reply(message)
                else:
                    await ctx.reply("Something went wrong! You might not be tracking your points!")
        else:
            await ctx.reply("!gamble is on cooldown. Please, play responsibly.")
            self.bot.logger.info("!gamble not completed, on cooldown")

    @commands.command(name="points")
    async def points(self, ctx: discord.ext.commands.Context) -> None:
        curr_user: User = self.database.get_user(ctx.author.id)
        if curr_user.dist_id == 0:
            await ctx.reply("You are not tracking points. Use command !trackpoints to begin tracking")
        else:
            await ctx.reply(f"You have {curr_user.points}!")

    @tasks.loop(minutes=5.0)
    async def db_update(self) -> None:
        try:
            async with self.session.get(
                    URL + '/db_points'
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    user: User = self.database.get_user(data['id'])
                    user.points += data['points']
                    if self.database.update_user(user):
                        self.bot.logger.info("DB point addition successful")
                else:
                    self.bot.logger.info('No db updates needed')
        except Exception as e:
            print(f"didn't work: {e}")

    @tasks.loop(minutes=30.0)
    async def refresh_gamble_cooldown(self) -> None:
        self.gamble_cooldown = False
        self.bot.logger.info("!gamble off of cooldown")

    @tasks.loop(minutes=60.0)
    async def add_points_roulette(self) -> None:
        users = self.database.get_users()
        user = r.choice(users)
        user.points += 50
        self.database.update_user(user)
        self.bot.logger.info(f'Roulette: 50 points added for {user.name}')


    @db_update.before_loop
    @add_points_roulette.before_loop
    @refresh_gamble_cooldown.before_loop
    async def before_loops(self) -> None:
        await self.bot.wait_until_ready()

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        users = self.database.get_users()
        listing = ''
        for user in users:
            points = user.points
            username = user.name
            listing += username + ":  " + str(points) + '\n'
        embed = discord.Embed(title="Leaderboard", description = listing, color=0x00ff00)
        await ctx.send(embed=embed)






async def setup(bot: discord.ext.commands.Bot) -> None:
    await bot.add_cog(PointsCog(bot))