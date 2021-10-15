from __future__ import unicode_literals
print('Loading libraries')
import time
print('Imported time')
start = time.time()
import asyncio
print(f'Imported asyncio - Took {time.time() - start}s')
start = time.time()
import datetime
print(f'Imported datetime - Took {time.time() - start}s')
start = time.time()
import json
print(f'Imported json - Took {time.time() - start}s')
start = time.time()
from os import remove
print(f'Imported os - Took {time.time() - start}s')
start = time.time()
import random
print(f'Imported random - Took {time.time() - start}s')
start = time.time()
from cv2 import imwrite, imread
print(f'Imported cv2 - Took {time.time() - start}s')
start = time.time()
import discord
print(f'Imported discord - Took {time.time() - start}s')
start = time.time()
import mcstatus
print(f'Imported mcstatus - Took {time.time() - start}s')
start = time.time()
from requests import get
print(f'Imported requests - Took {time.time() - start}s')
start = time.time()
import youtube_dl
print(f'Imported youtube-dl - Took {time.time() - start}s')
start = time.time()
from PIL import ImageEnhance, Image
print(f'Imported PIL - Took {time.time() - start}s')
start = time.time()
from discord.ext import commands
print(f'Imported commands - Took {time.time() - start}s')
start = time.time()
from discord_slash import SlashCommand
print(f'Imported slash-commands - Took {time.time() - start}s')
start = time.time()
from discord_slash.model import ButtonStyle
print(f'Imported ButtonStyles - Took {time.time() - start}s')
start = time.time()
from discord_components import *
print(f'Imported discord-components - Took {time.time() - start}s')
start = time.time()
import translate as tl
print(f'Imported translator - Took {time.time() - start}s')
start = time.time()
import deepfrier as dp
print(f'Imported deepfrier - Took {time.time() - start}s')
start = time.time()
from playlistEntry import PlaylistEntry
print(f'Imported Playlist Entry - Took {time.time() - start}s')
start = time.time()
from playlistEntry import DirectStream
print(f'Imported Direct Stream - Took {time.time() - start}s')
start = time.time()
import autoplay_engine
print('Libraries loaded...')

activity = discord.Activity(type=discord.ActivityType.listening, name="POWERWOLF")
bot = commands.Bot(command_prefix='b-', status=discord.Status.online, activity=activity, help_command=None, intents=discord.Intents.all())
online = True
slash = SlashCommand(bot, sync_commands=True)
DiscordComponents(bot)
tl.read_files()

guild_ids = [702452892241625099]  # , 821495407619997746

playerInstances = {}
playerUpdater = None
language_file = json.load(open('data/languages.json'))
song_end_loop = asyncio.new_event_loop()
member_update_last_member_id = 0
member_update_last_action = ''
omg_counter_last_member_id = 0
omg_counter_last_increase = 0
omg_counter_last_spam = 0


def handle_exception_without_doing_anything_because_of_the_annoying_broad_exception_error(e):
    if e:
        pass


def get_lang(key):
    global language_file
    if str(key) in language_file.keys():
        return language_file[str(key)]
    else:
        return 'en'


def check_authorization(ctx):
    for i in ctx.author.roles:
        if 875430701393129492 == i.id:
            return True
    return False


def is_in_same_talk_as_vc_client(guild_id, author_vc):
    global playerInstances
    pi = playerInstances.get(guild_id)
    if not pi or not author_vc.channel:
        return False
    if pi.voice_client.channel == author_vc.channel:
        return pi, get_lang(guild_id)


def search_yt(song):
    with youtube_dl.YoutubeDL() as ydl:
        entries = ydl.extract_info(str(f'ytsearch:{str(song)}'), download=False)['entries']
        if len(entries) == 0:
            return None
        else:
            info = entries[0]
            url = info['formats'][0]['url']
            name = info['title']
            thumbnail = info['thumbnail']
            duration = info['duration']
            vid = info['id']
            channel_id = info['channel_id']
            tags = info['tags']
            return PlaylistEntry(url, name, thumbnail, duration, vid, channel_id, tags)
    

