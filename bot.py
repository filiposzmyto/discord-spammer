import asyncio
import json
import logging
import os
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = Path("config.json")
ROOM_MARKER = "discord-spammer-managed-v1"
DEFAULT_CONFIG = {
    "allowed_user_ids": [],
    "allowed_role_ids": [],
    "private_user_ids": [],
    "private_role_ids": [],
    "mention_user_ids": [],
    "mention_role_ids": [],
    "spam_category_name": "spam-room",
    "spam_channel_prefix": "spam",
    "spam_channel_count": 5,
    "spam_message": "Hej {mentions}!",
    "max_batches": 20,
    "interval_seconds": 0.5,
}


def load_config():
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    with CONFIG_FILE.open("r", encoding="utf-8") as config_file:
        loaded = json.load(config_file)
    return {**DEFAULT_CONFIG, **loaded}


def id_set(config, key):
    return {int(value) for value in config.get(key, [])}


config = load_config()
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("Brakuje sekretu DISCORD_BOT_TOKEN.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
room_lock = asyncio.Lock()
spam_task = None


def refresh_config():
    global config
    config = load_config()


def allowed_to_control(interaction):
    allowed_users = id_set(config, "allowed_user_ids")
    allowed_roles = id_set(config, "allowed_role_ids")
    if interaction.user.id in allowed_users:
        return True
    if interaction.guild and any(role.id in allowed_roles for role in interaction.user.roles):
        return True
    return bool(interaction.guild and interaction.user.guild_permissions.manage_guild)


def selected_targets(guild, users, roles):
    user_ids = [member.id for member in users if member]
    role_ids = [role.id for role in roles if role]
    if not user_ids:
        user_ids = list(id_set(config, "private_user_ids") or id_set(config, "mention_user_ids"))
    if not role_ids:
        role_ids = list(id_set(config, "private_role_ids") or id_set(config, "mention_role_ids"))
    return user_ids, role_ids


async def resolve_visibility_overwrites(guild, user_ids, role_ids):
    bot_member = guild.me or await guild.fetch_member(bot.user.id)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        bot_member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
        ),
    }
    members = []
    for user_id in user_ids:
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound as error:
                raise ValueError(f"Nie znaleziono osoby `{user_id}` na tym serwerze.") from error
        members.append(member)
        overwrites[member] = discord.PermissionOverwrite(view_channel=True)

    selected_roles = []
    for role_id in role_ids:
        role = guild.get_role(role_id)
        if role is None:
            raise ValueError(f"Nie znaleziono roli `{role_id}` na tym serwerze.")
        selected_roles.append(role)
        overwrites[role] = discord.PermissionOverwrite(view_channel=True)

    if any(not role.mentionable for role in selected_roles) and not bot_member.guild_permissions.mention_everyone:
        raise ValueError("Bot potrzebuje Mention Everyone, aby oznaczać niewzmiankowalne role.")

    return overwrites, members, selected_roles


async def create_private_room(guild, user_ids, role_ids):
    overwrites, members, roles = await resolve_visibility_overwrites(guild, user_ids, role_ids)
    category = None
    channels = []
    category_name = str(config["spam_category_name"])[:100]
    channel_prefix = str(config["spam_channel_prefix"])[:90]
    channel_count = max(1, min(int(config["spam_channel_count"]), 5))
    try:
        category = await guild.create_category(
            name=category_name,
            overwrites=overwrites,
            reason="Private spam room requested by a moderator",
        )
        for index in range(1, channel_count + 1):
            channels.append(
                await guild.create_text_channel(
                    name=f"{channel_prefix}-{index}",
                    category=category,
                    overwrites=overwrites,
                    topic=ROOM_MARKER,
                    reason="Private spam room channel",
                )
            )
    except Exception:
        for channel in reversed(channels):
            await channel.delete(reason="Cleaning up incomplete private spam room")
        if category:
            await category.delete(reason="Cleaning up incomplete private spam room")
        raise
    return category, channels, members, roles


async def stop_active_spam():
    global spam_task
    task = spam_task
    if not task or task.done():
        return False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    return True


