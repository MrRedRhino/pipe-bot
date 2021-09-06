from __future__ import unicode_literals
import discord
import youtube_dl
import json
import datetime
import threading
import requests
import time
import cv2
import random
import asyncio
import numpy as np
from discord.ext import commands
from discord_slash import SlashCommand
from discord_slash.model import ButtonStyle
from discord_components import *
from PIL import ImageEnhance, Image

bot = commands.Bot(command_prefix='-')
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


@bot.event
async def on_ready():
    print('started up')


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
    global playlist
    global url
    global currentSong
    with youtube_dl.YoutubeDL() as ydl:
        info = ydl.extract_info(str("ytsearch:" + str(song)), download=False)['entries'][0]
        url = info['formats'][0]['url']
        name = info['title']
        thumbnail = info['thumbnail']
        duration = info['duration']
        id = info['id']
        playlist.append(dict(url=url, name=name, thumbnail=thumbnail, duration=duration, id=id))


def generate_playtime(current_time, duration):
    output = f'{str(datetime.timedelta(seconds=current_time))} '

    for i in range(int(current_time / duration * 10)):
        output += '┈'
    output += '◉'
    for i in range(10 - int(current_time / duration * 10)):
        output += '┈'
    output += f' {str(datetime.timedelta(seconds=duration))}'
    return output





####################### MUSIK ########################

@bot.command('player')
async def player(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    await update_player(ctx, True)


async def update_player(ctx=None, sendNew=False):
    global playerMsg, playerUpdater,startTime
    embed = discord.Embed(title="PLAYER", colour=discord.Colour.blue())
    if len(playlist) == 0:
        embed.add_field(name="Song", value='Nothing is playing at the moment', inline=False)
    else:
        embed.add_field(name="Song",
            value=f'[{playlist[currentSong]["name"]}](https://www.youtube.com/watch?v={playlist[currentSong]["id"]})\n'
                  f'{generate_playtime(time.time()-startTime,playlist[currentSong]["duration"])}', inline=False)
        embed.set_thumbnail(url=playlist[currentSong]['thumbnail'])

    if sendNew:
        try:
            await playerMsg.delete()
        except:
            pass
        playerMsg = await ctx.send(components=[[Button(style=ButtonStyle.grey, label='<<', custom_id='back'),
                                                Button(style=ButtonStyle.grey, label='||', custom_id='startstop'),
                                                Button(style=ButtonStyle.grey, label='>>', custom_id='skip')]],
                                   embed=embed)

    elif playerMsg:
        await playerMsg.edit(components=[[Button(style=ButtonStyle.grey, label='<<', custom_id='back'),
                                          Button(style=ButtonStyle.grey, label='||', custom_id='startstop'),
                                          Button(style=ButtonStyle.grey, label='>>', custom_id='skip')]], embed=embed)


async def playerHelper():
    global playerUpdater
    try:
        while True:
            time.sleep(10)
            await update_player()
    except:
        pass


@bot.event
async def on_component(ctx):
    print('a button has been pressed')
    #await update_player()
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

    if playerMsg != None:
        await ctx.message.delete()

    if ctx.author.voice == None:
        await ctx.send("Please connect to a voice channel so I can join you")
        return
    try:
        await ctx.author.voice.channel.connect()
    except:
        pass

    if song != None and ctx.author.voice.channel.id == bot.voice_clients[0].channel.id:
        add_song(song)
        if not bot.voice_clients[0].is_playing():
            startTime = time.time()
            bot.voice_clients[0].play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=print('song done?'))
    else:
        await ctx.send("What should I play? Try: `-p <LINK/NAME>`")

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
async def pause(ctx=None):
    bot.voice_clients[0].pause()