async def find_song(song):
    if song.startswith('https://'):
        if song.startswith('https://youtu.be/'):
            return search_yt(song)
        elif song.startswith('https://www.youtube.com/watch?v='):  # https://www.youtube.com/watch?v=E787YU3EtNA
            song = f'https://youtu.be/{song[32:43]}'
            return search_yt(song)
        else:
            return DirectStream(song)
    else:
        if song.startswith('http://'):
            return DirectStream(song)
        else:
            return search_yt(song)


def generate_playtime(current_time, duration):
    output = f'{str(datetime.timedelta(seconds=int(current_time)))} '

    for i in range(int(current_time / duration * 10)):
        output += '┈'
    output += '◉'
    for i in range(10 - int(current_time / duration * 10)):
        output += '┈'
    output += f' {str(datetime.timedelta(seconds=duration))}'
    return output


# MUSIK

@bot.command('player')
async def player_command(ctx):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        player_inst = playerInstances[ctx.guild.id]
        embed = player_inst.gen_embed()
        if player_inst.player_msg:
            await player_inst.player_msg.delete()

        player_inst.player_msg = await ctx.send(
            components=[[Button(style=ButtonStyle.grey, label='<<', custom_id='back'),
                         Button(style=ButtonStyle.grey, label='||', custom_id='startstop'),
                         Button(style=ButtonStyle.grey, label='>>', custom_id='skip')]],
            embed=embed)
    else:
        await ctx.send(tl.translate('command.player.not_connected', get_lang(ctx.guild.id)))


