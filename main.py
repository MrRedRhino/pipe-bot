from __future__ import unicode_literals

import datetime
import json
import time

import cv2
import discord
import requests
import youtube_dl
from PIL import ImageEnhance, Image
from discord.ext import commands
from discord_slash import SlashCommand
from discord_slash.model import ButtonStyle
from discord_components import *
import translate as tl
import deepfrier as dp

activity = discord.Activity(type=discord.ActivityType.listening, name="")
bot = commands.Bot(command_prefix='-', status=discord.Status.online, activity=activity, help_command=None)
slash = SlashCommand(bot, sync_commands=False)
DiscordComponents(bot)

playlist = []
oldPlaylist = []
currentPlaylist = None
savedPlaylists = {"pl1": {'ownerID': "123", 'contents': [{'url': "", 'name': "", 'thumbnail': ""}]}}
# {"pl1":{'ownerID':"123",'contents:'[{'url':"",'name':"",'thumbnail':""}]}}

currentSong = 0
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
url = ''
startTime = 0

playerMsg = None
playerUpdater = None


def get_lang(file, key):
    languages = json.load(open(file))
    if str(key) in languages.keys():
        return languages[str(key)]
    else:
        return 'en'


def check_authorization(ctx):
    for i in ctx.author.roles:
        if 875430701393129492 == i.id:
            return True
    return False


def is_pl_owner(user, pl):
    if savedPlaylists[pl]['ownerID'] == user.id:
        return True
    else:
        return False


def add_song(song):
    global playlist, url, currentSong
    
    with youtube_dl.YoutubeDL() as ydl:
        info = ydl.extract_info(str("ytsearch:" + str(song)), download=False)['entries'][0]
        url = info['formats'][0]['url']
        name = info['title']
        thumbnail = info['thumbnail']
        duration = info['duration']
        vid = info['id']
        playlist.append(dict(url=url, name=name, thumbnail=thumbnail, duration=duration, id=vid))


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
    try:
        await ctx.message.delete()
    except Exception as e:
        print(e)
    await update_player(ctx, True)


# noinspection PyUnresolvedReferences
async def update_player(ctx=None, send_new=False):
    global playerMsg, playerUpdater, startTime
    embed = discord.Embed(title="PLAYER", colour=discord.Colour.blue())
    if len(playlist) == 0:
        embed.add_field(name=tl.translate('player.title', get_lang('data/languages.json', ctx.message.guild.id)),
                        value=tl.translate('player.nothing_playing', get_lang('data/languages.json', ctx.message.guild.id)), inline=False)
    else:
        embed.add_field(
            name="Song",
            value=f'[{playlist[currentSong]["name"]}](https://www.youtube.com/watch?v={playlist[currentSong]["id"]})\n'
            f'{generate_playtime(time.time()-startTime,playlist[currentSong]["duration"])}', inline=False)
        embed.set_thumbnail(url=playlist[currentSong]['thumbnail'])

    if send_new:
        try:
            await playerMsg.delete()
        except Exception as e:
            print(e)
        playerMsg = await ctx.send(components=[[Button(style=ButtonStyle.grey, label='<<', custom_id='back'),
                                                Button(style=ButtonStyle.grey, label='||', custom_id='startstop'),
                                                Button(style=ButtonStyle.grey, label='>>', custom_id='skip')]],
                                   embed=embed)

    elif playerMsg:
        await playerMsg.edit(components=[[Button(style=ButtonStyle.grey, label='<<', custom_id='back'),
                                          Button(style=ButtonStyle.grey, label='||', custom_id='startstop'),
                                          Button(style=ButtonStyle.grey, label='>>', custom_id='skip')]], embed=embed)


async def player_helper():
    global playerUpdater
    try:
        while True:
            time.sleep(10)
            await update_player()
    except Exception as e:
        print(e)


@bot.event
async def on_component(ctx):
    print('a button has been pressed')
