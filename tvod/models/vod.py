from typing import List

from pydantic import BaseModel

from tvod.models.stream import Stream


class VOD(BaseModel):
    id: str
    title: str
    streamer: str
    streams: List[Stream]

    def filter_quality(self, quality=None):
        streams = sorted(self.streams, key=lambda s: int(s.resolution.replace('p', '')), reverse=True)

        if len(streams) < 1:
            return None

        if not quality:
            quality = streams[0].resolution

        return next(iter(sorted(filter(
            lambda s: s.resolution == quality,
            streams
        ), key=lambda s: s.fps or 60, reverse=True)), None)
