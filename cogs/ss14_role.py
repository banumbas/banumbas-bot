import discord
from discord.ext import commands
import os

ROLE_NAME = os.getenv("ROLE_NAME", "Играет")

def is_playing_ss14(activity: discord.BaseActivity) -> bool:
    if activity is None:
        return False
    name = getattr(activity, "name", "") or ""
    details = getattr(activity, "details", "") or ""
    text = f"{name} {details}".lower()
    return "space station 14" in text or "ss14" in text

class SS14Role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_role(self, guild: discord.Guild) -> discord.Role | None:
        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if role is None:
            try:
                role = await guild.create_role(name=ROLE_NAME, reason="Автосоздание роли для SS14")
                print(f"Создана роль '{ROLE_NAME}' на сервере {guild.name}")
            except Exception as e:
                print(f"Не удалось создать роль в {guild.name}: {e}")
                return None
        return role

    async def set_role_for_member(self, member: discord.Member, add: bool):
        guild = member.guild
        role = await self.ensure_role(guild)
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

    @commands.Cog.listener()
    async def on_ready(self):
        print("Запуск initial scan по всем серверам...")
        for guild in self.bot.guilds:
            role = await self.ensure_role(guild)
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

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        try:
            before_has = any(is_playing_ss14(a) for a in (before.activities or []))
            after_has = any(is_playing_ss14(a) for a in (after.activities or []))
        except Exception:
            return

        if before_has == after_has:
            return

        await self.set_role_for_member(after, add=after_has)

async def setup(bot):
    await bot.add_cog(SS14Role(bot))