#   await update_player()
    await ctx.edit_origin()
    if ctx.custom_id == 'back':
        await back()
        await update_player(ctx)

    elif ctx.custom_id == 'startstop':
        if bot.voice_clients[0].is_playing():
            await pause()
        else:
            await resume()
        await update_player(ctx)

    elif ctx.custom_id == 'skip':
        await next()
        await update_player(ctx)


@bot.command('play', aliases=['p', 'paly', 'pasl'])
async def play(ctx, *, song=None):
    global playerMsg, FFMPEG_OPTIONS, url, startTime

    if not playerMsg:
        await ctx.message.delete()

    if not ctx.author.voice:
        await ctx.send(tl.translate('command.player.user_not_connected', get_lang('data/languages.json', ctx.message.guild.id)))
        return
    try:
        await ctx.author.voice.channel.connect()
    except Exception as e:
        print(e)

    if song and ctx.author.voice.channel.id == bot.voice_clients[0].channel.id:
        add_song(song)
        if not bot.voice_clients[0].is_playing():
            startTime = time.time()
            bot.voice_clients[0].play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=print('song done?'))
    else:
        await ctx.send(tl.translate('command.player.no_song_specified', get_lang('data/languages.json', ctx.message.guild.id)))

    await update_player(ctx)


@bot.command('next', aliases=['skip'])
async def next(ctx=None):
    global currentSong
    bot.voice_clients[0].stop()
    if currentSong < len(playlist) - 1:
        currentSong += 1
        bot.voice_clients[0].play(discord.FFmpegPCMAudio(playlist[currentSong]['url'], **FFMPEG_OPTIONS),
                                  after=await next(ctx))
        await update_player(ctx)


@bot.command('back')
async def back(ctx=None):
    global currentSong
    global playlist
    bot.voice_clients[0].stop()
    if currentSong > 0:
        currentSong -= 1
    bot.voice_clients[0].play(discord.FFmpegPCMAudio(playlist[currentSong]['url'], **FFMPEG_OPTIONS))
    await update_player(ctx)


@bot.command('pause')
async def pause():
    bot.voice_clients[0].pause()


@bot.command('resume')
async def resume():
    bot.voice_clients[0].resume()


@bot.command("leave", aliases=['stop', 'leav', 'laeve'])
async def leave(ctx):
    global currentSong
    currentSong = 0
    global playlist
    playlist = []
    for x in bot.voice_clients:
        if ctx.author.voice.channel.id == x.channel.id:
            await x.disconnect()


@bot.command('clear', aliases=[])
async def clear(ctx):
    global playlist
    playlist = []
    await update_player(ctx=ctx)


@bot.command('playlist')
async def playlist_command(ctx, arg1=None, arg2=None):
    global playlist, oldPlaylist, currentPlaylist

    if arg1 in ['load', 'l']:
        if not arg2:
            await ctx.send(tl.translate('command.playlist.load.no_playlist_specified', get_lang('data/languages.json', ctx.message.guild.id)))
            return
        if arg2 not in savedPlaylists.keys():
            await ctx.send(tl.translate('command.playlist.playlist_not_found', get_lang('data/languages.json', ctx.message.guild.id)))
            return
        else:
            oldPlaylist = playlist
            playlist = savedPlaylists[arg2]
            currentPlaylist = arg2

    elif arg1 in ['save', 's']:
        if currentPlaylist in savedPlaylists.keys():
            if not is_pl_owner(ctx.author.id, arg2):
                await ctx.send(tl.translate('command.playlist.not_owned', get_lang('data/languages.json', ctx.message.guild.id)))
                return

        if not arg2:
            if not currentPlaylist:
                await ctx.send(tl.translate('command.playlist.save.no_name_specified', get_lang('data/languages.json', ctx.message.guild.id)))
                return
            elif is_pl_owner(ctx.author.id, arg2):
                savedPlaylists[arg2] = playlist

        if arg2 in savedPlaylists.keys():
            await ctx.send(tl.translate('command.playlist.save.already_taken', get_lang('data/languages.json', ctx.message.guild.id)))
            return
        else:
            savedPlaylists[arg2] = playlist

    elif arg1 in ['del']:
        if not arg2:
            await ctx.send(tl.translate('command.playlist.delete.no_playlist_specified', get_lang('data/languages.json', ctx.message.guild.id)))
            return

    elif arg1 in ['unload', 'ul']:
        playlist = oldPlaylist
        currentPlaylist = None

    elif arg1 in ['list', 'ls']:
        embed = discord.Embed(title=tl.translate('command.playlist.list.title', get_lang('data/languages.json', ctx.message.guild.id)),
                              colour=discord.Colour.blurple())
        for i in savedPlaylists.keys():
            embed.add_field(name=i, value=tl.translate('command.playlist.list.title.item_desc', get_lang('data/languages.json', ctx.message.guild.id)), inline=False)
        await ctx.send(embed=embed)


