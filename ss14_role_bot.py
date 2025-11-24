import os
import asyncio
from dotenv import load_dotenv
import discord

load_dotenv()

ROLE_NAME = os.getenv("ROLE_NAME", "Играет")


def find_token():
    """
    Ищет токен по распространённым именам переменных окружения.
    Возвращает (token, name) или (None, None).
    """
    candidates = [
        "DISCORD_TOKEN",
        "TOKEN",
        "BOT_TOKEN",
        "BOT_SECRET",
        "SECRET_TOKEN",
        "DISCORD_BOT_TOKEN",
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

intents = discord.Intents.default()
intents.members = True
intents.presences = True

client = discord.Client(intents=intents)


def is_playing_ss14(activity: discord.BaseActivity) -> bool:
    if activity is None:
        return False
    name = getattr(activity, "name", "") or ""
    details = getattr(activity, "details", "") or ""
    text = f"{name} {details}".lower()
    if "space station 14" in text:
        return True
    if "ss14" in text:
        return True
    return False


async def ensure_role(guild: discord.Guild) -> discord.Role | None:
    role = discord.utils.get(guild.roles, name=ROLE_NAME)
    if role is None:
        try:
            role = await guild.create_role(name=ROLE_NAME, reason="Автосоздание роли для SS14")
        except Exception as e:
            print(f"Не удалось создать роль в {guild.name}: {e}")
            return None
    return role


async def set_role_for_member(member: discord.Member, add: bool):
    guild = member.guild
    role = await ensure_role(guild)
    if role is None:
        return
    try:
        if add and role not in member.roles:
            await member.add_roles(role, reason="Detected playing Space Station 14")
            print(f"Добавил роль {ROLE_NAME} -> {member.display_name} ({member.id})")
        elif (not add) and (role in member.roles):
            await member.remove_roles(role, reason="Stopped playing Space Station 14")
            print(f"Убрал роль {ROLE_NAME} -> {member.display_name} ({member.id})")
    except Exception as e:
        print(f"Ошибка при обновлении ролей у {member}: {e}")


@client.event
async def on_ready():
    print(f"Logged in as {client.user} ({client.user.id})")
    client.loop.create_task(initial_scan())


@client.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    try:
        before_has = any(is_playing_ss14(a) for a in (before.activities or []))
        after_has = any(is_playing_ss14(a) for a in (after.activities or []))
    except Exception:
        before_has = False
        after_has = False

    if before_has == after_has:
        return

    await set_role_for_member(after, add=after_has)


async def initial_scan():
    await client.wait_until_ready()
    print("Запуск initial scan по всем серверам...")
    for guild in client.guilds:
        role = await ensure_role(guild)
        if role is None:
            continue
        for member in guild.members:
            try:
                has = any(is_playing_ss14(a) for a in (member.activities or []))
            except Exception:
                has = False
            if has and role not in member.roles:
                try:
                    await member.add_roles(role, reason="Initial scan: playing SS14")
                    print(f"Добавил роль (scan) -> {member.display_name}")
                except Exception as e:
                    print("Ошибка add_roles (scan):", e)
            elif (not has) and (role in member.roles):
                try:
                    await member.remove_roles(role, reason="Initial scan: not playing SS14")
                    print(f"Убрал роль (scan) -> {member.display_name}")
                except Exception as e:
                    print("Ошибка remove_roles (scan):", e)
    print("Initial scan завершён.")


if __name__ == "__main__":
    if TOKEN is None:
        print("DISCORD_TOKEN не найден в окружении. Укажите DISCORD_TOKEN в переменных окружения (Railway variables / UI).")
        try:
            keys = list(os.environ.keys())
            print("Ключи окружения (первые 50):", keys[:50])
        except Exception:
            pass
    else:
        try:
            preview = TOKEN[:4] + "***" if len(TOKEN) >= 4 else "***"
            print(f"Токен найден в переменной: {TOKEN_NAME} (начало: {preview})")
        except Exception:
            print(f"Токен найден в переменной: {TOKEN_NAME}")
        client.run(TOKEN)
