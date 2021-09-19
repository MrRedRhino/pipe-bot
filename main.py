from __future__ import unicode_literals

import datetime
import json
import random
import time
import cv2
import discord
import mcstatus
import requests
import youtube_dl
from PIL import ImageEnhance, Image
from discord.ext import commands
from discord_slash import SlashCommand
from discord_slash.model import ButtonStyle
from discord_components import *
import translate as tl
import deepfrier as dp
from playlistEntry import PlaylistEntry

activity = discord.Activity(type=discord.ActivityType.listening, name="")
bot = commands.Bot(command_prefix='b-', status=discord.Status.online, activity=activity, help_command=None)
slash = SlashCommand(bot, sync_commands=False)
DiscordComponents(bot)
tl.read_files()

playerInstances = {}

playerUpdater = None
language_file = json.load(open('data/languages.json'))


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
    if guild_id in playerInstances.keys() and author_vc:
        if playerInstances[guild_id].voice_client.channel == author_vc.channel:
            return True
    return False


# def is_pl_owner(user, pl):
#     return savedPlaylists[pl]['ownerID'] == user.id


async def find_song(song):
    with youtube_dl.YoutubeDL() as ydl:
        info = ydl.extract_info(str(f'ytsearch:{str(song)}'), download=False)['entries'][0]
        url = info['formats'][0]['url']
        name = info['title']
        thumbnail = info['thumbnail']
        duration = info['duration']
        vid = info['id']
        return PlaylistEntry(url, name, thumbnail, duration, vid)
        # return dict(url=url, name=name, thumbnail=thumbnail, duration=duration, id=vid)


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
async def player(ctx):
    ctx += 1


class PlayerInstance:
    def __init__(self):
        self.player_msg = None
        self.voice_client = None
        self.playlist = []
        self.current_song_idx = 0
        self.start_time = 0
        self.time_playing = 0
        self.playtime_modifier = 0
        self.pause_duration = 0
        self.pause_start = 0
        self.is_playing = False
        self.guild_id = 0
        self.volume = 1
        self.loop_mode = 'off'
        self.song_over_scheduler_entry = None
    
    async def join_vc(self, vc):
        try:
            if not self.voice_client:
                self.voice_client = await vc.connect()
        except Exception as e:
            print(e)
    
    async def leave_vc(self):
        try:
            await self.voice_client.disconnect()
            if self.player_msg:
                await self.player_msg.delete()
        except Exception as e:
            print(e)
        del self
    
    async def pause(self):
        self.pause_start = time.time()
        self.voice_client.pause()
    
    async def resume(self):
        self.playtime_modifier -= time.time() - self.pause_start
        self.voice_client.resume()
    
    def next(self):
        if self.current_song_idx < len(self.playlist)-1:
            self.current_song_idx += 1
            self.start_time = time.time()
            self.playtime_modifier = 0
            self.stop()
            self.play(self.current_song_idx)
    
    async def back(self):
        if self.current_song_idx > 0:
            self.current_song_idx -= 1
            self.start_time = time.time()
            self.playtime_modifier = 0
            self.stop()
            self.play(self.current_song_idx)
    
    async def fastforward(self, duration):
        time_playing = self.get_time_playing()
        if self.get_time_playing() + duration > self.get_current_song()['duration']:
            self.next()
        else:
            self.stop()
            self.play(self.current_song_idx, begin=time_playing + duration)
            self.playtime_modifier -= duration
    
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
        
    def seek(self, time_in_song):
        self.stop()
        self.playtime_modifier = time_in_song
        self.play(self.current_song_idx, time_in_song)
    
    def stop(self):
        self.voice_client.stop()
        self.playtime_modifier = 0
    
    def set_volume(self, volume):
        self.volume = volume
        self.seek(self.get_time_playing())
    
    def play(self, idx, begin=0):
        if begin == 0:
            self.start_time = time.time()
            self.playtime_modifier = 0
        ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': f'-vn -ss {begin} -filter:a "volume={self.volume}"'}  # -filter:a "atempo=20"
        self.voice_client.play(discord.FFmpegPCMAudio(self.playlist[int(idx)].stream_link, **ffmpeg_options), after=lambda e: self.song_end())

    def get_time_playing(self):
        if self.voice_client.is_paused():
            return self.pause_start - self.start_time
        if not self.voice_client.is_playing():
            return 0
        if self.voice_client.is_playing():
            return time.time() - self.start_time + self.playtime_modifier
        
    def get_current_song(self):
        return self.playlist[self.current_song_idx]
    
    def set_loop_mode(self, mode):  # playlist, song, off
        self.loop_mode = mode
        print(self.loop_mode)

    def song_end(self):
        if self.loop_mode == 'playlist':
            print(len(self.playlist), self.current_song_idx + 1)
            if self.current_song_idx + 1 >= len(self.playlist):
                self.current_song_idx = 0
                self.stop()
                self.play(self.current_song_idx)
            else:
                self.next()
        elif self.loop_mode == 'song':
            self.play(self.current_song_idx)
        elif self.loop_mode == 'off':
            self.next()
        
    async def gen_embed(self):
        current_song = self.playlist[self.current_song_idx]
        language = get_lang(self.guild_id)
        embed = discord.Embed(title="PLAYER", colour=discord.Colour.blue())
    
        if not self.is_playing:
            embed.add_field(name=tl.translate('player.title', language),
                            value=tl.translate('player.nothing_playing', language), inline=False)
        else:
            embed.add_field(
                name="Song",
                value=f'[{current_song["name"]}](https://www.youtube.com/watch?v={current_song["id"]})\n'
                      f'{generate_playtime(self.time_playing, current_song["duration"])}', inline=False)
            embed.set_thumbnail(url=current_song['thumbnail'])
    
        return embed


