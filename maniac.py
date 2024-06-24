import discord
from discord.ext import commands
from discord import app_commands
import os
import yt_dlp
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the bot token from environment variables
TOKEN = os.getenv('discord_token')

# Ensure the token is valid
if TOKEN is None:
    print("Error: Bot token not found in environment variables.")
    exit()

# Set up the bot with appropriate intents
intents = discord.Intents.default()
intents.message_content = True

# Create the bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

# Define yt-dlp options
yt_dl_options = {
    "format": "bestaudio",
    "extract_flat": "in_playlist",
    "noplaylist": False,
}
ytdl = yt_dlp.YoutubeDL(yt_dl_options)

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=0.25"'
}

voice_clients = {}
queues = {}

@bot.event
async def on_ready():
    await bot.tree.sync()  # Sync the slash commands with Discord
    print(f'{bot.user} is now connected and ready to use!')

@bot.tree.command(name="play", description="Play a song or playlist from a URL")
async def play(interaction: discord.Interaction, url: str):
    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message("You are not connected to a voice channel.")
        return

    channel = interaction.user.voice.channel
    guild_id = interaction.guild.id

    if guild_id not in voice_clients or voice_clients[guild_id] is None or not voice_clients[guild_id].is_connected():
        voice_client = await channel.connect()
        voice_clients[guild_id] = voice_client
    else:
        voice_client = voice_clients[guild_id]
        await voice_client.move_to(channel)

    await interaction.response.defer()  # Defer the response to give the bot more time to process

    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:  # Playlist
            queues[guild_id] = data['entries']  # Queue the entire playlist
            await play_next_song(guild_id, voice_client, interaction)
        else:  # Single video
            queues[guild_id] = []
            await play_song(interaction, voice_client, data, guild_id)
    except Exception as e:
        print(e)
        await interaction.followup.send("An error occurred while trying to play the audio.")

async def play_song(interaction, voice_client, song, guild_id):
    song_url = song['url']
    player = discord.FFmpegPCMAudio(song_url, **ffmpeg_options)

    def after_playing(error):
        coro = play_next_song(guild_id, voice_client, None)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(e)

    voice_client.play(player, after=after_playing)
    if interaction:
        await interaction.followup.send(f"Now playing: {song['title']}")

async def play_next_song(guild_id, voice_client, interaction):
    if guild_id in queues and queues[guild_id]:
        next_entry = queues[guild_id].pop(0)
        if isinstance(next_entry, dict):
            url = next_entry['url']
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            await play_song(interaction, voice_client, data, guild_id)
        else:
            await voice_client.disconnect()
            del voice_clients[guild_id]
    else:
        await voice_client.disconnect()
        del voice_clients[guild_id]

@bot.tree.command(name="pause", description="Pause the current song")
async def pause(interaction: discord.Interaction):
    try:
        voice_clients[interaction.guild.id].pause()
        await interaction.response.send_message("Paused the song.")
    except Exception as e:
        print(e)
        await interaction.response.send_message("An error occurred while trying to pause the audio.")

@bot.tree.command(name="resume", description="Resume the current song")
async def resume(interaction: discord.Interaction):
    try:
        voice_clients[interaction.guild.id].resume()
        await interaction.response.send_message("Resumed the song.")
    except Exception as e:
        print(e)
        await interaction.response.send_message("An error occurred while trying to resume the audio.")

@bot.tree.command(name="stop", description="Stop the current song and disconnect")
async def stop(interaction: discord.Interaction):
    try:
        voice_clients[interaction.guild.id].stop()
        await voice_clients[interaction.guild.id].disconnect()
        voice_clients[interaction.guild.id] = None
        queues[interaction.guild.id] = []
        await interaction.response.send_message("Stopped the song and disconnected.")
    except Exception as e:
        print(e)
        await interaction.response.send_message("An error occurred while trying to stop the audio.")

# Run the bot
bot.run(TOKEN)
