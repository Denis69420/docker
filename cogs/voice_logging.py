import discord
from discord.ext import commands
import asyncio

class VoiceLogging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Check if the member was moved to a different channel
        if before.channel != after.channel and before.channel is not None and after.channel is not None:
            guild = member.guild

            # Increase delay to ensure audit log entry is available
            await asyncio.sleep(5)
            print(f"Checking audit log for move event of {member.name} after 10 seconds...")

            # Fetch the most recent audit log entry for member_move
            try:
                async for log_entry in guild.audit_logs(action=discord.AuditLogAction.member_move, limit=1):
                    # Directly use the last log entry, regardless of checks
                    print(f"Found audit log entry: {log_entry.action} by {log_entry.user} at {log_entry.created_at}")

                    # Create the embed with mentions
                    embed = discord.Embed(
                        title="Member Moved",
                        description=f"{member.mention} was moved by {log_entry.user.mention}.",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="From", value=before.channel.name, inline=True)
                    embed.add_field(name="To", value=after.channel.name, inline=True)

                    # Send the embed to the specified channel
                    log_channel = self.bot.get_channel(1275058058233380926)
                    if log_channel:
                        await log_channel.send(embed=embed)
                    else:
                        print("Log channel not found.")
                    return

                print("No audit log entry found.")

            except discord.Forbidden:
                print("Bot doesn't have permission to access audit logs.")
            except discord.HTTPException as e:
                print(f"Failed to fetch audit logs: {e}")

async def setup(bot):
    await bot.add_cog(VoiceLogging(bot))