class PlayerInstance:
    def __init__(self):
        self.player_msg = None
        self.voice_client = None
        self.playlist = []
        self.current_song_idx = 0
        self.start_time = 0
        self.playtime_modifier = 0
        self.pause_start = 0
        self.is_playing = False
        self.volume = 1
        self.loop_mode = 'off'
        self.equalizer = [0, 0, 0, 0, 0]
        self.autoplay = False

    async def join_vc(self, vc):
        try:
            if not self.voice_client:
                self.voice_client = await vc.connect()
        except Exception as e:
            handle_exception_without_doing_anything_because_of_the_annoying_broad_exception_error(e)
    
    async def leave_vc(self):
        try:
            await self.voice_client.disconnect()
            if self.player_msg:
                await self.player_msg.delete()
        except Exception as e:
            handle_exception_without_doing_anything_because_of_the_annoying_broad_exception_error(e)
        if self.voice_client.guild.id in playerInstances:
            playerInstances.pop(self.voice_client.guild.id)
        del self
    
    async def pause(self):
        self.pause_start = time.time()
        self.voice_client.pause()
        await self.update_player_message()
    
    def resume(self):
        self.playtime_modifier -= time.time() - self.pause_start
        self.voice_client.resume()
    
    async def next(self):
        if self.current_song_idx < len(self.playlist) - 1:
            self.current_song_idx += 1
            self.stop()
            self.play(self.current_song_idx)
        await self.update_player_message()
    
    async def back(self):
        if self.current_song_idx > 0:
            self.current_song_idx -= 1
            self.stop()
            self.play(self.current_song_idx)
        else:
            self.current_song_idx = 0
            self.stop()
            self.play(self.current_song_idx)
        await self.update_player_message()
    
    async def fastforward(self, duration):
        time_playing = self.get_time_playing()
        if self.get_time_playing() + duration > self.get_current_song().duration:
            await self.next()
        else:
            self.stop()
            self.play(self.current_song_idx, begin=time_playing + duration)
            self.playtime_modifier -= duration
        await self.update_player_message()
    
    async def fastbackward(self, duration):
        time_playing = self.get_time_playing()
        self.stop()
        if self.get_time_playing() - duration < 0:
            self.play(self.current_song_idx, begin=time_playing - duration)
            self.start_time = time.time()
            self.playtime_modifier = 0
        else:
            self.play(self.current_song_idx, begin=time_playing - duration)
            self.playtime_modifier += duration
        await self.update_player_message()
        
    async def seek(self, time_in_song):
        self.stop()
        self.playtime_modifier = time_in_song
        self.play(self.current_song_idx, time_in_song)
        await self.update_player_message()
    
    def stop(self):
        self.voice_client.stop()
        self.playtime_modifier = 0
    
    async def set_volume(self, volume):
        self.volume = volume
        await self.seek(self.get_time_playing())
    
    def play(self, idx, begin=0):
        if begin == 0:
            self.start_time = time.time()
            self.playtime_modifier = 0  # TOD create new song_end_loop every time calling this
        local_loop = asyncio.new_event_loop()
        ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': f'-vn -ss {begin} -af "volume={self.volume}, atempo=1"'}  # -vn -ss {begin} -af "equalizer=f=20:t=h:width=95:g=10, volume={self.volume}, atempo=1"
        if self.voice_client.is_playing():
            self.stop()
        self.voice_client.play(discord.FFmpegPCMAudio(self.playlist[int(idx)].stream_link, **ffmpeg_options), after=lambda e: local_loop.run_until_complete(self.on_song_end()))

    def get_time_playing(self):
        if self.voice_client.is_paused():
            return self.pause_start - self.start_time
        if not self.voice_client.is_playing():
            return 0
        if self.voice_client.is_playing():
            return time.time() - self.start_time + self.playtime_modifier
        
    def get_current_song(self):
        return self.playlist[self.current_song_idx]
    
    async def set_loop_mode(self, mode):  # playlist, song, off
        self.loop_mode = mode
        await self.update_player_message()
    
    async def on_song_end(self):
        if self.loop_mode == 'playlist':
            if self.current_song_idx + 1 >= len(self.playlist):
                self.current_song_idx = 0
                self.stop()
                self.play(self.current_song_idx)
            else:
                await self.next()
        elif self.loop_mode == 'song':
            self.play(self.current_song_idx)
        elif self.loop_mode == 'off':
            if self.autoplay:
                self.playlist.append(autoplay_engine.find_matching_song(50, self.get_current_song().channel_id))
            await self.next()

    def gen_embed(self):
        current_song = self.get_current_song()
        language = get_lang(self.voice_client.guild.id)
        embed = discord.Embed(title="PLAYER", colour=discord.Colour.blue())
        
        if len(self.playlist) == 0:
            embed.add_field(name=tl.translate('player.title', language),
                            value=tl.translate('player.nothing_playing', language), inline=False)
        else:
            if type(current_song) == PlaylistEntry:
                embed.add_field(
                    name=tl.translate('player.song', language),
                    value=f'[{current_song.video_name[0:45]}...](https://www.youtube.com/watch?v={current_song.vid})\n'
                          f'{generate_playtime(self.get_time_playing(), current_song.duration)}', inline=False)
                embed.set_thumbnail(url=current_song.thumbnail)
            else:
                embed.add_field(
                    name=tl.translate('player.song', language),
                    value=f'{current_song.stream_link}\n'
                          f'{str(datetime.timedelta(seconds=int(self.get_time_playing())))}', inline=False)

        return embed

    async def update_player_message(self):
        if self.player_msg:
            embed = self.gen_embed()
            await self.player_msg.edit(embed=embed)


@bot.event
async def on_component(ctx):
    if not is_in_same_talk_as_vc_client(ctx.guild_id, ctx.author.voice):
        return
    await ctx.edit_origin()
    player_inst = playerInstances[ctx.guild_id]
    
    if ctx.custom_id == 'back':
        await player_inst.back()

    elif ctx.custom_id == 'startstop':
        if player_inst.voice_client.is_paused():
            player_inst.resume()
        else:
            await player_inst.pause()

    elif ctx.custom_id == 'skip':
        await player_inst.next()


@bot.command('play', aliases=['p', 'paly', 'pasl'])
async def play(ctx, *, song=None):
    language = get_lang(ctx.guild.id)
    if not ctx.author.voice:
        await ctx.send(tl.translate('command.play.user_not_connected', language))
        return

    if song:
        if random.random() > 0.98:
            search_result = await find_song('rick astley never gonna give you up')
            await ctx.send(tl.translate('command.play.added_song', language, song))
        else:
            search_result = await find_song(song)
            if search_result:
                if type(search_result) == PlaylistEntry:
                    await ctx.send(tl.translate('command.play.added_song', language, song))
                else:
                    await ctx.send(tl.translate('command.play.streaming', language, song))
            else:
                await ctx.send(tl.translate('command.play.nothing_found', language))
                return
    else:
        await ctx.send(tl.translate('command.play.no_song_specified', language))
        return
        
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        player_inst = playerInstances[ctx.guild.id]
        player_inst.playlist.append(search_result)
        if not player_inst.voice_client.is_playing():
            await player_inst.next()
    else:
        new_player = PlayerInstance()
        playerInstances[ctx.guild.id] = new_player
        await new_player.join_vc(ctx.author.voice.channel)
        new_player.playlist.append(search_result)
        new_player.play(0)
        

