import discord
from discord.ext import commands
from discord import app_commands
import logging
import datetime

logger = logging.getLogger('Help')

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)  # 3分鐘超時

    @discord.ui.button(label="一般指令", style=discord.ButtonStyle.primary)
    async def show_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        if isinstance(interaction.channel, discord.DMChannel):
            embed = discord.Embed(
                title="指令說明",
                description="以下是可用的指令：",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📅 課表查詢", 
                value="使用 `/schedule` 查看當前課表",
                inline=False
            )
            embed.add_field(
                name="📊 個人進度", 
                value="使用 `/progress` 查看您的學習進度",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            try:
                # 在伺服器中轉址到 DM
                dm_embed = discord.Embed(
                    title="請在此使用指令",
                    description="請在私訊中使用 `/help` 指令查看可用功能",
                    color=discord.Color.blue()
                )
                await interaction.user.send(embed=dm_embed)
                await interaction.response.send_message("正在傳送訊息至您的私訊...", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message(
                    "無法發送私訊！請確保您已開啟接收私訊的權限!!",
                    ephemeral=True
                )
class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = 1311722075832062036
        self.errorlog = 1311732467308429353 

    @app_commands.command(name="help", description="顯示幫助選單")
    async def help(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.DMChannel):
            dm_embed = discord.Embed(
                title="歡迎使用help選單",
                description="點擊下方按鈕以獲取幫助。",
                color=discord.Color.blue()
            )
            view = HelpView()
            await interaction.response.send_message(embed=dm_embed, view=view, ephemeral=True)
        else:
            try:
                await interaction.response.send_message("正在傳送訊息至您的私訊...", ephemeral=True)
                dm_embed = discord.Embed(
                    title="請在此使用help指令~",
                    description="再輸入一次/help指令",
                    color=discord.Color.blue()
                )
                await interaction.user.send(embed=dm_embed)
                if not isinstance(interaction.channel, discord.DMChannel):
                    log_channel = self.bot.get_channel(self.log)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="指令使用記錄",
                            description=f"使用者 {interaction.user.mention} 在 {interaction.guild.name} 使用了 help 指令",
                            color=discord.Color.green()
                        )
                        await log_channel.send(embed=log_embed)
            except Exception as e:
                logger.error(f"記錄指令使用時發生錯誤: {e}")

            except discord.Forbidden:
                await interaction.followup.send("無法發送私訊！請確保您已開啟接收私訊的權限!!",ephemeral=True)
                try:
                    log_channel = self.bot.get_channel(self.errorlog)
                    if log_channel:
                        error_embed = discord.Embed(
                            title="❌ 錯誤報告",
                            description=f"無法向用戶 {interaction.user.mention} 發送私訊",
                            color=discord.Color.red(),
                            timestamp=datetime.datetime.now()
                        )
                        error_embed.add_field(
                            name="錯誤發生位置",
                            value=f"伺服器: {interaction.guild.name}\n指令: help",
                            inline=False
                        )
                        await log_channel.send(embed=error_embed)

                except Exception as e:
                    logger.error(f"發送錯誤日誌時發生錯誤: {e}")
                
                logger.warning(f"無法向 {interaction.user} 發送私訊")

    @help.error
    async def help_error(self, interaction: discord.Interaction, error):
        logger.error(f"/help指令異常: {error}")
        await interaction.response.send_message("執行指令時發生錯誤，請稍後再試。",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))