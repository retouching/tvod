import asyncio
import os
import subprocess

from tvod.helpers.binaries import Binaries
from tvod.helpers.enums.protocol import Protocol
from tvod.helpers.exceptions import DownloaderException
from tvod.helpers.proxy import Proxy


async def download(urls, download_path, proxy=None):
    if proxy:
        if type(proxy) != Proxy:
            raise ValueError('Invalid proxy provided')
        if proxy.proto != Protocol.HTTP:
            # aria2c only support HTTP as proxy protocol
            # use pproxy to bypass this limitation
            async with proxy.get_pproxy() as pproxy:
                return await download(urls, download_path, pproxy)

    try:
        urls = iter(urls)
    except TypeError:
        raise ValueError("Can't iterate urls")

    if not os.path.exists(download_path):
        os.makedirs(download_path)

    aria2c_txt_path = os.path.join(download_path, 'aria2c.txt')
    aria2c_txt_content = ''

    for url in urls:
        if type(url) != dict:
            raise ValueError('Invalid urls provided')

        if 'url' not in url or 'filename' not in url:
            raise ValueError('Invalid urls provided')

        aria2c_txt_content += f'{url.get("url")}\n' \
                              f'   out={url.get("filename")}\n' \
                              f'   dir={download_path}\n'

    with open(aria2c_txt_path, 'w+', encoding='utf-8') as f:
        f.write(aria2c_txt_content)

    args = [
        '-c',  # Continue downloading a partially downloaded file
        '--remote-time',  # Retrieve timestamp of the remote file from the and apply if available
        '-x', '16',  # The maximum number of connections to one server for each download
        '-j', '16',  # The maximum number of parallel downloads for every static (HTTP/FTP) URL
        '-s', '16',  # Download a file using N connections
        '--min-split-size', '20M',  # effectively disable split if segmented
        '--allow-overwrite=true',
        '--auto-file-renaming=false',
        '--retry-wait', '2',  # Set the seconds to wait between retries.
        '--max-tries', '5',
        '--max-file-not-found', '0',
        '--summary-interval', '0',
        '-i', aria2c_txt_path
    ]

    if proxy:
        args += ["--all-proxy", str(proxy)]

    proc = await asyncio.create_subprocess_exec(
        Binaries.get('aria2c'),
        *args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    await proc.wait()

    os.unlink(aria2c_txt_path)

    if proc.returncode != 0:
        for url in urls:
            filepath = os.path.join(download_path, url.get('filename'))

            for file in [filepath, f'{filepath}.aria2c']:
                if os.path.exists(file):
                    try:
                        os.unlink(filepath)
                    except OSError:
                        pass

        raise DownloaderException('Unable to download urls')
