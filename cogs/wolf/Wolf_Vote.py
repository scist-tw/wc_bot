import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import asyncio
from datetime import datetime, timedelta
import logging
import websockets

logger = logging.getLogger('WolfGame')

class WolfGameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scores = self.bot.score
        self.emoji = self.bot.emoji
        self.votes = {}
        self.wolf_kill_counter = {}
        self.vote_triggered = False
        self.member_data = self.get_member_data()
        self.check_wolf_kills.start()
        self.vote_interval = 600  
        self.disable_duration = 300  
        self.game_active = False  
        self.kill_cooldowns = {}  
        self.last_votes = {}  

    def get_member_data(self):
        """每次都重新讀取最新資料"""
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_member_data(self, data):
        """儲存資料"""
        with open('json/member.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # 在所有遊戲相關功能前添加檢查
    async def check_game_active(self, interaction: discord.Interaction) -> bool:
        if not self.game_active:
            await interaction.response.send_message(
                "❌ 遊戲尚未開始！",
                ephemeral=True
            )
            return False
        return True

    @app_commands.command(name="狼人殺人", description="狼人殺害其他玩家並獲得分數")
    async def werewolf_kill(self, interaction: discord.Interaction, 玩家編號: str):
        async def execute_command(interaction):
            if not await self.check_game_active(interaction):
                return
            user_id = str(interaction.user.id)
            
            # 因為可能玩家已經死亡或不是狼人，不需要檢查冷卻
            self.member_data = self.get_member_data()
            
            if user_id not in self.member_data:
                await interaction.response.send_message(
                    "❌ 你不是遊戲玩家！",
                    ephemeral=True
                )
                return

            if self.member_data[user_id]["lives"] <= 0:
                await interaction.response.send_message(
                    "❌ 你已經死亡，無法使用狼人技能！",
                    ephemeral=True
                )
                return

            if not self.member_data[user_id]["is_wolf"]:
                await interaction.response.send_message(
                    f"❌ 你不是狼人，無法執行此操作！",
                    ephemeral=True
                )
                return

            if not self.member_data[user_id]["is_skill_able"]:
                await interaction.response.send_message(
                    f"❌ 你的技能目前無法使用！",
                    ephemeral=True
                )
                return

            target_user_id = None
            for member_id, data in self.member_data.items():
                if data["id"] == 玩家編號:
                    target_user_id = member_id
                    break

            if target_user_id is None:
                await interaction.response.send_message(
                    f"❌ 找不到編號為 {玩家編號} 的玩家！",
                    ephemeral=True
                )
                return

            team_id = self.member_data[user_id]["team"]
            victim_team = self.member_data[target_user_id]["team"]
            
            # 先回應互動
            await interaction.response.send_message(
                f"✅ 成功殺害編號為 {玩家編號} 的玩家！",
                ephemeral=True
            )

            # 然後執行分數更新和其他操作
            try:
                await self.bot.update_score_ws(team_id, 5000)
                await self.bot.update_score_ws(victim_team, -3000)
                
                # 更新殺人計數
                if user_id not in self.wolf_kill_counter:
                    self.wolf_kill_counter[user_id] = 0
                self.wolf_kill_counter[user_id] += 1

                # 更新受害者資料
                self.member_data[target_user_id]["lives"] -= 1
                will_die = self.member_data[target_user_id]["lives"] <= 0
                self.member_data[target_user_id]["id"] = ""
                self.member_data[target_user_id]["killed_by"] = user_id
                
                self.save_member_data(self.member_data)
                self.kill_cooldowns[user_id] = datetime.now()

                # 通知被害者
                try:
                    victim_user = await self.bot.fetch_user(int(target_user_id))
                    if victim_user:
                        if will_die:
                            death_msg = f"{victim_user.mention} 💀 你已經死亡！\n"
                            death_msg += "- 你無法使用狼人技能(如果你是狼了話)\n"
                            death_msg += "- 你無法更換編號"
                            await victim_user.send(death_msg)
                        else:
                            await victim_user.send(
                                f"{victim_user.mention} 你被狼人殺害了！請立即去找工作人員更換新編號。"
                            )
                except Exception as e:
                    logger.error(f"無法通知玩家: {e}")

            except Exception as e:
                logger.error(f"執行狼人殺人操作時發生錯誤: {e}")

        await self.bot.handle_interaction(interaction, execute_command)

    @tasks.loop(seconds=30)
    async def check_wolf_kills(self):
        if self.vote_triggered:
            return

        for user_id, kill_count in self.wolf_kill_counter.items():
            if kill_count >= 5:
                await self.trigger_voting()
                self.vote_triggered = True
                return

    async def trigger_voting(self):
        self.member_data = self.get_member_data()
        
        for user_id in self.member_data:
            try:
                if self.member_data[user_id]["lives"] <= 0:
                    continue
                    
                try:
                    user = await self.bot.fetch_user(int(user_id))
                    if not user:
                        continue
                        
                    view = TeamSelectView(self.bot, self.member_data, interaction=None)
                    embed = discord.Embed(
                        title="🗳️ 狼人投票",
                        description="請在2分鐘內選擇一位可疑的玩家\n投票於 <t:{}:R> 結束".format(
                            int((datetime.now() + timedelta(minutes=2)).timestamp())
                        ),
                        color=discord.Color.blue()
                    )
                    await user.send(embed=embed, view=view)
                except discord.Forbidden:
                    logger.warning(f"無法發送私訊給用戶 {user_id}")
                except discord.NotFound:
                    logger.warning(f"找不到用戶 {user_id}")
                    
            except Exception as e:
                logger.error(f"投票過程出錯: {e}")

    @tasks.loop(minutes=10) 
    async def periodic_vote(self):
        if not self.game_active:  
            return
        await self.start_voting()  

    @periodic_vote.before_loop
    async def before_periodic_vote(self):
        """等待10分鐘後再開始第一次投票"""
        await asyncio.sleep(600)  

    @app_commands.command(
        name="手動發起投票", 
        description="[工作人員]手動發起狼人投票"
    )
    async def manual_vote(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ 此命令只能在伺服器中使用！",
                ephemeral=True
            )
            return
            
        if not any(role.name == "score_admin" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此功能！",
                ephemeral=True
            )
            return

        # 檢查遊戲是否開始
        if not await self.check_game_active(interaction):
            return

        await interaction.response.send_message(
            "🗳️ 投票已發起！所有玩家將收到投票訊息。",
            ephemeral=False
        )
        
        await self.start_voting()

    async def start_voting(self):
        self.votes = {}
        end_time = datetime.now() + timedelta(minutes=2)
        
        for user_id in self.member_data:
            try:
                user = await self.bot.fetch_user(int(user_id))
                if user:
                    view = TeamSelectView(self.bot, self.member_data, interaction=None)
                    embed = discord.Embed(
                        title="🗳️ 狼人投票",
                        description="請在2分鐘內選擇一位可疑的玩家\n投票於 <t:{}:R> 結束".format(
                            int(end_time.timestamp())
                        ),
                        color=discord.Color.blue()
                    )
                    await user.send(embed=embed, view=view)
            except Exception as e:
                logger.error(f"無法發送投票: {e}")

        try:
            await asyncio.sleep(120)
            
            result_embed = await self.process_votes()
            
            if result_embed:  # 
                for user_id in self.member_data:
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        if user:
                            await user.send(embed=result_embed)
                    except Exception as e:
                        logger.error(f"無法發送投票結果: {e}")

            self.save_member_data(self.member_data)
        except Exception as e:
            logger.error(f"投票過程出錯: {e}")

    async def process_votes(self):
        """處理投票結果"""
        if not self.votes: 
            return None
            
        self.last_votes = self.votes.copy()
        self.member_data = self.get_member_data()
        
        # 過濾掉死亡玩家的投票
        self.votes = {
            voter_id: voted_id 
            for voter_id, voted_id in self.votes.items()
            if voter_id in self.member_data and self.member_data[voter_id]["lives"] > 0
        }
        
        vote_counts = {}
        for voted_id in self.votes.values():
            if voted_id in vote_counts:
                vote_counts[voted_id] += 1
            else:
                vote_counts[voted_id] = 1
                
        # 找出前五名（包括並列）
        if vote_counts:
            sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
            top_votes = []
            current_count = None
            
            for voted_id, count in sorted_votes:
                if len(top_votes) < 5 or count == current_count:
                    top_votes.append((voted_id, count))
                    current_count = count
                else:
                    break
            
            for voted_id, count in top_votes:
                if voted_id in self.member_data:
                    self.member_data[voted_id]["is_skill_able"] = False
                    asyncio.create_task(self.enable_skill_after_delay(voted_id))
            
            self.save_member_data(self.member_data)
            
            result_embed = discord.Embed(
                title="🎯 投票結果",
                description="以下是得票最高的前五位玩家：",
                color=discord.Color.gold()
            )
            
            for voted_id, count in top_votes:
                player_data = self.member_data[voted_id]
                result_embed.add_field(
                    name=f"第 {player_data['team']} 組的 {player_data.get('name', '未知')}",
                    value=f"獲得 {count} 票",
                    inline=False
                )
            
            self.votes.clear()
            
            return result_embed

        self.votes.clear()
        return None

    async def enable_skill_after_delay(self, user_id):
        """5分鐘後重新啟用技能"""
        await asyncio.sleep(self.disable_duration)
        self.member_data = self.get_member_data()
        if user_id in self.member_data:
            self.member_data[user_id]["is_skill_able"] = True
            self.save_member_data(self.member_data)

    @app_commands.command(
        name="回復生命", 
        description="[工作人員]回復玩家生命值"
    )
    @app_commands.describe(user_id="玩家的Discord ID", lives="要設定的生命值")
    async def restore_lives(self, interaction: discord.Interaction, user_id: str, lives: int):
        # 檢查是否在伺服器中
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ 此命令只能在伺服器中使用！",
                ephemeral=True
            )
            return
            
        # 檢查是否有特定身分組
        if not any(role.name == "score_admin" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此命令！",
                ephemeral=True
            )
            return
            
        # 獲取最新資料
        self.member_data = self.get_member_data()
        
        # 處理 mention 格式
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
            
        if user_id not in self.member_data:
            await interaction.response.send_message("❌ 找不到該玩家！", ephemeral=True)
            return
            
        old_lives = self.member_data[user_id]["lives"]
        self.member_data[user_id]["lives"] = lives
        self.save_member_data(self.member_data)
        
        await interaction.response.send_message(
            f"✅ 已將玩家生命值從 {old_lives} 更改為 {lives}",
            ephemeral=True
        )

