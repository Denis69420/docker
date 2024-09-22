import os
import requests
from flask import Flask, render_template, redirect, url_for, session, request
from flask_discord import DiscordOAuth2Session, requires_authorization, Unauthorized
from dotenv import load_dotenv
import certifi
import mysql.connector
import concurrent.futures

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='/static')

app.secret_key = os.getenv("SECRET_KEY")
app.config["DISCORD_CLIENT_ID"] = os.getenv("DISCORD_CLIENT_ID")
app.config["DISCORD_CLIENT_SECRET"] = os.getenv("DISCORD_CLIENT_SECRET")
app.config["DISCORD_REDIRECT_URI"] = os.getenv("DISCORD_REDIRECT_URI")
app.config["DISCORD_SCOPES"] = ["identify", "guilds"]

discord_oauth = DiscordOAuth2Session(app)

from bot import run_bot, get_detailed_guild_info

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        database=os.getenv('DB_NAME'),
        ssl_ca=certifi.where()
    )

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login/")
def login():
    return discord_oauth.create_session(scope=app.config["DISCORD_SCOPES"])

@app.route("/callback/")
def callback():
    discord_oauth.callback()
    return redirect(url_for("index"))

@app.route("/logout/")
def logout():
    discord_oauth.revoke()
    return redirect(url_for("home"))

@app.errorhandler(Unauthorized)
def redirect_unauthorized(e):
    return redirect(url_for("login"))

@app.route('/index')
@requires_authorization
def index():
    user_guilds = discord_oauth.fetch_guilds()
    admin_guilds = []

    for guild in user_guilds:
        guild_dict = vars(guild)
        permissions = guild_dict['permissions'].value
        if permissions & 0x8:  # Check if the user has admin permissions (ADMINISTRATOR permission bit is 0x8)
            detailed_guild = get_detailed_guild_info(guild_dict['id'])
            if detailed_guild:
                print(f"Guild: {detailed_guild['name']}, Icon URL: {detailed_guild['icon_url']}")  # Print icon URLs for debugging
                admin_guilds.append({
                    "id": detailed_guild["id"],
                    "name": detailed_guild["name"],
                    "icon_url": detailed_guild["icon_url"],
                    "role": "Bot Master"
                })

    return render_template('index.html', guilds=admin_guilds)

@app.route('/config/<int:guild_id>', methods=['GET', 'POST'])
@requires_authorization
def config(guild_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        setting_name = request.form['settingName']
        setting_value = request.form['settingValue']
        cursor.execute("INSERT INTO config (guild_id, setting_name, setting_value) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE setting_value = %s", (guild_id, setting_name, setting_value, setting_value))
        db.commit()
        return redirect(url_for('config', guild_id=guild_id))

    cursor.execute("SELECT * FROM config WHERE guild_id = %s", (guild_id,))
    settings = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('config.html', guild_id=guild_id, settings=settings)

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(run_bot)
        executor.submit(app.run, host='0.0.0.0', port=443, ssl_context=('certs/toxicnet.org_ssl_certificate (1).cer', 'certs/_.toxicnet.org_private_key.key'))
