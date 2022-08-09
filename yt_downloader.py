# ------------------------------ # Credits # ------------------------------ #
# Written by ELM with help from Gabe
# This software is licensed under the MIT License. All rights reserved.
#
# Huge thanks to https://tyrrrz.me/blog/reverse-engineering-youtube for information about how YouTube processes
# HTTP requests.

# ------------------------------ # Imports # ------------------------------ #
from __future__ import annotations
import os
import subprocess
import time
import requests
import re
import threading
from requests.structures import CaseInsensitiveDict


# ------------------------------ # Exceptions and Errors # ------------------------------ #
class InvalidLinkError(Exception):
    pass


# ------------------------------ # Main Class # ------------------------------ #
class YouTubeVideo(object):

    def __init__(self, url):
        self.API_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
        self.url = url
        self.id = self.get_video_id()
        self.video_metadata = self.get_metadata()
        self.resolution_data, self.audio_data = self.get_all_available_resolutions()
        self.sts = None  # self.get_video_sts()
        self.downloaded_video_data_segments = {}
        self.downloaded_audio_data_segments = {}
        self.title = self.get_video_name()
        self.output_filetype = 0
        self.avalible_output_formats = [
            '.mp4',
            '.mkv',
            '.mov',
            '.av1'
        ]
        self.ffmpeg_preset = 5
        self.ffmpeg_presets = [
            'ultrafast',
            'superfast',
            'veryfast',
            'faster',
            'fast',
            'medium',
            'slow',
            'slower',
            'veryslow',
        ]
        self.start_time = 0
        self.last_time = 0

    def get_video_id(self) -> str:
        pattern = re.compile(
            r'https?:\/{1,2}(www)?.(music\.)?youtube.com\/watch\?v=(?P<video_id>[a-zA-Z0-9\-]+)(&.*?)?')
        match_object = pattern.match(self.url)
        try:
            id_ = match_object.group('video_id')
            return id_
        except:
            raise InvalidLinkError()

    def get_video_name(self) -> str:
        return self.video_metadata["videoDetails"]["title"]

    def get_video_sts(self, url_html_content) -> str:
        p = re.compile(r"\"(sts)|(STS)\": ?(?P<sts>\w+),")
        mo = p.search(url_html_content)
        try:
            sts = mo.group('sts')
            return sts
        except:
            raise InvalidLinkError()

    def get_metadata(self):
        print('Fetching Video Information From Server... ', end='')
        to_url = f"https://youtubei.googleapis.com/youtubei/v1/player?key={self.API_KEY}"

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                                'Chrome/102.0.5005.115 Safari/537.36 OPR/88.0.4412.85 '
        data = f'''
                    {{
                     "context": {{
                       "client": {{
                        "hl": "en",
                        "clientName": "WEB",
                        "clientVersion": "2.20210721.00.00",
                        "mainAppWebInfo": {{
                            "graftUrl": "/watch?v={self.id}"
                        }}
                       }}
                      }},
                      "videoId": "{self.id}"
                    }}'''

        resp = requests.post(to_url, headers=headers, data=data)
        print('\033[38;2;0;255;0mOK\033[0m', end='\n')
        return resp.json()

    def get_all_available_resolutions(self) -> dict[str: str]:
        print('Fetching Resolution Data From Server... ', end='')
        json_data = self.video_metadata['streamingData']
        streaming_json_data = json_data['formats'] + json_data['adaptiveFormats']
        output_dict = {}
        audio_output_dict = {}
        for i, v in enumerate(streaming_json_data):
            isVideoMp4 = 'video/mp4' in v['mimeType']
            isAudioMp4 = 'audio/mp4' in v['mimeType']
            try:
                audioType = v['audioQuality']
            except:
                audioType = None

            if 'qualityLabel' in v and 'contentLength' in v:
                if isVideoMp4 and audioType is None:
                    output_dict.update({f'{v["qualityLabel"]}':
                                            {'width': v['width'], 'height': v['height'], 'fps': v['fps'],
                                             'contentLength': v['contentLength'], 'url': v['url'],
                                             'mimeType': v['mimeType']}})
            if audioType is not None and isAudioMp4:
                audio_output_dict.update({f'{v["audioQuality"]}':
                                              {'contentLength': v['contentLength'], 'url': v['url'],
                                               'mimeType': v['mimeType']}})
        print('\033[38;2;0;255;0mOK\033[0m', end='\n')
        return output_dict, audio_output_dict

    def download_data_segment(self, quality, data_range, segment_number, t='video'):
        if t == 'video':
            video_output_url = self.resolution_data[quality]['url']
        elif t == 'audio':
            video_output_url = self.audio_data[quality]['url']

        authority = re.search(r"https?:\/{1,2}(?P<authority>[a-zA-Z0-9\-\.]*?)\/", video_output_url).group('authority')

        output_request_headers = {
            "authority": authority,
            "method": 'GET',
            "path": video_output_url.lstrip(authority),
            "scheme": "https",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "range": f"bytes={data_range}",
            "sec-ch-ua-mobile": '?0',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)" \
                          "Chrome/102.0.5005.115 Safari/537.36 OPR/88.0.4412.85"
        }
        out = requests.get(video_output_url, headers=output_request_headers, stream=True).content

        if t == 'video':
            self.downloaded_video_data_segments[data_range] = out
        elif t == 'audio':
            self.downloaded_audio_data_segments[data_range] = out

    def download_video(self, quality):
        self.start_time = time.time()
        # ------------------------------ video download --------------------------- #
        byte_segment_len = int(int(self.resolution_data[quality]['contentLength'])/70)
        for i in range((int(self.resolution_data[quality]['contentLength']) // byte_segment_len) + 1):
            range_ = f'{byte_segment_len * i + (0 if (i == 0) else 1)}-' \
                     f'{byte_segment_len * (i + 1)}'
            self.downloaded_video_data_segments.update({range_: threading.Thread(target=self.download_data_segment,
                                                                                 args=(quality,
                                                                                       range_, i, 'video'))})

        for key in self.downloaded_video_data_segments:
            self.downloaded_video_data_segments[key].start()
        self.last_time = time.time()
        print(f'Awaiting {len(self.downloaded_video_data_segments)} Video Download Threads... ', end='')
        self.assert_downloaded_all_video_data_segments()
        print(f'\033[38;2;0;255;0m[OK - Completed in {time.time()-self.last_time}]\033[0m', end='\n')

        # ------------------------------ audio download --------------------------- #
        audioquality = 'AUDIO_QUALITY_LOW' if "AUDIO_QUALITY_MEDIUM" not in self.audio_data else "AUDIO_QUALITY_MEDIUM"
        byte_segment_len = int(int(self.audio_data[audioquality]['contentLength'])/70)
        for i in range((int(self.audio_data[audioquality]['contentLength']) // byte_segment_len) + 1):
            range_ = f'{byte_segment_len * i + (0 if (i == 0) else 1)}-' \
                     f'{byte_segment_len * (i + 1)}'
            self.downloaded_audio_data_segments.update({range_: threading.Thread(target=self.download_data_segment,
                                                                                 args=(audioquality,
                                                                                       range_, i, 'audio'))})

        for key in self.downloaded_audio_data_segments:
            self.downloaded_audio_data_segments[key].start()
        self.last_time = time.time()
        print(f'Awaiting {len(self.downloaded_audio_data_segments)} Audio Download Threads... ', end='')
        self.assert_downloaded_all_audio_data_segments()
        print(f'\033[38;2;0;255;0m[OK - Completed in {time.time() - self.last_time}]\033[0m', end='\n')

        # compile
        self.last_time = time.time()
        print('Re-Compiling Video Segments... ', end='')
        output_video_data = self.compile_downloaded_segments(self.downloaded_video_data_segments)
        print(f'\033[38;2;0;255;0m[OK - Completed in {time.time() - self.last_time}]\033[0m', end='\n')

        self.last_time = time.time()
        print('Finished Re-Compiling Audio Segments... ', end='')
        output_audio_data = self.compile_downloaded_segments(self.downloaded_audio_data_segments)
        print(f'\033[38;2;0;255;0m[OK - Completed in {time.time() - self.last_time}]\033[0m', end='\n')

        # write output to file
        self.last_time = time.time()
        print('Writing Bytes To File... ', end='')
        with open(f'video.mp4', 'wb') as output:
            output.write(output_video_data)
        with open(f'audio.mp4', 'wb') as output:
            output.write(output_audio_data)
        print(f'\033[38;2;0;255;0m[OK - Completed in {time.time() - self.last_time}]\033[0m', end='\n')

        self.merge_audio_video()
        print(f'Finished Download in {time.time()-self.start_time} seconds.')
        input('\n\033[38;2;255;255;0m[Press Enter to Continue]\033[0m')

    def assert_downloaded_all_video_data_segments(self):
        while True:
            if any([(type(v[1]) is not bytes) for v in self.downloaded_video_data_segments.items()]):
                pass
            else:
                break

    def assert_downloaded_all_audio_data_segments(self):
        while True:
            if any([(type(v[1]) is not bytes) for v in self.downloaded_audio_data_segments.items()]):
                pass
            else:
                break

    def compile_downloaded_segments(self, d):
        raw_data = b''
        for key in d:
            raw_data += d[key]

        return raw_data

    def merge_audio_video(self):
        print('Multiplexing Audio And Video Data... ', end='')
        video_file = 'video.mp4'
        audio_file = 'audio.mp3'

        while ' ' in self.title:
            self.title = self.title.replace(' ', '_')
        self.title = "".join(x for x in self.title if x.isalnum() or x == '_')

        os.system(f'ffmpeg -i audio.mp4 audio.mp3 -hide_banner -loglevel error -preset {self.ffmpeg_preset}')
        os.system(f"ffmpeg -i {video_file} -i {audio_file}"
                  f" {self.title}{self.avalible_output_formats[self.output_filetype]} "
                  f"-hide_banner -loglevel error -preset {self.ffmpeg_preset} -tune film")
        os.remove('video.mp4');
        os.remove('audio.mp4');
        os.remove('audio.mp3');
        print(f'\033[38;2;0;255;0m[OK - Completed in {time.time() - self.last_time}]\033[0m', end='\n')

