import discord
from discord.ext import commands
import logging
import os
import json
import asyncio
import datetime

from cogs.member_verification import AlwaysView
# from dotenv import load_dotenv
logging.basicConfig(level=logging.INFO)
intents = discord.Intents.all()
intents.members = True
intents.dm_messages = True
Logchannel = 1323010589911421030
# load_dotenv()

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

#------------------------------------------------------
class Bot(commands.Bot):
    def __init__(self) :
        super().__init__(command_prefix="#", intents=intents,dm_permission=True)
        self.loadcogs = [f"cogs.{i[:-3]}" for i in os.listdir("./cogs") if i.endswith(".py")]
        self.json_data = json_data
        self.emoji = self.json_data["emoji"]
        self.score = self.json_data["score"]

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.DMChannel):
            if message.author == self.user:
                return

            await self.process_commands(message)

    async def setup_hook(self):
        logging.info(f"-->嘗試加載: {self.loadcogs}")
        for ext in self.loadcogs:
            try:
                await self.load_extension(ext)
                logging.info(f"-->{ext} 加載成功")
            except Exception as e:
                logging.error(f"-->加載 {ext} 失敗: {e}")
        try:
            self.add_view(AlwaysView())
        except Exception as e:
            logging.error(f"-->按鈕註冊失敗: {e}")

        synced = await self.tree.sync()
        print(f'-->已加載{len(synced)}個指令')


    async def on_ready(self):
        logging.info(f'-->Bot ID: {self.user.id}')
        asyncio.create_task(self.change_status())
        logging.info(f"-->{self.user}已啟動<--")

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
                    value=f"```py\n{error_trace[:1000]}```",
                    inline=False
                )
            await channel.send(embed=embed)

    async def change_status(self):
        activities = [
            discord.Game(name="|需要協助請提出"),
            discord.Game(name="|打/help查看注意事項"),
            discord.Game(name="|功能當機請通知資訊組"),
        ]

        while True:
            for activity in activities:
                await self.change_presence(activity=activity)
                await asyncio.sleep(5)

bot = Bot()
#------------------------------------------------------
bot.run(token)
