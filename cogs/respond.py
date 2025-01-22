import discord
from discord.ext import commands
import json

class Respond(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scores = self.bot.score
        self.emoji = self.bot.emoji
        self.questions = self.bot.question
        self.team_question = self.bot.team_question
        self.member_data = {}
        self.load_member_data()

    def load_member_data(self):
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                self.member_data = json.load(f)
        except FileNotFoundError:
            self.member_data = {}

    def save_member_data(self):
        # 先讀取現有資料
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except FileNotFoundError:
            current_data = {}
        
        # 更新資料
        current_data.update(self.member_data)
        
        # 儲存更新後的資料
        with open('json/member.json', 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=4)

    @commands.Cog.listener()
    async def on_message(self, message):
        # 忽略機器人的訊息
        if message.author.bot:
            return

        content = message.content.lower()
            
        # 處理更改組別命令
        if content.startswith('!更改組別'):
            # 嘗試刪除訊息（不管是在伺服器還是私訊）
            try:
                await message.delete()
            except Exception as e:
                print(f"刪除訊息時發生錯誤: {e}")

            # 使用私訊回應
            try:
                parts = content.split()
                if len(parts) != 2:
                    await message.author.send("請輸入正確格式 !")
                    return

                try:
                    team_num = int(parts[1])
                    if team_num < 1 or team_num > 8:
                        await message.author.send("無效的隊伍編號！請輸入 1-8 之間的數字。")
                        return

                    user_id = str(message.author.id)
                    if user_id not in self.member_data:
                        await message.author.send("您還未綁定任何隊伍。")
                        return

                    old_team = self.member_data[user_id]["team"]
                    self.member_data[user_id]["team"] = str(team_num)
                    self.save_member_data()
                    await message.author.send(f"您的隊伍已從 {old_team} 更改為 {team_num}。")

                except ValueError:
                    await message.author.send("請輸入有效的數字！")
                    return

            except discord.Forbidden:
                # 如果無法私訊，則在頻道中發送訊息並設定自動刪除
                response = await message.channel.send("請開啟私人訊息功能，以接收回應。")
                await response.delete(delay=5)

        # 處理其他關鍵字回應
        if 'hello' in content:
            await message.channel.send('Hello!')

async def setup(bot):
    await bot.add_cog(Respond(bot))