@bot.command("leave", aliases=['stop', 'leav', 'laeve', 'disconnect'])
async def leave(ctx):
    global playerInstances
    language = get_lang(ctx.guild.id)
    
    if ctx.guild.id in playerInstances.keys():
        await playerInstances[ctx.guild.id].leave_vc()
        playerInstances.pop(ctx.guild.id)  # TODO investigate key-error
    else:
        await ctx.send(tl.translate('command.leave.not_connected', language))


@bot.command('next', aliases=['skip'])
async def next(ctx):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        if not pi.is_playing and pi.get_current_song() is PlaylistEntry and pi.autoplay:
            pi.playlist.append(autoplay_engine.find_matching_song(50, pi.get_current_song().channel_id))
        if len(pi.playlist) == pi.current_song_idx + 1:
            pi.playlist.append(autoplay_engine.find_matching_song(50, pi.get_current_song().channel_id))
        await pi.next()


@bot.command('back', aliases=['prev', 'previous'])
async def back(ctx):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        await playerInstances[ctx.guild.id].back()


@bot.command('pause')
async def pause(ctx):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        await pi.pause()


@bot.command('resume')
async def resume(ctx):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        await pi.resume()


@bot.command('clear', aliases=[])
async def clear(ctx):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        pi.playlist = []
        await ctx.send(tl.translate('command.clear.done', language))


@bot.command('seek', aliases=[])
async def seek(ctx, position):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        output = ''
        colon_count = 0
        for i in position:
            if i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':']:
                if i == ':':
                    colon_count += 1
                output += i
        
        if colon_count > 2:
            await ctx.send(tl.translate('command.seek.wrong_format', language))  # 'Too many colons, only `HH:MM:SS` or `MM:SS` allowed'
            return
        
        if colon_count == 2:
            await ctx.send(tl.translate('command.seek.seeking', language, sum(x * int(t) for x, t in zip([3600, 60, 1], output.split(":")))))  # f'Seeking to {sum(x * int(t) for x, t in zip([3600, 60, 1], output.split(":")))}'
        elif colon_count == 1:
            await ctx.send(tl.translate('command.seek.seeking', language, sum(x * int(t) for x, t in zip([60, 1], output.split(":")))))
        elif colon_count == 0:
            await ctx.send(tl.translate('command.seek.seeking', language, output))

        await pi.seek(position)


@bot.command('fastforward', aliases=['ff'])
async def ff(ctx, duration='10'):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        output = ''
        for i in duration:
            if i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                output += i
        await ctx.send(tl.translate('command.fastforward.fastforwarding', language, output))
        await pi.fastforward(int(output))


@bot.command('fastbackward', aliases=['fb'])
async def fb(ctx, duration='10'):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        output = ''
        for i in duration:
            if i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                output += i
        await ctx.send(tl.translate('command.fastbackward.fastbackwarding', language, output))
        await pi.fastbackward(int(output))


@bot.command('volume', aliases=['voume', 'vol', 'v'])
async def vol(ctx, volume=None):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi and volume:
        try:
            await playerInstances[ctx.guild.id].set_volume(volume=int(volume))
        except Exception as e:
            handle_exception_without_doing_anything_because_of_the_annoying_broad_exception_error(e)