class TeamSelectView(discord.ui.View):
    def __init__(self, bot, member_data, interaction):
        super().__init__(timeout=None)
        self.bot = bot
        self.member_data = member_data
        self.interaction = interaction
        self.add_team_select()

    def add_team_select(self):
        options = []
        # 先檢查使用者是否死亡
        user_id = str(self.interaction.user.id)
        if user_id in self.member_data and self.member_data[user_id]["lives"] <= 0:
            return  # 如果死亡就不添加任何選項
            
        # 先列出所有有活人的組別
        for team_id in range(1, 9):
            team_members = [
                (mid, data) for mid, data in self.member_data.items() 
                if data["team"] == str(team_id) and data["lives"] > 0
            ]
            if team_members:  # 只添加有活著成員的小組
                options.append(
                    discord.SelectOption(
                        label=f"第 {team_id} 組",
                        value=str(team_id),
                        description=f"成員數: {len(team_members)}"
                    )
                )

        if options:  # 只有在有選項時才添加選單
            select = discord.ui.Select(
                placeholder="選擇一個小組",
                options=options,
                custom_id="team_select"
            )
            select.callback = self.team_select_callback
            self.add_item(select)

    async def team_select_callback(self, interaction: discord.Interaction):
        selected_team = interaction.data["values"][0]
        # 顯示該組的成員選擇
        view = TeamMemberSelectView(self.bot, self.member_data, selected_team)
        await interaction.response.edit_message(
            content=f"請選擇第 {selected_team} 組中的可疑玩家",
            view=view
        )

