class PlaylistEntry:
    def __init__(self, stream_link, video_name, thumbnail, duration, video_id, channel_id):
        self.stream_link = stream_link
        self.video_name = video_name
        self.thumbnail = thumbnail
        self.duration = duration
        self.vid = video_id
        self.channel_id = channel_id


class DirectStream:
    def __init__(self, stream_link):
        self.stream_link = stream_link
