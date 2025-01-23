import discord
from discord.ext import commands
from discord import app_commands
import json

class PlayerInfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_member_data(self):
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
#-----------------------------------------------------------------------------------------------
    @app_commands.command(name="個人資訊", description="查看你的個人遊戲資訊")
    async def show_player_info(self, interaction: discord.Interaction):
        # 先延遲回應，給我們更多時間處理
        await interaction.response.defer(ephemeral=True)
        
        # 只能在私訊中使用
        if interaction.guild is not None:
            await interaction.followup.send(
                "❌ 請在私訊中使用此命令！",
                ephemeral=True
            )
            return

        member_data = self.get_member_data()
        user_id = str(interaction.user.id)
        if user_id not in member_data:
            await interaction.followup.send(
                "❌ 你還不是遊戲玩家！",
                ephemeral=True
            )
            return

        player_data = member_data[user_id]
        
        # 死人紅 平民綠 狼人用狼emoji
        status = "🐺" if player_data["is_wolf"] else "🟩"
        status = "🟥" if player_data["lives"] <= 0 else status
        
        embed = discord.Embed(
            title="🎮 個人遊戲資訊",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="基本資料",
            value=(
                f"{status} 姓名：{player_data['name']}\n"
                f"🏷️ 使用者ID：{interaction.user.mention}\n"
                f"🎯 目前編號：{player_data['id'] or '無'}\n"
                f"👥 所屬小組：第 {player_data['team']} 組\n"
                f"❤️ 剩餘生命：{player_data['lives']}"
            ),
            inline=False
        )

        view = PlayerInfoView(self.bot, user_id)
        await interaction.followup.send(embed=embed, view=view)

#-----------------------------------------------------------------------------------------------
class PlayerInfoView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.add_info_select()

    def get_member_data(self):
        """每次都重新讀取最新資料"""
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def add_info_select(self):
        select = discord.ui.Select(
            placeholder="查看更多資訊",
            options=[
                discord.SelectOption(
                    label="殺人記錄",
                    value="kills",
                    description="查看你殺了多少人"
                ),
                discord.SelectOption(
                    label="投票記錄",
                    value="votes",
                    description="查看你的投票歷史"
                )
            ],
            custom_id="player_info_select"
        )
        select.callback = self.info_select_callback
        self.add_item(select)

    async def info_select_callback(self, interaction: discord.Interaction):
        wolf_cog = self.bot.get_cog('WolfGameCog')
        if not wolf_cog:
            return

        option = interaction.data["values"][0]
        member_data = self.get_member_data()  # 獲取最新資料
        player_data = member_data[self.user_id]

        if option == "kills":
            if not player_data["is_wolf"]:
                content = "你不是狼人，沒有殺人記錄。"
            else:
                kills = wolf_cog.wolf_kill_counter.get(self.user_id, 0)
                content = f"你總共殺了 {kills} 個人。"
                killed_players = [
                    data['id'] for data in member_data.values()
                    if data.get("killed_by") == self.user_id and data.get('id', '').strip()  
                ]
                if killed_players:  
                    content += "\n被你殺害的玩家編號："
                    for player_id in killed_players:
                        content += f"\n- {player_id}"

        else:  # votes
            # 檢查是否在當前投票中
            if self.user_id in wolf_cog.votes:
                voted_id = wolf_cog.votes[self.user_id]
                voted_data = member_data[voted_id]
                content = f"你投票給了第 {voted_data['team']} 組的 {voted_data.get('name', '未知')}"
            # 檢查是否在上一輪投票中
            elif hasattr(wolf_cog, 'last_votes') and self.user_id in wolf_cog.last_votes:
                voted_id = wolf_cog.last_votes[self.user_id]
                if voted_id in member_data:  # 確保投票的玩家還在遊戲中
                    voted_data = member_data[voted_id]
                    content = f"你上一輪投票給了第 {voted_data['team']} 組的 {voted_data.get('name', '未知')}"
                else:
                    content = "你還沒有投過票。"
            else:
                content = "你還沒有投過票。"

        await interaction.response.send_message(content, ephemeral=True) 

#-----------------------------------------------------------------------------------------------
async def setup(bot):
    await bot.add_cog(PlayerInfoCog(bot)) 