async def cleanup_managed_rooms(guild):
    await stop_active_spam()
    deleted_channels = 0
    deleted_categories = 0
    preserved_categories = 0

    for category in list(guild.categories):
        managed_channels = [
            channel
            for channel in category.channels
            if isinstance(channel, discord.TextChannel) and channel.topic == ROOM_MARKER
        ]
        if not managed_channels:
            continue

        managed_ids = {channel.id for channel in managed_channels}
        failed_channel_ids = set()
        for channel in managed_channels:
            try:
                await channel.delete(reason="Cleaning up a managed spam room")
                deleted_channels += 1
            except (discord.Forbidden, discord.HTTPException) as error:
                failed_channel_ids.add(channel.id)
                logging.error("Nie udało się usunąć kanału %s: %s", channel.id, error)

        remaining_channels = [channel for channel in category.channels if channel.id not in managed_ids]
        if not remaining_channels and not failed_channel_ids:
            try:
                await category.delete(reason="Cleaning up an empty managed spam category")
                deleted_categories += 1
            except (discord.Forbidden, discord.HTTPException) as error:
                logging.error("Nie udało się usunąć kategorii %s: %s", category.id, error)
        else:
            preserved_categories += 1

    return deleted_channels, deleted_categories, preserved_categories


def build_message(template, members, roles):
    mentions = " ".join([member.mention for member in members] + [role.mention for role in roles])
    message = template.replace("{mentions}", mentions).strip()
    if "{mentions}" not in template and mentions:
        message = f"{message} {mentions}".strip()
    return message or mentions or "Wiadomość testowa."


async def send_batches(channels, content, allowed_mentions):
    global spam_task
    try:
        max_batches = max(1, min(int(config["max_batches"]), 20))
        interval = max(0.5, float(config["interval_seconds"]))
        for batch in range(max_batches):
            await asyncio.gather(
                *(channel.send(content, allowed_mentions=allowed_mentions) for channel in channels)
            )
            if batch + 1 < max_batches:
                await asyncio.sleep(interval)
        logging.info("Spam zakończony po osiągnięciu limitu wiadomości.")
    except asyncio.CancelledError:
        logging.info("Spam zatrzymany przez /spam off.")
        raise
    except (discord.Forbidden, discord.HTTPException) as error:
        logging.error("Nie udało się wysłać wiadomości: %s", error)
    finally:
        spam_task = None


@bot.event
async def on_ready():
    logging.info("Zalogowano jako %s (ID: %s)", bot.user, bot.user.id)
    synced = await tree.sync()
    logging.info("Zsynchronizowano %s komend slash.", len(synced))