@bot.command('resume')
async def resume(ctx=None):
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
async def playlistCommand(ctx, arg1=None, arg2=None, arg3=None, arg4=None):
    global playlist, oldPlaylist, currentPlaylist

    if arg1 in ['load', 'l']:
        if arg2 == None:
            await ctx.send('You have to specify a playlist-name to load')
            return
        if arg2 not in savedPlaylists.keys():
            await ctx.send('Couldnt find the specified playlist.\n`-playlist list/ls` sends available playlists')
            return
        else:
            oldPlaylist = playlist
            playlist = savedPlaylists[arg2]
            currentPlaylist = arg2

    elif arg1 in ['save', 's']:
        if currentPlaylist in savedPlaylists.keys():
            if not is_pl_owner(ctx.author.id, arg2):
                await ctx.send('You have to be the owner of a playlist, to save it')
                return

        if arg2 == None:
            if currentPlaylist == None:
                await ctx.send('You have to specify a name that your playlist should get')
                return
            elif is_pl_owner(ctx.author.id, arg2):
                savedPlaylists[arg2] = playlist

        if arg2 in savedPlaylists.keys():
            await ctx.send(
                'The name is already taken, choose a different one or delete the playlist with this name first')
            return
        else:
            savedPlaylists[arg2] = playlist


    elif arg1 in ['del']:
        if arg2 == None:
            await ctx.send('You have to specify a playlist to delete')
            return

    elif arg1 in ['unload', 'ul']:
        playlist = oldPlaylist
        currentPlaylist = None

    elif arg1 in ['list', 'ls']:
        embed = discord.Embed(title='Saved playlists', colour=discord.Colour.blurple())
        for i in savedPlaylists.keys():
            embed.add_field(name=i, value='Description, perhaps no of songs and playtime or smth', inline=False)
        await ctx.send(embed=embed)


####################### PURGE ########################

@bot.command("purge", aliases=[])
async def purge(ctx, action=None, actionParam1=None):
    if not check_authorization(ctx):
        await ctx.send('You dont have permission to use this command!', delete_after=10)
        await ctx.message.delete()
        return

    if action == None and ctx.message.reference == None:
        embed = discord.Embed(title="Purge command", colour=discord.Colour.blue())
        embed.add_field(name="Options",
                        value="-purge <MSG-COUNT>: Deletes <MSG-COUNT> messages (has to be smaller than 100000)\n" +
                              "-purge <MSG-ID>: Deletes all messages until the message with the id: <MSG-ID>\n" +
                              "-purge: Deletes all messages until the message replied to",

                        inline=False)

        await ctx.send(embed=embed)
        await ctx.message.delete()
        return

    try:
        action = int(action)
        if action < 100000 and ctx.message.reference == None:
            await ctx.channel.purge(limit=action + 1)

        elif action > 100000 and ctx.message.reference == None:
            history = await ctx.channel.history(limit=100).flatten()
            msg = [msgCount for msgCount in range(len(history)) if history[msgCount].id == action]

            if len(msg) == 0:
                await ctx.send('No message with the given id within 100 messages found', delete_after=10)
            else:
                await ctx.channel.purge(limit=msg[0])

    except:
        if action == None and ctx.message.reference != None:
            messages = 0
            history = await ctx.channel.history(limit=100).flatten()
            msg = [msgCount for msgCount in range(len(history)) if
                   history[msgCount].id == ctx.message.reference.message_id]
            if len(msg) == 0:
                await ctx.send('No message matching your reply within 100 messages found', delete_after=10)
            else:
                await ctx.channel.purge(limit=msg[0])

        if action == 'untilid' and actionParam1 != None:
            messages = 0
            history = await ctx.channel.history(limit=100).flatten()
            for i in history:
                messages += 1
                if i.id == int(actionParam1):
                    await ctx.channel.purge(limit=messages)
                    return
            await ctx.send('No message with the given id within 100 messages found', delete_after=10)

        if action == 'untilreply' and ctx.message.reference != None:
            messages = 0
            history = await ctx.channel.history(limit=100).flatten()
            history = [msg.id for msg in history if msg.id == ctx.message.reference.message_id]
            print(history)
            for i in history:
                messages += 1
                if i.id == ctx.message.reference.message_id:
                    await ctx.channel.purge(limit=messages)
                    return
            await ctx.send('No message matching your reply within 100 messages found', delete_after=10)


####################### STARBOARD ########################

