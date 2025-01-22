import discord
from discord.ext import commands
from discord import app_commands
import json

class UpdateIDModal(discord.ui.Modal, title="更新編號"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        
        self.new_id = discord.ui.TextInput(
            label="新編號",
            placeholder="輸入你的新編號",
            required=True
        )
        
        self.password = discord.ui.TextInput(
            label="密碼",
            placeholder="輸入工作人員的密碼",
            required=True
        )
        
        self.add_item(self.new_id)
        self.add_item(self.password)

    async def on_submit(self, interaction: discord.Interaction):
        # 檢查密碼
        if self.password.value != "1234":  # 可以改成從設定檔讀取
            await interaction.response.send_message(
                "❌ 密碼錯誤！",
                ephemeral=True
            )
            return

        member_data = self.cog.get_member_data()
        user_id = str(interaction.user.id)
        
        if user_id not in member_data:
            await interaction.response.send_message(
                "❌ 你還不是遊戲玩家！",
                ephemeral=True
            )
            return

        # 更新編號
        member_data[user_id]["id"] = self.new_id.value
        self.cog.save_member_data(member_data)

        await interaction.response.send_message(
            f"✅ 你的編號已更改為：{self.new_id.value}",
            ephemeral=True
        )

class UpdateIDCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_member_data(self):
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_member_data(self, data):
        with open('json/member.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @app_commands.command(name="更改編號", description="更改你的遊戲編號")
    async def update_id(self, interaction: discord.Interaction):
        # 只能在私訊中使用
        if interaction.guild is not None:
            await interaction.response.send_message(
                "❌ 請在私訊中使用此命令！",
                ephemeral=True
            )
            return

        modal = UpdateIDModal(self)
        await interaction.response.send_modal(modal)

async def setup(bot):
    await bot.add_cog(UpdateIDCog(bot)) 