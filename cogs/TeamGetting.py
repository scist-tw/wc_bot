import discord
from discord.ext import commands
from discord import Interaction, app_commands
import logging
import json

# 設定日誌
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('TeamGetting')

#--------------------------------------------------------------------------------------------------

class TeamGetting(discord.ui.Button):
    def __init__(self, button_id=1):
        super().__init__(label="🔰領取組別", style=discord.ButtonStyle.success, custom_id=f"TeamGetting{button_id}")

    async def callback(self, interaction: Interaction):
        user_id = interaction.user.id
        username = interaction.user.name

        team_data = self.load_team_data()
        if not team_data:
            await interaction.response.send_message(
                "系統錯誤：無法讀取小隊資料，請聯絡管理員。",
                ephemeral=True
            )
            logger.error("無法讀取小隊資料")
            return

        user_team, user_name = self.find_user_team_and_name(username, team_data)

        if user_team and user_name:
            role = discord.utils.get(interaction.guild.roles, name=user_team)
            studen_role = discord.utils.get(interaction.guild.roles, name="學員")
            if role:
                try:
                    await interaction.user.add_roles(role)
                    await interaction.user.add_roles(studen_role)
                    # 更新使用者暱稱
                    new_nickname = f"[{user_team}] {user_name}"
                    await interaction.user.edit(nick=new_nickname)

                    embed = discord.Embed(color=0x7bcc6b)
                    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4315/4315445.png")
                    embed.add_field(name="成功領取", value=f"哈囉！{user_name}", inline=False)
                    embed.add_field(name=f"你是 {user_team}", value="快去找你的隊員聊天吧！", inline=False)

                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message(
                        "驗證失敗，機器人缺少權限來添加身分組或更改暱稱。",
                        ephemeral=True
                    )
                except Exception as e:
                    logger.error(f"發生未知錯誤: {e}")
                    await interaction.response.send_message(
                        "驗證過程中發生未知錯誤，請聯絡資訊組。",
                        ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    f"無法找到指定的角色 {user_team}，請聯絡管理員。",
                    ephemeral=True
                )
        else:
            # 使用者未找到
            await interaction.response.send_message(
                "無法找到你的資料，請聯絡管理員確認你的身份。",
                ephemeral=True
            )
            logger.warning(f"未找到使用者資料 - UserID: {user_id}, Username: {interaction.user.name} ({interaction.user.id})")
    @staticmethod
    def load_team_data():
        """從 JSON 檔案載入小隊資料"""
        try:
            with open("/app/json/users.json", "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            logger.error("小隊資料檔案未找到：/app/json/users.json")
        except json.JSONDecodeError as e:
            logger.error(f"小隊資料檔案格式錯誤：{e}")
        return None

    @staticmethod
    def find_user_team_and_name(username, team_data):
        """比對使用者 username，返回小隊名稱與本名"""
        for team_name, members in team_data.items():
            for member in members:
                if member["username"] == username:
                    return team_name, member["name"]
        return None, None

#--------------------------------------------------------------------------------------------------

class AlwaysView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TeamGetting(button_id=2))

class TeamGettingCog(commands.Cog):
    """歡迎按鈕相關功能"""
    def __init__(self, bot):
        self.bot = bot
        self.emoji = {
            "welcome": "🎉",
            "箭頭": "➡️"
        }

    #----------------------------------------------------------------------------------------------

    @app_commands.command(name="get_team", description="發送組別按鈕")
    @app_commands.checks.has_permissions(administrator=True)
    async def get_team(self, interaction: discord.Interaction):
        embed=discord.Embed(title="🎉 SCIST 2025 寒訓 資深玩家 🎉", color=0xffb30f)
        embed.add_field(name="點擊按鈕獲取組別", value="如果無法領取請開 ticket", inline=False)
        view = AlwaysView()
        await interaction.response.send_message(embed=embed, view=view)

    @get_team.error
    async def get_team_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
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
    await bot.add_cog(TeamGettingCog(bot))
    bot.add_view(AlwaysView())
