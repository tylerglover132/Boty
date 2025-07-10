import os
from enum import Enum

import discord
from discord.ext import commands
import random as r
import json
from pathlib import Path
from data.nick_names import discord_nicknames


class Potion(Enum):
    POLYMORPH = 1

class PotionCog(commands.Cog):
    """Cog that allows users to buy potions that affect the server"""

    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot


    @commands.command(name="randompotion")
    async def randompotion(self, ctx: discord.ext.commands.Context) -> None:
        user = ctx.author
        points_list = json.loads(Path("data/points.json").read_text())
        if str(user.id) in points_list:
            potion = r.choice(list(Potion))
            self.drink_potion(ctx, potion)

        else:
            await ctx.reply("You are not earning points! Type !trackpoints to start earning points")


    def drink_potion(self, ctx: discord.ext.commands.Context, potion_type: Potion):
        match potion_type:
            case Potion.POLYMORPH:
                new_nick = r.choice(discord_nicknames)
                ctx.author.edit(nick=new_nick)

async def setup(bot):
    await bot.add_cog(PotionCog(bot))