from typing import List

from pydantic import BaseModel

from tvod.models.stream import Stream


class VOD(BaseModel):
    id: str
    title: str
    streamer: str
    streams: List[Stream]

    @property
    def best_stream(self):
        return next(iter(sorted(self.streams, key=lambda s: int(s.resolution.replace('p', '')), reverse=True)), None)