@bot.command('loop', aliases=[])  # 'off', 'song', 'playlist', 'pl'
async def loop(ctx, mode=None):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        player_inst = playerInstances[ctx.guild.id]
    else:
        await ctx.send(tl.translate('command.loop.not_connected', language))
        return

    if not mode:
        await ctx.send(tl.translate('command.loop.no_mode', language))
        return
    
    if mode in ['off']:
        await player_inst.set_loop_mode('off')
        await ctx.send(tl.translate('command.loop.mode_off', language))
    elif mode in ['song', 's']:
        await player_inst.set_loop_mode('song')
        await ctx.send(tl.translate('command.loop.mode_song', language))
    elif mode in ['playlist', 'pl']:
        await player_inst.set_loop_mode('playlist')
        await ctx.send(tl.translate('command.loop.mode_playlist', language))
    else:
        await ctx.send(tl.translate('command.no_mode', language))
    

@bot.command('shuffle', aliases=[])
async def shuffle(ctx):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        playlist = pi.playlist
        random.shuffle(playlist)
        pi.playlist = playlist
        ctx.send(tl.translate('command.shuffle.done', language))


@bot.command('autoplay', aliases=['ap'])
async def autoplay_cmd(ctx):
    pi, language = is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice)
    if pi:
        if pi.autoplay:
            pi.autoplay = False
            await ctx.send(tl.translate('command.autoplay.off', language))
        else:
            pi.autoplay = True
            await ctx.send(tl.translate('command.autoplay.on', language))
            if not pi.is_playing and pi.get_current_song() is PlaylistEntry:
                pi.playlist.append(autoplay_engine.find_matching_song(50, pi.get_current_song().channel_id))

# @bot.command('playlist')
# async def playlist_command(ctx, arg1=None, arg2=None):
#     language = get_lang(ctx.guild.id)
#     if arg1 in ['load', 'l']:
#         if not arg2:
#             await ctx.send(tl.translate('command.playlist.load.no_playlist_specified', get_lang('data/languages.json', ctx.guild.id)))
#             return
#         if arg2 not in savedPlaylists.keys():
#             await ctx.send(tl.translate('command.playlist.playlist_not_found', get_lang('data/languages.json', ctx.guild.id)))
#             return
#         else:
#             oldPlaylist = playlist
#             playlist = savedPlaylists[arg2]
#             currentPlaylist = arg2
#
#     elif arg1 in ['save', 's']:
#         if currentPlaylist in savedPlaylists.keys():
#             if not is_pl_owner(ctx.author.id, arg2):
#                 await ctx.send(tl.translate('command.playlist.not_owned', get_lang('data/languages.json', ctx.guild.id)))
#                 return
#
#         if not arg2:
#             if not currentPlaylist:
#                 await ctx.send(tl.translate('command.playlist.save.no_name_specified', get_lang('data/languages.json', ctx.guild.id)))
#                 return
#             elif is_pl_owner(ctx.author.id, arg2):
#                 savedPlaylists[arg2] = playlist
#
#         if arg2 in savedPlaylists.keys():
#             await ctx.send(tl.translate('command.playlist.save.already_taken', get_lang('data/languages.json', ctx.guild.id)))
#             return
#         else:
#             savedPlaylists[arg2] = playlist
#
#     elif arg1 in ['del']:
#         if not arg2:
#             await ctx.send(tl.translate('command.playlist.delete.no_playlist_specified', get_lang('data/languages.json', ctx.guild.id)))
#             return
#
#     elif arg1 in ['unload', 'ul']:
#         playlist = oldPlaylist
#         currentPlaylist = None
#
#     elif arg1 in ['list', 'ls']:
#         embed = discord.Embed(title=tl.translate('command.playlist.list.title', get_lang('data/languages.json', ctx.guild.id)),
#                               colour=discord.Colour.blurple())
#         for i in savedPlaylists.keys():
#             embed.add_field(name=i, value=tl.translate('command.playlist.list.title.item_desc', get_lang('data/languages.json', ctx.guild.id)), inline=False)
#         await ctx.send(embed=embed)


# PURGE