# PURGE

# noinspection PyBroadException
@bot.command("purge", aliases=[])
async def purge(ctx, action=None):
    if not check_authorization(ctx):
        await ctx.send(tl.translate('command.purge.no_perm', get_lang('data/languages.json', ctx.message.guild.id)), delete_after=10)
        await ctx.message.delete()
        return

    if not action and not ctx.message.reference:
        embed = discord.Embed(title=tl.translate('command.purge.help.title', get_lang('data/languages.json', ctx.message.guild.id)), colour=discord.Colour.blue())
        embed.add_field(name=tl.translate('command.purge.help.options', get_lang('data/languages.json', ctx.message.guild.id)),
                        value=tl.translate('command.purge.help.content', get_lang('data/languages.json', ctx.message.guild.id)), inline=False)

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
                await ctx.send(tl.translate('command.purge.no_msg_with_id', get_lang('data/languages.json', ctx.message.guild.id)), delete_after=10)
            else:
                await ctx.channel.purge(limit=msg[0])

    except:
        if not action and ctx.message.reference:
            history = await ctx.channel.history(limit=100).flatten()
            msg = [msgCount for msgCount in range(len(history)) if
                   history[msgCount].id == ctx.message.reference.message_id]
            if len(msg) == 0:
                await ctx.send(tl.translate('command.purge.reply_too_old', get_lang('data/languages.json', ctx.message.guild.id)), delete_after=10)
            else:
                await ctx.channel.purge(limit=msg[0])


# STARBOARD

# noinspection PyUnreachableCode,PyBroadException
@bot.event
async def on_raw_reaction_add(payload):
    return payload
    f = open('data/starboardMsgs.txt', 'r')
    starboard_messages = f.readline()
    f.close()
    try:
        starboard_messages = json.loads(starboard_messages)
    except:
        starboard_messages = {}

    print(starboard_messages)

    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    for reaction in message.reactions:
        if reaction.emoji == '⭐':
            emoji_count = reaction.count
    if emoji_count < 2:
        return

    starboard_channel = await bot.fetch_channel(879703712740827186)

    if payload.emoji.name == '⭐' and payload.guild_id == 702452892241625099 and not str(
            payload.message_id) in starboard_messages.keys():
        embed = discord.Embed(colour=discord.Colour.purple())
        if len(message.attachments) > 0:
            embed.set_image(url=str(message.attachments[0]))
            print(message.attachments[0])

        s_id = channel.guild.id
        c_id = payload.channel_id
        m_id = payload.message_id
        original_msg_url = f'https://discord.com/channels/{s_id}/{c_id}/{m_id}'

        embed.add_field(name=message.author, value=f'[Original]({original_msg_url})')
        embed.add_field(name='‎‏‏‎ ‎', value=str(message.content), inline=False)  # '‎‏‏‎ ‎'
        # embed.add_field(name='‎‏‏‎ ‎',value='Starcounter')
        embed.set_footer(text='Starcounter')

        msg = await starboard_channel.send(embed=embed)

        starboard_messages[str(payload.message_id)] = msg.id  # {'originalMsgId':'starboardMsgID'}
        print(starboard_messages)
        f = open('data/starboardMsgs.txt', 'w')
        f.write(json.dumps(starboard_messages))
        f.close()

    edit_msg = await starboard_channel.fetch_message(int(starboard_messages[str(payload.message_id)]))
    await edit_msg.edit(embed=edit_msg.embeds[0].set_footer(text=f'⭐️ {emojiCount} | {payload.message_id}'))


