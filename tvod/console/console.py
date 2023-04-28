from rich.console import Console as _Console

from tvod.console.theme import TVODTheme


class Console(_Console):
    def __init__(self):
        super().__init__(
            color_system='auto',
            theme=TVODTheme()
        )

    def error(self, *args, **kwargs):
        self.print(*args, **kwargs, style='danger')
        exit(1)

    def warn(self, *args, **kwargs):
        self.print(*args, **kwargs, style='warn')
        exit(1)
