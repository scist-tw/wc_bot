import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import asyncio
import websockets
import logging

logger = logging.getLogger(__name__)

class TeamboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scores = self.bot.score
        self.emoji = self.bot.emoji
        self.team_question = self.bot.team_question
        self.message_cache = {}
        self.last_data = {}
        self.last_scores = {}
        self.last_team_question = {}
        self.auto_refresh.start()

    def get_member_data(self):
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_member_data(self, data):
        with open('json/member.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

#-----------------------------------------------------------------------------------------------
    def create_main_embed(self):
        """創建主頁面嵌入"""
        embed = discord.Embed(title="🎮 小組詳細狀況板", color=discord.Color.blue())
        member_data = self.get_member_data()
        
        for team_id in range(1, 9):
            team_members = [
                member_id for member_id, data in member_data.items() 
                if data["team"] == str(team_id)
            ]
            
            status = "🟢" if team_members else "⚪"
            member_count = len(team_members)
            
            embed.add_field(
                name=f"第 {team_id} 組",
                value=f"{status} 成員數: {member_count}",
                inline=False
            )
        
        embed.set_footer(text="自動更新中...")
        return embed

    async def create_team_detail_embed(self, team_id):
        """創建小組詳細資訊嵌入"""
        member_data = self.get_member_data()
        team_members = {
            mid: data for mid, data in member_data.items() 
            if data["team"] == str(team_id)
        }
        
        embed = discord.Embed(
            title=f"第 {team_id} 組詳細資訊",
            color=discord.Color.gold()
        )
        
        members_text = ""
        for mid, data in team_members.items():
            try:
                member = self.bot.get_user(int(mid))
                name = data.get("name", "未知") 
                status = "🐺" if data["is_wolf"] else "🟩"
                status = "🟥" if data["lives"] <= 0 else status
                members_text += f"{status} {name} ({member.mention}) (命: {data['lives']})\n"
            except:
                continue
        
        embed.add_field(
            name="成員列表",
            value=members_text or "暫無成員",
            inline=False
        )
        
        try:
            async with websockets.connect("ws://10.130.0.6:30031",) as websocket:
                response = await websocket.recv()
                scores = json.loads(response)
                team_score = next(
                    (item['points'] for item in scores if item['team'] == str(team_id)), 
                    0
                )
                embed.add_field(name="小組分數", value=f"{team_score} 分", inline=False)
        except Exception as e:
            logger.error(f"獲取分數時發生錯誤: {e}")
            embed.add_field(name="小組分數", value="無法獲取分數", inline=False)
        
        answered = len(self.team_question.get(str(team_id), []))
        embed.add_field(name="已答題數", value=f"{answered} 題", inline=False)
        
        return embed
    
#-----------------------------------------------------------------------------------------------
    @app_commands.command(
        name="主控板", 
        description="[工作人員]顯示所有小組的詳細狀況"
    )
    async def show_teamboard(self, interaction: discord.Interaction):
        if not any(role.name == "score_admin" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此命令！",
                ephemeral=True
            )
            return

        embed = self.create_main_embed()
        view = TeamboardView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)
        message = await interaction.original_response()
        self.message_cache[message.id] = {
            'message': message,
            'type': 'main',
            'team_id': None
        }

#-----------------------------------------------------------------------------------------------
    @tasks.loop(seconds=2)
    async def auto_refresh(self):
        """自動更新所有活動的團隊面板"""
        current_data = self.get_member_data()
        current_scores = self.bot.score
        current_team_question = self.bot.team_question

        data_changed = (
            current_data != self.last_data or
            current_scores != self.last_scores or
            current_team_question != self.last_team_question
        )
        
        if not data_changed:
            return
            
        # 更新快取
        self.last_data = current_data.copy()
        self.last_scores = current_scores.copy()
        self.last_team_question = current_team_question.copy()
        
        for message_id, data in list(self.message_cache.items()):
            try:
                message = data['message']
                if not message.channel: 
                    self.message_cache.pop(message_id, None)
                    continue
                    
                if data['type'] == 'main':
                    embed = self.create_main_embed()
                else:
                    embed = await self.create_team_detail_embed(data['team_id'])
                
                await message.edit(embed=embed)
            except Exception as e:
                self.message_cache.pop(message_id, None)

    @show_teamboard.error
    async def show_teamboard_error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此功能！",
                ephemeral=True
            )

