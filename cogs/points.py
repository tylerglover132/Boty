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

class TriviaGame(discord.ui.View):

    def __init__(self) -> None:
        super().__init__(timeout=60*29)
        self.question: dict = None
        self.already_answered = []
        self.answer_list = list()
        self.winner: int = None
        self.done = False

    @discord.ui.button(label="A", style=discord.ButtonStyle.primary)
    async def a(self, interaction: discord.Interaction, button: discord.ui.Button):
        correct = self.answer_list[0] == self.get_correct()
        button.disabled = True
        if correct:
            button.style = discord.ButtonStyle.green
        else:
            button.style = discord.ButtonStyle.red
        await self.process_response(interaction.user.id, correct, interaction)

    @discord.ui.button(label="B", style=discord.ButtonStyle.primary)
    async def b(self, interaction: discord.Interaction,  button: discord.ui.Button):
        correct = self.answer_list[1] == self.get_correct()
        button.disabled = True
        if correct:
            button.style = discord.ButtonStyle.green
        else:
            button.style = discord.ButtonStyle.red
        await self.process_response(interaction.user.id, correct, interaction)

    @discord.ui.button(label="C", style=discord.ButtonStyle.primary)
    async def c(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        correct = self.answer_list[2] == self.get_correct()
        if correct:
            button.style = discord.ButtonStyle.green
        else:
            button.style = discord.ButtonStyle.red
        await self.process_response(interaction.user.id, correct, interaction)

    @discord.ui.button(label="D", style=discord.ButtonStyle.primary)
    async def d(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        correct = self.answer_list[3] == self.get_correct()
        if correct:
            button.style = discord.ButtonStyle.green
        else:
            button.style = discord.ButtonStyle.red
        await self.process_response(interaction.user.id, correct, interaction)

    async def process_response(self, user_id: int, correct: bool, interaction: discord.Interaction):
        if self.question:
            if user_id in self.already_answered:
                print(f'User {interaction.user.name} already answered.')
                await interaction.response.send_message("You already answered!", ephemeral=True)
                return
            else:
                if self.winner:
                    await interaction.response.send_message("Someone already got this question correct.", ephemeral=True)
                    return
                else:
                    self.already_answered.append(user_id)
                    if correct:
                        print(f'User {interaction.user.name} got the question correct.')
                        try:
                            async def post_form():
                                async with aiohttp.ClientSession() as session:
                                    async with session.post(
                                        URL + 'db_points',
                                        data = {"id": user_id, "points": 100}
                                    ) as resp:
                                        print(resp.status)
                                        text = await resp.text()
                                        print(text)
                            await post_form()
                            await interaction.response.send_message(f"{interaction.user.name} was the first to get the message right! They will be awarded 100 points!")
                        except Exception as e:
                            print(f"Error: {e}")
                            await interaction.response.send_message("Something went wrong. Shutting down trivia.")
                            self.question = None
                    else:
                        await interaction.response.send_message("Sorry. Wrong answer. You'll get it next time.", ephemeral=True)


    async def retrieve_question(self) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(TRIVIA_URL) as response:
                response = await response.json()
                self.question = response['results'][0]
                self.question['question'] = html.unescape(self.question['question'])
                self.question['correct_answer'] = html.unescape(self.question['correct_answer'])
                self.question['incorrect_answers'] = html.unescape(self.question['incorrect_answers'])

    def get_question(self) -> str:
        return self.question['question']

    def return_options(self) -> list:
        options = [self.question['correct_answer']]
        for option in self.question['incorrect_answers']:
            options.append(option)
        r.shuffle(options)
        self.answer_list = options
        return options

    def get_correct(self) -> str:
        return self.question['correct_answer']

class PointsCog(commands.Cog):
    """Cog that manages user points"""

    def __init__(self, bot: discord.ext.commands.Bot)-> None:
        self.bot = bot
        self.trivia_game = None
        self.gamble_cooldown = False
        self.database = DB()
        self.session = aiohttp.ClientSession()

        # Start loops
        self.add_points_roulette.start()
        self.trivia.start()
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
                message = f"You lose! You're points have been cut in half. New value: {curr_user.points}"
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


    @tasks.loop(minutes=60.0)
    async def trivia(self) -> None:
        if r.randint(1, 100) < config['trivia_chance']:
            self.bot.logger.info("Starting trivia")
            self.trivia_game = TriviaGame()
            await self.trivia_game.retrieve_question()
            options_text = ''
            options = self.trivia_game.return_options()
            options_text += ('A: ' + options[0] + '\n')
            options_text += ('B: ' + options[1] + '\n')
            options_text += ('C: ' + options[2] + '\n')
            options_text += ('D: ' + options[3] + '\n')
            embed = discord.Embed(
                title="🎉 Trivia Time!",
                description=f"💡 The first person to respond with the right answer will win points!\n\n"
                            f"❓ *{self.trivia_game.get_question()}*\n\n"
                            f"{options_text}",
            )
            embed.set_footer(text="Reply with the correct answer exactly as shown. You have 30 minutes!")

            trivia_channels = config['trivia_channel_id']
            for channel_id in trivia_channels:
                channel = self.bot.get_channel(channel_id)
                await channel.send(embed=embed, view=self.trivia_game)

            await asyncio.sleep(30 * 60)

            if not self.trivia_game.winner:
                correct_answer = self.trivia_game.get_correct()
                self.trivia_game = None
                for channel_id in trivia_channels:
                    channel = self.bot.get_channel(channel_id)
                    await channel.send(f"Looks like no one got the answer to the trivia question.\n The correct answer was {correct_answer}.\nBetter luck next time!")

        else:
            self.bot.logger.info('Trivia loop. No trivia this time.')

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
    @trivia.before_loop
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