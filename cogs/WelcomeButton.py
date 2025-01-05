import discord
from discord.ext import commands
from discord import Interaction, app_commands
import logging

# 設定日誌
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('WelcomeButton')

#--------------------------------------------------------------------------------------------------

class WelcomeButton(discord.ui.Button):
    """輸入學校領取學員身份組"""
    def __init__(self, button_id=1):
        super().__init__(label="領取學員身份組", style=discord.ButtonStyle.success, custom_id=f"WelcomeButton{button_id}")

    async def callback(self, interaction: Interaction):
        role_id = 1307742539427614792
        role = interaction.guild.get_role(role_id)

        if role_id:
            if role:
                try:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(
                        f"已成功領取 `<@&{role_id}>` 身分組",
                        ephemeral=True
                    )
                except discord.Forbidden:
                    await interaction.response.send_message(
                        "驗證失敗，機器人缺少權限來添加身分組。",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"發生未知錯誤: {e}")
                    await interaction.response.send_message(
                        "驗證過程中發生未知錯誤，請聯絡資訊組。",
                        ephemeral=True
                    )
                return

            await interaction.response.send_message(
                "指定的身分組不存在，請聯絡資訊組。",
                ephemeral=True
            )
            logger.error(f"無法找到角色 ID: {role_id}")
            return

        await interaction.response.send_message("驗證失敗，無效的 Token。", ephemeral=True)
        logger.warning(f"驗證失敗 - Token 無效: {role_id}, 使用者: {interaction.user.name} ({interaction.user.id})")

#--------------------------------------------------------------------------------------------------

class AlwaysView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(WelcomeButton(button_id=2))

class WelcomeButtonCog(commands.Cog):
    """歡迎按鈕相關功能"""
    def __init__(self, bot):
        self.bot = bot
        self.emoji = {
            "welcome": "🎉",
            "箭頭": "➡️"
        }

    #----------------------------------------------------------------------------------------------

    @app_commands.command(name="send_welcome_button", description="發送領取身份組按鈕")
    @app_commands.checks.has_permissions(administrator=True)
    async def send_welcome_button(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{self.emoji['welcome']} SCIST 2025 寒訓 資深玩家 {self.emoji['welcome']}",
            description="點擊按鈕領取學員身份組",
            color=discord.Color.blue()
        )
        view = AlwaysView()
        await interaction.response.send_message(embed=embed, view=view)

    @send_welcome_button.error
    async def send_welcome_button_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "你沒有權限執行此命令，此命令只能由管理員使用。",
                ephemeral=True
            )
        else:
            logger.error(f"生成按鈕時出現未知錯誤: {error}")
            await interaction.response.send_message(
                "生成按鈕時發生未知錯誤，請聯絡資訊組。",
                ephemeral=True
            )

#--------------------------------------------------------------------------------------------------

async def setup(bot):
    await bot.add_cog(WelcomeButtonCog(bot))
    bot.add_view(AlwaysView())
