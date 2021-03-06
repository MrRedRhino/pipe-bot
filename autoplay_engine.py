import json
import urllib.request
import random
import youtube_dl
from playlistEntry import PlaylistEntry

# count = 50
API_KEY = 'AIzaSyAHplK7tFwChb13FJbFZ7ak_jLnnxTPiYc'
# cid = 'UCG7AaCh_CiG6pq_rRDNw72A'


def find_matching_song(count, cid):
    url_data = 'https://www.googleapis.com/youtube/v3/search?key={}&channelId={}&part=snippet,id&order=date&maxResults={}&type=video'.format(API_KEY, cid, count)
    web_url = urllib.request.urlopen(url_data)
    data = web_url.read()
    results = json.loads(data.decode(web_url.info().get_content_charset('utf-8')))
    found = False
    while not found:
        data = results['items'][random.randint(0, len(results['items']) - 1)]
        video_id = (data['id']['videoId'])
        with youtube_dl.YoutubeDL({'quiet': True}) as ydl:
            entries = ydl.extract_info(str(f'ytsearch:https://youtu.be/{video_id}'), download=False)['entries']
            if len(entries) > 0:
                if 150 < entries[0]['duration'] < 300:
                    found = True
                    info = entries[0]
                    url = info['formats'][0]['url']
                    name = info['title']
                    thumbnail = info['thumbnail']
                    duration = info['duration']
                    vid = info['id']
                    channel_id = info['channel_id']
                    tags = info['tags']
                    return PlaylistEntry(url, name, thumbnail, duration, vid, channel_id, tags)
