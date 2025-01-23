import discord
from discord.ext import commands
from discord import app_commands
import json
import logging

logger = logging.getLogger('QuestionSystem')

class QuestionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scores = self.bot.score
        self.emoji = self.bot.emoji
        self.questions = self.bot.question
        self.team_question = self.bot.team_question
        self.member_data = self.bot.member_data

    def save_scores(self):
        """儲存分數到 JSON 檔案"""
        with open("json/score.json", 'w', encoding='utf-8') as f:
            json.dump(self.scores, f, ensure_ascii=False, indent=4)

    def save_team_question(self):
        """儲存隊伍答題記錄"""
        with open('json/team_question.json', 'w', encoding='utf-8') as f:
            json.dump(self.team_question, f, ensure_ascii=False, indent=4)

    def get_team_question(self):
        """每次都重新讀取最新資料"""
        try:
            with open('json/team_question.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def get_member_data(self):
        """每次都重新讀取最新資料"""
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

#-----------------------------------------------------------------------------------------------
    # 所有遊戲相關功能前檢查開始了沒
    async def check_game_active(self, interaction: discord.Interaction) -> bool:
        wolf_cog = self.bot.get_cog('WolfGameCog')
        if not wolf_cog or not wolf_cog.game_active:
            await interaction.response.send_message(
                "❌ 遊戲尚未開始！",
                ephemeral=True
            )
            return False
        return True

#-----------------------------------------------------------------------------------------------
    class AnswerModal(discord.ui.Modal, title="回答題目"):
        def __init__(self, cog):
            super().__init__()
            self.cog = cog
            self.bot = cog.bot

            self.question_id = discord.ui.TextInput(
                label="題目編號",
                placeholder="輸入題目編號",
                required=True
            )

            self.team_id = discord.ui.TextInput(
                label="小隊編號",
                placeholder="輸入你的小隊編號",
                required=True
            )

            self.answer = discord.ui.TextInput(
                label="答案",
                placeholder="輸入你的答案",
                required=True
            )

            self.add_item(self.question_id)
            self.add_item(self.team_id)
            self.add_item(self.answer)

        async def on_submit(self, interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            member_data = self.cog.get_member_data()
            team_question = self.cog.get_team_question()

            # 題目是否存在
            if str(self.question_id.value) not in self.cog.questions:
                await interaction.response.send_message(
                    f"❌ 無效的題目編號！",
                    ephemeral=True
                )
                return

            # 是否已答過
            if str(self.question_id.value) in team_question[str(self.team_id.value)]:
                await interaction.response.send_message(
                    f"❌ 這題你們小隊已經回答過了！",
                    ephemeral=True
                )
                return

            question_data = self.cog.questions[str(self.question_id.value)]
            correct_answer = question_data["answer"]
            points = question_data["points"]

            if self.answer.value.lower() == correct_answer.lower():
                await interaction.response.send_message(
                    f"✅ 答對了！獲得 {points} 分",
                    ephemeral=True
                )
                try:
                    await self.bot.update_score_ws(str(self.team_id.value), points)
                    self.cog.team_question[str(self.team_id.value)].append(str(self.question_id.value))
                    self.cog.save_team_question()
                except Exception as e:
                    logging.error(f"更新分數時發生錯誤: {e}")
            else:
                await interaction.response.send_message(
                    f"❌ 答案錯誤！",
                    ephemeral=True
                )

#-----------------------------------------------------------------------------------------------
    @app_commands.command(name="答題", description="回答題目")
    async def answer_question(self, interaction: discord.Interaction):
        # 檢查遊戲是否開始
        if not await self.check_game_active(interaction):
            return

        user_id = str(interaction.user.id)

        # 是否死亡
        if user_id in self.member_data and self.member_data[user_id]["lives"] <= 0:
            await interaction.response.send_message(
                "❌ 你已經死亡，無法回答題目！",
                ephemeral=True
            )
            return

        modal = self.AnswerModal(self)
        await interaction.response.send_modal(modal)

#-----------------------------------------------------------------------------------------------
async def setup(bot):
    await bot.add_cog(QuestionCog(bot))
