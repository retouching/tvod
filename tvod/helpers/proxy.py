import re
from contextlib import contextmanager
from typing import Union

import pproxy
from pydantic import BaseModel

from tvod.helpers.enums.protocol import Protocol


class Proxy(BaseModel):
    proto: Protocol = Protocol.HTTP
    hostname: str
    port: Union[int, None] = None
    username: Union[str, None] = None
    password: Union[str, None] = None

    def __str__(self):
        val = f'{self.proto.value}://'

        if self.hostname and self.password:
            val += f'{self.username}:{self.password}@'

        val += self.hostname

        if self.port:
            val += f':{self.port}'

        return val

    @staticmethod
    def from_string(data):
        if type(data) != str:
            raise ValueError('Invalid proxy provided')

        parsed = re.match(
            r'^(?P<proto>http|socks5|socks4)://'
            r'((?P<username>[^@!:/\\]+):'
            r'(?P<password>[^@!:\\]+)@)?'
            r'(?P<hostname>[^@!:\\]+):?'
            r'(?P<port>[0-9]+)?$',
            data
        )
        if not parsed:
            raise ValueError('Invalid proxy provided')

        parsed = parsed.groupdict()

        return Proxy(
            proto=Protocol.get(parsed.get('proto').upper()),
            hostname=parsed.get('hostname'),
            port=int(parsed.get('port')) if parsed.get('port') else None,
            username=parsed.get('username'),
            password=parsed.get('password')
        )

    @contextmanager
    async def get_pproxy(self):
        server = pproxy.Server('http://localhost:0')
        remote = pproxy.Connection(str(self))
        handler = await server.start_server({'rserver': [remote]})

        try:
            port = handler.sockets[0].getsockname()[1]
            yield Proxy.from_string(f'http://localhost:{port}')
        finally:
            handler.close()
            await handler.wait_closed()
