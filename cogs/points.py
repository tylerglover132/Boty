import asyncio
import json
import discord
from discord.ext import commands, tasks
from pathlib import Path
import random as r
import aiohttp
import html
from discord.ui import View, Button

TRIVIA_URL = "https://opentdb.com/api.php?amount=1&difficulty=hard&type=multiple"

config = json.loads(Path('config/config.json').read_text())


def add_points(user_id: int, points: int) -> int:
    print(f'Adding points for {user_id}')
    points_list = json.loads(Path('data/points.json').read_text())
    if str(user_id) in points_list.keys():
        points_list[str(user_id)] += points
        try:
            with open("data/points.json", "w", encoding="utf-8") as f:
                json.dump(points_list, f, ensure_ascii=True, indent=4)
            return points_list[str(user_id)]
        except Exception as e:
            return -1
    else:
        return -2

class TriviaGame:

    def __init__(self) -> None:
        self.question: dict = None
        self.already_answered = []

    async def retrieve_question(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(TRIVIA_URL) as response:
                response = await response.json()
                self.question = response['results'][0]
                self.question['question'] = html.unescape(self.question['question'])
                self.question['correct_answer'] = html.unescape(self.question['correct_answer'])
                self.question['incorrect_answers'] = html.unescape(self.question['incorrect_answers'])

    def end_game(self) -> None:
        self.question = None

    def get_question(self) -> str:
        return self.question['question']

    def return_options(self) -> list:
        options = [self.question['correct_answer']]
        for option in self.question['incorrect_answers']:
            options.append(option)
        r.shuffle(options)
        return options

    def get_correct(self) -> str:
        return self.question['correct_answer']

class PointsCog(commands.Cog):
    """Cog that manages user points"""

    def __init__(self, bot: discord.ext.commands.Bot)-> None:
        self.bot = bot
        self.trivia_game = None
        self.gamble_cooldown = False

        # Start loops
        self.add_points_for_all.start()
        self.trivia.start()
        self.refresh_gamble_cooldown.start()


    @commands.command(name="trackpoints")
    async def trackpoints(self, ctx: discord.ext.commands.Context) -> None:
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

    @commands.command(name="gamble")
    async def gamble(self, ctx: discord.ext.commands.Context) -> None:
        if not self.gamble_cooldown:
            points_list = json.loads(Path("data/points.json").read_text())
            if str(ctx.author.id) in points_list:
                double = r.choice([True, False])
                if double:
                    points_list[str(ctx.author.id)] = int(points_list[str(ctx.author.id)] * 2)
                    response = "Congrats! Your points have been doubled! New points value: "
                else:
                    points_list[str(ctx.author.id)] = int(points_list[str(ctx.author.id)] / 2)
                    response = "Better luck next time. You lost half your points :( New points value: "
                try:
                    with open("data/points.json", "w", encoding="utf-8") as f:
                        json.dump(points_list, f, ensure_ascii=True, indent=4)
                    await ctx.reply(response + str(points_list[str(ctx.author.id)]))
                except Exception as e:
                    await ctx.reply("Sorry, there was an error. No points changed")
                    self.bot.logger.error(f"Error occurred while gambling: {e}")
            else:
                await ctx.reply("You are currently not tracking points. Use command !trackpoints to begin tracking")
            self.gamble_cooldown = True

        else:
            await ctx.reply("!gamble is on cooldown. Please, play responsibly.")
            self.bot.logger.info("!gamble not completed, on cooldown")

    @commands.command(name="points")
    async def points(self, ctx: discord.ext.commands.Context) -> None:
        points_list = json.loads(Path("data/points.json").read_text())
        if str(ctx.author.id) in points_list:
            await ctx.reply(f"You have {points_list[str(ctx.author.id)]}!")
        else:
            await ctx.reply("You are currently not tracking points. Use command !trackpoints to begin tracking")

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        points_list = json.loads(Path("data/points.json").read_text())
        points_list_sorted_keys = dict(sorted(points_list.items(), key=lambda item: item[1], reverse=True)).keys()
        listing = ''
        for key in points_list_sorted_keys:
            points = points_list[key]
            user = await self.bot.fetch_user(int(key))
            username = user.display_name
            listing += username + ":  " + str(points) + '\n'
        embed = discord.Embed(title="Leaderboard", description = listing, color=0x00ff00)
        await ctx.send(embed=embed)

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

    @tasks.loop(minutes=60.0)
    async def trivia(self) -> None:
        if r.randint(1, 100) < config['trivia_chance']:
            self.bot.logger.info("Starting trivia")
            self.trivia_game = TriviaGame()
            await self.trivia_game.retrieve_question()
            options_text = ''
            for option in self.trivia_game.return_options():
                options_text += (option + '\n')
            embed = discord.Embed(
                title="🎉 Trivia Time!",
                description=f"💡 The first person to respond with the right answer will win points!\n\n"
                            f"❓ *{self.trivia_game.get_question()}*\n\n"
                            f"{options_text}"
            )
            embed.set_footer(text="Reply with the correct answer exactly as shown. You have 30 minutes!")

            trivia_channels = config['trivia_channel_id']
            for channel_id in trivia_channels:
                channel = self.bot.get_channel(channel_id)
                await channel.send(embed=embed)

            await asyncio.sleep(30 * 60)

            if self.trivia_game:
                self.trivia_game = None
                for channel_id in trivia_channels:
                    channel = self.bot.get_channel(channel_id)
                    await channel.send("Looks like no one got the answer to the trivia question.\nBetter luck next time!")

        else:
            self.bot.logger.info('Trivia loop. No trivia this time.')

    @tasks.loop(minutes=30.0)
    async def refresh_gamble_cooldown(self) -> None:
        self.gamble_cooldown = False
        self.bot.logger.info("!gamble off of cooldown")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        if self.trivia_game:
            if message.channel.id in config['trivia_channel_id']:
                user_id = message.author.id
                if user_id in self.trivia_game.already_answered:
                    await message.reply("You already answered! Don't be greedy!")
                    return

                if message.content == self.trivia_game.get_correct():
                    result = add_points(user_id, 100)
                    self.trivia_game = None
                    if result == -2:
                        await message.reply("You're right but we can't add your points! Looks like you're not tracking your points. !trackpoints to start stracking.")
                        return
                    if result == -1:
                        await message.reply('Oh no! There was an issue! Trivia time over :(')
                        self.bot.logger.error('Trivia error occurred. Ending trivia')
                        return
                    await message.reply('Correct! 100 points added!')

                else:
                    self.trivia_game.already_answered.append(user_id)
                    await message.reply('Nope! Better luck next time!')

    @add_points_for_all.before_loop
    async def before_add_points_for_all(self) -> None:
        """
        Before adding points, we make sure that the bot is running
        """
        await self.bot.wait_until_ready()

    @trivia.before_loop
    async def before_trivia(self) -> None:
        await self.bot.wait_until_ready()

    @refresh_gamble_cooldown.before_loop
    async def before_refresh_gamble_cooldown(self) -> None:
        await self.bot.wait_until_ready()



async def setup(bot: discord.ext.commands.Bot) -> None:
    await bot.add_cog(PointsCog(bot))