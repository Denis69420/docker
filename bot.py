import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import certifi
import mysql.connector
import requests

from cogs.ticket import TicketView, PersistentSelect

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

os.environ['SSL_CERT_FILE'] = certifi.where()

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='/', intents=intents)

def get_db_connection():
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        database=os.getenv('DB_NAME'),
        ssl_ca=certifi.where()
    )
    return connection

def ensure_config_table_exists():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS config (
        id INT AUTO_INCREMENT PRIMARY KEY,
        guild_id BIGINT NOT NULL,
        setting_name VARCHAR(255) NOT NULL,
        setting_value VARCHAR(255) NOT NULL,
        UNIQUE KEY (guild_id, setting_name)
    ) ENGINE=InnoDB;
    """)
    db.commit()
    cursor.close()
    db.close()

def get_guild_config(guild_id):
    ensure_config_table_exists()  # Ensure the table exists before querying it
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT setting_name, setting_value FROM config WHERE guild_id = %s", (guild_id,))
    config = {row['setting_name']: row['setting_value'] for row in cursor.fetchall()}
    cursor.close()
    db.close()
    return config

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.load_extension('cogs.voice')
    await bot.load_extension('cogs.voice_logging')
    await bot.load_extension('cogs.meeting')  # Load the new meeting cog
    
    view = discord.ui.View(timeout=None)
    view.add_item(PersistentSelect(bot, [], 'Wähle ein Anliegen aus'))
    bot.add_view(view)
    
    print('Cogs loaded.')
    print('Database updated with guild information.')
    update_guild_configs.start()


@tasks.loop(minutes=5)  # Periodically check for updates
async def update_guild_configs():
    for guild in bot.guilds:
        config = get_guild_config(guild.id)
        # Apply your configuration settings as needed
        # For example, you could update prefix, channels, roles, etc.

@bot.event
async def on_guild_join(guild):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("INSERT INTO guilds (id, name) VALUES (%s, %s)", (guild.id, guild.name))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

@bot.event
async def on_guild_remove(guild):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("DELETE FROM guilds WHERE id = %s", (guild.id,))
        cursor.execute("DELETE FROM config WHERE guild_id = %s", (guild.id,))
        db.commit()
        cursor.close()
        db.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")

def get_detailed_guild_info(guild_id):
    token = os.getenv('DISCORD_TOKEN')
    url = f"https://discord.com/api/v10/guilds/{guild_id}"

    headers = {
        "Authorization": f"Bot {token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        guild = response.json()
        icon_url = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png" if guild['icon'] else "https://cdn.discordapp.com/embed/avatars/0.png"
        return {
            "id": guild['id'],
            "name": guild['name'],
            "icon_url": icon_url
        }
    else:
        print(f"Failed to fetch guild details: {response.status_code}")
        return None

def run_bot():
    bot.run(TOKEN)