@bot.event
async def on_raw_reaction_add(payload):
    f = open('data/starboardMsgs.txt', 'r')
    starboardMessages = f.readline()
    f.close()
    try:
        starboardMessages = json.loads(starboardMessages)
    except:
        starboardMessages = {}

    print(starboardMessages)

    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    for reaction in message.reactions:
        if reaction.emoji == '⭐':
            emojiCount = reaction.count
    if emojiCount < 2:
        return

    starboardChannel = await bot.fetch_channel(879703712740827186)

    if payload.emoji.name == '⭐' and payload.guild_id == 702452892241625099 and not str(
            payload.message_id) in starboardMessages.keys():
        embed = discord.Embed(colour=discord.Colour.purple())
        if len(message.attachments) > 0:
            embed.set_image(url=str(message.attachments[0]))
            print(message.attachments[0])

        serverID = channel.guild.id
        channelId = payload.channel_id
        msgId = payload.message_id
        originalMsgUrl = f'https://discord.com/channels/{serverID}/{channelId}/{msgId}'

        embed.add_field(name=message.author, value=f'[Original]({originalMsgUrl})')
        embed.add_field(name='‎‏‏‎ ‎', value=str(message.content), inline=False)  # '‎‏‏‎ ‎'
        # embed.add_field(name='‎‏‏‎ ‎',value='Starcounter')
        embed.set_footer(text='Starcounter')

        msg = await starboardChannel.send(embed=embed)

        starboardMessages[str(payload.message_id)] = msg.id  # {'originalMsgId':'starboardMsgID'}
        print(starboardMessages)
        f = open('data/starboardMsgs.txt', 'w')
        f.write(json.dumps(starboardMessages))
        f.close()

    editMsg = await starboardChannel.fetch_message(int(starboardMessages[str(payload.message_id)]))
    # await editMsg.edit(embed=editMsg.embeds[0].set_field_at(index=2,name='‎‏‏‎ ‎',value=f'⭐️ {emojiCount} | {payload.message_id}'))
    await editMsg.edit(embed=editMsg.embeds[0].set_footer(text=f'⭐️ {emojiCount} | {payload.message_id}'))

    # vielleicht doch set_footer benutzen damit das bild über der letzten zeile ist

    # Hallo @ElectroBOOMer⚡, es gibt jetzt ein #starboard - System. D.H, wenn ihr eine Nachricht oder ein Meme seht, 
    # die ihr besonders gut/witzig/wichtig/bemerkenswert findet und sie für die Nachwelt in einem extra Kanal behalten wollt,
    # reagiert ihr einfach mit einem Stern auf diese Nachricht. Nachrichten mit ZWEI Sternen werden in den Starboard-Kanal 
    # geschrieben und sind dort schön in einem Kanal zusammengefasst.


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.emoji.name == '⭐':
        pass


bot.remove_command("help")


@bot.command("help")
async def help(ctx):
    embed = discord.Embed(title="Pipe-Bot", description="Mainly to play music", colour=discord.Colour.blue())
    embed.add_field(name="Music:", value="-play <TITLE/LINK>", inline=True)
    await ctx.send(embed=embed)


@bot.command('printReply')
async def printMsg(ctx):
    channel = await bot.fetch_channel(ctx.message.reference.channel_id)
    message = await channel.fetch_message(ctx.message.reference.message_id)
    await ctx.send(message)
    await ctx.send(str(message.content))
    print(str(message.content))
    await ctx.send(message.attachments)


def sp_noise(image, prob):
    '''
    Add salt and pepper noise to image
    prob: Probability of the noise
    '''
    output = np.zeros(image.shape, np.uint8)
    thres = 1 - prob
    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            rdn = random.random()
            if rdn < prob:
                output[i][j] = 0
            elif rdn > thres:
                output[i][j] = 255
            else:
                output[i][j] = image[i][j]
    return output


@bot.command('deepfry')
async def deepfry(ctx, amount=6, iterations=1, noiseType=0.05):
    start = time.time()
    await ctx.send('DEEPFRYING NOISE INTENSIFIES')
    msg = await ctx.send('...')
    try:
        img_url = ctx.message.attachments[0].url
        img = Image.open(requests.get(img_url, stream=True).raw)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(amount)
        img.save('file.png')

        image = cv2.imread('file.png')  # Only for grayscale image
        noise_img = sp_noise(image, float(noiseType))  # 0.05
        cv2.imwrite('file.png', noise_img)

        for i in range(iterations):
            img = Image.open('file.png')
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(amount)

            if i % 10 == 0 and iterations > 50:
                try:
                    await msg.edit(f'Already {i}/{iterations} iterations done...')
                except Exception:
                    pass

            if time.time() - start > 45:
                await ctx.send(f'That took too long to process, i\'m sorry, stopping after {i} iterations',
                               delete_after=10)
                break

        await msg.delete()
        if iterations > 50:
            await ctx.send(f'**DONE!** <@!{ctx.author.id}>', file=discord.File(open('file.png', 'rb')))
        else:
            await ctx.send(file=discord.File(open('file.png', 'rb')))

    except Exception as e:
        await ctx.send(e)


# @bot.listen('on_message')
# async def onMsg(message):


bot.run('ODY0MTk4NjY4NTMzNDk3ODc3.YOx9ug.TFSxDOsWngQcMuICmK01AQFIzB8')
