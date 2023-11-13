TVOD_NAME = 'TwitchVOD'
TVOD_VERSION = '1.0.0'
TVOD_VERSION_NAME = 'Obsidian'

TWITCH_STREAMS_URL = 'https://usher.ttvnw.net/vod'
TWITCH_URL = 'https://www.twitch.tv'
TWITCH_GQL_URL = 'https://gql.twitch.tv/gql'
TWITCH_VOD_QUALITIES = [
    ('chunked', {'width': 1920, 'height': 1080},),
    ('1080p30', {'width': 1920, 'height': 1080, 'fps': 30},),
    ('1080p60', {'width': 1920, 'height': 1080, 'fps': 60},),
    ('720p30', {'width': 1280, 'height': 720, 'fps': 30},),
    ('720p60', {'width': 1280, 'height': 720, 'fps': 60},),
    ('480p30', {'width': 854, 'height': 480, 'fps': 30},),
    ('360p30', {'width': 640, 'height': 360, 'fps': 30},),
    ('160p30', {'width': 284, 'height': 160, 'fps': 30},),
]
