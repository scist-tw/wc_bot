import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class ScoreSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scores = self.bot.score
        self.emoji = self.bot.emoji

    def save_scores(self):
        with open("json/score.json", 'w', encoding='utf-8') as f:
            json.dump(self.scores, f, ensure_ascii=False, indent=4)

    @app_commands.command(name="addscore", description="給指定組別加分")
    @app_commands.describe(group_number = "組別編號", points = "分數")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_score(self, interaction: discord.Interaction, group_number: int, points: int):
        if str(group_number) not in self.scores["groups"]:
            await interaction.response.send_message(f"無效的組別編號 請輸入 1 至 {len(self.scores['groups'])} 之間的數字", ephemeral=True)
            return

        group_data = self.scores["groups"][str(group_number)] 
        group_name = group_data["name"] 
        current_score = group_data["score"]  

        self.scores["groups"][str(group_number)]["score"] += points
        self.save_scores() 
        await interaction.response.send_message(
            f"{self.emoji['勾勾']}  已為 {group_name} 增加 {points} 分 目前分數為 {self.scores['groups'][str(group_number)]['score']} 分"
        )

    @app_commands.command(name="scoreboard", description="查看分數板")
    async def scoreboard(self, interaction: discord.Interaction):
        if not self.scores["groups"]:
            await interaction.response.send_message("目前沒有任何組別分數")
            return

        embed = discord.Embed(title=f"{self.emoji['星星']} 分數板 {self.emoji['星星']}", color=discord.Color.blue())
        for group_number, group_data in self.scores["groups"].items():
            embed.add_field(name=group_data["name"], value=f"{group_data['score']} 分", inline=False)

        view = ScoreboardView(scores=self.scores["groups"], emoji=self.bot.emoji)
        await interaction.response.send_message(embed=embed, view=view)
        self.bot.add_view(view)

class ScoreboardView(discord.ui.View):
    def __init__(self, scores, emoji):
        super().__init__(timeout=None)
        self.scores = scores
        self.emoji = emoji

    @discord.ui.button(
        label="各組分數", 
        style=discord.ButtonStyle.primary,
        custom_id="scoreboard:all_scores"
    )
    async def show_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title=f"{self.emoji['星星']} 分數板 {self.emoji['星星']}", color=discord.Color.blue())
        for group_number, group_data in self.scores.items():
            embed.add_field(name=group_data["name"], value=f"{group_data['score']} 分", inline=False)
        await interaction.response.defer()
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(
        label="排名", 
        style=discord.ButtonStyle.secondary,
        custom_id="scoreboard:rankings"
    )
    async def show_rankings(self, interaction: discord.Interaction, button: discord.ui.Button):
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1]['score'], reverse=True)
        embed = discord.Embed(title="🏆 排名", color=discord.Color.gold())

        rank_emoji = {
            1: self.emoji['1'],
            2: self.emoji['2'],
            3: self.emoji['3'],
        }
        all_zero = all(group_data["score"] == 0 for _, group_data in sorted_scores)
        for rank, (group_number ,group_data) in enumerate(sorted_scores, start=1):
            emoji = rank_emoji.get(rank, f"#{rank}")
            if group_data["score"] == 0:
                continue
            embed.add_field(name=f"{emoji} {group_data['name']}", value=f"{group_data['score']} 分", inline=False)
        if all_zero:
            emoji = "暫無排行"
            embed.add_field(name=f"{emoji}",value=f"目前無任何分數", inline=False)
        await interaction.response.defer()
        await interaction.message.edit(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

async def setup(bot):
    await bot.add_cog(ScoreSystem(bot))
