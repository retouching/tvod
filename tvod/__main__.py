import sys

from tvod.commands.commands import Commands
from tvod.console import console
from tvod.helpers.binaries import Binaries, BinaryException


def main():
    if sys.version_info.major < 3 or sys.version_info.minor < 9:
        return console.error('Error: Python 3.9 or newer is required')

    try:
        Binaries.check_binaries()
    except BinaryException:
        return console.error('Error: Some binaries missing')

    Commands()()


if __name__ == '__main__':
    main()
