import discord
from discord import app_commands
from discord.ext import commands, tasks
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ====================== KONFIGURACJA ======================
CONFIG_FILE = "config.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

TOKEN = os.getenv("DISCORD_TOKEN")
SPAM_CHANNEL_ID = config["spam_channel_id"]
ALLOWED_USER_IDS = set(config.get("allowed_user_ids", []))
ALLOWED_ROLE_IDS = set(config.get("allowed_role_ids", []))
MENTION_USER_IDS = config.get("mention_user_ids", [])
MENTION_ROLE_IDS = config.get("mention_role_ids", [])
SPAM_MESSAGE = config.get("spam_message", "Spam {mentions}")

# ==========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # potrzebne do ról

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

spam_active = False


def is_allowed(interaction: discord.Interaction) -> bool:
    """Sprawdza czy użytkownik może używać komend /spam"""
    if interaction.user.id in ALLOWED_USER_IDS:
        return True
    if interaction.guild:
        user_roles = {role.id for role in interaction.user.roles}
        if user_roles & ALLOWED_ROLE_IDS:
            return True
    return False


def build_mentions() -> str:
    """Buduje string z @mentionami"""
    mentions = []
    for uid in MENTION_USER_IDS:
        mentions.append(f"<@{uid}>")
    for rid in MENTION_ROLE_IDS:
        mentions.append(f"<@&{rid}>")
    return " ".join(mentions) if mentions else ""


@tasks.loop(seconds=0.5)
async def spam_task():
    if not spam_active:
        return

    channel = bot.get_channel(SPAM_CHANNEL_ID)
    if channel is None:
        print(f"[BŁĄD] Nie znaleziono kanału o ID {SPAM_CHANNEL_ID}")
        return

    mentions = build_mentions()
    content = SPAM_MESSAGE.replace("{mentions}", mentions)

    try:
        await channel.send(content)
    except discord.Forbidden:
        print("[BŁĄD] Bot nie ma uprawnień do wysyłania wiadomości na ten kanał")
    except Exception as e:
        print(f"[BŁĄD] {e}")


@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend slash")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")

    if not spam_task.is_running():
        spam_task.start()


@tree.command(name="spam", description="Włącz lub wyłącz spam")
@app_commands.describe(action="on = włącz, off = wyłącz")
@app_commands.choices(action=[
    app_commands.Choice(name="on", value="on"),
    app_commands.Choice(name="off", value="off"),
])
async def spam_command(interaction: discord.Interaction, action: app_commands.Choice[str]):
    if not is_allowed(interaction):
        await interaction.response.send_message(
            "❌ Nie masz uprawnień do używania tej komendy.",
            ephemeral=True
        )
        return

    global spam_active

    if action.value == "on":
        if spam_active:
            await interaction.response.send_message("⚠️ Spam jest już włączony.", ephemeral=True)
            return
        spam_active = True
        await interaction.response.send_message("✅ Spam **włączony** (co 0.5 s).", ephemeral=True)
        print(f"[SPAM] Włączony przez {interaction.user}")

    elif action.value == "off":
        if not spam_active:
            await interaction.response.send_message("⚠️ Spam jest już wyłączony.", ephemeral=True)
            return
        spam_active = False
        await interaction.response.send_message("🛑 Spam **wyłączony**.", ephemeral=True)
        print(f"[SPAM] Wyłączony przez {interaction.user}")


@tree.command(name="spam_status", description="Sprawdź status spamu")
async def spam_status(interaction: discord.Interaction):
    if not is_allowed(interaction):
        await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
        return

    status = "🟢 **WŁĄCZONY**" if spam_active else "🔴 **WYŁĄCZONY**"
    await interaction.response.send_message(f"Status spamu: {status}", ephemeral=True)


# Opcjonalnie: komenda do przeładowania configu bez restartu
@tree.command(name="reload_config", description="Przeładuj config.json")
async def reload_config(interaction: discord.Interaction):
    if not is_allowed(interaction):
        await interaction.response.send_message("❌ Brak uprawnień.", ephemeral=True)
        return

    global config, SPAM_CHANNEL_ID, ALLOWED_USER_IDS, ALLOWED_ROLE_IDS
    global MENTION_USER_IDS, MENTION_ROLE_IDS, SPAM_MESSAGE

    try:
        config = load_config()
        SPAM_CHANNEL_ID = config["spam_channel_id"]
        ALLOWED_USER_IDS = set(config.get("allowed_user_ids", []))
        ALLOWED_ROLE_IDS = set(config.get("allowed_role_ids", []))
        MENTION_USER_IDS = config.get("mention_user_ids", [])
        MENTION_ROLE_IDS = config.get("mention_role_ids", [])
        SPAM_MESSAGE = config.get("spam_message", "Spam {mentions}")
        await interaction.response.send_message("✅ Config przeładowany.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Błąd: {e}", ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)
