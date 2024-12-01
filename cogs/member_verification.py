import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
import traceback

# 設定日誌
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('MemberVerification')

class MemberVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "cogs/tokens_roles.json"
        self.tokens_roles = self.load_data()
#--------------------------------------------------------------------------------------------------

    def load_data(self):
        """載入 Token 與身分組的對應資料"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f">>>>>加載 {self.data_file}失敗. 他是空的!!!<<<<<")
        return {}

    def save_data(self):
        """儲存 Token 與身分組的對應資料"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.tokens_roles, f, indent=4, ensure_ascii=False)
#--------------------------------------------------------------------------------------------------

    @app_commands.command(name="set_token_role", description="設置 token-身分組")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_token_role(self, interaction: discord.Interaction, token: str, role: discord.Role):
        try:
                self.tokens_roles[token] = role.id
                self.save_data()
                await interaction.response.send_message(
                    f"已設置 Token `{token}` 對應身分組 `{role.name}` (ID: {role.id})", ephemeral=True
                )
        except Exception as e:
            error_message = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.error(f">>>>>設置token-身分組失敗<<<<<: {error_message}")
            await interaction.response.send_message("設置過程中發生錯誤，請通知資訊組。", ephemeral=True)

    @set_token_role.error
    async def set_token_role_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("你沒有權限執行此命令，此命令只能由管理員使用。", ephemeral=True)
#--------------------------------------------------------------------------------------------------

    @app_commands.command(name="generate_panel", description="生成驗證面板")
    @app_commands.checks.has_permissions(administrator=True)
    async def generate_panel(self, interaction: discord.Interaction):
        """生成驗證面板"""
        embed = discord.Embed(
            title="驗證系統",
            description="請點擊下方按鈕輸入您的驗證 Token 以領取身分組。",
            color=discord.Color.blue()
        )
        button = VerificationButton()
        view = discord.ui.View()
        view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)
    
    @generate_panel.error
    async def generate_panel_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("你沒有權限執行此命令，此命令只能由管理員使用。", ephemeral=True)
        else:
            logger.error(f"Error generating panel: {error}")
            await interaction.response.send_message("生成面板時出現未知錯誤，請聯絡資訊組。", ephemeral=True)
#--------------------------------------------------------------------------------------------------

class VerificationButton(discord.ui.Button):
    """驗證按鈕"""
    def __init__(self):
        super().__init__(label="輸入驗證 Token", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        modal = VerificationModal()
        await interaction.response.send_modal(modal)

class VerificationModal(discord.ui.Modal, title="驗證 Token 輸入"):
    """驗證 Modal，處理 Token 輸入"""
    token = discord.ui.TextInput(label="請輸入您的驗證 Token", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("MemberVerification")
        if not cog:
            await interaction.response.send_message("系統錯誤，請聯絡資訊組。", ephemeral=True)
            return

        token = self.token.value
        role_id = cog.tokens_roles.get(token)

        if role_id:
            role = interaction.guild.get_role(role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(f"領取成功！您的組別是 `{role.name}`", ephemeral=True)

                except discord.Forbidden:
                    await interaction.response.send_message("驗證失敗，機器人缺少權限來添加身分組。", ephemeral=True)

                except Exception as e:
                    logger.error(f"出現錯誤{e}")
                    await interaction.response.send_message("驗證過程中發生未知錯誤 請聯絡資訊組。", ephemeral=True)

                return

            await interaction.response.send_message("指定的身分組不存在 請聯絡資訊組。", ephemeral=True)
            logger.error(f"這個 {role_id} 找不到 {token}")
            return

        await interaction.response.send_message(">> 驗證失敗 無效的Token <<", ephemeral=True)
        logger.warning(f"出現錯誤{token} by {interaction.user.name} ({interaction.user.id})")

async def setup(bot):
    await bot.add_cog(MemberVerification(bot))
