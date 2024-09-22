import discord
from discord.ext import commands
import mysql.connector
import os
import certifi

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        return mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            database=os.getenv('DB_NAME'),
            ssl_ca=certifi.where()
        )

    def get_channel_id(self, guild_id, setting_name):
        db = self.get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT setting_value FROM config WHERE guild_id = %s AND setting_name = %s", (guild_id, setting_name))
        result = cursor.fetchone()
        cursor.close()
        db.close()
        return int(result['setting_value']) if result else None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel_id = self.get_channel_id(member.guild.id, 'welcome_channel_id')
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="Welcome!",
                    description=f"Welcome to the server, {member.mention}!",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url=member.avatar_url)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel_id = self.get_channel_id(member.guild.id, 'leave_channel_id')
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="Goodbye!",
                    description=f"{member.mention} has left the server.",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.avatar_url)
                await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
