import datetime
import re
import urllib.parse

import httpx
import m3u8

from tvod.cacher import Cacher
from tvod.constants import TWITCH_STREAMS_URL, TWITCH_VOD_QUALITIES
from tvod.helpers.exceptions import TwitchException
from tvod.helpers.paths import DefaultPaths
from tvod.helpers.proxy import Proxy
from tvod.models.vod import Stream, VOD
from tvod.twitch.session import Session


class Client:
    KEEP_IN_CACHE = 3000

    def __init__(self, cache_path=None, proxy=None):
        if proxy and type(proxy) != Proxy:
            raise ValueError('Invalid proxy provided')

        self.proxy = proxy
        self.cache = Cacher(
            'twitch',
            (cache_path or DefaultPaths.get_cache_path())
        )
        self.session = Session(self)

    @staticmethod
    def parse_url(url):
        match = re.match(
            r'https?://(www\.)?twitch\.tv/([^/]+/)?(videos|clip)/([^? ]+)',
            url
        )

        if not match:
            raise TwitchException('Invalid URL provided')

        return match.group(3), match.group(4)

    def get_vod_data(self, vod_id, from_cache=True):
        if type(vod_id) != str or len(vod_id) < 1:
            raise TwitchException('Invalid VOD id')

        if from_cache:
            track_or_exc = self.cache.get(f'vod:{vod_id}')

            if track_or_exc:
                if type(track_or_exc) == TwitchException:
                    raise track_or_exc
                return track_or_exc

        video_playback, vod = self.session.create_request([
            {
                'query': """
                    query ($vodID: ID!) {
                        videoPlaybackAccessToken(
                            id: $vodID,
                            params: {
                                platform: "web",
                                playerBackend: "mediaplayer",
                                playerType: "site"
                            }
                        ) {
                            value,
                            signature
                        }
                    }
                """,
                'variables': {'vodID': vod_id}
            },
            {
                'query': """
                    query ($vodID: ID!) {
                        video(id: $vodID) {
                            broadcastType,
                            seekPreviewsURL,
                            owner { displayName login },
                            title,
                            createdAt
                        }
                    }
                """,
                'variables': {'vodID': vod_id}
            }
        ])

        video_playback = video_playback.get('data').get('videoPlaybackAccessToken')
        vod = vod.get('data').get('video')

        if not video_playback or not vod:
            exc = TwitchException('Invalid or unavailable VOD data')
            self.cache.set(f'vod:{vod_id}', exc, Client.KEEP_IN_CACHE)
            raise exc

        with self.session.get_session() as session:
            req = session.get(f'{TWITCH_STREAMS_URL}/{vod_id}.m3u8', params={
                'token': video_playback.get('value'),
                'sig': video_playback.get('signature'),
                'allow_source': 'true'
            })

        streams = []

        if req.status_code == httpx.codes.OK:
            playlist = m3u8.parser.parse(req.text)

            for stream in playlist.get('playlists'):
                width, height = stream.get('stream_info').get('resolution').split('x')
                streams.append(Stream(**{
                    'height': height,
                    'width': width,
                    'url': stream.get('uri')
                }))
        elif req.status_code == httpx.codes.FORBIDDEN:
            if not vod.get('seekPreviewsURL'):
                raise TwitchException('Unable to fetch VOD data')

            parsed_url = urllib.parse.urlparse(vod.get('seekPreviewsURL'))

            try:
                paths = parsed_url.path.split('/')
                stream_id = paths[paths.index('storyboards') - 1]
            except ValueError:
                raise TwitchException('Unable to fetch VOD data')

            is_old_upload = (
                (datetime.datetime.fromisoformat(
                    '2023-02-10'
                ).timestamp() * 1000) - (datetime.datetime.strptime(
                    vod.get('createdAt'),
                    '%Y-%m-%dT%H:%M:%SZ'
                ).timestamp() * 1000)
            ) / (1000 * 3600 * 24) > 7

            for quality_key, quality in TWITCH_VOD_QUALITIES:
                if vod.get('broadcastType') == 'HIGHLIGHT':
                    url = f'https://{parsed_url.netloc}/{stream_id}/{quality_key}/highlight-{vod_id}.m3u8'
                elif vod.get('broadcastType') == 'UPLOAD' and is_old_upload:
                    url = f'https://{parsed_url.netloc}/{vod.get("owner").get("login")}/{vod_id}/' \
                          f'{stream_id}/{quality_key}/index-dvr.m3u8'
                else:
                    url = f'https://{parsed_url.netloc}/{stream_id}/{quality_key}/index-dvr.m3u8'

                with self.session.get_session() as session:
                    req = session.get(url)

                if req.status_code == httpx.codes.OK:
                    streams.append(Stream(**{
                        **quality,
                        'url': url
                    }))
        else:
            raise TwitchException('Unable to fetch VOD data')

        if len(streams) < 1:
            raise TwitchException('Unable to fetch VOD data')

        vod = VOD(**{
            'id': vod_id,
            'title': vod.get('title'),
            'streamer': vod.get('owner').get('displayName'),
            'streams': streams
        })

        self.cache.set(f'vod:{vod_id}', vod, Client.KEEP_IN_CACHE)

        return vod

    def get_clip_data(self, clip_slug, from_cache=True):
        if type(clip_slug) != str or len(clip_slug) < 1:
            raise TwitchException('Invalid clip id')

        if from_cache:
            track_or_exc = self.cache.get(f'clip:{clip_slug}')

            if track_or_exc:
                if type(track_or_exc) == TwitchException:
                    raise track_or_exc
                return

        clip_data = self.session.create_request([
            {
                'query': """
                    query ($clipSlug: ID!) {
                        clip(slug: $clipSlug) {
                            broadcaster { displayName },
                            title
                            videoQualities { quality, sourceURL }
                            playbackAccessToken(
                                params: {
                                    platform: "web",
                                    playerBackend: "mediaplayer",
                                    playerType: "site"
                                }
                            ) {
                                value,
                                signature
                            }
                        }
                    }
                """,
                'variables': {'clipSlug': clip_slug}
            }
        ])[0].get('data').get('clip')

        print(clip_data)

        video_playback = clip_data.get('playbackAccessToken')
        clip_videos = clip_data.get('videoQualities')

        if not video_playback or not clip_videos:
            exc = TwitchException('Invalid or unavailable VOD data')
            self.cache.set(f'clip:{clip_slug}', exc, Client.KEEP_IN_CACHE)
            raise exc

        clip = VOD(**{
            'id': clip_slug,
            'title': clip_data.get('title'),
            'streamer': clip_data.get('broadcaster').get('displayName'),
            'streams': [
                Stream(**{
                    'height': int(video.get('quality')),
                    'width': {
                        '1080': 1920,
                        '720': 1280,
                        '480': 854,
                        '360': 640,
                        '160': 284
                    }[video.get('quality')],
                    'url': f'{video.get("sourceURL")}'
                           f'?token={urllib.parse.quote(video_playback.get("value"))}'
                           f'&sig={video_playback.get("signature")}'
                })
                for video in clip_videos
            ]
        })

        self.cache.set(f'vod:{clip_slug}', clip, Client.KEEP_IN_CACHE)

        return clip
