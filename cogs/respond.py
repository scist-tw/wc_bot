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
        if message.author.bot:
            return

        content = message.content.lower()

        if content.startswith('!刪除使用者'):
            # 檢查權限
            if not any(role.name == "score_admin" for role in message.author.roles):
                await message.channel.send("❌ 只有管理員可以使用此指令！", delete_after=5)
                return

            try:
                args = content.split()
                if len(args) != 2:
                    await message.channel.send("❌ 格式錯誤！使用方式：!刪除使用者 <@玩家或all>", delete_after=5)
                    return

                target = args[1]

                # 讀取當前資料
                with open('json/member.json', 'r', encoding='utf-8') as f:
                    member_data = json.load(f)

                if target.lower() == 'all':
                    # 清空所有玩家資料
                    member_data = {}
                    await message.channel.send("✅ 已清空所有玩家資料！", delete_after=5)
                else:
                    # 處理 mention 格式
                    if target.startswith('<@') and target.endswith('>'):
                        user_id = target[2:-1]
                        if user_id.startswith('!'):
                            user_id = user_id[1:]
                    else:
                        user_id = target

                    if user_id in member_data:
                        player_name = member_data[user_id].get('name', '未知')
                        del member_data[user_id]
                        await message.channel.send(f"✅ 已刪除玩家 {player_name} 的資料！", delete_after=5)
                    else:
                        await message.channel.send("❌ 找不到該玩家！", delete_after=5)
                        return

                # 儲存更新後的資料
                with open('json/member.json', 'w', encoding='utf-8') as f:
                    json.dump(member_data, f, ensure_ascii=False, indent=4)

            except Exception as e:
                await message.channel.send("❌ 刪除使用者時發生錯誤！", delete_after=5)
                print(f"刪除使用者時發生錯誤: {e}")

            # 刪除指令訊息
            try:
                await message.delete()
            except:
                pass

        elif content.startswith('!刪除答題記錄'):
            # 檢查權限
            if not any(role.name == "score_admin" for role in message.author.roles):
                await message.channel.send("❌ 只有管理員可以使用此指令！", delete_after=5)
                return

            try:
                args = content.split()
                if len(args) != 2:
                    await message.channel.send("❌ 格式錯誤！使用方式：!刪除答題記錄 <組別或all>", delete_after=5)
                    return

                target = args[1]
                with open('json/team_question.json', 'r', encoding='utf-8') as f:
                    team_question = json.load(f)

                if target.lower() == 'all':
                    # 清空所有組別的答題記錄
                    team_question = {str(i): [] for i in range(1, 9)}
                    await message.channel.send("✅ 已清空所有組別的答題記錄！", delete_after=5)
                elif target.isdigit() and 1 <= int(target) <= 8:
                    # 清空指定組別的答題記錄
                    team_question[target] = []
                    await message.channel.send(f"✅ 已清空第 {target} 組的答題記錄！", delete_after=5)
                else:
                    await message.channel.send("❌ 無效的組別！請輸入 1-8 或 all", delete_after=5)
                    return

                # 儲存更新後的資料
                with open('json/team_question.json', 'w', encoding='utf-8') as f:
                    json.dump(team_question, f, ensure_ascii=False, indent=4)

            except Exception as e:
                await message.channel.send("❌ 刪除答題記錄時發生錯誤！", delete_after=5)
                print(f"刪除答題記錄時發生錯誤: {e}")

            # 刪除指令訊息
            try:
                await message.delete()
            except:
                pass

        if content.startswith('!更改組別'):
            try:
                await message.delete()
            except Exception as e:
                print(f"刪除訊息時發生錯誤: {e}")

            # 檢查格式
            parts = content.split()

            # 重新讀取最新的 member_data
            try:
                with open('json/member.json', 'r', encoding='utf-8') as f:
                    self.member_data = json.load(f)
            except FileNotFoundError:
                self.member_data = {}

            # 如果是管理員且有 mention 玩家
            if (len(parts) == 3 and
                any(role.name == "score_admin" for role in message.author.roles) and
                message.mentions):

                target_user = message.mentions[0]
                team_num = parts[2]

                try:
                    team_num = int(team_num)
                    if team_num < 1 or team_num > 8:
                        await message.channel.send(
                            "❌ 無效的隊伍編號！請輸入 1-8 之間的數字。",
                            delete_after=5
                        )
                        return

                    user_id = str(target_user.id)
                    if user_id not in self.member_data:
                        await message.channel.send(
                            "❌ 該玩家還未綁定任何隊伍。",
                            delete_after=5
                        )
                        return

                    old_team = self.member_data[user_id]["team"]
                    self.member_data[user_id]["team"] = str(team_num)
                    self.save_member_data()
                    await message.channel.send(
                        f"✅ 已將 {target_user.mention} 的隊伍從 {old_team} 更改為 {team_num}。",
                        delete_after=5
                    )

                except ValueError:
                    await message.channel.send(
                        "❌ 請輸入有效的數字！",
                        delete_after=5
                    )
                    return

            # 原本的自己更改組別功能
            else:
                try:
                    if len(parts) != 2:
                        await message.author.send("請輸入正確格式：!更改組別 <組別>")
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
                    response = await message.channel.send(
                        "請開啟私人訊息功能，以接收回應。",
                        delete_after=5
                    )

        if 'hello' in content:
            await message.channel.send('Hello!')
        if self.bot.user.mentioned_in(message):
            await message.reply("同學你好，你ㄊㄟˋ到我了🗣️")
async def setup(bot):
    await bot.add_cog(Respond(bot))