# noinspection PyBroadException
@bot.command("purge", aliases=[])
@commands.has_any_role('Organisation', 'Admin')
async def purge(ctx, action=None):
    language = get_lang(ctx.guild.id)
    # if not check_authorization(ctx):
    #     await ctx.send(tl.translate('command.purge.no_perm', language), delete_after=10)
    #     await ctx.message.delete()
    #     return

    if not action and not ctx.message.reference:
        embed = discord.Embed(title=tl.translate('command.purge.help.title', language), colour=discord.Colour.blue())
        embed.add_field(name=tl.translate('command.purge.help.options', language),
                        value=tl.translate('command.purge.help.content', language), inline=False)

        await ctx.send(embed=embed)
        await ctx.message.delete()
        return

    try:
        action = int(action)
        if action < 100000 and not ctx.message.reference:
            await ctx.channel.purge(limit=action + 1)

        elif action > 100000 and not ctx.message.reference:
            history = await ctx.channel.history(limit=100).flatten()
            msg = [msgCount for msgCount in range(len(history)) if history[msgCount].id == action]

            if len(msg) == 0:
                await ctx.send(tl.translate('command.purge.no_msg_with_id', language), delete_after=10)
            else:
                await ctx.channel.purge(limit=msg[0])

    except:
        if not action and ctx.message.reference:
            history = await ctx.channel.history(limit=100).flatten()
            msg = [msgCount for msgCount in range(len(history)) if
                   history[msgCount].id == ctx.message.reference.message_id]
            if len(msg) == 0:
                await ctx.send(tl.translate('command.purge.reply_too_old', language), delete_after=10)
            else:
                await ctx.channel.purge(limit=msg[0])


@bot.command("help")
async def help_command(ctx):
    language = get_lang(ctx.guild.id)
    embed = discord.Embed(title=tl.translate('command.help.title', language),
                          description=tl.translate('command.help.desc', language), colour=discord.Colour.blue())
    embed.add_field(name=tl.translate('command.help.field1.title', language),
                    value=tl.translate('command.help.field1.desc', language), inline=True)
    await ctx.send(embed=embed)


@bot.command("setlanguage")
async def set_language(ctx, language=None):
    await ctx.message.delete()
    if not language or language not in ['en', 'de', 'fr']:
        await ctx.send(f'Available languages are: `"en","de","fr"`\nThe current one is `{get_lang(ctx.guild.id)}`')
        return
    
    if get_lang(ctx.guild.id) == language:
        await ctx.send(f'Nothing changed - language was `{language}` before')
    else:
        await ctx.send(f'Language has been set to `{language}`')
    
    if language == 'en':
        languages = json.load(open('data/languages.json', 'r'))
        languages[str(ctx.guild.id)] = 'en'
        json.dump(languages, open('data/languages.json', 'w'))
        
    elif language == 'de':
        languages = json.load(open('data/languages.json', 'r'))
        languages[str(ctx.guild.id)] = 'de'
        json.dump(languages, open('data/languages.json', 'w'))

    elif language == 'fr':
        languages = json.load(open('data/languages.json', 'r'))
        languages[str(ctx.guild.id)] = 'fr'
        json.dump(languages, open('data/languages.json', 'w'))
        

@bot.command('server', aliases=['serverinfo', 'mcinfo'])
async def server(ctx, ip):
    language = get_lang(ctx.guild.id)
    try:
        mcserver = mcstatus.MinecraftServer.lookup(ip)
        print(mcserver.status().raw)
        if ':' in ip:
            embed = discord.Embed(title=ip[:ip.find(':')])
        else:
            embed = discord.Embed(title=ip)
            
        embed.add_field(name=tl.translate('command.server.version', language),
                        value=f'{mcserver.status().version.name}')
        
        embed.add_field(name=tl.translate('command.server.players', language),
                        value=f'{mcserver.status().players.online} / {mcserver.status().players.max}')
        embed.colour = discord.Colour.blurple()
    except Exception as e:
        embed = discord.Embed(title=tl.translate('command.server.error', language))
        embed.add_field(name=tl.translate('command.server.could_not_connect', language),
                        value=f'It\'s either offline or the given ip/port is wrong\n\n`{str(e)}`')
        await ctx.send(embed=embed)
    else:
        await ctx.send(embed=embed)


@bot.command('printreply')
async def print_msg(ctx):
    channel = await bot.fetch_channel(ctx.message.reference.channel_id)
    msg = await channel.fetch_message(ctx.message.reference.message_id)
    await ctx.send(f'```{msg.content}```')


