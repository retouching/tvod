from typing import List

from pydantic import BaseModel

from tvod.models.stream import Stream


class VOD(BaseModel):
    id: str
    title: str
    streamer: str
    streams: List[Stream]
