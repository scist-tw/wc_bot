import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import io

class Member(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='member_list', description='輸出伺服器中所有的成員名稱')
    async def member_list(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if not interaction.guild:
            await interaction.followup.send("此指令僅能在伺服器中使用！")
            return

        embed = discord.Embed(title="成員名單", description="正在收集成員資訊，請稍候...", color=discord.Color.blue())
        message = await interaction.followup.send(embed=embed)

        member_names = [member.name for member in interaction.guild.members]

        file_content = "\n".join(member_names)
        member_file = io.BytesIO(file_content.encode('utf-8'))
        member_file.seek(0)

        embed.description = f"收集完成，共有 {len(member_names)} 位成員。"
        await message.edit(embed=embed)

        await interaction.followup.send(content="以下是成員名單：", file=discord.File(member_file, filename="member_list.txt"))

async def setup(bot):
    await bot.add_cog(Member(bot))
