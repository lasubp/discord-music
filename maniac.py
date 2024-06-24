import discord
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv

def run_bot():
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve the bot token from environment variables
    TOKEN = os.getenv('discord_token')

    # Check if the token is valid
    if TOKEN is None:
        print("Error: Bot token not found in environment variables.")
        exit()

    # Bot setup
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    voice_clients = {}
    yt_dl_options = {
        "format": "bestaudio/best",
        "noplaylist": True,
    }
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.25"'
    }

    @client.event
    async def on_ready():
        print(f'{client.user} is now jamming')

    @client.event
    async def on_message(message):
        if message.content.startswith("?play"):
            if message.author.voice is None or message.author.voice.channel is None:
                await message.channel.send("You are not connected to a voice channel.")
                return

            channel = message.author.voice.channel
            guild_id = message.guild.id

            if guild_id not in voice_clients or voice_clients[guild_id] is None or not voice_clients[guild_id].is_connected():
                voice_client = await channel.connect()
                voice_clients[guild_id] = voice_client
            else:
                voice_client = voice_clients[guild_id]
                await voice_client.move_to(channel)

            try:
                url = message.content.split()[1]
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

                song = data['url']

                # exit arter playing song
                def after_playing(error):
                    coro = voice_client.disconnect()
                    fut = asyncio.run_coroutine_threadsafe(coro, client.loop)
                    try:
                        fut.result()
                    except Exception as e:
                        print(e)

                player = discord.FFmpegPCMAudio(song, **ffmpeg_options)
                voice_client.play(player, after=after_playing)
                await message.channel.send(f"Now playing: {data['title']}")
            except Exception as e:
                print(e)
                await message.channel.send("An error occurred while trying to play the audio.")

        elif message.content.startswith("?pause"):
            try:
                voice_clients[message.guild.id].pause()
            except Exception as e:
                print(e)

        elif message.content.startswith("?resume"):
            try:
                voice_clients[message.guild.id].resume()
            except Exception as e:
                print(e)

        elif message.content.startswith("?stop"):
            try:
                voice_clients[message.guild.id].stop()
                await voice_clients[message.guild.id].disconnect()
                voice_clients[message.guild.id] = None
            except Exception as e:
                print(e)

    client.run(TOKEN)