@tree.command(name="spam", description="Włącz lub wyłącz prywatny pokój wiadomości")
@app_commands.describe(
    action="on = utwórz kanały, off = zatrzymaj, cleanup = posprzątaj",
    message="Treść wiadomości; {mentions} zostanie zastąpione wybranymi wzmiankami",
    user="Osoba, która ma widzieć kanały i być oznaczona",
    user2="Druga osoba, która ma widzieć kanały i być oznaczona",
    role="Rola, która ma widzieć kanały i być oznaczona",
    role2="Druga rola, która ma widzieć kanały i być oznaczona",
)
@app_commands.choices(
    action=[
        app_commands.Choice(name="On", value="on"),
        app_commands.Choice(name="Off", value="off"),
        app_commands.Choice(name="Cleanup", value="cleanup"),
    ]
)
async def spam_command(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    message: str | None = None,
    user: discord.Member | None = None,
    user2: discord.Member | None = None,
    role: discord.Role | None = None,
    role2: discord.Role | None = None,
):
    if not interaction.guild:
        await interaction.response.send_message("Ta komenda działa tylko na serwerze.", ephemeral=True)
        return
    if not allowed_to_control(interaction):
        await interaction.response.send_message("Nie masz uprawnień do używania tej komendy.", ephemeral=True)
        return

    global spam_task
    if action.value == "off":
        if spam_task and not spam_task.done():
            await stop_active_spam()
            await interaction.response.send_message("🛑 Spam wyłączony. Kategoria i historia kanałów zostały zachowane.", ephemeral=True)
        else:
            await interaction.response.send_message("Spam jest już wyłączony.", ephemeral=True)
        return

    bot_member = interaction.guild.me
    if action.value == "cleanup":
        if not bot_member or not bot_member.guild_permissions.manage_channels:
            await interaction.response.send_message("Bot potrzebuje uprawnienia Manage Channels do sprzątania.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            async with room_lock:
                deleted_channels, deleted_categories, preserved_categories = await cleanup_managed_rooms(
                    interaction.guild
                )
            preserved_note = (
                f" Zachowano {preserved_categories} kategorii z innymi kanałami."
                if preserved_categories
                else ""
            )
            await interaction.edit_original_response(
                content=(
                    f"🧹 Usunięto {deleted_channels} kanałów i {deleted_categories} kategorii "
                    f"utworzonych przez bota.{preserved_note}"
                )
            )
        except (discord.Forbidden, discord.HTTPException):
            await interaction.edit_original_response(
                content="❌ Discord odrzucił sprzątanie. Sprawdź uprawnienie Manage Channels."
            )
        return

    if spam_task and not spam_task.done():
        await interaction.response.send_message("Spam jest już włączony. Użyj `/spam` z opcją `Off`.", ephemeral=True)
        return

    if not bot_member or not all(
        (
            bot_member.guild_permissions.manage_channels,
            bot_member.guild_permissions.view_channel,
            bot_member.guild_permissions.send_messages,
        )
    ):
        await interaction.response.send_message(
            "Bot potrzebuje uprawnień Manage Channels, View Channels i Send Messages.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)
    try:
        async with room_lock:
            if spam_task and not spam_task.done():
                await interaction.edit_original_response(content="Spam został włączony przez inną osobę.")
                return
            user_ids, role_ids = selected_targets(
                interaction.guild,
                [user, user2],
                [role, role2],
            )
            if not user_ids and not role_ids:
                raise ValueError("Wybierz przynajmniej jedną osobę lub rolę.")

            category, channels, members, roles = await create_private_room(
                interaction.guild,
                user_ids,
                role_ids,
            )
            template = (message or config["spam_message"])[:1800]
            content = build_message(template, members, roles)
            allowed_mentions = discord.AllowedMentions(
                users=members,
                roles=roles,
                everyone=False,
                replied_user=False,
            )
            spam_task = asyncio.create_task(send_batches(channels, content, allowed_mentions))
            await interaction.edit_original_response(
                content=(
                    f"✅ Utworzono kategorię **{category.name}** i {len(channels)} prywatnych kanałów. "
                    f"Wysłano serię wiadomości. Użyj `/spam` → `Off`, aby zatrzymać."
                )
            )
    except ValueError as error:
        await interaction.edit_original_response(content=f"❌ {error}")
    except (discord.Forbidden, discord.HTTPException) as error:
        logging.error("Błąd Discord API przy tworzeniu pokoju: %s", error)
        await interaction.edit_original_response(
            content="❌ Bot nie ma wymaganych uprawnień albo Discord odrzucił tworzenie kanałów."
        )
    except Exception:
        logging.exception("Nieoczekiwany błąd komendy /spam.")
        await interaction.edit_original_response(content="❌ Wystąpił nieoczekiwany błąd. Sprawdź logi bota.")


@tree.command(name="spam_status", description="Sprawdź status prywatnego pokoju")
async def spam_status(interaction: discord.Interaction):
    if not allowed_to_control(interaction):
        await interaction.response.send_message("Brak uprawnień.", ephemeral=True)
        return
    active = bool(spam_task and not spam_task.done())
    await interaction.response.send_message(
        "Status spamu: 🟢 WŁĄCZONY" if active else "Status spamu: 🔴 WYŁĄCZONY",
        ephemeral=True,
    )


@tree.command(name="reload_config", description="Przeładuj konfigurację JSON")
async def reload_config(interaction: discord.Interaction):
    if not allowed_to_control(interaction):
        await interaction.response.send_message("Brak uprawnień.", ephemeral=True)
        return
    try:
        refresh_config()
        await interaction.response.send_message("✅ Konfiguracja przeładowana.", ephemeral=True)
    except Exception as error:
        await interaction.response.send_message(f"❌ Błąd konfiguracji: {error}", ephemeral=True)


bot.run(TOKEN)