import asyncio
import os
import re
import shutil
import subprocess
import time

import click
import httpx
import m3u8

from tvod.console import console
from tvod.helpers.binaries import Binaries
from tvod.helpers.downloaders import aria2c
from tvod.helpers.exceptions import DownloaderException, TwitchException
from tvod.helpers.paths import DefaultPaths
from tvod.helpers.proxy import Proxy
from tvod.twitch.client import Client


@click.command()
@click.argument('url')
@click.option('-p', '--proxy')
@click.option('-q', '--quality', type=click.Choice(['1080p', '720p', '480p', '360p', '160p']))
@click.pass_context
def cli(ctx, url, proxy=None, quality=None):
    """Download VOD and clips"""

    try:
        url_type, url_id = Client.parse_url(url)
    except TwitchException as e:
        return console.error(f'Error: {e}')

    if proxy:
        try:
            proxy = Proxy.from_string(proxy)
        except ValueError as e:
            return console.error(f'Error: {e}')

    ctx.client = Client(proxy=proxy)

    if url_type == 'videos':
        download_vod(ctx, url_id, quality, proxy)
    elif url_type == 'clip':
        download_clip(ctx, url_id, quality, proxy)
    else:
        console.error(f'Error: {url_type}s not handled yet')


def download_vod(ctx, vod_id, quality, proxy):
    with console.status(
        '[white]Fetching VOD data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            vod = ctx.client.get_vod_data(vod_id)
        except TwitchException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download of '
        f'[info]{vod.title}[/info]'
        f' by '
        f'[info]{vod.streamer}[/info]',
        style='white'
    )

    stream = vod.filter_quality(quality)

    if not stream:
        return console.error(f'Error: Unable to find {quality} stream')

    with ctx.client.session.get_session() as session:
        req = session.get(stream.url)

    if req.status_code != httpx.codes.OK:
        return console.error('Error: Unable to fetch stream')

    parsed_stream = m3u8.loads(req.text)

    temp_dir = os.path.join(DefaultPaths.get_temp_path(), f'{vod.id}.{stream.resolution}')
    temp_file = os.path.join(
        DefaultPaths.get_temp_path(),
        f'{vod.id}.{stream.resolution}',
        f'{vod.id}.{stream.resolution}.ts'
    )

    def clean_string(text):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"*]+', ' ', text))

    downloaded_file = os.path.join(
        DefaultPaths.get_download_path(),
        f'{clean_string(vod.title)} - {clean_string(vod.streamer)} [{stream.resolution}].mp4'
    )

    if os.path.exists(downloaded_file):
        os.unlink(downloaded_file)

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    with console.status(
        '[white]Download [info]raw ts segments',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            asyncio.run(aria2c.download(
                [
                    {'filename': segment.uri, 'url': f'{stream.base_url}/{segment.uri}'}
                    for segment in parsed_stream.segments
                ],
                temp_dir,
                proxy
            ))
        except DownloaderException as e:
            shutil.rmtree(temp_dir)
            return console.error(f'Error: {e}')

    with console.status(
        '[white]Merge [info]segments[/info] into [info]ts file',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            with open(temp_file, 'w+b') as f:
                for segment in parsed_stream.segments:
                    segment_path = os.path.join(temp_dir, segment.uri)

                    with open(segment_path, 'rb') as ff:
                        f.write(ff.read())
        except OSError:
            shutil.rmtree(temp_dir)
            return console.error('Error: Unable to merge segments')

    with console.status(
        '[white]Convert [info]raw ts file[/info] into [info]mp4 file',
        spinner_style='info',
        spinner='arc'
    ):
        ffmpeg = subprocess.Popen([
            Binaries.get('ffmpeg'), '-y',
            '-i', temp_file,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            '-map_metadata', '-1',
            downloaded_file
        ], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        ffmpeg.wait()
        shutil.rmtree(temp_dir)

        if ffmpeg.returncode != 0:
            return console.error('Error: Unable to convert file')

    console.print(
        'Successfully downloaded '
        f'[info]{vod.title}[/info]'
        f' by '
        f'[info]{vod.streamer}[/info]',
        style='white'
    )


def download_clip(ctx, clip_id, quality, proxy):
    with console.status(
        '[white]Fetching clip data ...',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            clip = ctx.client.get_clip_data(clip_id)
        except TwitchException as e:
            time.sleep(1)
            return console.error(f'Error: {e}')

    console.print(
        f'Starting download of '
        f'[info]{clip.title}[/info]'
        f' by '
        f'[info]{clip.streamer}[/info]',
        style='white'
    )

    stream = clip.best_stream if not quality else next(filter(
        lambda s: s.resolution == quality,
        clip.streams
    ), None)

    if not stream:
        return console.error(f'Error: Unable to find {quality} for this clip')

    temp_dir = os.path.join(DefaultPaths.get_temp_path(), f'{clip.id}.{stream.resolution}')

    def clean_string(text):
        return re.sub(r' +', ' ', re.sub(r'[/\\:@?<>"*]+', ' ', text))

    downloaded_file = os.path.join(
        DefaultPaths.get_download_path(),
        f'{clean_string(clip.title)} - {clean_string(clip.streamer)} [{stream.resolution}].mp4'
    )

    if os.path.exists(downloaded_file):
        os.unlink(downloaded_file)

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    with console.status(
        '[white]Download [info]raw clip',
        spinner_style='info',
        spinner='arc'
    ):
        try:
            asyncio.run(aria2c.download(
                [
                    {'filename': f'{clip.id}.mp4', 'url': stream.url}
                ],
                temp_dir,
                proxy
            ))
        except DownloaderException as e:
            shutil.rmtree(temp_dir)
            return console.error(f'Error: {e}')

    with console.status(
        '[white]Convert [info]raw clip file[/info] into [info]clean mp4 file',
        spinner_style='info',
        spinner='arc'
    ):
        ffmpeg = subprocess.Popen([
            Binaries.get('ffmpeg'), '-y',
            '-i', os.path.join(temp_dir, f'{clip.id}.mp4'),
            '-c', 'copy',
            '-map_metadata', '-1',
            downloaded_file
        ], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        ffmpeg.wait()
        shutil.rmtree(temp_dir)

        if ffmpeg.returncode != 0:
            return console.error('Error: Unable to convert file')

    console.print(
        'Successfully downloaded '
        f'[info]{clip.title}[/info]'
        f' by '
        f'[info]{clip.streamer}[/info]',
        style='white'
    )
