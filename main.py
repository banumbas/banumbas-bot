import os
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands

load_dotenv()

def find_token():
    candidates = [
        "DISCORD_TOKEN", "TOKEN", "BOT_TOKEN",
        "BOT_SECRET", "SECRET_TOKEN", "DISCORD_BOT_TOKEN"
    ]
    for k in candidates:
        v = os.getenv(k)
        if v:
            return v, k

    for k, v in os.environ.items():
        if not v:
            continue
        up = k.upper()
        if ("DISCORD" in up and "TOKEN" in up) or up == "DISCORD" or ("BOT" in up and "TOKEN" in up):
            return v, k
    return None, None

TOKEN, TOKEN_NAME = find_token()
if TOKEN is None:
    print("Токен не найден. Проверьте переменные окружения.")
    exit(1)

intents = discord.Intents.default()
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)



@bot.event
async def on_ready():
    print(f"Бот {bot.user} ({bot.user.id}) запущен и готов к работе.")


async def load_extensions():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"Загружен модуль: {filename}")
            

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())