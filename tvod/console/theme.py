from rich.theme import Theme


class TVODTheme(Theme):
    def __init__(self):
        super().__init__({
            # Define colors
            'dark_violet': '#6441A4',
            'white': '#ecf0f1',
            'red': '#c0392b',
            'orange3': '#d35400',

            # define rules
            'rule.text': 'dark_violet',
            'rule.line': 'white',
            'danger': 'bold red',
            'info': 'bold dark_violet',
            'warn': 'bold orange3',
            'bar.complete': 'dark_violet',
            'bar.pulse': 'dark_violet',
            'bar.finished': 'dark_violet',
            'progress.percentage': 'bold dark_violet',
            'progress.remaining': 'bold dark_violet',
            'progress.description': 'white'
        }, inherit=True)
