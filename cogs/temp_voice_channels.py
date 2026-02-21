import discord
from discord.ext import commands
from discord import app_commands
import logging

TEXT_CHANNEL_NAME = "чат-войса"

logger = logging.getLogger(__name__)

class TempVoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_to_text = {}
        self.guild_settings = {}

    async def cog_load(self):
        await self.restore_state()

    async def restore_state(self):
        logger.info("Восстановление состояния временных текстовых каналов...")
        for guild in self.bot.guilds:
            target_id = self.guild_settings.get(guild.id)
            if not target_id:
                continue
            target_channel = guild.get_channel(target_id)
            if not target_channel or not isinstance(target_channel, discord.VoiceChannel):
                continue

            expected_name_prefix = f"{TEXT_CHANNEL_NAME}-{target_channel.name}"
            for text_channel in guild.text_channels:
                if text_channel.name.startswith(expected_name_prefix):
                    self.voice_to_text[target_channel.id] = text_channel.id
                    logger.info(f"Восстановлена связь: {target_channel.name} -> {text_channel.name}")
                    break
        logger.info("Восстановление завершено.")

    async def get_target_channel(self, guild: discord.Guild) -> int | None:
        return self.guild_settings.get(guild.id)

    async def ensure_text_channel(self, voice_channel: discord.VoiceChannel) -> discord.TextChannel | None:
        if voice_channel.id in self.voice_to_text:
            channel_id = self.voice_to_text[voice_channel.id]
            text_channel = voice_channel.guild.get_channel(channel_id)
            if text_channel is not None:
                return text_channel
            else:
                del self.voice_to_text[voice_channel.id]

        if not voice_channel.guild.me.guild_permissions.manage_channels:
            logger.error(f"Нет прав manage_channels на сервере {voice_channel.guild.name}")
            return None

        category = voice_channel.category
        overwrites = {
            voice_channel.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        }
        for member in voice_channel.members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel_name = f"{TEXT_CHANNEL_NAME}-{voice_channel.name}"
        if len(channel_name) > 100:
            channel_name = channel_name[:100]

        try:
            text_channel = await voice_channel.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                reason="Автоматическое создание для временного войс-чата"
            )
            self.voice_to_text[voice_channel.id] = text_channel.id
            logger.info(f"Создан текстовый канал {text_channel.name} для войс-канала {voice_channel.name}")
            return text_channel
        except Exception as e:
            logger.exception(f"Ошибка при создании текстового канала для {voice_channel.name}: {e}")
            return None

    async def delete_text_channel(self, voice_channel: discord.VoiceChannel):
        if voice_channel.id not in self.voice_to_text:
            return
        channel_id = self.voice_to_text[voice_channel.id]
        text_channel = voice_channel.guild.get_channel(channel_id)
        if text_channel is not None:
            try:
                await text_channel.delete(reason="Войс-канал опустел")
                logger.info(f"Удалён текстовый канал {text_channel.name}")
            except Exception as e:
                logger.exception(f"Ошибка при удалении текстового канала {text_channel.name}: {e}")
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
                logger.info(f"Добавлен доступ для {member.display_name} к {text_channel.name}")
            else:
                await text_channel.set_permissions(member, overwrite=None)
                logger.info(f"Убран доступ для {member.display_name} к {text_channel.name}")
        except Exception as e:
            logger.exception(f"Ошибка при изменении прав {member} в канале {text_channel.name}: {e}")

    @app_commands.command(name="setup", description="Установить голосовой канал для создания временных текстовых каналов")
    @app_commands.describe(channel="Голосовой канал, который будет отслеживаться")
    async def setup(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        self.guild_settings[interaction.guild_id] = channel.id
        await interaction.response.send_message(
            f"✅ Целевой голосовой канал установлен: {channel.mention}\n"
            f"Теперь при входе пользователей в {channel.mention} будет создаваться временный текстовый канал.",
            ephemeral=True
        )
        logger.info(f"Сервер {interaction.guild.name} (ID: {interaction.guild_id}) настроен на канал {channel.name} (ID: {channel.id})")

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