@bot.command("help")
async def help_command(ctx):
    embed = discord.Embed(title=tl.translate('command.help.title', get_lang('data/languages.json', ctx.message.guild.id)),
                          description=tl.translate('command.help.desc', get_lang('data/languages.json', ctx.message.guild.id)), colour=discord.Colour.blue())
    embed.add_field(name=tl.translate('command.help.field1.title', get_lang('data/languages.json', ctx.message.guild.id)),
                    value=tl.translate('command.help.field1.desc', get_lang('data/languages.json', ctx.message.guild.id)), inline=True)
    await ctx.send(embed=embed)


@bot.command("setlanguage")
async def setlanguage(ctx, language=None):
    await ctx.message.delete()
    if not language or language not in ['en', 'de', 'fr']:
        await ctx.send(f'Available languages are: `"en","de","fr"`\nThe current one is `{get_lang("data/languages.json",str(ctx.message.guild.id))}`')
        return
    
    if get_lang("data/languages.json", str(ctx.message.guild.id)) == language:
        await ctx.send(f'Nothing changed, language was `{language}` before')
    else:
        await ctx.send(f'Language is now `{language}`')
    
    if language == 'en':
        languages = json.load(open('data/languages.json', 'r'))
        languages[str(ctx.message.guild.id)] = 'en'
        json.dump(languages, open('data/languages.json', 'w'))
        
    elif language == 'de':
        languages = json.load(open('data/languages.json', 'r'))
        languages[str(ctx.message.guild.id)] = 'de'
        json.dump(languages, open('data/languages.json', 'w'))

    elif language == 'fr':
        languages = json.load(open('data/languages.json', 'r'))
        languages[str(ctx.message.guild.id)] = 'fr'
        json.dump(languages, open('data/languages.json', 'w'))
        

@bot.command('printreply')
async def print_msg(ctx):
    channel = await bot.fetch_channel(ctx.message.reference.channel_id)
    message = await channel.fetch_message(ctx.message.reference.message_id)
    await ctx.send(message)
    await ctx.send(str(message.content))
    print(str(message.content))
    await ctx.send(message.attachments)


# noinspection PyBroadException
@bot.command('deepfry')
async def deepfry(ctx, amount=6, iterations=1, noise_intensity=0.05):
    await ctx.send(tl.translate('command.deepfry.answer', get_lang('data/languages.json', ctx.message.guild.id)))
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
                    await msg.edit(content=tl.translate('command.deepfry.progress', get_lang('data/languages.json', ctx.message.guild.id), i))
                except:
                    pass

            if time.time() - start > 45:
                await ctx.send(tl.translate('command.deepfry.too_long', get_lang('data/languages.json', ctx.message.guild.id), i), delete_after=10)
                break

        await msg.delete()
        img.save('file.png')
        if iterations > 50:
            await ctx.send(tl.translate('command.deepfry.done', get_lang('data/languages.json', ctx.message.guild.id), ctx.author.id),
                           file=discord.File(open('file.png', 'rb')))
        else:
            await ctx.send(file=discord.File(open('file.png', 'rb')))

    except Exception as e:
        await ctx.send(e)


@bot.listen('on_message deactivated')
async def on_msg(message):
    if ('pipe-bot' in message.content or 'pipebot' in message.content or '<@!864198668533497877>' in message.content or '<@&864224161290125323>' in message.content) and 'offline' in message.content:
        await message.channel.send(tl.translate('only_ghosting', get_lang('data/languages.json', message.channel.guild.id)))
        await message.channel.send('https://cdn.discordapp.com/emojis/855160244023459850.gif?v=1')


@bot.event
async def on_ready():
    print('(re)connected')


print('Startup done. Connecting to discord...')
bot.run(open('data/token.txt').readline())
