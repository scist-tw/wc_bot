import discord
from discord.ext import commands
from discord import Interaction, app_commands
from discord.enums import TextStyle
import logging
import websockets
import json

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ScoreUpdater')

#--------------------------------------------------------------------------------------------------

class ScoreUpdaterButton(discord.ui.Button):
    """發送添加小隊分數按鈕"""
    def __init__(self, button_id=3):
        super().__init__(label="添加小隊分數", style=discord.ButtonStyle.primary, custom_id=f"score_updater_{button_id}")

    async def callback(self, interaction: discord.Interaction):
        """按鈕被點擊後發送 Select Menu"""
        options = [
            {"label": "第一小隊", "description": "", "value": "1"},
            {"label": "第二小隊", "description": "", "value": "2"},
            {"label": "第三小隊", "description": "", "value": "3"},
            {"label": "第四小隊", "description": "", "value": "4"},
            {"label": "第五小隊", "description": "", "value": "5"},
            {"label": "第六小隊", "description": "", "value": "6"},
            {"label": "第七小隊", "description": "", "value": "7"},
            {"label": "第八小隊", "description": "", "value": "8"},
        ]
        select = TeamSelect(options)
        view = discord.ui.View(timeout=180)  # 設定 3 分鐘超時
        view.add_item(select)
        await interaction.response.send_message("請選擇小隊：", view=view, ephemeral=True)

#--------------------------------------------------------------------------------------------------

class TeamSelect(discord.ui.Select):
    """小隊選單"""
    def __init__(self, options, placeholder="點開選擇小隊"):
        select_options = [
            discord.SelectOption(label=opt['label'], description=opt.get('description'), value=opt['value'])
            for opt in options
        ]
        super().__init__(placeholder=placeholder, options=select_options)

    async def callback(self, interaction: discord.Interaction):
        """使用者回傳的小隊"""
        selected_value = self.values[0]
        logger.info(f"第 {selected_value} 小隊被 {interaction.user} 選擇了")
        await interaction.response.send_modal(ScoreInputModal(selected_value, interaction))

#--------------------------------------------------------------------------------------------------

class ScoreInputModal(discord.ui.Modal, title="輸入分數"):
    score_input = discord.ui.TextInput(
        label="請輸入分數",
        style=TextStyle.short,
        placeholder="僅能輸入整數",
        required=True,
        min_length=1,
        max_length=5
    )

    def __init__(self, selected_value, interaction):
        super().__init__()
        self.selected_value = selected_value
        self.interaction = interaction

    def check_permissions(self):
        """檢查用戶是否擁有 score_admin 身份組"""
        allowed_role = "score_admin"
        # 必須擁有 score_admin 才能點擊按鈕
        for role in self.interaction.user.roles:
            if role.name == allowed_role:
                return True
        return False

    async def update_score_ws(self, team: str, score: int):
        """更新分數"""
        try:
            async with websockets.connect('ws://10.130.0.6:30031') as websocket:
                data = {
                    'team': team,
                    'points': score
                }
                await websocket.send(json.dumps(data))
                logger.info(f"成功發送更新請求: 第{team}小隊 +{score}分")
                return True
        except Exception as e:
            logger.error(f"WebSocket 更新分數時發生錯誤: {str(e)}")
            return False

    async def on_submit(self, interaction: discord.Interaction):
        """當用戶提交表單時調用"""
        if not self.check_permissions():
            # 用戶沒有指定身份組，拒絕操作
            await interaction.response.send_message(
                "❌ 您沒有權限進行此操作 必須擁有 `score_admin` 身份組",
                ephemeral=True
            )
            return

        try:
            score_value = int(self.score_input.value)  # 轉換為整數
            logger.info(f"用戶選擇了小隊: {self.selected_value} 輸入的分數: {score_value}")
            if score_value > 0:
                embed_color = discord.Color.green()
            elif score_value < 0:
                embed_color = discord.Color.red()
            else:
                embed_color = discord.Color.dark_gray()
            # 嘗試更新分數
            success = await self.update_score_ws(self.selected_value, score_value)

            if success:
                embed = discord.Embed(
                    title="✅更新成功",
                    description=f"""
                    由  <@{interaction.user.id}>
                    第 `{self.selected_value}` 小隊增加了 `{score_value}` 分
                    線上計分版瀏覽: https://wc.scist.org/scoreboard
                    """,
                    color=embed_color
                )
                await interaction.response.send_message(embed=embed,ephemeral=True)
                """log"""
                log_channel_id = 1330101749008302112
                log_channel = interaction.guild.get_channel(log_channel_id)
                await log_channel.send(embed=embed)

            else:
                await interaction.response.send_message(
                    "❌ 分數更新失敗 請稍後重試或聯繫資訊組",
                    ephemeral=True
                )

        except ValueError:
            await interaction.response.send_message(
                "❌ 請輸入有效的整數分數! ",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"處理分數提交時發生錯誤: {str(e)}")
            await interaction.response.send_message(
                "❌ 處理分數時發生錯誤，請重試。",
                ephemeral=True
            )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """錯誤處理"""
        logger.error(f"Modal 提交時發生錯誤: {error}")
        await interaction.response.send_message("❌ 提交時發生錯誤，請重試。", ephemeral=True)

#--------------------------------------------------------------------------------------------------

class PersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ScoreUpdaterButton(button_id=3))

class ScoreUpdater(commands.Cog):
    """選單相關的指令與功能"""
    def __init__(self, bot):
        self.bot = bot
        self.persistent_views_added = False

    async def cog_load(self):
        """當 Cog 被載入時"""
        if not self.persistent_views_added:
            # 添加持久化 view
            self.bot.add_view(PersistentView())
            self.persistent_views_added = True

    @app_commands.command(name="score_updater", description="發送小隊計分器")
    @app_commands.checks.has_permissions(administrator=True)
    async def score_updater(self, interaction: discord.Interaction):
        """發送一個帶有按鈕的訊息"""
        view = PersistentView()

        embed = discord.Embed(
            title="小隊分數添加",
            description="""
            點擊下面按鈕添加小隊分數
            線上計分版瀏覽: https://wc.scist.org/scoreboard
            """,
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, view=view)

    @score_updater.error
    async def score_updater_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """錯誤處理"""
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("你沒有權限執行此命令，此命令只能由管理員使用。", ephemeral=True)
        else:
            logger.error(f"發送選單時出現錯誤: {error}")
            await interaction.response.send_message("生成選單時發生未知錯誤，請聯繫資訊組。", ephemeral=True)

#--------------------------------------------------------------------------------------------------

async def setup(bot):
    await bot.add_cog(ScoreUpdater(bot))
