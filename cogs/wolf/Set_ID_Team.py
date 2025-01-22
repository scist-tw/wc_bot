import discord
from discord.ext import commands
from discord import app_commands
import json
import logging

logger = logging.getLogger('TeamBinding')

class TeamBindModal(discord.ui.Modal, title="綁定組別"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        
        self.team = discord.ui.TextInput(
            label="組別",
            placeholder="輸入你的組別編號 (1-8)",
            required=True,
            min_length=1,
            max_length=1
        )
        
        self.name = discord.ui.TextInput(
            label="姓名",
            placeholder="輸入你的姓名",
            required=True
        )
        
        self.add_item(self.team)
        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # 檢查是否已綁定
        if user_id in self.cog.member_data and self.cog.member_data[user_id]["team"]:
            await interaction.response.send_message(
                f"❌ 你已經綁定過隊伍了，無法自行更改。請通知工作人員幫你進行更改。",
                ephemeral=True
            )
            return
        
        # 檢查數字在範圍
        try:
            team_num = int(self.team.value)
            if team_num < 1 or team_num > 8:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ 無效的隊伍編號！請輸入 1-8 之間的數字。",
                ephemeral=True
            )
            return

        # 更新資料
        self.cog.member_data[user_id] = {
            "team": str(team_num),
            "id": "",
            "name": self.name.value,
            "is_wolf": False,
            "is_skill_able": True,
            "lives": 6
        }
        
        self.cog.save_member_data()
        
        await interaction.response.send_message(
            f"✅ 已將你綁定至第 {team_num} 組！\n"
            f"姓名：{self.name.value}",
            ephemeral=True
        )

#-----------------------------------------------------------------------------------------------
class TeamBindingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = self.bot.emoji
        self.member_data = {}
        self.load_member_data()

    def load_member_data(self):
        """載入玩家資料"""
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                self.member_data = json.load(f)
        except FileNotFoundError:
            self.member_data = {}

    def save_member_data(self):
        """儲存玩家資料"""
        # 先讀取現有資料
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except FileNotFoundError:
            current_data = {}
        
        current_data.update(self.member_data)
        
        with open('json/member.json', 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=4)

#-----------------------------------------------------------------------------------------------
    @app_commands.command(name="綁定組別", description="綁定你的組別和姓名")
    async def bind_team(self, interaction: discord.Interaction):
        modal = TeamBindModal(self)
        await interaction.response.send_modal(modal)

#-----------------------------------------------------------------------------------------------
async def setup(bot):
    await bot.add_cog(TeamBindingCog(bot))