# noinspection PyBroadException
@bot.command('deepfry')
async def deepfry(ctx, amount=6, iterations=1, noise_intensity=0.05):
    language = get_lang(ctx.guild.id)
    await ctx.send(tl.translate('command.deepfry.answer', language))
    msg = await ctx.send('...')
    try:
        img_url = ctx.message.attachments[0].url
        img = Image.open(get(img_url, stream=True).raw)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(amount)
        img.save('file.png')

        image = imread('file.png')
        noise_img = dp.apply_noise(image, float(noise_intensity))
        imwrite('file.png', noise_img)

        img = Image.open('file.png')
        enhancer = ImageEnhance.Color(img)
        start = time.time()
        for i in range(iterations):
            img = enhancer.enhance(amount)

            if i % 10 == 0 and iterations > 50:
                try:
                    await msg.edit(content=tl.translate('command.deepfry.progress', language, i))
                except:
                    pass

            if time.time() - start > 45:
                await ctx.send(tl.translate('command.deepfry.too_long', language, i), delete_after=10)
                break

        await msg.delete()
        img.save('file.png')
        if iterations > 50:
            await ctx.send(tl.translate('command.deepfry.done', language, ctx.author.id),
                           file=discord.File(open('file.png', 'rb')))
        else:
            await ctx.send(file=discord.File(open('file.png', 'rb')))

    except Exception as e:
        await ctx.send(e)
    remove('file.png')


@bot.command('yt')
async def search(ctx, argument=None):
    if argument:
        result = await find_song(argument)
        if result:
            await ctx.channel.send(f'https://www.youtube.com/watch?v={result.vid}')
            await ctx.message.delete()
        else:
            await ctx.channel.send(tl.translate('command.play.nothing_found', get_lang(ctx.guild.id)))


@bot.listen('on_message')
async def on_msg(msg: discord.Message):
    global omg_counter_last_increase, omg_counter_last_member_id, omg_counter_last_spam
    language = get_lang(msg.guild.id)
    msg_content = f' {msg.content} '
    omg_occurrences = msg_content.lower().count('omg ') + msg_content.lower().count(' omtsch ')
    if ('pipe-bot' in msg.content or 'pipebot' in msg.content or '<@!864198668533497877>' in msg.content or '<@&864224161290125323>' in msg.content) and 'offline' in msg.content and online:
        await msg.channel.send(tl.translate('only_ghosting', language))
        await msg.channel.send('https://cdn.discordapp.com/emojis/855160244023459850.gif?v=1')
    
    if 'kurbel' in msg.content.lower() or 'krank' in msg.content.lower():
        emoji = bot.get_emoji(845738466247049236)
        await msg.add_reaction(emoji)

    elif 0 < omg_occurrences < 15:
        if time.time() > omg_counter_last_increase + 5 or omg_counter_last_member_id != msg.author.id:
            omg_counter_last_increase = time.time()
            omg_counter_last_member_id = msg.author.id
            counter_file = open('data/omg_counter.txt', 'r')
            counter = counter_file.readline()
            counter_file.close()
            counter = int(counter) + omg_occurrences
            counter_file = open('data/omg_counter.txt', 'w')
            counter_file.write(str(counter))
            counter_file.close()
            await msg.channel.send(tl.translate('omg_counter.increase', language, omg_occurrences))
            channel = await bot.fetch_channel(834011282645843979)
            await channel.edit(topic=tl.translate('omg_counter.base', language, counter))
        else:
            if omg_counter_last_spam + 5 < time.time():
                await msg.channel.send(tl.translate('omg_counter.spam', language))
                omg_counter_last_spam = time.time()


@bot.event
async def on_ready():
    print('(re)connected')


@bot.event
async def on_member_update(before, after):
    global member_update_last_member_id, member_update_last_action
    before: discord.Member
    after: discord.Member
    if member_update_last_action == f'{before.status} > {after.status}' and member_update_last_member_id == before.id:
        return
    else:
        member_update_last_action = f'{before.status} > {after.status}'
        member_update_last_member_id = before.id
    
    if before.status != after.status:
        f = open('data/activity_stats.txt', 'a')
        tm = f'{time.localtime().tm_hour}:{time.localtime().tm_min}:{time.localtime().tm_sec}'
        date = f'{time.localtime().tm_year} {time.localtime().tm_mon} {time.localtime().tm_mday}'
        f.write(f'[{date} {tm}] {before.display_name}: {before.status} >>> {after.status}\n')


