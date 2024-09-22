import discord
from discord.ext import commands

class Meeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_authorized(self, ctx):
        return ctx.author.id == ctx.guild.owner_id or ctx.author.id == 334095388141420554

    @commands.command(name='meeting', description='Move all users currently in voice channels to a specific channel')
    async def meeting(self, ctx):
        if not self.is_authorized(ctx):
            await ctx.respond("You do not have permission to use this command.", ephemeral=True)
            return

        target_channel_id = 1103075031635996728
        target_channel = self.bot.get_channel(target_channel_id)

        if not isinstance(target_channel, discord.VoiceChannel):
            await ctx.respond("The target channel is not a voice channel.", ephemeral=True)
            return

        moved_count = 0
        for vc in ctx.guild.voice_channels:
            for member in vc.members:
                await member.move_to(target_channel)
                moved_count += 1

        await ctx.respond(f"Moved {moved_count} user(s) to the meeting channel.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Meeting(bot))