class TeamMemberSelectView(discord.ui.View):
    def __init__(self, bot, member_data, team_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.member_data = member_data
        self.team_id = team_id
        self.add_member_select()

    def get_member_data(self):
        """每次都重新讀取最新資料"""
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def add_member_select(self):
        # 重新讀取最新資料
        self.member_data = self.get_member_data()
        
        options = []
        # 列出該組所有活著的成員
        team_members = [
            (mid, data) for mid, data in self.member_data.items() 
            if data["team"] == self.team_id and data["lives"] > 0
        ]
        
        for member_id, data in team_members:
            options.append(
                discord.SelectOption(
                    label=f"{data.get('name', '未知')}",  # 只顯示姓名
                    value=member_id
                )
            )

        select = discord.ui.Select(
            placeholder="選擇一位可疑的玩家",
            options=options,
            custom_id="member_select"
        )
        select.callback = self.member_select_callback
        self.add_item(select)

        # 添加返回按鈕
        back_button = discord.ui.Button(
            label="返回選擇組別",
            style=discord.ButtonStyle.gray,
            custom_id="back_to_team"
        )
        back_button.callback = self.back_to_team
        self.add_item(back_button)

    async def member_select_callback(self, interaction: discord.Interaction):
        # 獲取最新資料
        self.member_data = self.get_member_data()
        
        # 檢查投票者是否死亡
        user_id = str(interaction.user.id)
        if user_id in self.member_data and self.member_data[user_id]["lives"] <= 0:
            await interaction.response.send_message(
                "❌ 你已經死亡，無法參與投票！",
                ephemeral=True
            )
            return
        
        wolf_cog = self.bot.get_cog('WolfGameCog')
        if wolf_cog:
            voted_id = interaction.data["values"][0]
            wolf_cog.votes[str(interaction.user.id)] = voted_id
            
            # 創建投票結果的 embed
            voted_player = self.member_data[voted_id]
            embed = discord.Embed(
                title="✅ 投票成功",
                description=f"你投票給了第 {voted_player['team']} 組的 {voted_player.get('name', '未知')}",
                color=discord.Color.green()
            )
            
            # 刪除原本的訊息並發送新的 embed
            await interaction.message.delete()
            await interaction.channel.send(embed=embed)  # 改為公開訊息

    async def back_to_team(self, interaction: discord.Interaction):
        # 獲取最新資料
        self.member_data = self.get_member_data()
        
        view = TeamSelectView(self.bot, self.member_data, interaction=None)
        await interaction.response.edit_message(
            content="請選擇一個小組",
            view=view
        )

async def setup(bot):
    await bot.add_cog(WolfGameCog(bot))
