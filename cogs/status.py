import discord
from discord.ext import commands
from discord import app_commands
import psutil
import asyncio

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='status', description='顯示機器人狀態(測試嘻嘻嘻)')
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embed = discord.Embed(title="機器人狀態", color=discord.Color.red())
        message = await interaction.followup.send("正在收集數據...", embed=embed)

        # CPU
        embed.add_field(name="CPU使用率", value="計算中...", inline=False)
        await message.edit(content="正在檢查 CPU 使用率...", embed=embed)
        await asyncio.sleep(1)
        cpu_usage = psutil.cpu_percent(interval=1)
        embed.set_field_at(0, name="CPU使用率", value=f"{cpu_usage}%", inline=False)
        await message.edit(embed=embed)

        # RAM
        embed.add_field(name="RAM使用率", value="計算中...", inline=False)
        await message.edit(content="正在檢查 RAM 使用率...", embed=embed)
        await asyncio.sleep(1)
        ram = psutil.virtual_memory()
        ram_usage = ram.percent
        embed.set_field_at(1, name="RAM使用率", value=f"{ram_usage}%", inline=False)
        await message.edit(embed=embed)

        # 網路
        embed.add_field(name="網路接收", value="計算中...", inline=False)
        embed.add_field(name="網路發送", value="計算中...", inline=False)
        await message.edit(content="正在檢查網路使用情況...", embed=embed)
        await asyncio.sleep(1)
        network = psutil.net_io_counters()
        network_recv = round(network.bytes_recv / (1024 * 1024), 2)
        network_sent = round(network.bytes_sent / (1024 * 1024), 2)
        embed.set_field_at(2, name="網路接收", value=f"{network_recv} MB", inline=False)
        embed.set_field_at(3, name="網路發送", value=f"{network_sent} MB", inline=False)
        await message.edit(embed=embed)

        # 磁碟
        embed.add_field(name="磁碟使用率", value="計算中...", inline=False)
        await message.edit(content="正在檢查磁碟使用率...", embed=embed)
        await asyncio.sleep(1)
        disk_usage = psutil.disk_usage('/').percent
        embed.set_field_at(4, name="磁碟使用率", value=f"{disk_usage}%", inline=False)
        await message.edit(embed=embed)

        # 其他資訊
        bot_version = '1.2.1'
        server_count = len(self.bot.guilds)
        user_count = len(set(self.bot.users))
        
        embed.add_field(name="使用語言", value="Python", inline=False)
        embed.add_field(name="機器人版本", value=bot_version, inline=False)
        embed.add_field(name="服務器數量", value=server_count, inline=False)
        embed.add_field(name="用戶數量", value=user_count, inline=False)

        await message.edit(content="資料收集完成！", embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))
