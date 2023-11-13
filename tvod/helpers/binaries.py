import shutil

from tvod.helpers.exceptions import BinaryException


class Binaries:
    @staticmethod
    def get(binary_name):
        binary = shutil.which(binary_name)
        if not binary:
            raise BinaryException(f'Unable to find {binary_name}')
        return binary

    @staticmethod
    def check_binaries():
        for binary_name in ['ffmpeg']:
            Binaries.get(binary_name)
