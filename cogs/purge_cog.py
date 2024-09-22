import discord
from discord.ext import commands

class PurgeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='purge_all_channels')
    @commands.has_permissions(administrator=True)
    async def purge_all_channels(self, ctx):
        """Deletes all channels in the server."""
        guild = ctx.guild
        await ctx.send("Purging all channels...")

        # Delete all channels
        for channel in guild.channels:
            try:
                await channel.delete()
            except discord.Forbidden:
                await ctx.send(f"Failed to delete {channel.name}: Missing permissions.")
            except discord.HTTPException as e:
                await ctx.send(f"Failed to delete {channel.name}: {e}")

        await ctx.send("All channels have been purged.")

async def setup(bot):
    await bot.add_cog(PurgeCog(bot))