# noinspection PyUnresolvedReferences
async def send_or_update_player(send_new, message_or_channel):  # player_msg, time_playing, guild_id, send_new=False
    embed = 0
    if send_new:
        return await message_or_channel.send(
            components=[[Button(style=ButtonStyle.grey, label='<<', custom_id='back'),
                         Button(style=ButtonStyle.grey, label='||', custom_id='startstop'),
                         Button(style=ButtonStyle.grey, label='>>', custom_id='skip')]],
            embed=embed)
    else:
        return await message_or_channel.edit(
            components=[[Button(style=ButtonStyle.grey, label='<<', custom_id='back'),
                         Button(style=ButtonStyle.grey, label='||', custom_id='startstop'),
                         Button(style=ButtonStyle.grey, label='>>', custom_id='skip')]],
            embed=embed)


def generate_player_embed(guild_id, current_song, is_playing, time_playing):  # playing, language, time_playing=0, duration=0, current_song=None
    language = get_lang(guild_id)
    embed = discord.Embed(title="PLAYER", colour=discord.Colour.blue())

    if not is_playing:
        embed.add_field(name=tl.translate('player.title', language),
                        value=tl.translate('player.nothing_playing', language), inline=False)
    else:
        embed.add_field(
            name="Song",
            value=f'[{current_song["name"]}](https://www.youtube.com/watch?v={current_song["id"]})\n'
                  f'{generate_playtime(time_playing, current_song["duration"])}', inline=False)
        embed.set_thumbnail(url=current_song['thumbnail'])

    return embed


@bot.event
async def on_component(ctx):
    print('a button has been pressed')
#   await update_player()
    await ctx.edit_origin()
    if ctx.custom_id == 'back':
        await back()
#       await update_player(ctx)

    elif ctx.custom_id == 'startstop':
        if bot.voice_clients[0].is_playing():
            await pause()
        else:
            await resume()
#       await update_player(ctx)

    elif ctx.custom_id == 'skip':
        await next()
#       await update_player(ctx)


@bot.command('play', aliases=['p', 'paly', 'pasl'])
async def play(ctx, *, song=None):
    global playerInstances
    language = get_lang(ctx.guild.id)

    if not ctx.author.voice:
        await ctx.send(tl.translate('command.player.user_not_connected', language))
        return
    # add song if user can control player and it is connected
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice) and song:
        player_inst = playerInstances[ctx.guild.id]
        if random.random() > 0.98:
            player_inst.playlist.append(await find_song('rick astley never gonna give you up'))
        player_inst.playlist.append(await find_song(song))

        if not player_inst.voice_client.is_playing():
            player_inst.play(player_inst.current_song_idx + 1)
            player_inst.current_song_idx += 1
        return
    
    # there's no player in the user's vc and nothing else can be wrong
    if song:
        new_player = PlayerInstance()
        playerInstances[ctx.guild.id] = new_player
        
        if random.random() > 0.98:
            new_player.playlist.append(await find_song('rick astley never gonna give you up'))
        new_player.playlist.append(await find_song(song))
    
        await new_player.join_vc(ctx.author.voice.channel)
        new_player.guild_id = ctx.guild.id
        new_player.play(0)
    else:
        await ctx.send(tl.translate('command.player.no_song_specified', language))
    # have to update player


@bot.command("leave", aliases=['stop', 'leav', 'laeve'])
async def leave(ctx):
    global playerInstances
    language = get_lang(ctx.guild.id)
    
    if ctx.guild.id in playerInstances.keys():
        await playerInstances[ctx.guild.id].leave_vc()
        playerInstances.pop(ctx.guild.id)
    else:
        await ctx.send(tl.translate('command.leave.not_connected', language))


@bot.command('next', aliases=['skip'])
async def next(ctx):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        playerInstances[ctx.guild.id].next()


@bot.command('back', aliases=['prev', 'previous'])
async def back(ctx):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        playerInstances[ctx.guild.id].back()


