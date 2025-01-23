import discord
from discord.ext import commands, tasks
import logging
import os
import json
import asyncio
from datetime import datetime
import psutil
import websockets

from cogs.member_verification import AlwaysView
from cogs.score import ScoreboardView
from cogs.wolf.teamboard import TeamboardView, TeamDetailView
from dotenv import load_dotenv
logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()
intents.members = True
intents.dm_messages = True
Logchannel = 1323010589911421030
load_dotenv()

def load_json_folder(folder_path: str) -> dict:
    data = {}
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            name = filename.replace('.json', '')
            with open(f"{folder_path}/{filename}", 'r', encoding='utf-8') as f:
                data[name] = json.load(f)
    return data

json_data = load_json_folder("json")

token = os.getenv("DISCORD_TOKEN")  

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )
        
        self.json_data = json_data
        self.emoji = self.json_data["emoji"]
        self.score = self.json_data["score"]
        self.question = self.json_data["question"]
        self.team_question = self.json_data["team_question"]
        self.member_data = self.json_data["member"]

        # Discord API 請求監控
        self.system_status = "normal"
        self.request_count = 0
        self.last_reset = datetime.now()
        self.rate_limit_hits = 0
        self.activity_index = 0

        self.loadcogs = []
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                self.loadcogs.append(f"cogs.{filename[:-3]}")
        wolf_dir = "./cogs/wolf"
        if os.path.exists(wolf_dir):
            for filename in os.listdir(wolf_dir):
                if filename.endswith(".py"):
                    self.loadcogs.append(f"cogs.wolf.{filename[:-3]}")
        self.data_manager = DataManager()
        
        # 需要再用
        self.team_roles = {
            "1": None, 
            "2": None,
            "3": None,  
            "4": None, 
            "5": None, 
            "6": None, 
            "7": None, 
            "8": None, 
            "9": None
        }

#-----------------------------------------------------------------------------------------------
    @tasks.loop(seconds=5)
    async def status_monitor(self):
        try:
            if self.rate_limit_hits > 80:  
                if self.system_status != "critical":
                    self.system_status = "critical"
                    await self.change_presence(
                        activity=discord.Game(name="|⚠️ 系統分流處理中"),
                        status=discord.Status.dnd
                    )
            elif self.rate_limit_hits > 50: 
                if self.system_status != "unstable":
                    self.system_status = "unstable"
                    await self.change_presence(
                        activity=discord.Game(name="|⚡ 系統請求量較高"),
                        status=discord.Status.idle
                    )
            else:
                activities = [
                    discord.Game(name="✅ 系統運行正常"),
                    discord.Game(name="| 需要協助請提出"),
                    discord.Game(name="| 功能當機請通知資訊組"),
                ]
                self.activity_index = (self.activity_index + 1) % len(activities)
                await self.change_presence(
                    activity=activities[self.activity_index],
                    status=discord.Status.online
                )
            self.rate_limit_hits = 0

        except Exception as e:
            logging.error(f"Status monitor error: {e}")

#-----------------------------------------------------------------------------------------------
    @status_monitor.before_loop
    async def before_status_monitor(self):
        await self.wait_until_ready()

    async def setup_hook(self):
        self.status_monitor.start()
        
        logging.info(f"-->嘗試加載: {self.loadcogs}")
        
        for ext in self.loadcogs:
            try:
                await self.load_extension(ext)
                logging.info(f"-->{ext} 加載成功")
            except Exception as e:
                logging.error(f"-->加載 {ext} 失敗: {e}")

        print(f"機器人已上線 --> {self.user}")

#-----------------------------------------------------------------------------------------------
        try:
            self.add_view(AlwaysView())
        except Exception as e:
            logging.error(f"-->按鈕註冊失敗: {e}")

        self.add_view(ScoreboardView(scores=self.score["groups"], emoji=self.emoji))
        self.add_view(TeamboardView(self))
        self.add_view(TeamDetailView(self, None))
        for i in range(1, 9):
            self.add_view(TeamDetailView(self, i))

        synced = await self.tree.sync()
        print(f'-->已加載{len(synced)}個指令')

    async def on_ready(self):
        logging.info(f'-->Bot ID: {self.user.id}')
        logging.info(f"-->{self.user}已啟動<--")

#-----------------------------------------------------------------------------------------------
    async def send_error_log(self, error_msg: str, error_trace: str = None):
        channel = self.get_channel(Logchannel)
        if channel:
            embed = discord.Embed(
                title="❌ 錯誤報告",
                description=error_msg,
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            if error_trace:
                embed.add_field(
                    name="錯誤追蹤",
                    value=f"```py\n{error_trace}```",
                    inline=False
                )
            await channel.send(embed=embed)

#-----------------------------------------------------------------------------------------------
    async def queue_request(self, interaction: discord.Interaction, callback):
        """將請求加入佇列"""
        await self.request_queue.put((interaction, callback))
        
        if not self.is_processing_queue:
            self.is_processing_queue = True
            asyncio.create_task(self.process_queue())

    async def process_queue(self):
        """處理佇列中的請求"""
        while not self.request_queue.empty():
            interaction, callback = await self.request_queue.get()
            try:
                await callback(interaction)
                await asyncio.sleep(1.2)  
            except discord.errors.HTTPException as e:
                if e.status == 429:  
                    self.rate_limit_hits += 1

                    await self.request_queue.put((interaction, callback))
                    await asyncio.sleep(e.retry_after)
                else:
                    logging.error(f"Error processing request: {e}")
            except Exception as e:
                logging.error(f"Error processing request: {e}")

        self.is_processing_queue = False

    async def handle_interaction(self, interaction: discord.Interaction, callback):
        """處理互動請求"""
        try:
            await callback(interaction)
        except discord.errors.HTTPException as e:
            if e.status == 429:  
                self.rate_limit_hits += 1
                await interaction.response.send_message(
                    "系統正在處理大量請求，已將您的請求加入佇列，請稍候...",
                    ephemeral=True
                )
                await self.queue_request(interaction, callback)

#-----------------------------------------------------------------------------------------------
    async def update_score_ws(self, team: str, score: int):
        """通用更新分數"""
        try:
            async with websockets.connect('ws://10.130.0.6:30031') as websocket:
                data = {
                    'team': team,
                    'points': score
                }
                await websocket.send(json.dumps(data))
                logging.info(f"成功發送更新請求: 第{team}小隊 +{score}分")
                return True
        except Exception as e:
            logging.error(f"WebSocket 更新分數時發生錯誤: {str(e)}")
            return False

class DataManager:
    @staticmethod
    def save_member_data(data_to_update):
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        except FileNotFoundError:
            current_data = {}
        
        current_data.update(data_to_update)
        
        with open('json/member.json', 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def load_member_data():
        try:
            with open('json/member.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

bot = Bot()
bot.run(token)  