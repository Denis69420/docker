import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

# Ensure ffmpeg is in your PATH
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # Bind to IPv4 since IPv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_player = None
        self.queue = asyncio.Queue()
        self.history = []

    @commands.command(name='join', help='Bot joins the voice channel')
    async def join(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send(f"{ctx.message.author.name} is not connected to a voice channel")
            return
        else:
            channel = ctx.message.author.voice.channel
        
        await channel.connect()

    @commands.command(name='leave', help='Bot leaves the voice channel')
    async def leave(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_connected():
            await voice_client.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    @commands.command(name='play', help='Play audio from a YouTube URL')
    async def play(self, ctx, url):
        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
        
        if ctx.voice_client.is_playing():
            await self.queue.put(player)
            await ctx.send(f'Queued: {player.title}')
        else:
            ctx.voice_client.play(player, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next, ctx))
            self.current_player = player
            self.history.append(player)
            await ctx.send(f'Now playing: {player.title}', view=MusicControls(self))

    def play_next(self, ctx):
        if not self.queue.empty():
            next_player = self.queue.get_nowait()
            ctx.voice_client.play(next_player, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next, ctx))
            self.current_player = next_player
            self.history.append(next_player)

    @commands.command(name='pause', help='Pauses the audio')
    async def pause(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
        else:
            await ctx.send("The bot is not playing anything at the moment.")

    @commands.command(name='resume', help='Resumes the audio')
    async def resume(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()
        else:
            await ctx.send("The bot was not playing anything before this. Use the play command")

    @commands.command(name='stop', help='Stops the audio')
    async def stop(self, ctx):
        voice_client = ctx.message.guild.voice_client
        if voice_client.is_playing():
            voice_client.stop()
        else:
            await ctx.send("The bot is not playing anything at the moment.")

    @commands.command(name='volume', help='Changes the volume of the player')
    async def volume(self, ctx, volume: int):
        if self.current_player is not None:
            self.current_player.volume = volume / 100
            await ctx.send(f'Changed volume to {volume}%')
        else:
            await ctx.send("No audio is playing at the moment.")

    @commands.command(name='queue', help='Displays the current queue')
    async def queue_(self, ctx):
        if self.queue.empty():
            await ctx.send("The queue is currently empty.")
        else:
            queue_list = [f"{index + 1}. {player.title}" for index, player in enumerate(self.queue._queue)]
            await ctx.send("\n".join(queue_list))

    @commands.command(name='next', help='Skips to the next song in the queue')
    async def next(self, ctx):
        ctx.voice_client.stop()
        await ctx.send("Skipped to the next song.")

    @commands.command(name='previous', help='Plays the previous song')
    async def previous(self, ctx):
        if len(self.history) > 1:
            self.history.pop()  # Remove current song from history
            previous_player = self.history.pop()
            ctx.voice_client.stop()
            ctx.voice_client.play(previous_player, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next, ctx))
            self.current_player = previous_player
            self.history.append(previous_player)
            await ctx.send(f'Now playing: {previous_player.title}')
        else:
            await ctx.send("No previous song in history.")

class MusicControls(discord.ui.View):
    def __init__(self, cog: Voice):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.pause(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.success)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.resume(interaction)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.stop(interaction)

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.previous(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.next(interaction)  

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.secondary)
    async def volume_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog.current_player is not None:
            new_volume = max(self.cog.current_player.volume - 0.1, 0.0)
            self.cog.current_player.volume = new_volume
            await interaction.response.send_message(f'Volume set to {int(new_volume * 100)}%', ephemeral=True)
        else:
            await interaction.response.send_message("No audio is playing at the moment.", ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.secondary)
    async def volume_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog.current_player is not None:
            new_volume = min(self.cog.current_player.volume + 0.1, 1.0)
            self.cog.current_player.volume = new_volume
            await interaction.response.send_message(f'Volume set to {int(new_volume * 100)}%', ephemeral=True)
        else:
            await interaction.response.send_message("No audio is playing at the moment.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Voice(bot))
