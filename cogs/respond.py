import discord
from discord.ext import commands

class Respond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.content.lower().startswith('hello'):
            await message.channel.send('Hello!')
        if message.contents('hello'):
            await message.channel.send('Hello!')

async def setup(bot):
    await bot.add_cog(Respond(bot))