#
# @bot.event
# async def on_voice_state_update(member, before, after):  # bot was disconnected, everyone in the bots channel has disconnected
#     if member == bot.user and not after.channel and member.guild.id in playerInstances.keys():
#         await playerInstances[member.guild.id].leave_vc()
#
#     if before.channel and not after.channel:
#         pi_chanels = [playerInstances[pi].voice_client.channel for pi in playerInstances.keys()]
#         if before.channel in pi_chanels and len(before.channel.voice_states) > 1:
#             await playerInstances[member.guild.id].leave_vc()
         

@slash.slash(name='back', description='Moves back in queue', guild_ids=guild_ids)
async def _back(ctx):
    await back(ctx)


@slash.slash(name='clear', description='Empties the current palylist', guild_ids=guild_ids)
async def _clear(ctx):
    await clear(ctx)


# DEEPFRY


@slash.slash(name='fastbackward', description='', guild_ids=guild_ids)
async def _fastbackward(ctx, amount):
    await fb(ctx, amount)


@slash.slash(name='fastforward', description='Skips the given amount of time', guild_ids=guild_ids)
async def _fastforward(ctx, amount):
    await fb(ctx, amount)


# HELP

@slash.slash(name='leave', description='Disconnects from your voice chnnel', guild_ids=guild_ids)
async def _leave(ctx):
    await leave(ctx)


@slash.slash(name='loop', description='Sets the loop mode for the player', guild_ids=guild_ids)  # TODO Add option thingy
async def _loop(ctx, mode=None):
    await loop(ctx, mode)


@slash.slash(name='skip', description='Skips the current song', guild_ids=guild_ids)
async def _next(ctx):
    await next(ctx)


@slash.slash(name='pause', description='Pauses the player (You might want to use `/player` instead)', guild_ids=guild_ids)
async def _pause(ctx):
    await pause(ctx)


@slash.slash(name='play', description='Adds the given song to the playlist', guild_ids=guild_ids)
async def _play(ctx, song):
    await ctx.defer()
    await play(ctx=ctx, song=song)


@slash.slash(name='player', description='Sends an embed to control the player', guild_ids=guild_ids)
async def _player_command(ctx):
    await player_command(ctx)


@slash.slash(name='purge', description='Deletes messages, for help, send `/purge`')
async def _purge(ctx):
    await purge(ctx, action=None)


@slash.slash(name='resume', description='Unpauses the player', guild_ids=guild_ids)
async def _resme(ctx):
    await resume(ctx)


@slash.slash(name='yt-search', description='Searches the given video name on youtube', guild_ids=guild_ids)
async def _ytsearch(ctx, videoname):
    await ctx.defer()
    result = await find_song(videoname)
    if result:
        await ctx.send(f'https://www.youtube.com/watch?v={result.vid}')
    else:
        await ctx.send('Nothing was found matching your search :(')


@slash.slash(name='seek', description='Jumps to the given timestamp in the song (`HH:MM:SS`, `MM:SS`, `seconds` supported)')
async def _seek(ctx, position):
    await seek(ctx, position)


@slash.slash(name='mc-server', description='Shows info about the given minecraft server', guild_ids=guild_ids)
async def _server(ctx, ip):
    await server(ctx, ip)


@slash.slash(name='set-language', description='Sets the bot\'s language of this server', guild_ids=guild_ids)
async def _set_language(ctx, language=None):
    await set_language(ctx, language)


@slash.slash(name='shuffle', description='Randomizes the bot\'s playlist', guild_ids=guild_ids)
async def _shuffle(ctx):
    await shuffle(ctx)


@slash.slash(name='volume', description='Sets the player\'s volume', guild_ids=guild_ids)
async def _vol(ctx, volume=None):
    await vol(ctx, volume)


print('Startup done. Connecting to discord...')
bot.run(open('data/token.txt').readline())
