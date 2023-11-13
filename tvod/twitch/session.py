import re

import httpx

from tvod.constants import TWITCH_GQL_URL, TWITCH_URL
from tvod.helpers.exceptions import TwitchException


class Session:
    def __init__(self, client):
        self.client = client
        self._twitch_client_id = self.client.cache.get('twitch_client_id')

    @property
    def twitch_client_id(self):
        if not self._twitch_client_id:
            with self.get_session() as session:
                req = session.get(TWITCH_URL)

            if 'clientId' not in req.text:
                raise TwitchException('Unable to find twitch client id')

            client_id = re.search(r'clientId="([^"]+)', req.text)
            if not client_id:
                raise TwitchException('Unable to find twitch client id')

            self.client.cache.set('twitch_client_id', client_id.group(1), self.client.KEEP_IN_CACHE)
            self._twitch_client_id = client_id.group(1)
        return self._twitch_client_id

    def get_session(self):
        return httpx.Client(proxies=self.client.proxy)

    def create_request(self, data):
        with self.get_session() as session:
            req = session.post(
                TWITCH_GQL_URL,
                json=data,
                headers={'Client-Id': self.twitch_client_id}
            )

        if req.status_code != httpx.codes.OK:
            raise TwitchException('Unable to create GQL request')

        return req.json()
