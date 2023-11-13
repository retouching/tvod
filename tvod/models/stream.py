from typing import Union

from pydantic import BaseModel


class Stream(BaseModel):
    height: int
    width: int
    url: str
    fps: Union[int, None] = None

    @property
    def base_url(self):
        to_remove = self.url.split('/')[-1]
        return self.url.replace(f'/{to_remove}', '')

    @property
    def resolution(self):
        quality = self.height

        if self.width in [192, 256] and self.height <= 144:
            quality = 144

        elif self.width in [320, 352, 426] and self.height <= 240:
            quality = 240

        elif self.width in [480, 568, 640] and self.height <= 360:
            quality = 360

        elif self.width == 960 and self.height <= 540:
            quality = 540

        elif self.width in [1024, 960, 768, 720, 704, 544, 480] and self.height <= 576:
            quality = 576

        elif self.width in [960, 1280] and self.height <= 720:
            quality = 720

        elif self.width in [1920, 1440, 2560, 2160, 2400] and self.height <= 1080:
            quality = 1080

        elif self.width in [4096, 3840] and self.height <= 2160:
            quality = 2160

        return f'{str(quality)}p'
