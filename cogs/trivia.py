import asyncio
import discord
from discord.ext import commands, tasks
import random as r
import aiohttp
import html
import json
from pathlib import Path

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.db import User

URL = 'https://botly-api-rcyr.shuttle.app'
TRIVIA_URL = "https://opentdb.com/api.php?amount=1&type=multiple"

config = json.loads(Path('config/config.json').read_text())

class TriviaGame(discord.ui.View):
    def __init__(self, bot: discord.ext.commands.Bot):
        super().__init__(timeout=60*29)
        self.bot = bot
        self.question: dict = None
        self.already_answered = []
        self.answer_list = []
        self.winner: int = None
        self.message = None

    @discord.ui.button(label="A", style=discord.ButtonStyle.primary)
    async def a(self, interaction: discord.Interaction, button: discord.ui.Button):
        correct = self.answer_list[0] == self.get_correct()
        await self.process_response(interaction.user.id, correct, interaction, button)

    @discord.ui.button(label="B", style=discord.ButtonStyle.primary)
    async def b(self, interaction: discord.Interaction, button: discord.ui.Button):
        correct = self.answer_list[1] == self.get_correct()
        await self.process_response(interaction.user.id, correct, interaction, button)

    @discord.ui.button(label="C", style=discord.ButtonStyle.primary)
    async def c(self, interaction: discord.Interaction, button: discord.ui.Button):
        correct = self.answer_list[2] == self.get_correct()
        await self.process_response(interaction.user.id, correct, interaction, button)

    @discord.ui.button(label="D", style=discord.ButtonStyle.primary)
    async def d(self, interaction: discord.Interaction, button: discord.ui.Button):
        correct = self.answer_list[3] == self.get_correct()
        await self.process_response(interaction.user.id, correct, interaction, button)

    async def process_response(self, user_id: int, correct: bool, interaction: discord.Interaction, button: discord.ui.Button):
        if user_id in self.already_answered:
            self.bot.logger.info(f'User {interaction.user.name} already answered.')
            await interaction.response.send_message("You already answered!", ephemeral=True)
            return
        else:
            if self.winner:
                await interaction.response.send_message("Someone already got this question correct.", ephemeral=True)
                return
            else:
                button.disabled = True
                self.already_answered.append(user_id)
                if correct:
                    button.style = discord.ButtonStyle.green
                    await interaction.response.edit_message(view=self)
                    self.winner = interaction.user.id
                    self.bot.logger.info(f'User {interaction.user.id} got the question correct.')
                    try:
                        curr_user: User = self.bot.database.get_user(user_id)
                        curr_user.points += 100
                        self.bot.database.update_user(curr_user)
                        await interaction.followup.send(f"{interaction.user.display_name} was the first to get the message right! They will be awarded 100 points!")
                        await self.disable_buttons()
                    except Exception as e:
                        self.bot.logger.error(f"Error: {e}")
                        await interaction.followup.send("Something went wrong. Shutting down trivia.")
                        await self.disable_buttons()

                else:
                    button.style = discord.ButtonStyle.red
                    await interaction.response.edit_message(view=self)
                    await interaction.followup.send("Sorry. Wrong answer. You'll get it next time.", ephemeral=True)


    async def start(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(TRIVIA_URL) as response:
                    response = await response.json()
                    self.question = response['results'][0]
                    self.question['question'] = html.unescape(self.question['question'])
                    self.question['correct_answer'] = html.unescape(self.question['correct_answer'])
                    self.question['incorrect_answers'] = html.unescape(self.question['incorrect_answers'])
            options = [self.question['correct_answer']]
        except Exception as e:
            self.bot.logger.error(f'Failed to get trivia question: {e}')
            return False
        for option in self.question['incorrect_answers']:
            options.append(option)
        r.shuffle(options)
        self.answer_list = options
        await self.create_send_message()
        return True

    async def end(self) -> None:
        if not self.winner:
            correct_answer = self.get_correct()
            trivia_channels = config['trivia_channel_id']
            for channel_id in trivia_channels:
                channel = self.bot.get_channel(channel_id)
                await channel.send(f"Looks like no one got the answer to the trivia question. \n The correct answer was {correct_answer}.\nBetter luck next time!")
        await self.disable_buttons()

    def get_question(self) -> str:
        return self.question['question']

    def return_options(self) -> list:
        return self.answer_list

    def get_correct(self) -> str:
        return self.question['correct_answer']

    async def create_send_message(self) -> None:
        options_text = ''
        options_text += ('A: ' + self.answer_list[0] + '\n')
        options_text += ('B: ' + self.answer_list[1] + '\n')
        options_text += ('C: ' + self.answer_list[2] + '\n')
        options_text += ('D: ' + self.answer_list[3] + '\n')
        embed = discord.Embed(
            title="🎉 Trivia Time!",
            description=f"💡 The first person to respond with the right answer will win points!\n\n"
                        f"❓ *{self.get_question()}*\n\n"
                        f"{options_text}",
        )
        embed.set_footer(text="Select your answer using the buttons below. You have 30 minutes!")
        trivia_channels = config['trivia_channel_id']
        for channel_id in trivia_channels:
            channel = self.bot.get_channel(channel_id)
            self. message = await channel.send(embed=embed, view=self)

    async def disable_buttons(self) -> None:
        for item in self.children:
            if hasattr(item, "disabled"):
                item.disabled = True
        await self.message.edit(view=self)

class TriviaCog(commands.Cog):
    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        self.bot = bot
        self.trivia_game = None

        # Start loops
        self.trivia.start()
        self.update_trivia_leader.start()

    @tasks.loop(minutes=60.0)
    async def trivia(self) -> None:
        if r.randint(1, 100) < 80:
            self.bot.logger.info("Starting trivia")
            self.trivia_game = TriviaGame(self.bot)
            if not await self.trivia_game.start():
                return
            await asyncio.sleep(30 * 60)
            await self.trivia_game.end()
            self.trivia_game = None
        else:
            self.bot.logger.info("No trivia this time")

    @tasks.loop(minutes=120.0)
    async def update_trivia_leader(self) -> None:
        top_user: User = self.bot.database.get_top_trivia()
        guild = self.bot.get_guild(11911156230198436741191115623019843674)
        if not guild:
            self.bot.logger.error("Guild not found when assigning roles")
            return

        member = await guild.fetch_member(top_user.dist_id)

        role = guild.get_role(1400575823676838069)

        if not role:
            self.bot.logger.error("Role not found")
            return

        for member in guild.members:
            if role in member.roles:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    self.bot.logger.error(f"Can't remove {role.name} from {member}")

        await member.add_roles(role)

        self.bot.logger.info(f"Added role {role.name} to {member.display_name}")

    @update_trivia_leader.before_loop
    @trivia.before_loop
    async def before_loops(self) -> None:
        await self.bot.wait_until_ready()

async def setup(bot: discord.ext.commands.Bot) -> None:
    await bot.add_cog(TriviaCog(bot))