#-----------------------------------------------------------------------------------------------
class TeamboardView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_team_buttons()
        
    def add_team_buttons(self):
        select = discord.ui.Select(
            placeholder="選擇小組查看詳情",
            options=[
                discord.SelectOption(
                    label=f"第 {i} 組",
                    value=str(i)
                ) for i in range(1, 9)
            ],
            custom_id="team_select",
            row=0
        )
        select.callback = self.team_select_callback
        self.add_item(select)

        # 檢查當前遊戲狀態
        wolf_cog = self.bot.get_cog('WolfGameCog')
        game_active = wolf_cog.game_active if wolf_cog else False

        # 添加開始遊戲按鈕
        start_button = discord.ui.Button(
            label="開始遊戲",
            style=discord.ButtonStyle.success,
            custom_id="start_game",
            row=1,
            disabled=game_active 
        )
        start_button.callback = self.start_game
        self.add_item(start_button)

        # 添加結束遊戲按鈕
        stop_button = discord.ui.Button(
            label="結束遊戲",
            style=discord.ButtonStyle.danger,
            custom_id="stop_game",
            row=1,
            disabled=not game_active
        )
        stop_button.callback = self.stop_game
        self.add_item(stop_button)

    async def team_select_callback(self, interaction: discord.Interaction):
        try:
            # 先延遲回應
            await interaction.response.defer()
            
            team_id = int(interaction.data["values"][0])
            cog = self.bot.get_cog('TeamboardCog')
            embed = await cog.create_team_detail_embed(team_id)
            view = TeamDetailView(self.bot, team_id)
            
            # 使用 edit_original_response 而不是 edit_message
            await interaction.edit_original_response(embed=embed, view=view)
            
            message = interaction.message
            cog.message_cache[message.id] = {
                'message': message,
                'type': 'detail',
                'team_id': team_id
            }
        except Exception as e:
            logger.error(f"處理小組選擇時發生錯誤: {e}")

    async def start_game(self, interaction: discord.Interaction):
        if not any(role.name == "score_admin" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此功能！",
                ephemeral=True
            )
            return

        wolf_cog = self.bot.get_cog('WolfGameCog')
        if wolf_cog:
            # 重置遊戲狀態
            wolf_cog.game_active = True
            wolf_cog.votes = {}
            wolf_cog.last_votes = {}
            wolf_cog.vote_triggered = False
            wolf_cog.wolf_kill_counter = {}
            
            # 開始新的投票任務
            wolf_cog.periodic_vote.start()
            
            # 更新按鈕狀態
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.custom_id == "start_game":
                        item.disabled = True
                    elif item.custom_id == "stop_game":
                        item.disabled = False
            
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("✅ 遊戲已開始！", ephemeral=True)

    async def stop_game(self, interaction: discord.Interaction):
        if not any(role.name == "score_admin" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此功能！",
                ephemeral=True
            )
            return

        wolf_cog = self.bot.get_cog('WolfGameCog')
        if wolf_cog:
            wolf_cog.game_active = False
            # 停止所有任務
            wolf_cog.periodic_vote.cancel()
            wolf_cog.votes = {}
            wolf_cog.last_votes = {}
            wolf_cog.vote_triggered = False
            wolf_cog.wolf_kill_counter = {}
            
            # 更新按鈕狀態
            for item in self.children:
                if isinstance(item, discord.ui.Button):
                    if item.custom_id == "start_game":
                        item.disabled = False
                    elif item.custom_id == "stop_game":
                        item.disabled = True
            
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("🛑 遊戲已結束！", ephemeral=True)

#-----------------------------------------------------------------------------------------------
class TeamDetailView(discord.ui.View):
    def __init__(self, bot, team_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.team_id = team_id

    @discord.ui.button(
        label="返回主頁",
        style=discord.ButtonStyle.gray,
        custom_id="back_main",
        row=0
    )
    async def back_to_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # 先延遲回應
            await interaction.response.defer()
            
            cog = self.bot.get_cog('TeamboardCog')
            embed = cog.create_main_embed()
            view = TeamboardView(self.bot)
            
            # 使用 edit_original_response
            await interaction.edit_original_response(embed=embed, view=view)
            
            message = interaction.message
            cog.message_cache[message.id] = {
                'message': message,
                'type': 'main',
                'team_id': None
            }
        except Exception as e:
            logger.error(f"返回主頁時發生錯誤: {e}")

    @discord.ui.button(
        label="刷新",
        style=discord.ButtonStyle.green,
        custom_id="refresh",
        row=0
    )
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog('TeamboardCog')
        embed = await cog.create_team_detail_embed(self.team_id)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(
        label="隨機選擇狼人",
        style=discord.ButtonStyle.red,
        custom_id="select_wolves",
        row=0
    )
    async def select_wolves(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.name == "score_admin" for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ 只有管理員可以使用此功能！",
                ephemeral=True
            )
            return

        # 先回應互動
        await interaction.response.defer()

        try:
            cog = self.bot.get_cog('TeamboardCog')
            member_data = cog.get_member_data()
            team_members = [
                mid for mid, data in member_data.items() 
                if data["team"] == str(self.team_id)
            ]
            
            if len(team_members) < 2:
                await interaction.followup.send(
                    "成員數量不足，無法選擇狼人！",
                    ephemeral=True
                )
                return
                
            wolves = random.sample(team_members, 2)
            
            # 更新資料
            for mid in member_data:
                member_data[mid]["is_wolf"] = mid in wolves
            
            cog.save_member_data(member_data)
            
            # 更新顯示
            embed = await cog.create_team_detail_embed(self.team_id)
            await interaction.edit_original_response(embed=embed, view=self)
            
            # 私訊通知被選中的狼人
            for wolf_id in wolves:
                try:
                    user = await self.bot.fetch_user(int(wolf_id))
                    await user.send("🐺 你被選為狼人了！")
                except:
                    continue

        except Exception as e:
            logger.error(f"選擇狼人時發生錯誤: {e}")
            await interaction.followup.send(
                "❌ 選擇狼人時發生錯誤，請稍後再試。",
                ephemeral=True
            )

#-----------------------------------------------------------------------------------------------
async def setup(bot):
    await bot.add_cog(TeamboardCog(bot))
