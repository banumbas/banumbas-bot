import discord
from discord.ext import commands
from discord import app_commands

TEXT_CHANNEL_NAME = "чат-войса"

class TempVoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_to_text = {}
        self.guild_settings = {}

    async def get_target_channel(self, guild: discord.Guild) -> int | None:
        return self.guild_settings.get(guild.id)

    async def ensure_text_channel(self, voice_channel: discord.VoiceChannel) -> discord.TextChannel | None:
        if voice_channel.id in self.voice_to_text:
            channel_id = self.voice_to_text[voice_channel.id]
            channel = voice_channel.guild.get_channel(channel_id)
            if channel is not None:
                return channel
            else:
                del self.voice_to_text[voice_channel.id]

        category = voice_channel.category
        overwrites = {
            voice_channel.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        }
        for member in voice_channel.members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            channel_name = f"{TEXT_CHANNEL_NAME}-{voice_channel.name}"
            if len(channel_name) > 100:
                channel_name = channel_name[:100]
            text_channel = await voice_channel.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason="Автоматическое создание для временного войс-чата"
            )
            self.voice_to_text[voice_channel.id] = text_channel.id
            print(f"Создан текстовый канал {text_channel.name} для войс-канала {voice_channel.name}")
            return text_channel
        except Exception as e:
            print(f"Ошибка при создании текстового канала: {e}")
            return None

    async def delete_text_channel(self, voice_channel: discord.VoiceChannel):
        if voice_channel.id not in self.voice_to_text:
            return
        channel_id = self.voice_to_text[voice_channel.id]
        text_channel = voice_channel.guild.get_channel(channel_id)
        if text_channel is not None:
            try:
                await text_channel.delete(reason="Войс-канал опустел")
                print(f"Удалён текстовый канал {text_channel.name}")
            except Exception as e:
                print(f"Ошибка при удалении текстового канала: {e}")
        del self.voice_to_text[voice_channel.id]

    async def update_member_permissions(self, voice_channel: discord.VoiceChannel, member: discord.Member, add: bool):
        if voice_channel.id not in self.voice_to_text:
            return
        channel_id = self.voice_to_text[voice_channel.id]
        text_channel = voice_channel.guild.get_channel(channel_id)
        if text_channel is None:
            del self.voice_to_text[voice_channel.id]
            return

        try:
            if add:
                await text_channel.set_permissions(member, read_messages=True, send_messages=True)
                print(f"Добавлен доступ для {member.display_name} к {text_channel.name}")
            else:
                await text_channel.set_permissions(member, overwrite=None)
                print(f"Убран доступ для {member.display_name} к {text_channel.name}")
        except Exception as e:
            print(f"Ошибка при изменении прав {member} в канале {text_channel.name}: {e}")

    @app_commands.command(name="setup", description="Установить голосовой канал для создания временных текстовых каналов")
    @app_commands.describe(channel="Голосовой канал, который будет отслеживаться")
    async def setup(self, interaction: discord.Interaction, channel: discord.VoiceChannel):

        self.guild_settings[interaction.guild_id] = channel.id
        await interaction.response.send_message(
            f"✅ Целевой голосовой канал установлен: {channel.mention}\n"
            f"Теперь при входе пользователей в {channel.mention} будет создаваться временный текстовый канал.",
            ephemeral=True
        )
        print(f"Сервер {interaction.guild.name} (ID: {interaction.guild_id}) настроен на канал {channel.name} (ID: {channel.id})")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        target_id = await self.get_target_channel(member.guild)
        if not target_id:
            return

        if after.channel and after.channel.id == target_id:
            if before.channel != after.channel:
                text_channel = await self.ensure_text_channel(after.channel)
                if text_channel:
                    await self.update_member_permissions(after.channel, member, add=True)

        if before.channel and before.channel.id == target_id:
            if after.channel != before.channel:
                await self.update_member_permissions(before.channel, member, add=False)
                if len(before.channel.members) == 0:
                    await self.delete_text_channel(before.channel)

async def setup(bot):
    await bot.add_cog(TempVoiceChannels(bot))