@bot.command('pause')
async def pause(ctx):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        await playerInstances[ctx.guild.id].pause()


@bot.command('resume')
async def resume(ctx):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        await playerInstances[ctx.guild.id].resume()


@bot.command('clear', aliases=[])
async def clear(ctx):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        playerInstances[ctx.guild.id].playlist = []


@bot.command('seek', aliases=[])
async def seek(ctx, position):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        language = get_lang(ctx.guild.id)
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

        playerInstances[ctx.guild.id].seek(position)


@bot.command('fastforward', aliases=['ff'])
async def ff(ctx, duration='10'):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        language = get_lang(ctx.guild.id)
        output = ''
        for i in duration:
            if i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                output += i
        await ctx.send(tl.translate('command.fastforward.fastforwarding', language, output))
        await playerInstances[ctx.guild.id].fastforward(int(output))


@bot.command('fastbackward', aliases=['fb'])
async def fb(ctx, duration='10'):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        language = get_lang(ctx.guild.id)
        output = ''
        for i in duration:
            if i in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
                output += i
        await ctx.send(tl.translate('command.fastbackward.fastbackwarding', language, output))
        await playerInstances[ctx.guild.id].fastbackward(int(output))


@bot.command('volume')
async def vol(ctx, volume=None):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice) and volume:
        # language = get_lang('data/languages.json', ctx.guild.id)
        try:
            playerInstances[ctx.guild.id].set_volume(volume=int(volume))
        except Exception as e:
            print(e)


@bot.command('loop', aliases=[])  # 'off', 'song', 'playlist', 'pl'
async def loop(ctx, mode=None):
    language = get_lang(ctx.guild.id)
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        player_inst = playerInstances[ctx.guild.id]
    else:
        await ctx.send(tl.translate('command.loop.not_connected', language))
        return

    if not mode:
        await ctx.send(tl.translate('command.loop.no_mode', language))
        return
    
    if mode in ['off']:
        player_inst.set_loop_mode('off')
    elif mode in ['song', 's']:
        player_inst.set_loop_mode('song')
    elif mode in ['playlist', 'pl']:
        player_inst.set_loop_mode('playlist')
    else:
        await ctx.send(tl.translate('command.loop.mode_wrong', language))
    

@bot.command('shuffle', aliases=[])
async def shuffle(ctx):
    if is_in_same_talk_as_vc_client(ctx.guild.id, ctx.author.voice):
        playlist = playerInstances[ctx.guild.id].playlist
        random.shuffle(playlist)
        playerInstances[ctx.guild.id].playlist = playlist
#
#
# @bot.command('playlist')
# async def playlist_command(ctx, arg1=None, arg2=None):
#     global playlist, oldPlaylist, currentPlaylist
#
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
async def purge(ctx, action=None):
    language = get_lang(ctx.guild.id)
    if not check_authorization(ctx):
        await ctx.send(tl.translate('command.purge.no_perm', language), delete_after=10)
        await ctx.message.delete()
        return

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
    language = get_lang(ctx.guil.did)
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
        await ctx.send(f'Nothing changed, language was `{language}` before')
    else:
        await ctx.send(f'Language is now `{language}`')
    
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
    try:
        mcserver = mcstatus.MinecraftServer.lookup(ip)
        print(mcserver.status().raw)
        if ':' in ip:
            embed = discord.Embed(title=ip[:ip.find(':')])
        else:
            embed = discord.Embed(title=ip)
            
        embed.add_field(name='Version:', value=f'{mcserver.status().version.name}')
        
        embed.add_field(name='Players', value=f'{mcserver.status().players.online} / {mcserver.status().players.max}')
        embed.colour = discord.Colour.blurple()
    except Exception as e:
        embed = discord.Embed(title='Error')
        embed.add_field(name='Could not connect to the given server!', value=f'It\'s either offline or the given ip/port is wrong\n\n`{str(e)}`')
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
        img = Image.open(requests.get(img_url, stream=True).raw)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(amount)
        img.save('file.png')

        image = cv2.imread('file.png')
        noise_img = dp.apply_noise(image, float(noise_intensity))
        cv2.imwrite('file.png', noise_img)

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


@bot.listen('on_message (deactivated)')
async def on_msg(msg):
    language = get_lang(msg.guild.id)
    if ('pipe-bot' in msg.content or 'pipebot' in msg.content or '<@!864198668533497877>' in msg.content or '<@&864224161290125323>' in msg.content) and 'offline' in msg.content:
        await msg.channel.send(tl.translate('only_ghosting', language))
        await msg.channel.send('https://cdn.discordapp.com/emojis/855160244023459850.gif?v=1')


@bot.event
async def on_ready():
    print('(re)connected')


print('Startup done. Connecting to discord...')
bot.run(open('data/token.txt').readline())
